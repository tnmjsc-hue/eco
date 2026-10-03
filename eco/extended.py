"""Independent research candidates kept outside the frozen Core engine."""

from collections import deque
from datetime import date, timedelta
import math

import numpy as np

from .core import Normalizer
from .research import MODEL_NAMES, REGIMES, _regime_for, ap, labels, spearman, statistics


def _fee_value(row):
    if row is None:
        return None
    metrics = row.get("metrics", {})
    value = metrics.get("FeeTotNtv")
    if value is None:
        return None
    try:
        value = float(value)
    except (TypeError, ValueError):
        raise ValueError("FeeTotNtv must be finite and non-negative, or null") from None
    if not math.isfinite(value) or value < 0:
        raise ValueError("FeeTotNtv must be finite and non-negative, or null")
    return value


def compute_fee_activity(rows, end=None):
    """Compute exploratory E4 raw and causal normalized series.

    Calendar gaps stay as null observations. This function does not alter the
    frozen Core score or publish a candidate release.
    """
    by_date = {}
    for row in rows:
        if row.get("asset") != "eth":
            raise ValueError("E4 candidate requires asset=eth")
        day = date.fromisoformat(row["observation_date"])
        if day in by_date:
            raise ValueError("duplicate E4 observation date")
        by_date[day] = _fee_value(row)
    if not by_date:
        raise ValueError("empty E4 candidate dataset")
    first, last_source = min(by_date), max(by_date)
    last = date.fromisoformat(end) if isinstance(end, str) else end or last_source
    if last < last_source:
        raise ValueError("end precedes source observations")

    fees = deque(maxlen=365)
    normalizer = Normalizer()
    output = []
    day = first
    while day <= last:
        fee = by_date.get(day)
        fees.append(fee)

        def rolling_mean(window):
            if len(fees) < window:
                return None
            values = list(fees)[-window:]
            if any(value is None for value in values):
                return None
            return math.fsum(values) / window

        sma30 = rolling_mean(30)
        sma365 = rolling_mean(365)
        if sma30 is None or sma365 is None:
            raw = None
            raw_reason = "insufficient_history_or_calendar_gap"
        elif sma30 <= 0 or sma365 <= 0:
            raw = None
            raw_reason = "nonpositive_rolling_mean"
        else:
            raw = math.log(sma30 / sma365)
            raw_reason = None
        normalized = normalizer.compute(day, raw)
        output.append({
            "date": day.isoformat(),
            "fee_tot_ntv": fee,
            "sma30": sma30,
            "sma365": sma365,
            "raw": raw,
            "raw_reason": raw_reason,
            "score": normalized["score"],
            "score_reason": normalized["reason"],
            "normalizer": normalized,
            "source_row_present": day in by_date,
        })
        day += timedelta(days=1)
    return output


def evaluate_fee_activity(core_rows, fee_rows, primary_start="2020-01-01"):
    """Run a descriptive E4 comparison against the frozen Core baselines.

    The comparison intentionally reuses the reconstructed Core primary window
    and therefore cannot claim incremental utility. A new holdout or
    prospective vintage is required before a candidate success decision.
    """
    fee_by_date = {row["date"]: row for row in fee_rows}

    def component_score(row, component):
        value = row["components"].get(component)
        return value.get("score") if isinstance(value, dict) else value

    future_labels = labels(core_rows)
    chosen = []
    for row in core_rows:
        fee = fee_by_date.get(row["date"])
        if (row["date"] >= primary_start and row["date"] in future_labels
                and row.get("score") is not None and fee and fee.get("score") is not None
                and all(component_score(row, k) is not None for k in ("E1", "E5", "E6", "E7"))):
            chosen.append((row, fee))
    if len(chosen) < 90:
        raise ValueError("insufficient overlapping completed E4 evaluation dates")
    y = [future_labels[row["date"]] for row, _ in chosen]
    scores = {
        "fee_activity": [fee["score"] for _, fee in chosen],
        "core": [row["score"] for row, _ in chosen],
        "normalized_E7_only": [component_score(row, "E7") for row, _ in chosen],
        "normalized_price_group_only": [sum(component_score(row, k) for k in ("E1", "E5", "E6")) / 3 for row, _ in chosen],
    }
    stats = {name: statistics(y, values) for name, values in scores.items()}
    correlations = {name: {"rho": spearman(scores["fee_activity"], values), "n": len(values)}
                    for name, values in scores.items() if name != "fee_activity"}

    offsets = np.asarray([(date.fromisoformat(row["date"]) - date.fromisoformat(chosen[0][0]["date"])).days
                          for row, _ in chosen])
    length = int(offsets[-1] + 1)
    generator = np.random.default_rng(20261003)
    block_count = math.ceil(length / 90)
    deltas = {name: [] for name in scores if name != "fee_activity"}
    for _ in range(10000):
        starts = generator.integers(0, length - 90 + 1, size=block_count)
        sampled = (starts[:, None] + np.arange(90)).ravel()[:length]
        weights = np.bincount(sampled, minlength=length)[offsets]
        candidate_ap = ap(y, scores["fee_activity"], weights)
        if candidate_ap is None:
            continue
        values = {name: ap(y, model, weights) for name, model in scores.items() if name != "fee_activity"}
        if all(value is not None for value in values.values()):
            for name, value in values.items():
                deltas[name].append(candidate_ap - value)
    intervals = {}
    for name, values in deltas.items():
        if values:
            bounds = np.quantile(values, [.025, .975], method="linear")
            intervals[name] = {"lower_95": float(bounds[0]), "upper_95": float(bounds[1]),
                               "valid_replicates": len(values)}

    regimes = {}
    for regime in REGIMES:
        selected = [(row, fee) for row, fee in chosen if _regime_for(row["date"])["id"] == regime["id"]]
        regime_y = [future_labels[row["date"]] for row, _ in selected]
        regimes[regime["id"]] = {
            "label": regime["label"], "start": regime["start"], "end": regime["end"],
            "n": len(selected), "positive_labels": int(sum(regime_y)) if selected else 0,
            "models": ({
                "fee_activity": statistics(regime_y, [fee["score"] for _, fee in selected]),
                "core": statistics(regime_y, [row["score"] for row, _ in selected]),
            } if selected else {}),
        }
    return {
        "protocol": "e4-fee-v0.1.0-protocol-1",
        "status": "exploratory_reconstructed_only",
        "n": len(chosen), "start": chosen[0][0]["date"], "end": chosen[-1][0]["date"],
        "positive_labels": int(sum(y)), "prevalence": float(sum(y) / len(y)),
        "statistics": stats, "spearman": correlations, "bootstrap_deltas": intervals,
        "regime_analysis": {"method": "observation_date_protocol_era", "regimes": regimes},
        "bootstrap": {"method": "paired_moving_block", "block_calendar_days": 90,
                      "replicates": 10000, "seed": 20261003},
        "decision": "insufficient_evidence_for_incremental_utility; requires_new_holdout_or_prospective_vintage",
        "limitations": ["reuses_core_primary_holdout_descriptively", "unknown_historical_source_availability",
                        "not_an_investment_recommendation", "0-100_score_is_not_probability"],
    }
