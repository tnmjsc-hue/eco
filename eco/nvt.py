"""Frozen E9 candidate mathematics and descriptive research, outside Core."""

from collections import Counter, deque
from datetime import date, timedelta
import math

import numpy as np

from .core import Normalizer
from .research import REGIMES, _regime_for, ap, labels, spearman, statistics

VERSION = "e9-nvt-candidate-v0.1.0"
PROTOCOL = "e9-nvt-v0.1.0-protocol-1"
METRICS = ("CapMrktCurUSD", "TxTfrValAdjUSD")


def _value(value, allow_zero=False):
    if value is None:
        return None
    if isinstance(value, bool):
        raise ValueError("E9 numeric input cannot be boolean")
    try:
        number = float(value)
    except (ValueError, TypeError):
        raise ValueError("invalid E9 numeric input") from None
    if not math.isfinite(number) or number < 0 or (number == 0 and not allow_zero):
        raise ValueError("E9 input must be finite, positive (transfer can be zero), or null")
    return number


def compute_nvt(rows, end=None):
    """Compute ln(cap/SMA90(adjusted transfer USD)) on complete UTC windows.

    Historical provider availability is not inferred here. The CLI requires a
    verified licensed snapshot and labels output reconstructed research only.
    """
    source = {}
    for row in rows:
        if row.get("asset") != "eth" or set(row.get("metrics", {})) != set(METRICS):
            raise ValueError("E9 requires ETH CapMrktCurUSD/TxTfrValAdjUSD; no metric substitution")
        day = date.fromisoformat(row["observation_date"])
        if day.isoformat() != row["observation_date"] or day in source:
            raise ValueError("duplicate or invalid E9 observation date")
        source[day] = (_value(row["metrics"][METRICS[0]]),
                       _value(row["metrics"][METRICS[1]], allow_zero=True))
    if not source:
        raise ValueError("empty E9 dataset")
    first, last_source = min(source), max(source)
    last = date.fromisoformat(end) if isinstance(end, str) else end or last_source
    if last < last_source:
        raise ValueError("E9 end precedes source observations")
    transfers = deque(maxlen=90)
    normalizer = Normalizer()
    output = []
    day = first
    while day <= last:
        cap, transfer = source.get(day, (None, None))
        transfers.append(transfer)
        complete = len(transfers) == 90 and all(v is not None for v in transfers)
        # Scaling avoids overflow of the sum and underflow of every summand.
        scale = max(transfers) if complete else None
        mean = (scale * (math.fsum(v / scale for v in transfers) / 90) if scale else 0.0) if complete else None
        if cap is None:
            raw, reason = None, "missing_market_cap"
        elif mean is None:
            raw, reason = None, "insufficient_history_or_calendar_gap"
        elif mean <= 0:
            raw, reason = None, "nonpositive_transfer_mean"
        else:
            raw, reason = math.log(cap) - math.log(mean), None
        normalized = normalizer.compute(day, raw)
        output.append({"date": day.isoformat(), "market_cap_usd": cap,
                       "adjusted_transfer_usd": transfer, "sma90_adjusted_transfer_usd": mean,
                       "raw": raw, "raw_reason": reason, "score": normalized["score"],
                       "score_reason": normalized["reason"], "normalizer": normalized,
                       "source_row_present": day in source})
        day += timedelta(days=1)
    return output


def _daily_unique(rows):
    days = [date.fromisoformat(row["date"]) for row in rows]
    if not days or any(right - left != timedelta(days=1) for left, right in zip(days, days[1:])):
        raise ValueError("E9 evaluation requires ordered, unique, continuous calendar rows")


def evaluate_nvt(core_rows, nvt_rows, primary_start="2020-01-01", replicates=10000):
    """Descriptive E9-only/composite comparisons with paired calendar blocks.

    A reused Core holdout cannot establish out-of-sample incremental utility.
    Reduced bootstrap replicates are only for fixtures; production CLI fixes
    the frozen count at 10000 and records it in the private result.
    """
    _daily_unique(core_rows)
    _daily_unique(nvt_rows)
    if not isinstance(replicates, int) or replicates < 1:
        raise ValueError("invalid E9 bootstrap replicate count")
    candidates = {row["date"]: row for row in nvt_rows}
    future = labels(core_rows)

    def component(row, metric):
        item = row["components"].get(metric)
        return item.get("score") if isinstance(item, dict) else item

    chosen = [(row, candidates[row["date"]]) for row in core_rows
              if row["date"] >= primary_start and row["date"] in future
              and row.get("score") is not None and row["date"] in candidates
              and candidates[row["date"]].get("score") is not None
              and all(component(row, key) is not None for key in ("E1", "E5", "E6", "E7"))]
    if len(chosen) < 90:
        raise ValueError("insufficient overlapping completed E9 evaluation dates")
    y = [future[row["date"]] for row, _ in chosen]
    price = [sum(component(row, key) for key in ("E1", "E5", "E6")) / 3 for row, _ in chosen]
    e7 = [component(row, "E7") for row, _ in chosen]
    e9 = [candidate["score"] for _, candidate in chosen]
    scores = {"nvt_only": e9, "core": [row["score"] for row, _ in chosen],
              "normalized_E7_only": e7, "normalized_price_group_only": price,
              "experimental_with_E9": [.5*p + .25*v + .25*n for p, v, n in zip(price, e7, e9)],
              "experimental_without_E7": [(2*p + n)/3 for p, n in zip(price, e9)],
              "experimental_without_price_group": [(v + n)/2 for v, n in zip(e7, e9)]}
    if any(not math.isfinite(v) or not 0 <= v <= 100 for values in scores.values() for v in values):
        raise ValueError("E9 evaluation score must be finite and in 0..100")
    comparisons = {f"nvt_only_vs_{baseline}": ("nvt_only", baseline)
                   for baseline in ("core", "normalized_E7_only", "normalized_price_group_only")}
    comparisons.update({f"with_E9_vs_{baseline}": ("experimental_with_E9", baseline)
                        for baseline in ("core", "normalized_E7_only", "normalized_price_group_only",
                                         "experimental_without_E7", "experimental_without_price_group")})
    offsets = np.array([(date.fromisoformat(row["date"]) - date.fromisoformat(chosen[0][0]["date"])).days
                        for row, _ in chosen])
    length = int(offsets[-1] + 1)
    generator = np.random.default_rng(20261003)
    deltas = {name: [] for name in comparisons}
    for _ in range(replicates):
        starts = generator.integers(0, length - 90 + 1, size=math.ceil(length / 90))
        sampled = (starts[:, None] + np.arange(90)).ravel()[:length]
        weights = np.bincount(sampled, minlength=length)[offsets]
        aps = {name: ap(y, values, weights) for name, values in scores.items()}
        if all(value is not None for value in aps.values()):
            for name, (left, right) in comparisons.items():
                deltas[name].append(aps[left] - aps[right])
    intervals = {}
    for name, values in deltas.items():
        bounds = np.quantile(values, [.025, .975], method="linear") if values else (None, None)
        intervals[name] = {"lower_95": float(bounds[0]) if values else None,
                           "upper_95": float(bounds[1]) if values else None, "valid_replicates": len(values)}
    regimes = {}
    for regime in REGIMES:
        indices = [i for i, (row, _) in enumerate(chosen) if _regime_for(row["date"])["id"] == regime["id"]]
        ry = [y[i] for i in indices]
        regimes[regime["id"]] = {"start": regime["start"], "end": regime["end"],
                                 "n": len(indices), "positive_labels": sum(ry),
                                 "models": {name: statistics(ry, [values[i] for i in indices])
                                            for name, values in scores.items()} if indices else {}}
    raw_dates = [row["date"] for row in nvt_rows if row["raw"] is not None]
    score_dates = [row["date"] for row in nvt_rows if row["score"] is not None]
    return {"methodology_version": VERSION, "protocol": PROTOCOL,
            "status": "exploratory_reconstructed_only", "n": len(chosen),
            "start": chosen[0][0]["date"], "end": chosen[-1][0]["date"],
            "positive_labels": sum(y), "prevalence": sum(y)/len(y),
            "coverage": {"calendar_rows": len(nvt_rows), "raw_rows": len(raw_dates),
                         "normalized_rows": len(score_dates), "first_raw_date": raw_dates[0] if raw_dates else None,
                         "first_score_date": score_dates[0] if score_dates else None,
                         "raw_reasons": dict(Counter(row["raw_reason"] for row in nvt_rows if row["raw_reason"])),
                         "score_reasons": dict(Counter(row["score_reason"] for row in nvt_rows if row["score_reason"]))},
            "statistics": {name: statistics(y, values) for name, values in scores.items()},
            "spearman": {name: {"rho": spearman(e9, values), "n": len(y)}
                         for name, values in scores.items() if name != "nvt_only"},
            "ablation": {"remove_E9": "core", "remove_E7": "experimental_without_E7",
                         "remove_price_group": "experimental_without_price_group",
                         "weight_policy": "restore_Core_for_remove_E9; renormalize_remaining_flat_weights_for_other_ablations"},
            "bootstrap_deltas": intervals,
            "bootstrap": {"method": "paired_moving_block", "block_calendar_days": 90,
                          "replicates": replicates, "seed": 20261003},
            "regime_analysis": {"method": "observation_date_protocol_era", "regimes": regimes},
            "decision": "research_only_requires_new_holdout_or_prospective_vintage_and_public_rights",
            "public_release_allowed": False,
            "limitations": ["reuses_core_primary_holdout_descriptively", "unknown_historical_source_availability",
                            "provider_revisions_and_hourly_netting_bias", "L1_native_ETH_is_not_total_Ethereum_L2_activity",
                            "0-100_score_is_not_probability"]}
