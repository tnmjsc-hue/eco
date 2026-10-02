"""Locked evaluation, including paired calendar moving-block bootstrap."""

from datetime import date, timedelta
import math
import numpy as np

MODEL_NAMES = ("core", "normalized_E7_only", "equal_weight_four_components", "normalized_price_group_only")


def labels(rows, horizon=365, drawdown=-.5):
    result = {}
    for i in range(len(rows) - horizon):
        current = rows[i]["price_usd"]
        future = [r["price_usd"] for r in rows[i + 1:i + horizon + 1]]
        if current is not None and all(p is not None for p in future):
            result[rows[i]["date"]] = int(min(future) <= current * (1 + drawdown))
    return result


def ap(y, scores, weights=None):
    """Non-interpolated AP, treating equal score values as one threshold."""
    y = np.asarray(y)
    s = np.asarray(scores)
    w = np.ones(len(y)) if weights is None else np.asarray(weights)
    order = np.argsort(-s, kind="stable")
    ranked = s[order]
    tp = np.cumsum(y[order] * w[order])
    total = np.cumsum(w[order])
    ends = np.r_[np.flatnonzero(ranked[1:] != ranked[:-1]), len(y) - 1]
    if tp[-1] == 0:
        return None
    recall = tp[ends] / tp[-1]
    precision = np.divide(tp[ends], total[ends], out=np.zeros(len(ends)), where=total[ends] > 0)
    return float(np.sum(np.diff(np.r_[0., recall]) * precision))


def auc(y, scores):
    positive = sum(y)
    negative = len(y) - positive
    if not positive or not negative:
        return None
    order = np.argsort(scores, kind="stable")
    ranked_scores = np.asarray(scores)[order]
    ranks = np.empty(len(y), dtype=float)
    i = 0
    while i < len(y):
        j = i + 1
        while j < len(y) and ranked_scores[j] == ranked_scores[i]:
            j += 1
        ranks[order[i:j]] = (i + 1 + j) / 2
        i = j
    return float((ranks[np.asarray(y) == 1].sum() - positive * (positive + 1) / 2) / (positive * negative))


def statistics(y, scores):
    prediction = np.asarray(scores) >= 90
    tp = int(np.sum(prediction & (np.asarray(y) == 1)))
    return {"average_precision": ap(y, scores), "roc_auc": auc(y, scores),
            "precision_at_90": tp / int(prediction.sum()) if prediction.sum() else None,
            "recall_at_90": tp / sum(y) if sum(y) else None,
            "predictions_at_90": int(prediction.sum())}


def evaluate(rows):
    label = labels(rows)
    end = date.fromisoformat(rows[-1]["date"]) - timedelta(days=365)
    chosen = [r for r in rows if "2020-01-01" <= r["date"] <= end.isoformat()
              and r["score"] is not None and r["date"] in label]
    if len(chosen) < 90:
        raise ValueError("insufficient completed evaluation horizon")
    y = np.array([label[r["date"]] for r in chosen])
    scores = np.array([[r["score"], r["components"]["E7"]["score"],
                        sum(r["components"][k]["score"] for k in ("E1", "E5", "E6", "E7")) / 4,
                        sum(r["components"][k]["score"] for k in ("E1", "E5", "E6")) / 3] for r in chosen]).T
    stats = {name: statistics(y, s) for name, s in zip(MODEL_NAMES, scores)}
    offsets = [(date.fromisoformat(r["date"]) - date.fromisoformat(chosen[0]["date"])).days for r in chosen]
    # Sample calendar blocks before filtering evaluated dates, not adjacent surviving rows.
    length = offsets[-1] + 1
    offsets = np.asarray(offsets)
    generator = np.random.default_rng(20261003)
    delta = []
    block_count = math.ceil(length / 90)
    for _ in range(10000):
        starts = generator.integers(0, length - 90 + 1, size=block_count)
        sampled = (starts[:, None] + np.arange(90)).ravel()[:length]
        weights = np.bincount(sampled, minlength=length)[offsets]
        values = [ap(y, s, weights) for s in scores]
        if all(v is not None for v in values):
            delta.append([values[0] - v for v in values[1:]])
    if not delta:
        raise ValueError("bootstrap contains no positive-label replicates")
    delta = np.asarray(delta)
    comparisons = {}
    folds = {}
    for year in sorted({r["date"][:4] for r in chosen}):
        indices = np.array([r["date"].startswith(year) for r in chosen])
        yy = y[indices]
        if sum(yy):
            folds[year] = {name: ap(yy, s[indices]) for name, s in zip(MODEL_NAMES, scores)}
    for j, name in enumerate(MODEL_NAMES[1:]):
        bounds = np.quantile(delta[:, j], [.025, .975], method="linear")
        positive_years = sum(f["core"] > f[name] for f in folds.values())
        comparisons[name] = {"ap_delta": stats["core"]["average_precision"] - stats[name]["average_precision"],
                             "lower_95": float(bounds[0]), "upper_95": float(bounds[1]),
                             "positive_years": positive_years, "eligible_years": len(folds),
                             "pass": bool(bounds[0] > 0 and positive_years > len(folds) / 2)}
    sensitivities = {}
    for horizon, threshold in ((180, -.5), (365, -.3)):
        alternate = labels(rows, horizon, threshold)
        eligible = [r for r in chosen if r["date"] in alternate]
        yy = [alternate[r["date"]] for r in eligible]
        sensitivities[f"{horizon}d_{threshold}"] = {"n": len(eligible), "prevalence": sum(yy) / len(yy),
                                                 **statistics(yy, [r["score"] for r in eligible])}
    return {"protocol": "core-v0.1.0-protocol-1", "status": "evaluated_reconstructed_only",
            "start": chosen[0]["date"], "end": chosen[-1]["date"], "n": len(chosen),
            "positive_labels": int(y.sum()), "prevalence": float(y.mean()),
            "statistics": stats, "comparisons": comparisons, "year_folds": folds,
            "sensitivity_only": sensitivities,
            "bootstrap": {"method": "paired_moving_block", "block_calendar_days": 90,
                          "replicates": 10000, "valid_replicates": len(delta), "seed": 20261003},
            "success": all(c["pass"] for c in comparisons.values()),
            "limitations": ["current-vintage reconstructed history", "unknown historical availability",
                            "not an investment recommendation", "0-100 score is not a probability"]}
