"""Core v0.2: fixed information-family budgets and causally normalized diagnostics."""
import argparse
from datetime import date, datetime, timezone
import math
from pathlib import Path
import re
import numpy as np
from .pipeline import ROOT, digest, encode, read_json, verify_release
from .daily import atomic_json
from .core import Normalizer
from . import seven, diagnostics
from .diagnostic_pipeline import ATTRIBUTION as DIAGNOSTIC_ATTRIBUTION
from .research import labels, ap, statistics, spearman, REGIMES, _regime_for

VERSION = "core-v0.2.0"
PROTOCOL = VERSION + "-protocol-1"
PROTOCOL_HASH = "43fc1f29c02868f4d1f5b02ed0f121fc15d9e79e5f886dbaf2061e8b8837d404"
NEW_IDS = ("E2", "supply_scarcity", "exchange_balance_pressure")
IDS = seven.IDS + NEW_IDS
WEIGHTS = dict(zip(IDS, (.125, .125, .125, .1875, .03125, .0625, .0625, .1875, .0625, .03125)))
ATTRIBUTION = {**seven.ATTRIBUTION, "changes": "Core 10: normalized NUPL, signed supply/exchange changes and fixed information-family aggregation"}
PREFIX = "core-v2"


def protocol():
    config = read_json(ROOT / "configs/research/core-v0.2.0.json")
    if digest(encode(config)) != PROTOCOL_HASH or config["weights"] != WEIGHTS or config["components"] != list(IDS):
        raise ValueError("frozen Core v0.2 protocol changed")
    return config


def aggregate(components, selected=IDS):
    if not selected or len(set(selected)) != len(selected) or any(m not in WEIGHTS for m in selected):
        return None
    values = [components.get(m) for m in selected]
    if any(v is None for v in values):
        return None
    if any(isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v) or not 0 <= v <= 100 for v in values):
        raise ValueError("invalid Core v0.2 component")
    if len(values) == 1:
        return values[0]
    return sum(components[m]*WEIGHTS[m] for m in selected)/sum(WEIGHTS[m] for m in selected)


def normalize(rows):
    config = protocol(); normalizers = {m: Normalizer() for m in NEW_IDS}; result = {}; previous = None
    for row in rows:
        day = date.fromisoformat(row["date"])
        if day.isoformat() != row["date"] or previous is not None and (day-previous).days != 1:
            raise ValueError("diagnostic normalization calendar is not continuous")
        previous = day; features = {}
        for m in NEW_IDS:
            spec = config["new_features"][m]; item = row["metrics"][spec["input"]]; value = item["value"]
            if (item["unit"] != spec["unit"] or value is not None and (isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value))
                    or (value is None and not isinstance(item["reason"], str)) or (value is not None and item["reason"] is not None)
                    or not isinstance(item["source_flags"], list) or any(not isinstance(f, str) for f in item["source_flags"])):
                raise ValueError("diagnostic raw input/unit/reason/flags invalid")
            if m == "E2" and value is not None and value >= 1:
                raise ValueError("NUPL outside its positive-MVRV domain")
            raw = spec["sign"]*value if value is not None else None
            feature = normalizers[m].compute(day, raw)
            if value is None:
                feature["reason"] = item["reason"]
            features[m] = {**feature, "input_value": value, "input_unit": spec["unit"], "source_flags": item["source_flags"]}
        result[row["date"]] = features
    if not result:
        raise ValueError("no diagnostic observations")
    return result


def join(extended_rows, diagnostic_rows):
    features = normalize(diagnostic_rows); result = []; previous = None
    if not extended_rows or diagnostic_rows[0]["date"] > extended_rows[0]["date"] or diagnostic_rows[-1]["date"] < extended_rows[-1]["date"]:
        raise ValueError("diagnostic calendar does not cover its Core parent")
    for row in extended_rows:
        day = date.fromisoformat(row["date"])
        if previous is not None and (day-previous).days != 1:
            raise ValueError("Core parent calendar is not continuous")
        previous = day
        expected_extended = seven.aggregate(row["components"])
        if row["score"] != expected_extended and not (row["score"] is not None and expected_extended is not None and math.isclose(row["score"], expected_extended, rel_tol=1e-12, abs_tol=1e-8)):
            raise ValueError("ECO 7 parent score differs from its components")
        current = features[row["date"]]
        components = {**row["components"], **{m: f["score"] for m, f in current.items()}}
        reasons = {**row["reasons"], **{m: f["reason"] for m, f in current.items()}}
        flags = {**row["source_flags"], **{m: f["source_flags"] for m, f in current.items()}}
        result.append({**row, "extended_score": row["score"], "score": aggregate(components) if row["period_closed_at_retrieval"] else None,
                       "components": components, "reasons": reasons, "source_flags": flags,
                       "coverage": sum(v is not None for v in components.values()), "new_features": current})
    return result


def _derived_parent(public, prefix, version, pattern, protocol_hash):
    root = public/"data"/prefix; pointer = read_json(root/"latest.json"); release_id = pointer.get("release_id", "")
    url = f"/data/{prefix}/releases/{release_id}/manifest.json"
    if (not re.fullmatch(pattern, release_id) or pointer.get("manifest_url") != url or pointer.get("methodology_version") != version):
        raise ValueError("derived parent pointer contract mismatch")
    folder = root/"releases"/release_id
    if digest((folder/"manifest.json").read_bytes()) != pointer.get("manifest_sha256"):
        raise ValueError("derived parent manifest checksum mismatch")
    manifest = verify_release(folder); history = read_json(folder/"history.json"); report = read_json(folder/"research.json")
    if (manifest.get("methodology_version") != version or manifest.get("protocol_sha256") != protocol_hash
            or manifest.get("asset") != "eth" or manifest.get("series_type") != "reconstructed"
            or history.get("methodology_version") != version or history.get("asset") != "eth" or history.get("release_id") != release_id
            or set(manifest["files"]) != {"history.json", "research.json"} or manifest.get("source_available_at") is not None):
        raise ValueError("derived parent contract mismatch")
    ref = {"release_id": release_id, "methodology_version": version, "manifest_url": url, "manifest_sha256": pointer["manifest_sha256"],
           "history_sha256": manifest["files"]["history.json"], "last_observation_date": manifest["last_observation_date"]}
    return ref, manifest, history, report


def expected(public):
    protocol(); seven.protocol(); diagnostics.protocol()
    core, core_rows = seven.parent(public, "", "core-v0.1.0", r"core-[a-f0-9]{20}")
    proxy, proxy_rows = seven.parent(public, "network-proxies", "network-proxies-v0.1.0", r"proxy-[a-f0-9]{20}")
    ext, em, eh, er = _derived_parent(public, "extended", seven.VERSION, r"extended-[a-f0-9]{20}", seven.PROTOCOL_HASH)
    diag, dm, dh, dr = _derived_parent(public, "diagnostics", diagnostics.VERSION, r"diagnostic-[a-f0-9]{20}", diagnostics.PROTOCOL_HASH)
    parents = {"core": core, "proxies": proxy}
    if em.get("parents") != parents or dm.get("parents") != parents:
        raise ValueError("mixed parent lineages; wait for successful upstream joins")
    diagnostics.validate_history(dh, dm, dr)
    if dm.get("attribution") != DIAGNOSTIC_ATTRIBUTION:
        raise ValueError("diagnostic licence/scope gate failed")
    if (em.get("attribution") != seven.ATTRIBUTION or em.get("weights") != seven.WEIGHTS or eh.get("weights") != seven.WEIGHTS
            or em.get("research_only") is not True or em.get("required_coverage") != 7
            or er.get("decision") != "publish_experimental_preview_no_predictive_validation_claim"):
        raise ValueError("ECO 7 research/licence gate failed")
    replay = seven.join(core_rows, proxy_rows)
    if eh["rows"] != replay:
        # The old publisher may retain equivalent floats after an upstream revision.
        if len(eh["rows"]) != len(replay) or any(not equivalent(a, b) for a, b in zip(eh["rows"], replay)):
            raise ValueError("ECO 7 differs from verified parents")
    proofs = dm.get("private_inputs_verified", {})
    for kind, ref in parents.items():
        parent_manifest = read_json(public/ref["manifest_url"].lstrip("/")); proof = proofs.get(kind, {})
        if (proof.get("canonical_sha256") != parent_manifest["snapshot_sha256"] or proof.get("objects_readback_verified") is not True
                or proof.get("file_count") != (7 if kind == "core" else 8)
                or any(not re.fullmatch(r"[a-f0-9]{64}", proof.get(k, "")) for k in ("source_manifest_sha256", "receipt_sha256"))):
            raise ValueError("diagnostic private source/readback proof mismatch")
    return join(eh["rows"], dh["rows"]), {**parents, "extended": ext, "diagnostics": diag}, proofs


def equivalent(a, b):
    if isinstance(a, bool) or isinstance(b, bool):
        return type(a) is type(b) and a == b
    if isinstance(a, (int, float)) and isinstance(b, (int, float)):
        return math.isclose(a, b, rel_tol=1e-12, abs_tol=1e-8)
    if isinstance(a, dict) and isinstance(b, dict):
        return a.keys() == b.keys() and all(equivalent(a[k], b[k]) for k in a)
    if isinstance(a, list) and isinstance(b, list):
        return len(a) == len(b) and all(equivalent(x, y) for x, y in zip(a, b))
    return a == b


def evaluate(rows, replicates=10000):
    future = labels(rows)
    chosen = [r for r in rows if r["date"] >= "2020-01-01" and r["score"] is not None and r["date"] in future]
    if not chosen:
        raise ValueError("no completed evaluation horizon")
    y = [future[r["date"]] for r in chosen]
    scores = {"core_ten": [r["score"] for r in chosen], "core": [r["core_score"] for r in chosen],
              "extended": [r["extended_score"] for r in chosen], "normalized_E7_only": [r["components"]["E7"] for r in chosen],
              "normalized_price_group_only": [sum(r["components"][m] for m in seven.CORE_IDS[:3])/3 for r in chosen]}
    baselines = tuple(n for n in scores if n != "core_ten"); ya = np.asarray(y, dtype=float); plans = {}
    for n, values in scores.items():
        a = np.asarray(values); order = np.argsort(-a, kind="stable")
        plans[n] = order, np.r_[np.flatnonzero(np.diff(a[order]) != 0), len(a)-1]

    def estimates(w):
        positive = float(np.sum(w*ya))
        if positive == 0:
            return None
        values = {}
        for n, (order, ends) in plans.items():
            tp = np.cumsum(w[order]*ya[order])[ends]; total = np.cumsum(w[order])[ends]
            values[n] = float(np.sum(np.divide(tp, total, out=np.zeros_like(tp), where=total > 0)*np.diff(np.r_[0., tp]))/positive)
        return values

    check = estimates(np.ones(len(y)))
    if check is None or any(abs(check[n]-ap(y, v)) > 1e-12 for n, v in scores.items()):
        raise ValueError("Core v0.2 AP cross-check failed")
    offsets = np.asarray([(date.fromisoformat(r["date"])-date.fromisoformat(chosen[0]["date"])).days for r in chosen])
    length = int(offsets[-1]+1)
    if length < 90:
        raise ValueError("insufficient block bootstrap calendar")
    rng = np.random.default_rng(20261003); deltas = {n: [] for n in baselines}
    for _ in range(replicates):
        starts = rng.integers(0, length-90+1, size=math.ceil(length/90))
        sampled = (starts[:, None]+np.arange(90)).ravel()[:length]
        result = estimates(np.bincount(sampled, minlength=length)[offsets])
        if result:
            for n in baselines:
                deltas[n].append(result["core_ten"]-result[n])
    comparisons = {}
    for n, values in deltas.items():
        lo, hi = np.quantile(values, [.025, .975], method="linear") if values else (None, None)
        comparisons[n] = {"ap_delta": check["core_ten"]-check[n], "lower_95": float(lo) if values else None,
                          "upper_95": float(hi) if values else None, "valid_replicates": len(values)}
    components = {m: [r["components"][m] for r in chosen] for m in IDS}; regimes = {}
    for regime in REGIMES:
        indices = [i for i, r in enumerate(chosen) if _regime_for(r["date"])["id"] == regime["id"]]; ry = [y[i] for i in indices]
        regimes[regime["id"]] = {"n": len(indices), "positive_labels": sum(ry),
                                "models": {n: statistics(ry, [v[i] for i in indices]) for n, v in scores.items()} if indices else {}}
    return {"methodology_version": VERSION, "protocol": PROTOCOL, "status": "exploratory_reconstructed_only",
            "n": len(y), "start": chosen[0]["date"], "end": chosen[-1]["date"], "positive_labels": sum(y), "prevalence": sum(y)/len(y),
            "statistics": {n: statistics(y, v) for n, v in scores.items()}, "comparisons": comparisons,
            "bootstrap": {"replicates": replicates, "block_calendar_days": 90, "seed": 20261003},
            "correlations": {m: {n: spearman(v, components[n]) for n in IDS if n != m} for m, v in components.items()},
            "ablation": {m: statistics(y, [aggregate(r["components"], tuple(n for n in IDS if n != m)) for r in chosen]) for m in IDS},
            "regime_analysis": regimes, "feature_coverage": {m: {"valid_rows": sum(r["components"][m] is not None for r in rows),
                "first_valid_date": next((r["date"] for r in rows if r["components"][m] is not None), None)} for m in IDS},
            "decision": "publish_experimental_preview_no_predictive_validation_claim", "limitations": protocol()["limitations"]}


def engine_hash():
    return digest(b"".join((ROOT/p).read_bytes().replace(b"\r\n", b"\n") for p in ("eco/core_ten.py", "eco/core.py", "eco/research.py", "eco/seven.py", "eco/diagnostics.py")))


def build(public, output, *, replicates=10000):
    if replicates != 10000:
        raise ValueError("Core v0.2 publication requires 10000 bootstrap replicates")
    rows, parents, proofs = expected(public); config = protocol()
    identity = {"methodology_version": VERSION, "protocol_sha256": PROTOCOL_HASH, "engine_sha256": engine_hash(), "parents": parents,
                "bootstrap_replicates": replicates}
    release_id = "core10-"+digest(encode(identity))[:20]; folder = output/release_id
    history = {"schema_version": "1.0.0", "release_id": release_id, "methodology_version": VERSION, "asset": "eth", "series_type": "reconstructed",
               "weights": WEIGHTS, "attribution": ATTRIBUTION, "rows": rows}
    if folder.exists():
        manifest = verify_release(folder)
        if manifest["parents"] != parents or manifest["engine_sha256"] != engine_hash() or read_json(folder/"history.json") != history:
            raise ValueError("immutable private Core v0.2 candidate conflict")
        return folder
    valid = [r for r in rows if r["score"] is not None]
    if not valid:
        raise ValueError("no complete Core v0.2 observation")
    report = evaluate(rows, replicates); files = {"history.json": encode(history), "research.json": encode(report)}
    manifest = {"schema_version": "1.0.0", "release_id": release_id, **identity, "protocol": PROTOCOL, "asset": "eth", "series_type": "reconstructed",
                "research_only": True, "source_available_at": None, "weights": WEIGHTS, "groups": config["groups"], "new_features": config["new_features"],
                "normalizer": config["normalizer"], "required_coverage": 10, "rows": len(rows), "score_rows": len(valid),
                "first_observation_date": rows[0]["date"], "last_observation_date": rows[-1]["date"], "first_score_date": valid[0]["date"],
                "last_valid_score_date": valid[-1]["date"], "last_valid_score": valid[-1]["score"],
                "missing_dates": [r["date"] for r in rows if not r["source_row_present"]],
                "pending_dates": [r["date"] for r in rows if not r["period_closed_at_retrieval"]], "computed_at": datetime.now(timezone.utc).isoformat(),
                "attribution": ATTRIBUTION, "license_url": ATTRIBUTION["licence_url"], "private_inputs_verified": proofs, "limitations": config["limitations"],
                "files": {name: digest(content) for name, content in files.items()}}
    folder.mkdir(parents=True)
    for name, content in {**files, "manifest.json": encode(manifest)}.items():
        (folder/name).write_bytes(content)
    return folder


def publish(folder, public):
    manifest = verify_release(folder); config = protocol(); release_id = manifest["release_id"]
    identity = {k: manifest[k] for k in ("methodology_version", "protocol_sha256", "engine_sha256", "parents", "bootstrap_replicates")}
    if (release_id != "core10-"+digest(encode(identity))[:20] or manifest["methodology_version"] != VERSION
            or manifest["protocol_sha256"] != PROTOCOL_HASH or manifest["engine_sha256"] != engine_hash() or manifest["bootstrap_replicates"] != 10000
            or manifest.get("weights") != WEIGHTS or manifest.get("groups") != config["groups"] or manifest.get("new_features") != config["new_features"]
            or manifest.get("normalizer") != config["normalizer"] or manifest.get("required_coverage") != 10 or manifest.get("attribution") != ATTRIBUTION
            or manifest.get("research_only") is not True or manifest.get("source_available_at") is not None
            or manifest.get("schema_version") != "1.0.0" or manifest.get("asset") != "eth" or manifest.get("series_type") != "reconstructed"
            or manifest.get("protocol") != PROTOCOL or manifest.get("license_url") != ATTRIBUTION["licence_url"]
            or manifest.get("limitations") != config["limitations"] or set(manifest["files"]) != {"history.json", "research.json"}):
        raise ValueError("Core v0.2 publication contract failed")
    rows, parents, proofs = expected(public); history = read_json(folder/"history.json"); report = read_json(folder/"research.json")
    if (manifest["parents"] != parents or manifest["private_inputs_verified"] != proofs or history["rows"] != rows
            or history.get("weights") != WEIGHTS or history.get("attribution") != ATTRIBUTION or history.get("methodology_version") != VERSION
            or history.get("asset") != "eth" or history.get("release_id") != release_id or history.get("series_type") != "reconstructed"):
        raise ValueError("Core v0.2 candidate differs from verified parents")
    valid = [r for r in rows if r["score"] is not None]
    if (manifest["rows"] != len(rows) or manifest["score_rows"] != len(valid) or manifest["first_observation_date"] != rows[0]["date"]
            or manifest["last_observation_date"] != rows[-1]["date"] or manifest["first_score_date"] != valid[0]["date"]
            or manifest["last_valid_score_date"] != valid[-1]["date"] or manifest["last_valid_score"] != valid[-1]["score"]
            or manifest["missing_dates"] != [r["date"] for r in rows if not r["source_row_present"]]
            or manifest["pending_dates"] != [r["date"] for r in rows if not r["period_closed_at_retrieval"]]):
        raise ValueError("Core v0.2 coverage metadata mismatch")
    root = public/"data"/PREFIX; previous = read_json(root/"latest.json") if (root/"latest.json").exists() else None
    changed, new = [], [r["date"] for r in rows]
    if previous:
        if (not re.fullmatch(r"core10-[a-f0-9]{20}", previous.get("release_id", "")) or previous.get("methodology_version") != VERSION
                or previous.get("manifest_url") != f"/data/{PREFIX}/releases/{previous['release_id']}/manifest.json"):
            raise ValueError("previous Core v0.2 pointer invalid")
        old_folder = root/"releases"/previous["release_id"]
        if digest((old_folder/"manifest.json").read_bytes()) != previous["manifest_sha256"]:
            raise ValueError("previous Core v0.2 manifest changed")
        verify_release(old_folder)
        if previous["release_id"] == release_id:
            if read_json(old_folder/"history.json") != history or read_json(old_folder/"research.json") != report:
                raise ValueError("immutable Core v0.2 release conflict")
            return "unchanged"
        old = {r["date"]: r for r in read_json(old_folder/"history.json")["rows"]}
        if not set(old).issubset({r["date"] for r in rows}):
            raise ValueError("Core v0.2 calendar shrank")
        for r in rows:
            before = old.get(r["date"])
            if before and any(before["components"][m] is not None and r["components"][m] is None for m in IDS):
                raise ValueError("Core v0.2 lost previously usable components")
            if before and before["score"] is not None and r["score"] is None:
                raise ValueError("Core v0.2 lost a published valid score")
        changed = [r["date"] for r in rows if r["date"] in old and r != old[r["date"]]]
        new = [r["date"] for r in rows if r["date"] not in old]
    if report != evaluate(rows):
        raise ValueError("Core v0.2 evaluation differs from verified observations")
    revision = {"previous_release_id": previous["release_id"] if previous else None,
                "reason": "initial_reconstructed_release" if not previous else "parent_lineage_or_engine_updated",
                "changed_dates": changed, "new_observation_dates": new, "previous_releases_preserved": True}
    manifest = {**manifest, "revision": revision}; target = root/"releases"/release_id; target.mkdir(parents=True, exist_ok=True)
    for name, content in (("history.json", (folder/"history.json").read_bytes()), ("research.json", (folder/"research.json").read_bytes()), ("manifest.json", encode(manifest))):
        if (target/name).exists() and (target/name).read_bytes() != content:
            raise ValueError("immutable Core v0.2 release conflict")
        (target/name).write_bytes(content)
    atomic_json(root/"revisions"/(release_id+".json"), revision, immutable=True)
    last = rows[-1]
    if last["score"] is not None:
        ledger = root/"publications"/(last["date"]+".json")
        if not ledger.exists():
            atomic_json(ledger, {"observation_date": last["date"], "recorded_at": datetime.now(timezone.utc).isoformat(),
                                 "public_available_at": None, "source_available_at": None, "release_id": release_id,
                                 "methodology_version": VERSION, "score": last["score"], "components": last["components"], "historical_backfill_is_as_published": False}, immutable=True)
    atomic_json(root/"latest.json", {"schema_version": "1.0.0", "release_id": release_id, "methodology_version": VERSION,
                                   "manifest_url": f"/data/{PREFIX}/releases/{release_id}/manifest.json", "manifest_sha256": digest(encode(manifest))})
    return "published" if not previous else "revised"


def daily(public=ROOT/"public", output=ROOT/"data/computed/core-v2"):
    root = public/"data"/PREFIX; stage = "verified_parent_join"
    try:
        folder = build(public, output); stage = "publication_validation"; outcome = publish(folder, public)
        manifest = read_json(folder/"manifest.json")
        if manifest["last_valid_score_date"] < manifest["last_observation_date"]:
            outcome = "source_pending"
        failure = None
    except Exception:
        outcome, failure = "failed", stage
    pointer = read_json(root/"latest.json") if (root/"latest.json").exists() else None
    atomic_json(root/"status.json", {"methodology_version": VERSION, "release_id": pointer["release_id"] if pointer else None, "outcome": outcome,
                                   "last_attempt_at": datetime.now(timezone.utc).isoformat(), "failure_stage": failure,
                                   "schedule_vi": "Sau diagnostics và ECO 7 của batch Core 10:17/14:17 và network 10:47/14:47 giờ Việt Nam"})
    if failure:
        raise RuntimeError("Core v0.2 update failed; previous release preserved") from None
    return {"outcome": outcome, "release_id": pointer["release_id"]}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(); parser.add_argument("--public", type=Path, default=ROOT/"public")
    parser.add_argument("--output", type=Path, default=ROOT/"data/computed/core-v2")
    args = parser.parse_args(); print(__import__("json").dumps(daily(args.public, args.output)))
