"""Prospective regime-conditioned ETH classifier, independent of macro v1 rules."""
import argparse
from collections import Counter
from datetime import datetime, timedelta, timezone
from decimal import Decimal, localcontext, ROUND_HALF_EVEN
from hashlib import sha256
import json
import math
from pathlib import Path
import random
import re

from .macro_pipeline import ROOT, body, write, read_asset, publication_lock
from .macro_market import eth_input, checked_asset, utc, calendar_date, decimal

VERSION = "macro-probability-v1.0.0"
PROTOCOL_SHA = "3ae63a0eb85f431bcdd8a8f9a0cdb770dbb5233bc1868831fd5b7cdda3e47101"
CLASSES = ("down", "flat", "up")
PATTERN = r"/data/macro-probability/(?:records/case-[a-f0-9]{20}|outcomes/result-[a-f0-9]{20}|releases/prob-[a-f0-9]{20}/(?:report|manifest|inputs|protocol))\.json"


def digest(value):
    return sha256(body(value)).hexdigest()


def text_number(value):
    if not math.isfinite(value):
        raise ValueError("nonfinite model output")
    return format(value, ".15f").rstrip("0").rstrip(".") or "0"


def asset(root, record):
    return checked_asset(root, record, PATTERN)


def record_ref(root, path):
    return {"url": "/" + path.relative_to(root / "public").as_posix(), "sha256": sha256(path.read_bytes()).hexdigest()}


def classify(base, end, protocol):
    base, end = decimal(base), decimal(end)
    if base is None or end is None or min(base, end) <= 0:
        raise ValueError("invalid outcome price")
    change = (end / base - 1) * 100
    band = Decimal(protocol["flat_band_percent"])
    return ("up" if change > band else "down" if change < -band else "flat"), format(change, "f")


def verify_macro(root, refs, cutoff):
    parents = {k: read_asset(root, refs[k]) for k in ("assessment", "manifest", "calendar", "observations", "ruleset", "batch_status")}
    a, manifest, calendar = parents["assessment"], parents["manifest"], parents["calendar"]
    proof = parents["batch_status"]
    if a["schema_version"] != "macro-assessment-v1.0.1" or a["ruleset_version"] != "macro-cross-v1.0.1" or manifest["assessment_sha256"] != refs["assessment"]["sha256"] or a["assessment_id"] != manifest["assessment_id"] or a["calendar_release_id"] != calendar["release_id"] or any(manifest[k] != refs[k] for k in ("calendar", "observations", "ruleset")):
        raise ValueError("probability archived macro lineage mismatch")
    if proof["sha256"] != sha256(body(proof["data"])[:-1]).hexdigest() or proof["id"] != "macro-status-" + proof["sha256"][:20]:
        raise ValueError("probability source proof mismatch")
    if utc(a["as_of"]) > utc(cutoff) or utc(proof["data"]["known_at"]) > utc(cutoff):
        raise ValueError("future archived macro proof")
    return a, proof["data"]


def eth_history(root, parents, cutoff):
    manifest = checked_asset(root, parents["manifest"], r"/data/core-v2/releases/core10-[a-f0-9]{20}/manifest\.json")
    history = checked_asset(root, parents["history"], r"/data/core-v2/releases/core10-[a-f0-9]{20}/history\.json")
    if manifest["asset"] != "eth" or history["asset"] != "eth" or manifest["methodology_version"] != "core-v0.2.0" or manifest["release_id"] != history["release_id"] or manifest["files"]["history.json"] != parents["history"]["sha256"] or utc(manifest["computed_at"]) > utc(cutoff):
        raise ValueError("invalid probability ETH lineage or future parent")
    prices, seen = {}, set()
    for row in history["rows"]:
        calendar_date(row["date"])
        if row["date"] in seen:
            raise ValueError("duplicate ETH outcome date")
        seen.add(row["date"])
        if not row["period_closed_at_retrieval"]:
            continue
        value = row["price_usd"]
        if value is not None and (isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value <= 0):
            raise ValueError("invalid ETH outcome price")
        prices[row["date"]] = value
    return prices


def fit(rows, protocol):
    counts = Counter(r["label"] for r in rows)
    alpha, strength = protocol["prior_alpha"], protocol["shrinkage_strength"]
    baseline = [Decimal(counts[k] + alpha) / (len(rows) + 3 * alpha) for k in CLASSES]
    groups = {}
    for regime in protocol["regimes"]:
        subset = [r for r in rows if r["regime_id"] == regime]
        n = Counter(r["label"] for r in subset)
        groups[regime] = [(n[k] + strength * baseline[i]) / (len(subset) + strength) for i, k in enumerate(CLASSES)]
    return baseline, groups


def temper(p, temperature):
    values = [v ** (Decimal(1) / Decimal(str(temperature))) for v in p]
    return [v / sum(values) for v in values]


def scores(rows, predictions):
    if not rows or len(rows) != len(predictions):
        raise ValueError("empty or mismatched evaluation")
    briers, logs = [], []
    bins = [[[] for _ in range(5)] for _ in CLASSES]
    for row, p in zip(rows, predictions):
        p = [v if isinstance(v, Decimal) else Decimal(str(v)) for v in p]
        y = CLASSES.index(row["label"])
        if len(p) != 3 or any(not math.isfinite(v) or v <= 0 or v >= 1 for v in p) or abs(sum(p) - 1) > 1e-12:
            raise ValueError("invalid probability vector")
        briers.append(sum((v - (i == y)) ** 2 for i, v in enumerate(p)))
        logs.append(-p[y].ln())
        for i, v in enumerate(p):
            bins[i][min(4, int(v * 5))].append((v, int(i == y)))
    eces, reliability = [], {}
    for key, group in zip(CLASSES, bins):
        ece, table = 0, []
        for i, entries in enumerate(group):
            predicted = sum(x[0] for x in entries) / len(entries) if entries else None
            observed = Decimal(sum(x[1] for x in entries)) / len(entries) if entries else None
            if entries:
                ece += Decimal(len(entries)) / len(rows) * abs(predicted - observed)
            table.append({"bin": i, "n": len(entries), "predicted": None if predicted is None else text_number(predicted),
                          "observed": None if observed is None else text_number(observed)})
        eces.append(ece)
        reliability[key] = table
    return {"n": len(rows), "brier": text_number(sum(briers) / len(rows)), "log_loss": text_number(sum(logs) / len(rows)),
            "class_ece": dict(zip(CLASSES, map(text_number, eces))), "reliability": reliability}, briers


def bootstrap_delta(deltas, protocol):
    rng = random.Random(protocol["bootstrap_seed"])
    n, block = len(deltas), protocol["bootstrap_block_cases"]
    estimates = []
    for _ in range(protocol["bootstrap_replicates"]):
        sampled = []
        while len(sampled) < n:
            start = rng.randrange(n - min(block, n) + 1)
            sampled.extend(deltas[start:start + block])
        estimates.append(sum(sampled[:n]) / n)
    estimates.sort()
    return [text_number(estimates[int((len(estimates) - 1) * q)]) for q in (0.025, 0.975)]


def phase(rows, count, known_after=None):
    eligible = [r for r in rows if known_after is None or utc(r["issued_at"]) > known_after]
    # Do not skip a missing outcome to cherry-pick a later case.
    selected = eligible[:count]
    return selected, len(selected) == count and all(r.get("label") for r in selected)


def evaluate(rows, regime, protocol):
    with localcontext() as context:
        context.prec = 28
        context.rounding = ROUND_HALF_EVEN
        return _evaluate(rows, regime, protocol)


def _evaluate(rows, regime, protocol):
    ordered = sorted(rows, key=lambda r: (r["issued_at"], r["case_id"]))
    train, ready = phase(ordered, protocol["train_count"])
    report = {"state": "collecting", "train_n": sum(bool(r.get("label")) for r in train), "calibration_n": 0, "test_n": 0,
              "regime_counts": {"train": sum(r.get("label") is not None and r["regime_id"] == regime for r in train), "calibration": 0, "test": 0},
              "temperature": None, "test": None, "baseline": None, "regime_test": None, "regime_baseline": None,
              "brier_delta_ci95": None, "failures": [], "probabilities": None}
    if not ready:
        return report
    baseline, groups = fit(train, protocol)
    calibration, ready = phase(ordered, protocol["calibration_count"], max(utc(r["resolved_at"]) for r in train))
    report.update(state="awaiting_calibration", calibration_n=sum(bool(r.get("label")) for r in calibration))
    report["regime_counts"]["calibration"] = sum(r.get("label") is not None and r["regime_id"] == regime for r in calibration)
    if not ready:
        return report
    def predictions(part, temperature):
        return [temper(groups[r["regime_id"]], temperature) for r in part]
    temperature = min(map(float, protocol["temperatures"]), key=lambda t: (float(scores(calibration, predictions(calibration, t))[0]["log_loss"]), abs(t - 1), t))
    test, ready = phase(ordered, protocol["test_count"], max(utc(r["resolved_at"]) for r in calibration))
    report.update(state="awaiting_test", test_n=sum(bool(r.get("label")) for r in test), temperature=text_number(temperature))
    report["regime_counts"]["test"] = sum(r.get("label") is not None and r["regime_id"] == regime for r in test)
    if not ready:
        return report
    candidate, losses = scores(test, predictions(test, temperature))
    reference, base_losses = scores(test, [baseline] * len(test))
    ci = bootstrap_delta([a - b for a, b in zip(losses, base_losses)], protocol)
    report.update(test=candidate, baseline=reference, brier_delta_ci95=ci)
    def gate(a, b, prefix):
        if float(b["brier"]) - float(a["brier"]) < float(protocol["minimum_brier_improvement"]):
            report["failures"].append(prefix + "brier_no_improvement")
        if float(a["log_loss"]) > float(b["log_loss"]):
            report["failures"].append(prefix + "log_loss_worse")
        if max(map(float, a["class_ece"].values())) > float(protocol["maximum_class_ece"]):
            report["failures"].append(prefix + "calibration_error")
    gate(candidate, reference, "global_")
    if float(ci[1]) >= 0:
        report["failures"].append("brier_ci_not_below_zero")
    for key in ("train", "calibration", "test"):
        if report["regime_counts"][key] < protocol["minimum_regime_" + key]:
            report["failures"].append("insufficient_regime_" + key)
    subset = [r for r in test if r["regime_id"] == regime]
    if subset:
        a = scores(subset, predictions(subset, temperature))[0]
        b = scores(subset, [baseline] * len(subset))[0]
        report.update(regime_test=a, regime_baseline=b)
        gate(a, b, "regime_")
    report["state"] = "validation_failed" if report["failures"] else "validated_holdout"
    if not report["failures"]:
        report["probabilities"] = dict(zip(CLASSES, map(text_number, temper(groups[regime], temperature))))
    return report


def context(root, as_of, protocol):
    p = json.loads((root / "public/data/macro-assessment/latest.json").read_bytes())
    a, m = read_asset(root, p), read_asset(root, p["manifest"])
    calendar = read_asset(root, m["calendar"])
    for key in ("observations", "batch_status", "ruleset"):
        read_asset(root, m[key])
    latest = json.loads((root / "public/data/calendar/latest.json").read_bytes())
    s = json.loads((root / "public/data/macro-assessment/status.json").read_bytes())
    proof_record = s.get("batch_status", m["batch_status"])
    proof = read_asset(root, proof_record)["data"]
    now = utc(as_of)
    if a["assessment_id"] != p["assessment_id"] or m["assessment_sha256"] != p["sha256"] or a["calendar_release_id"] != calendar["release_id"] or latest["sha256"] != m["calendar"]["sha256"] or s["assessment_id"] != a["assessment_id"]:
        raise ValueError("probability macro parent mismatch")
    for time in (a["as_of"], s["checked_at"], proof["known_at"]):
        if utc(time) > now:
            raise ValueError("future macro proof")
    success = proof.get("last_successful_source_check_at")
    fresh = success is not None and utc(success) <= utc(proof["known_at"]) <= now
    fresh = fresh and now - utc(success) <= timedelta(hours=protocol["maximum_context_age_hours"])
    fresh = fresh and now - utc(a["as_of"]) <= timedelta(hours=protocol["maximum_context_age_hours"])
    eligible = fresh and s["outcome"] != "error" and a["assessment_state"] == "assessed" and a["pipeline_state"] == "fresh" and a["regime_id"] in protocol["regimes"]
    refs = {"assessment": {"url": p["url"], "sha256": p["sha256"]}, "manifest": p["manifest"],
            "calendar": m["calendar"], "observations": m["observations"], "ruleset": m["ruleset"], "batch_status": proof_record}
    verify_macro(root, refs, as_of)
    return {"regime_id": a["regime_id"], "crypto_conclusion": a["assets"]["crypto_risk_assets"]["conclusion"],
            "eligible": bool(eligible), "assessment_id": a["assessment_id"], "as_of": a["as_of"], "parents": refs}


def load_ledger(root, folder, as_of, protocol):
    cases, outcomes, refs = [], {}, {"cases": [], "outcomes": []}
    for path in sorted((folder / "records").glob("*.json")):
        row = json.loads(path.read_bytes())
        identity = {k: v for k, v in row.items() if k != "case_id"}
        if row["case_id"] != "case-" + digest(identity)[:20] or path.stem != row["case_id"] or row["version"] != VERSION or utc(row["issued_at"]) > utc(as_of):
            raise ValueError("invalid or future probability case")
        if row["regime_id"] not in protocol["regimes"] or calendar_date(row["base_date"]) != utc(row["issued_at"]).date() + timedelta(days=1) or calendar_date(row["end_date"]) - calendar_date(row["base_date"]) != timedelta(days=7):
            raise ValueError("invalid case window")
        a, proof = verify_macro(root, row["macro_parents"], row["issued_at"])
        success = proof.get("last_successful_source_check_at")
        if a["regime_id"] != row["regime_id"] or a["assessment_state"] != "assessed" or a["pipeline_state"] != "fresh" or success is None or not utc(success) <= utc(proof["known_at"]) <= utc(row["issued_at"]) or any(utc(row["issued_at"]) - utc(t) > timedelta(hours=48) for t in (a["as_of"], success)):
            raise ValueError("ineligible archived probability case")
        p = row["probabilities"]
        if row["model_state"] != "validated_holdout" and p is not None:
            raise ValueError("uncalibrated case probabilities")
        if p is not None and (set(p) != set(CLASSES) or any(not Decimal(0) < decimal(v) < Decimal(1) for v in p.values()) or abs(sum(decimal(v) for v in p.values()) - 1) > Decimal('0.000000000001')):
            raise ValueError("invalid case probabilities")
        cases.append(row)
        refs["cases"].append(record_ref(root, path))
    cases.sort(key=lambda r: utc(r["issued_at"]))
    if any(a["end_date"] > b["base_date"] for a, b in zip(cases, cases[1:])):
        raise ValueError("overlapping probability cases")
    for path in sorted((folder / "outcomes").glob("*.json")):
        row = json.loads(path.read_bytes())
        identity = {k: v for k, v in row.items() if k != "outcome_id"}
        case = next((r for r in cases if r["case_id"] == row["case_id"]), None)
        if row["version"] != VERSION or row["outcome_id"] != "result-" + digest(identity)[:20] or path.stem != row["outcome_id"] or case is None or row["case_id"] in outcomes:
            raise ValueError("invalid or duplicate outcome")
        if utc(row["resolved_at"]) > utc(as_of) or utc(row["resolved_at"]).date() <= calendar_date(case["end_date"]) or utc(row["resolved_at"]).date() > calendar_date(case["end_date"]) + timedelta(days=protocol["maximum_resolution_delay_days"]):
            raise ValueError("invalid outcome chronology")
        label, change = classify(row["base_price"], row["end_price"], protocol)
        if label != row["label"] or change != row["return_percent"]:
            raise ValueError("outcome value mismatch")
        prices = eth_history(root, row["eth_parent"], row["resolved_at"])
        if prices.get(case["base_date"]) is None or prices.get(case["end_date"]) is None or decimal(str(prices[case["base_date"]])) != decimal(row["base_price"]) or decimal(str(prices[case["end_date"]])) != decimal(row["end_price"]):
            raise ValueError("outcome source value mismatch")
        outcomes[row["case_id"]] = row
        refs["outcomes"].append(record_ref(root, path))
    return cases, outcomes, refs


def publish(root, folder, inputs, report, protocol, as_of):
    prior_path = folder / "latest.json"
    prior = json.loads(prior_path.read_bytes()) if prior_path.exists() else None
    state = digest({"inputs": inputs, "report": report, "protocol_sha256": PROTOCOL_SHA})
    if prior and asset(root, prior["manifest"])["state_sha256"] == state:
        asset(root, prior)
        write(folder / "status.json", {"outcome": "unchanged", "checked_at": as_of, "release_id": prior["release_id"]})
        return {"outcome": "unchanged", "release_id": prior["release_id"]}
    identity = {"state_sha256": state, "previous_release_id": prior["release_id"] if prior else None}
    release_id = "prob-" + digest(identity)[:20]
    target = folder / "releases" / release_id
    value = {**report, "schema_version": VERSION, "release_id": release_id, "generated_at": as_of}
    if (target / "report.json").exists():
        old = json.loads((target / "report.json").read_bytes())
        if {k: v for k, v in old.items() if k != "generated_at"} != {k: v for k, v in value.items() if k != "generated_at"}:
            raise ValueError("probability replay mismatch")
        value = old
    for name, data in (("report", value), ("inputs", inputs), ("protocol", protocol)):
        write(target / (name + ".json"), data, True)
    manifest = {**identity, "schema_version": VERSION, "release_id": release_id, "protocol_sha256": PROTOCOL_SHA,
                **{name: record_ref(root, target / (name + ".json")) for name in ("report", "inputs", "protocol")}}
    write(target / "manifest.json", manifest, True)
    pointer = {**manifest["report"], "schema_version": VERSION, "release_id": release_id, "manifest": record_ref(root, target / "manifest.json")}
    write(prior_path, pointer)
    write(folder / "status.json", {"outcome": "published", "checked_at": as_of, "release_id": release_id})
    return {"outcome": "published", "release_id": release_id, "model_state": report["evaluation"]["state"]}


def run(root=ROOT, as_of=None):
    root = Path(root)
    as_of = as_of or datetime.now(timezone.utc).isoformat()
    folder = root / "public/data/macro-probability"
    protocol = json.loads((root / "configs/macro" / (VERSION + ".json")).read_bytes())
    if digest(protocol) != PROTOCOL_SHA:
        raise ValueError("probability protocol changed under frozen version")
    try:
        with publication_lock(folder):
            if (folder / "latest.json").exists():
                p = json.loads((folder / "latest.json").read_bytes())
                m = asset(root, p["manifest"])
                previous_report = asset(root, p)
                if utc(previous_report["generated_at"]) > utc(as_of):
                    raise ValueError("future probability predecessor")
                asset(root, m["protocol"])
                previous_inputs = asset(root, m["inputs"])
                for r in previous_inputs["cases"] + previous_inputs["outcomes"]:
                    asset(root, r)
            current = context(root, as_of, protocol)
            market_protocol = json.loads((root / "configs/macro/macro-market-v1.0.0.json").read_bytes())
            _, eth_parent = eth_input(root, as_of, market_protocol)
            prices = eth_history(root, eth_parent, as_of)
            cases, outcomes, _ = load_ledger(root, folder, as_of, protocol)
            for case in cases:
                end = calendar_date(case["end_date"])
                if case["case_id"] in outcomes or not end < utc(as_of).date() <= end + timedelta(days=protocol["maximum_resolution_delay_days"]):
                    continue
                base_price, end_price = prices.get(case["base_date"]), prices.get(case["end_date"])
                if base_price is None or end_price is None:
                    continue
                label, change = classify(str(base_price), str(end_price), protocol)
                row = {"version": VERSION, "case_id": case["case_id"], "resolved_at": as_of,
                       "base_price": str(base_price), "end_price": str(end_price), "return_percent": change, "label": label, "eth_parent": eth_parent}
                row["outcome_id"] = "result-" + digest(row)[:20]
                write(folder / "outcomes" / (row["outcome_id"] + ".json"), row, True)
            cases, outcomes, refs = load_ledger(root, folder, as_of, protocol)
            rows = [{**c, **({"label": outcomes[c["case_id"]]["label"], "resolved_at": outcomes[c["case_id"]]["resolved_at"]} if c["case_id"] in outcomes else {})} for c in cases]
            evaluation = evaluate(rows, current["regime_id"], protocol)
            next_base = utc(as_of).date() + timedelta(days=1)
            if current["eligible"] and (not cases or next_base >= calendar_date(cases[-1]["end_date"])):
                case = {"version": VERSION, "issued_at": as_of, "base_date": next_base.isoformat(),
                        "end_date": (next_base + timedelta(days=7)).isoformat(), "regime_id": current["regime_id"],
                        "macro_parents": current["parents"], "model_state": evaluation["state"], "probabilities": evaluation["probabilities"],
                        "training_evidence": refs}
                case["case_id"] = "case-" + digest(case)[:20]
                write(folder / "records" / (case["case_id"] + ".json"), case, True)
                cases, outcomes, refs = load_ledger(root, folder, as_of, protocol)
            report = {"asset": "eth", "target": protocol["target"], "horizon_days": 7, "flat_band_percent": "1",
                      "scope": protocol["scope"], "consensus": "not_market_consensus", "current_context": current,
                      "cases_count": len(cases), "resolved_count": len(outcomes), "evaluation": evaluation,
                      "latest_case": cases[-1] if cases else None}
            inputs = {**refs, "macro_parents": current["parents"], "eth_parent": eth_parent}
            return publish(root, folder, inputs, report, protocol, as_of)
    except Exception as error:
        if str(error) != "macro publisher busy":
            write(folder / "status.json", {"outcome": "error", "checked_at": as_of, "last_good_retained": (folder / "latest.json").exists()})
        raise


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=ROOT)
    args = parser.parse_args()
    print(json.dumps(run(args.root), ensure_ascii=False))
