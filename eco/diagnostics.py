"""Raw ETH diagnostics: calendar windows, signed values and source flags."""
from datetime import date, timedelta
import math
from .core import nupl_diagnostic
from .pipeline import ROOT, digest, encode, read_json

VERSION = "diagnostics-v0.1.0"
PROTOCOL = VERSION + "-protocol-1"
PROTOCOL_HASH = "fb7f5b80ca84ffc4babb8b5ffe823574500f13fed31fc03a3a25922da76afc4a"
IDS = ("nupl_diagnostic", "supply_change_30d", "exchange_balance_change_30d")
UNITS = dict(zip(IDS, ("ratio", "percent", "ETH")))


def protocol():
    config = read_json(ROOT / "configs/research/diagnostics-v0.1.0.json")
    if digest(encode(config)) != PROTOCOL_HASH:
        raise ValueError("frozen diagnostics protocol changed")
    return config


def _calendar(rows):
    result = {}
    for row in rows:
        day = date.fromisoformat(row["observation_date"])
        if row.get("asset") != "eth" or day in result:
            raise ValueError("diagnostics require unique ETH observation dates")
        result[day] = row
    return result


def _number(row, field, *, positive=False):
    if row is None or row.get("metrics", {}).get(field) is None:
        return None
    value = row["metrics"][field]
    if isinstance(value, bool):
        return None
    try:
        value = float(value)
    except (TypeError, ValueError):
        return None
    return value if math.isfinite(value) and (value > 0 if positive else value >= 0) else None


def compute_diagnostics(core_rows, network_rows, *, first=None, end=None):
    core, network = _calendar(core_rows), _calendar(network_rows)
    if not core or not network:
        raise ValueError("both parent datasets are required")
    day = date.fromisoformat(first) if first else min(min(core), min(network))
    last = date.fromisoformat(end) if end else max(max(core), max(network))
    if day > min(min(core), min(network)) or last < max(max(core), max(network)):
        raise ValueError("diagnostic calendar cannot omit source observations")
    result = []
    while day <= last:
        c, n = core.get(day), network.get(day)
        nupl = nupl_diagnostic(_number(c, "CapMVRVCur", positive=True))
        values = {IDS[0]: {"value": nupl["value"], "unit": "ratio", "reason": nupl["reason"] if c else "parent_day_unavailable", "source_flags": []}}
        for field, metric, positive in (("SplyCur", IDS[1], True), ("SplyExNtv", IDS[2], False)):
            window = [network.get(day - timedelta(days=offset)) for offset in range(30, -1, -1)]
            flags = sorted({r.get("metric_status", {}).get(field, {}).get("status") for r in window if r and r.get("metric_status", {}).get(field, {}).get("status")})
            observed = [_number(r, field, positive=positive) for r in window]
            if n is None:
                value, reason = None, "parent_day_unavailable"
            elif day - timedelta(days=30) < min(network):
                value, reason = None, "window_warmup"
            elif any(value is None for value in observed):
                value, reason = None, "missing_or_invalid_window"
            else:
                value = 100 * (observed[-1] / observed[0] - 1) if positive else observed[-1] - observed[0]
                reason = None
            values[metric] = {"value": value, "unit": UNITS[metric], "reason": reason, "source_flags": flags}
        for item in values.values():
            if item["value"] is not None and not math.isfinite(item["value"]):
                item.update(value=None, reason="invalid_derived_value")
        result.append({"date": day.isoformat(), "metrics": values,
                       "source_rows_present": {"core": c is not None, "proxies": n is not None}})
        day += timedelta(days=1)
    return result


def describe(rows):
    def summary(subset, metric):
        valid = [(r["date"], r["metrics"][metric]["value"]) for r in subset if r["metrics"][metric]["value"] is not None]
        return {"valid_rows": len(valid), "null_rows": len(subset)-len(valid),
                "first_valid_date": valid[0][0] if valid else None, "last_valid_date": valid[-1][0] if valid else None,
                "last_value": valid[-1][1] if valid else None,
                "minimum": min(v for _, v in valid) if valid else None,
                "maximum": max(v for _, v in valid) if valid else None,
                "negative_rows": sum(v < 0 for _, v in valid), "zero_rows": sum(v == 0 for _, v in valid),
                "flagged_rows": sum(bool(r["metrics"][metric]["source_flags"]) for r in subset)}
    boundaries = (None, "2021-08-05", "2022-09-15", "2024-03-13", None)
    regimes = {}
    for i, name in enumerate(("pre_london", "london_pre_merge", "merge_pre_dencun", "post_dencun")):
        selected = [r for r in rows if (boundaries[i] is None or r["date"] >= boundaries[i]) and (boundaries[i+1] is None or r["date"] < boundaries[i+1])]
        regimes[name] = {"rows": len(selected), "metrics": {m: summary(selected, m) for m in IDS}}
    return {"methodology_version": VERSION, "protocol": PROTOCOL, "status": "descriptive_raw_diagnostics",
            "forecast_evaluation": "not_applicable_raw_context_only", "predictive_utility_claim": False,
            "coverage": {m: summary(rows, m) for m in IDS}, "regimes": regimes,
            "limitations": protocol()["limitations"]}


def validate_history(history, manifest, report):
    config = protocol()
    if (history.get("methodology_version") != VERSION or history.get("release_id") != manifest.get("release_id")
            or history.get("asset") != "eth" or history.get("series_type") != "reconstructed"
            or history.get("frequency") != "1d" or history.get("composite_score") is not None or history.get("metric_definitions") != config["metrics"]
            or manifest.get("methodology_version") != VERSION or manifest.get("protocol_sha256") != PROTOCOL_HASH
            or manifest.get("role") != "raw_diagnostics_only" or manifest.get("normalizer") is not None
            or manifest.get("composite_score") is not None or manifest.get("core_promotion") is not False
            or report.get("forecast_evaluation") != "not_applicable_raw_context_only"
            or report.get("predictive_utility_claim") is not False):
        raise ValueError("invalid raw diagnostic release contract")
    rows = history["rows"]
    dates = [r["date"] for r in rows]
    if not dates or dates != sorted(set(dates)) or any((date.fromisoformat(b)-date.fromisoformat(a)).days != 1 for a, b in zip(dates, dates[1:])):
        raise ValueError("diagnostic calendar is invalid")
    for row in rows:
        if (set(row["metrics"]) != set(IDS) or set(row.get("source_rows_present", {})) != {"core", "proxies"}
                or any(type(v) is not bool for v in row["source_rows_present"].values())):
            raise ValueError("diagnostic row schema is invalid")
        for metric, item in row["metrics"].items():
            value = item["value"]
            if (set(item) != {"value", "unit", "reason", "source_flags"} or item["unit"] != UNITS[metric]
                    or (value is None and not isinstance(item["reason"], str))
                    or (value is not None and (isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or item["reason"] is not None))
                    or (metric == IDS[0] and value is not None and value >= 1)
                    or not isinstance(item["source_flags"], list) or any(not isinstance(f, str) or not f for f in item["source_flags"])
                    or item["source_flags"] != sorted(set(item["source_flags"]))):
                raise ValueError("diagnostic value/unit/null/flags contract is invalid")
    if (manifest.get("rows") != len(rows) or manifest.get("first_date") != dates[0] or manifest.get("last_observation_date") != dates[-1]
            or report != describe(rows) or manifest.get("coverage") != report["coverage"]):
        raise ValueError("diagnostic report does not match its history")
