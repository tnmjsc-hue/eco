"""Locked evaluation, including paired calendar moving-block bootstrap."""

from datetime import date, timedelta
import math
import numpy as np

from .core import COMPONENTS, WEIGHTS

MODEL_NAMES = ("core", "normalized_E7_only", "equal_weight_four_components", "normalized_price_group_only")
CORE_COMPONENTS = tuple(COMPONENTS)
REGIMES = (
    {
        "id": "pre_london",
        "label": "Before London/EIP-1559",
        "start": None,
        "end": "2021-08-04",
        "boundary": "before 2021-08-05",
    },
    {
        "id": "london_to_merge",
        "label": "London/EIP-1559 to Merge",
        "start": "2021-08-05",
        "end": "2022-09-14",
        "boundary": "2021-08-05 through 2022-09-14",
    },
    {
        "id": "post_merge_pre_dencun",
        "label": "Post-Merge before Dencun",
        "start": "2022-09-15",
        "end": "2024-03-12",
        "boundary": "2022-09-15 through 2024-03-12",
    },
    {
        "id": "post_dencun",
        "label": "Post-Dencun",
        "start": "2024-03-13",
        "end": None,
        "boundary": "on or after 2024-03-13",
    },
)


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


def _rank_average(values):
    """Average ranks, retaining ties so Spearman is deterministic without SciPy."""
    values = np.asarray(values, dtype=float)
    order = np.argsort(values, kind="stable")
    ranks = np.empty(len(values), dtype=float)
    i = 0
    while i < len(values):
        j = i + 1
        while j < len(values) and values[order[j]] == values[order[i]]:
            j += 1
        ranks[order[i:j]] = (i + 1 + j) / 2
        i = j
    return ranks


def spearman(x, y):
    """Tie-aware Spearman rank correlation, or null for an undefined pair."""
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    if len(x) != len(y) or len(x) < 2:
        return None
    rx, ry = _rank_average(x), _rank_average(y)
    sx, sy = np.std(rx), np.std(ry)
    if sx <= 0 or sy <= 0:
        return None
    return float(np.corrcoef(rx, ry)[0, 1])


def _component_score(row, component):
    return row["components"].get(component, {}).get("score")


def component_correlations(rows):
    """Pairwise Spearman correlations of causal normalized Core components.

    The returned matrix carries pairwise counts because nulls can occur outside
    the complete Core window. E2/NUPL is deliberately absent: it is a derived
    diagnostic of E7 and is not a Core voting component.
    """
    result = {left: {} for left in CORE_COMPONENTS}
    for left in CORE_COMPONENTS:
        for right in CORE_COMPONENTS:
            pairs = [(_component_score(row, left), _component_score(row, right)) for row in rows]
            pairs = [(x, y) for x, y in pairs if x is not None and y is not None]
            x, y = zip(*pairs) if pairs else ((), ())
            result[left][right] = {"rho": 1.0 if left == right and pairs else spearman(x, y),
                                   "n": len(pairs)}
    return {"method": "spearman_on_causal_normalized_scores", "components": list(CORE_COMPONENTS),
            "pairwise_complete": True, "matrix": result}


def _model_scores(row, selected=None):
    """Return the frozen Core weighted composite for an ablation selection."""
    if selected is None or tuple(selected) == CORE_COMPONENTS:
        # Preserve the published engine result bit-for-bit for the full model.
        if row.get("score") is not None:
            return float(row["score"])
        selected = CORE_COMPONENTS
    else:
        selected = tuple(selected)
    if not selected:
        return None
    values = [_component_score(row, component) for component in selected]
    if any(value is None for value in values):
        return None
    total_weight = sum(WEIGHTS[component] for component in selected)
    return float(sum(value * WEIGHTS[component] for component, value in zip(selected, values)) / total_weight)


def _score_matrix(rows):
    return np.array([
        [_model_scores(row), _component_score(row, "E7"),
         sum(_component_score(row, k) for k in CORE_COMPONENTS) / 4,
         sum(_component_score(row, k) for k in ("E1", "E5", "E6")) / 3]
        for row in rows
    ]).T


def _ablation_score_names():
    return {
        "full_core": CORE_COMPONENTS,
        "without_E1": tuple(k for k in CORE_COMPONENTS if k != "E1"),
        "without_E5": tuple(k for k in CORE_COMPONENTS if k != "E5"),
        "without_E6": tuple(k for k in CORE_COMPONENTS if k != "E6"),
        "without_E7": tuple(k for k in CORE_COMPONENTS if k != "E7"),
        "price_group_only": ("E1", "E5", "E6"),
        "valuation_group_only": ("E7",),
    }


def ablation_analysis(rows, y, bootstrap_deltas=None):
    """Leave-one-component/group-out analysis on the frozen primary window.

    The original component weights are retained and renormalized only over
    selected components. This is a descriptive analysis; it never changes the
    official Core score or the protocol success decision.
    """
    names = _ablation_score_names()
    scores = {name: np.asarray([_model_scores(row, selected) for row in rows], dtype=float)
              for name, selected in names.items()}
    core_ap = ap(y, scores["full_core"])
    result = {}
    for name, selected in names.items():
        value = statistics(y, scores[name])
        result[name] = {"components": list(selected), "statistics": value,
                        "ap_delta_vs_core": None if name == "full_core" else value["average_precision"] - core_ap}
    if bootstrap_deltas is not None:
        # These deltas use the same calendar block weights as the primary
        # baseline comparison, so uncertainty remains paired and reproducible.
        ci = {}
        for name in scores:
            if name == "full_core":
                continue
            deltas = bootstrap_deltas.get(name, [])
            if deltas:
                bounds = np.quantile(deltas, [.025, .975], method="linear")
                ci[name] = {"lower_95": float(bounds[0]), "upper_95": float(bounds[1]),
                            "valid_replicates": len(deltas)}
        result["confidence_intervals"] = ci
    return {"method": "frozen_component_weights_renormalized_after_selection",
            "selection_is_descriptive": True, "models": result}


def _regime_for(day):
    for regime in REGIMES:
        if ((regime["start"] is None or day >= regime["start"])
                and (regime["end"] is None or day <= regime["end"])):
            return regime
    raise ValueError(f"date outside regime definitions: {day}")


def regime_analysis(rows, label):
    """Report Core and locked baselines by Ethereum protocol-era regime."""
    groups = {regime["id"]: [] for regime in REGIMES}
    for row in rows:
        groups[_regime_for(row["date"])["id"]].append(row)
    result = {}
    for regime in REGIMES:
        selected = groups[regime["id"]]
        y = np.asarray([label[row["date"]] for row in selected], dtype=int)
        scores = _score_matrix(selected)
        models = {name: statistics(y, score) for name, score in zip(MODEL_NAMES, scores)} if selected else {}
        result[regime["id"]] = {
            "label": regime["label"], "start": regime["start"], "end": regime["end"],
            "boundary": regime["boundary"], "n": len(selected),
            "positive_labels": int(y.sum()) if selected else 0,
            "prevalence": float(y.mean()) if selected else None, "models": models,
        }
    return {"method": "observation_date_protocol_era", "label_assignment": "future_drawdown_at_observation_date",
            "boundaries": [{k: regime[k] for k in ("id", "label", "start", "end", "boundary")} for regime in REGIMES],
            "regimes": result}


def evaluate(rows):
    label = labels(rows)
    end = date.fromisoformat(rows[-1]["date"]) - timedelta(days=365)
    chosen = [r for r in rows if "2020-01-01" <= r["date"] <= end.isoformat()
              and r["score"] is not None and r["date"] in label]
    if len(chosen) < 90:
        raise ValueError("insufficient completed evaluation horizon")
    y = np.array([label[r["date"]] for r in chosen])
    scores = _score_matrix(chosen)
    stats = {name: statistics(y, s) for name, s in zip(MODEL_NAMES, scores)}
    ablation_names = _ablation_score_names()
    ablation_scores = {name: np.asarray([_model_scores(row, selected) for row in chosen], dtype=float)
                       for name, selected in ablation_names.items()}
    ablation_bootstrap_deltas = {name: [] for name in ablation_names if name != "full_core"}
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
            core_value = values[0]
            for name, ablated_score in ablation_scores.items():
                if name == "full_core":
                    continue
                ablated_value = ap(y, ablated_score, weights)
                if ablated_value is not None:
                    ablation_bootstrap_deltas[name].append(core_value - ablated_value)
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
    complete_rows = [r for r in rows if r.get("score") is not None]
    return {"protocol": "core-v0.1.0-protocol-1", "status": "evaluated_reconstructed_only",
            "start": chosen[0]["date"], "end": chosen[-1]["date"], "n": len(chosen),
            "positive_labels": int(y.sum()), "prevalence": float(y.mean()),
            "statistics": stats, "comparisons": comparisons, "year_folds": folds,
            "sensitivity_only": sensitivities,
            "correlations": component_correlations(complete_rows),
            "ablation": ablation_analysis(chosen, y, ablation_bootstrap_deltas),
            "regime_analysis": regime_analysis(chosen, label),
            "bootstrap": {"method": "paired_moving_block", "block_calendar_days": 90,
                          "replicates": 10000, "valid_replicates": len(delta), "seed": 20261003},
            "success": all(c["pass"] for c in comparisons.values()),
            "limitations": ["current-vintage reconstructed history", "unknown historical availability",
                            "not an investment recommendation", "0-100 score is not a probability"]}
