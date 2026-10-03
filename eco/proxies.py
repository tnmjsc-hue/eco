"""Three frozen, named ETH research proxies; never an official composite."""
from collections import Counter, deque
from datetime import date, timedelta
import math
import numpy as np
from .core import Normalizer
from .research import labels, statistics, spearman, ap, REGIMES, _regime_for

VERSION = "network-proxies-v0.1.0"
PROTOCOL = "network-proxies-v0.1.0-protocol-1"
ORIGIN = date(2015, 7, 30)
METRICS = ("exchange_share", "address_activity", "value_per_transfer")
INPUTS = ("AdrActCnt", "AdrBalCnt", "CapMrktCurUSD", "SplyCur", "SplyExNtv", "TxTfrCnt")
ZERO_ALLOWED = {"AdrActCnt", "SplyExNtv", "TxTfrCnt"}

def _number(value, metric):
    if value is None:
        return None
    if isinstance(value, bool):
        raise ValueError("boolean is not a source number")
    try:
        result = float(value)
    except (ValueError, TypeError):
        raise ValueError("invalid proxy numeric input") from None
    if not math.isfinite(result) or result < 0 or (result == 0 and metric not in ZERO_ALLOWED):
        raise ValueError("proxy input must be finite and valid for its unit")
    if metric in {"AdrActCnt", "AdrBalCnt", "TxTfrCnt"} and not result.is_integer():
        raise ValueError("count must be an integer")
    return result

def compute_proxies(rows, end=None):
    by_date = {}
    for row in rows:
        day = date.fromisoformat(row["observation_date"])
        if row.get("asset") != "eth" or day in by_date or set(row["metrics"]) != set(INPUTS):
            raise ValueError("wrong asset, duplicate date or substituted source metrics")
        values = {m: _number(row["metrics"][m], m) for m in INPUTS}
        if values["SplyExNtv"] is not None and values["SplyCur"] is not None and values["SplyExNtv"] > values["SplyCur"]:
            raise ValueError("exchange supply exceeds current supply")
        by_date[day] = (values, row.get("metric_status", {}))
    if not by_date or min(by_date) != ORIGIN:
        raise ValueError("frozen proxy origin is required")
    last = date.fromisoformat(end) if end else max(by_date)
    if last < ORIGIN or last < max(by_date):
        raise ValueError("end excludes source observations")
    normalizers = {m: Normalizer() for m in METRICS}
    windows = {"exchange_share": deque(maxlen=30), "address_activity": deque(maxlen=30),
               "value_per_transfer": deque(maxlen=90)}
    flag_windows = {m: deque(maxlen=w.maxlen) for m, w in windows.items()}
    output = []
    day = ORIGIN
    while day <= last:
        values, status = by_date.get(day, ({m: None for m in INPUTS}, {}))
        pairs = {"exchange_share": ("SplyExNtv", "SplyCur"), "address_activity": ("AdrActCnt", "AdrBalCnt"),
                 "value_per_transfer": ("TxTfrCnt", "CapMrktCurUSD")}
        components = {}
        for metric, (numerator, denominator) in pairs.items():
            a, b = values[numerator], values[denominator]
            sample = a / b if metric == "exchange_share" and a is not None and b is not None else a if metric != "exchange_share" else None
            window = windows[metric]; window.append(sample)
            flags = {str(status[m]["status"]) for m in (numerator, denominator)
                     if status.get(m, {}).get("status") is not None}
            flag_windows[metric].append(flags)
            reason, value = None, None
            if len(window) < window.maxlen:
                reason = "feature_warmup"
            elif any(v is None for v in window) or (metric != "exchange_share" and b is None):
                reason = "missing_input_or_window"
            else:
                mean = math.fsum(v / window.maxlen for v in window)
                if mean <= 0:
                    reason = "nonpositive_log_argument"
                else:
                    value = mean if metric == "exchange_share" else mean / b if metric == "address_activity" else b / mean
            raw = math.log(value) if value is not None and value > 0 else None
            if raw is not None and not math.isfinite(raw):
                raise ValueError("proxy arithmetic overflow")
            normalized = normalizers[metric].compute(day, raw)
            components[metric] = {"raw": raw, "value": value, "score": normalized["score"],
                                  "raw_reason": reason, "score_reason": normalized["reason"],
                                  "source_flags": sorted(set().union(*flag_windows[metric]))}
        output.append({"date": day.isoformat(), "source_row_present": day in by_date, "metrics": components})
        day += timedelta(days=1)
    return output

def coverage(rows):
    result = {}
    for metric in METRICS:
        valid = [r["date"] for r in rows if r["metrics"][metric]["score"] is not None]
        raw = [r["date"] for r in rows if r["metrics"][metric]["raw"] is not None]
        result[metric] = {"calendar_rows": len(rows), "raw_rows": len(raw), "normalized_rows": len(valid),
                          "first_raw_date": raw[0] if raw else None, "first_score_date": valid[0] if valid else None,
                          "last_score_date": valid[-1] if valid else None,
                          "raw_reasons": dict(Counter(r["metrics"][metric]["raw_reason"] for r in rows if r["metrics"][metric]["raw_reason"])),
                          "score_reasons": dict(Counter(r["metrics"][metric]["score_reason"] for r in rows if r["metrics"][metric]["score_reason"])),
                          "source_flags": dict(Counter(flag for r in rows for flag in r["metrics"][metric]["source_flags"]))}
    return result

def evaluate_proxies(core_rows, proxy_rows, replicates=10000):
    # Same completed dates for all three; no threshold/weight/direction tuning.
    for rows in (core_rows, proxy_rows):
        days = [date.fromisoformat(r["date"]) for r in rows]
        if not days or any(b-a != timedelta(days=1) for a,b in zip(days, days[1:])):
            raise ValueError("evaluation requires continuous unique daily rows")
    if not isinstance(replicates, int) or replicates < 1:
        raise ValueError("invalid bootstrap replicates")
    candidates = {r["date"]: r for r in proxy_rows}
    future = labels(core_rows)
    chosen = [r for r in core_rows if r["date"] >= "2020-01-01" and r["date"] in future
              and r["score"] is not None and r["date"] in candidates
              and all(candidates[r["date"]]["metrics"][m]["score"] is not None for m in METRICS)]
    if len(chosen) < 90:
        raise ValueError("insufficient completed overlapping proxy evaluation dates")
    def component(row, metric):
        item = row["components"][metric]
        return item.get("score") if isinstance(item, dict) else item
    y = [future[r["date"]] for r in chosen]
    scores = {"core": [r["score"] for r in chosen],
              "normalized_E7_only": [component(r, "E7") for r in chosen],
              "normalized_price_group_only": [sum(component(r, m) for m in ("E1", "E5", "E6"))/3 for r in chosen]}
    for metric in METRICS:
        scores[metric] = [candidates[r["date"]]["metrics"][metric]["score"] for r in chosen]
        scores[f"with_{metric}"] = [.75*c + .25*p for c,p in zip(scores["core"], scores[metric])]
    if any(v is None or not math.isfinite(v) or not 0 <= v <= 100 for s in scores.values() for v in s):
        raise ValueError("invalid evaluation score")
    comparisons = {f"{m}_vs_core": (m,"core") for m in METRICS}
    comparisons.update({f"with_{m}_vs_{b}": (f"with_{m}",b) for m in METRICS
                        for b in ("core", "normalized_E7_only", "normalized_price_group_only")})
    # Sort fixed score vectors once. Equal scores are grouped exactly as research.ap.
    plans = {}
    labels_array = np.asarray(y, dtype=float)
    for name, values in scores.items():
        array = np.asarray(values); order = np.argsort(-array, kind="stable")
        ends = np.r_[np.flatnonzero(np.diff(array[order]) != 0), len(array)-1]
        plans[name] = (order, ends)
    def weighted_aps(weights):
        positive = float(np.sum(weights * labels_array))
        if positive <= 0:
            return None
        result = {}
        for name, (order, ends) in plans.items():
            w = weights[order]; tp = np.cumsum(w * labels_array[order])[ends]; total = np.cumsum(w)[ends]
            increments = np.diff(np.r_[0.,tp])
            result[name] = float(np.sum(np.divide(tp, total, out=np.zeros_like(tp), where=total > 0) * increments) / positive)
        return result
    # Independently cross-check optimized bootstrap AP against the baseline function.
    check = weighted_aps(np.ones(len(y)))
    if check is None or any(abs(check[n] - ap(y, v)) > 1e-12 for n,v in scores.items()):
        raise ValueError("bootstrap AP disagrees with evaluation AP")
    offsets = np.array([(date.fromisoformat(r["date"])-date.fromisoformat(chosen[0]["date"])).days for r in chosen])
    length = int(offsets[-1]+1); rng = np.random.default_rng(20261003)
    deltas = {name: [] for name in comparisons}
    for _ in range(replicates):
        starts = rng.integers(0, length-90+1, size=math.ceil(length/90))
        sampled = (starts[:,None] + np.arange(90)).ravel()[:length]
        estimates = weighted_aps(np.bincount(sampled,minlength=length)[offsets])
        if estimates is not None:
            for name,(a,b) in comparisons.items():
                deltas[name].append(estimates[a]-estimates[b])
    intervals = {}
    for name, values in deltas.items():
        low, high = np.quantile(values,[.025,.975],method="linear") if values else (None,None)
        a,b = comparisons[name]
        intervals[name] = {"ap_delta": check[a]-check[b], "lower_95": float(low) if values else None,
                           "upper_95": float(high) if values else None, "valid_replicates": len(values)}
    regimes = {}
    for regime in REGIMES:
        indices = [i for i,r in enumerate(chosen) if _regime_for(r["date"])["id"] == regime["id"]]
        ry = [y[i] for i in indices]
        regimes[regime["id"]] = {"n": len(indices), "positive_labels": sum(ry),
            "models": {n:statistics(ry,[v[i] for i in indices]) for n,v in scores.items()} if indices else {}}
    return {"methodology_version": VERSION, "protocol": PROTOCOL, "status": "exploratory_reconstructed_only",
            "n": len(y), "start": chosen[0]["date"], "end": chosen[-1]["date"], "positive_labels": sum(y),
            "prevalence": sum(y)/len(y), "statistics": {n:statistics(y,v) for n,v in scores.items()},
            "correlations": {m:{n:spearman(scores[m],scores[n]) for n in scores if not n.startswith("with_") and n != m} for m in METRICS},
            "coverage": coverage(proxy_rows), "comparisons": intervals,
            "bootstrap": {"replicates": replicates, "block_calendar_days": 90, "seed": 20261003, "method": "paired_moving_block"},
            "regime_analysis": regimes,
            "ablation": {"remove_proxy": "restore_core", "weight_policy": "each_probe_uses_0.75_Core_and_0.25_one_proxy"},
            "decision": "publish_research_metrics_only_no_core_promotion",
            "limitations": ["reused_holdout_is_exploratory", "unknown_historical_availability", "provisional_exchange_labels",
                            "proxy_not_original_metric", "three_scores_not_independent_confirmations", "not_probability"]}
