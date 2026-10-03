"""Pinned parent snapshots -> immutable, licensed raw diagnostic publications."""
import argparse
from datetime import date, datetime, timezone
import math
from pathlib import Path
import re
import subprocess
import sys
from urllib.parse import urlparse, parse_qs
from .pipeline import ROOT, digest, encode, read_json, load_snapshot, verify_release
from .core import compute as compute_core
from .daily import atomic_json
from .seven import parent
from .diagnostics import VERSION, PROTOCOL, PROTOCOL_HASH, IDS, protocol, compute_diagnostics, describe, validate_history

ATTRIBUTION = {"source": "Coin Metrics Community Data", "licence": "CC BY-NC 4.0",
               "licence_url": "https://creativecommons.org/licenses/by-nc/4.0/",
               "source_url": "https://docs.coinmetrics.io/packages/coin-metrics-community-data",
               "scope": "noncommercial_research_preview", "changes": "Derived NUPL and signed 30-day changes; no normalized score",
               "disclaimer": "Giá trị nghiên cứu có thể sửa hồi cứu; không phải xác suất hoặc khuyến nghị."}
CORE_FIELDS = ("PriceUSD", "CapMrktCurUSD", "SplyCur", "CapMVRVCur")
NETWORK_FIELDS = ("AdrActCnt", "AdrBalCnt", "CapMrktCurUSD", "SplyCur", "SplyExNtv", "TxTfrCnt")


def _parents(public):
    result = {}
    for kind, prefix, version, pattern in (("core", "", "core-v0.1.0", r"core-[a-f0-9]{20}"),
                                            ("proxies", "network-proxies", "network-proxies-v0.1.0", r"proxy-[a-f0-9]{20}")):
        reference, rows = parent(public, prefix, version, pattern)
        result[kind] = (reference, read_json(public/reference["manifest_url"].lstrip("/")), rows)
    return result


def verified_input(folder, receipt_path, reference, kind):
    if kind not in ("core", "proxies"):
        raise ValueError("unknown diagnostic parent")
    folder, receipt_path = Path(folder), Path(receipt_path)
    rows, source = load_snapshot(folder)
    public_manifest = reference[1]
    if source["snapshot"]["canonical_sha256"] != public_manifest["snapshot_sha256"] or source["retrieved_at"] != public_manifest["retrieved_at"]:
        raise ValueError("input snapshot does not match the pinned parent")
    if kind == "proxies" and digest((folder/"manifest.json").read_bytes()) != public_manifest["source_manifest_sha256"]:
        raise ValueError("network source manifest differs from parent")
    fields = CORE_FIELDS if kind == "core" else NETWORK_FIELDS
    if set(source["metrics"]) != set(fields):
        raise ValueError("input field contract mismatch")
    raw = {}
    for page in source["pages"]:
        url = urlparse(page["request_url"]); query = parse_qs(url.query)
        if (url.scheme != "https" or url.netloc != "community-api.coinmetrics.io" or url.path != "/v4/timeseries/asset-metrics"
                or query.get("assets") != ["eth"] or query.get("frequency") != ["1d"]
                or set(query.get("metrics", [""])[0].split(",")) != set(fields) or "api_key" in query):
            raise ValueError("input source request differs from Community ETH contract")
        for item in read_json(folder/page["raw_file"])["data"]:
            day = item["time"][:10]
            if day in raw: raise ValueError("duplicate private raw observation")
            raw[day] = (item, page)
    for row in rows:
        item, page = raw[row["observation_date"]]
        if (row.get("asset") != item["asset"] or row["source_timestamp"] != item["time"]
                or row["metrics"] != {m: item.get(m) for m in fields}
                or row["source_page_sha256"] != page["response_sha256"] or row["retrieved_at"] != page["completed_at"]):
            raise ValueError("canonical input differs from its raw provenance")
        if kind == "proxies" and row.get("metric_status") != {m: {"status": item.get(m+"-status"), "status_time": item.get(m+"-status-time")} for m in fields}:
            raise ValueError("input source flags were changed")
    if len(raw) != len(rows):
        raise ValueError("private raw/canonical row coverage differs")
    if kind == "proxies":
        if source.get("source_rights") != {"licence": "CC BY-NC 4.0", "scope": "noncommercial_research_preview", "policy": "ADR-005"}:
            raise ValueError("network input licence/scope changed")
        catalog = source["community_catalog"]
        if catalog["file"] != "community-catalog.json" or digest((folder/catalog["file"]).read_bytes()) != catalog["sha256"]:
            raise ValueError("Community catalogue checksum mismatch")
        available = next(r["metrics"] for r in read_json(folder/catalog["file"])["data"] if r["asset"] == "eth")
        if any(not any(m["metric"] == field and any(f["frequency"] == "1d" and f.get("community") is True for f in m["frequencies"]) for m in available) for field in fields):
            raise ValueError("diagnostic fields were not available in Community")
    receipt = read_json(receipt_path)
    files = {f.name: f for f in folder.iterdir() if f.is_file()}
    objects = receipt.get("objects", [])
    if (receipt.get("status") not in ("restored_private_snapshot", "uploaded_private_snapshot") or receipt.get("bucket") != "eco-eth-private"
            or receipt.get("snapshot_sha256") != source["snapshot"]["canonical_sha256"]
            or receipt.get("file_count") != len(files) or len(objects) != len(files) or len({o["object_key"] for o in objects}) != len(files)):
        raise ValueError("private input backup/readback receipt is invalid")
    prefix = "raw/coinmetrics/"+folder.name+"/"
    for obj in objects:
        name = obj["object_key"].removeprefix(prefix)
        if (not obj["object_key"].startswith(prefix) or name not in files or not obj.get("readback_verified")
                or obj["sha256"] != digest(files[name].read_bytes()) or obj["bytes"] != files[name].stat().st_size):
            raise ValueError("private input readback hash mismatch")
    if kind == "core":
        replay = compute_core(rows, end=date.fromisoformat(public_manifest["last_requested_date"]))
        published = reference[2]
        if len(replay) != len(published): raise ValueError("Core replay calendar differs")
        for a, b in zip(replay, published):
            if a["date"] != b["date"]: raise ValueError("Core replay date differs")
            for key, left, right in [("score", a["score"], b["score"]), ("price", a["price_usd"], b["price_usd"])] + [(m, a["components"][m]["score"], b["components"][m]) for m in ("E1", "E5", "E6", "E7")]:
                if left is None or right is None:
                    if left != right: raise ValueError("Core replay null differs")
                elif not math.isclose(left, right, rel_tol=1e-12, abs_tol=1e-8):
                    raise ValueError("Core replay values differ from the published parent")
    return rows, source, {"canonical_sha256": source["snapshot"]["canonical_sha256"], "source_manifest_sha256": digest((folder/"manifest.json").read_bytes()),
                          "receipt_sha256": digest(receipt_path.read_bytes()), "objects_readback_verified": True, "file_count": len(files)}


def expected(public, inputs):
    config = protocol()
    if digest((ROOT/"docs/evidence/network-proxies-source-2026-10-03.json").read_bytes()) != config["source_evidence_sha256"]:
        raise ValueError("frozen Community source evidence changed")
    evidence = read_json(ROOT/"docs/evidence/network-proxies-source-2026-10-03.json")
    if (evidence.get("access_verified") is not True or evidence.get("licence", {}).get("derived_research_publication") is not True
            or evidence["licence"].get("commercial_use") is not False):
        raise ValueError("Community diagnostic source rights are not verified")
    policy = read_json(ROOT/"configs/release-policy.json")
    if (policy.get("status") != "approved_noncommercial_research" or policy.get("raw_public") is not False
            or policy.get("commercial_use") is not False or policy.get("license") != "CC BY-NC 4.0"):
        raise ValueError("diagnostic Community licence gate failed")
    parents = _parents(public); datasets = {}; proofs = {}
    for kind in ("core", "proxies"):
        datasets[kind], _, proofs[kind] = verified_input(inputs[kind]["snapshot"], inputs[kind]["receipt"], parents[kind], kind)
    first = min(parents[k][2][0]["date"] for k in parents)
    end = max(parents[k][2][-1]["date"] for k in parents)
    rows = compute_diagnostics(datasets["core"], datasets["proxies"], first=first, end=end)
    return rows, describe(rows), {k: v[0] for k, v in parents.items()}, proofs


def engine_hash():
    return digest(b"".join((ROOT/p).read_text(encoding="utf-8").encode("utf-8") for p in ("eco/diagnostics.py", "eco/diagnostic_pipeline.py", "eco/core.py")))


def build(public, output, inputs):
    rows, report, parents, proofs = expected(public, inputs)
    identity = {"methodology_version": VERSION, "protocol_sha256": PROTOCOL_HASH, "engine_sha256": engine_hash(), "parents": parents}
    release_id = "diagnostic-"+digest(encode(identity))[:20]; folder = output/release_id
    history = {"schema_version": "1.0.0", "release_id": release_id, "methodology_version": VERSION, "asset": "eth", "frequency": "1d",
               "series_type": "reconstructed", "composite_score": None, "metric_definitions": protocol()["metrics"], "rows": rows}
    if folder.exists():
        verify_release(folder)
        if read_json(folder/"history.json") != history or read_json(folder/"research.json") != report:
            raise ValueError("immutable private diagnostic candidate conflict")
        return folder
    manifest = {"schema_version": "1.0.0", "release_id": release_id, **identity, "protocol": PROTOCOL, "asset": "eth", "series_type": "reconstructed",
                "role": "raw_diagnostics_only", "normalizer": None, "composite_score": None, "core_promotion": False,
                "computed_at": datetime.now(timezone.utc).isoformat(), "source_available_at": None, "rows": len(rows), "first_date": rows[0]["date"],
                "last_observation_date": rows[-1]["date"], "coverage": report["coverage"], "attribution": ATTRIBUTION, "private_inputs_verified": proofs,
                "limitations": protocol()["limitations"], "files": {"history.json": digest(encode(history)), "research.json": digest(encode(report))}}
    validate_history(history, manifest, report)
    folder.mkdir(parents=True)
    for name, value in (("history.json", history), ("research.json", report), ("manifest.json", manifest), ("inputs-private.json", inputs)):
        (folder/name).write_bytes(encode(value))
    return folder


def publish(folder, public):
    protocol(); manifest = verify_release(folder); release_id = manifest["release_id"]
    if (not re.fullmatch(r"diagnostic-[a-f0-9]{20}", release_id) or set(manifest["files"]) != {"history.json", "research.json"}
            or manifest.get("methodology_version") != VERSION or manifest.get("protocol_sha256") != PROTOCOL_HASH or manifest.get("engine_sha256") != engine_hash()
            or manifest.get("role") != "raw_diagnostics_only" or manifest.get("normalizer") is not None or manifest.get("composite_score") is not None
            or manifest.get("core_promotion") is not False or manifest.get("attribution") != ATTRIBUTION):
        raise ValueError("diagnostic publication gate failed")
    history, report = read_json(folder/"history.json"), read_json(folder/"research.json")
    validate_history(history, manifest, report)
    rows, expected_report, parents, proofs = expected(public, read_json(folder/"inputs-private.json"))
    if history["rows"] != rows or report != expected_report or manifest["parents"] != parents or manifest["private_inputs_verified"] != proofs:
        raise ValueError("diagnostic candidate differs from verified private parents")
    root = public/"data/diagnostics"; root.mkdir(parents=True, exist_ok=True)
    previous = read_json(root/"latest.json") if (root/"latest.json").exists() else None
    changed, new = [], [r["date"] for r in rows]
    if previous:
        if (not re.fullmatch(r"diagnostic-[a-f0-9]{20}", previous.get("release_id", ""))
                or previous.get("manifest_url") != f"/data/diagnostics/releases/{previous['release_id']}/manifest.json"):
            raise ValueError("previous diagnostic pointer is invalid")
        old_folder = root/"releases"/previous["release_id"]
        if digest((old_folder/"manifest.json").read_bytes()) != previous["manifest_sha256"]: raise ValueError("previous diagnostic manifest changed")
        verify_release(old_folder)
        if previous["release_id"] == release_id: return "unchanged"
        old = {r["date"]: r for r in read_json(old_folder/"history.json")["rows"]}
        if not set(old).issubset({r["date"] for r in rows}):
            raise ValueError("diagnostic revision lost published observations")
        changed = [r["date"] for r in rows if r["date"] in old and r != old[r["date"]]]
        new = [r["date"] for r in rows if r["date"] not in old]
    revision = {"previous_release_id": previous["release_id"] if previous else None, "reason": "initial_reconstructed_release" if not previous else "parent_lineage_or_observations_updated",
                "changed_dates": changed, "new_observation_dates": new, "previous_releases_preserved": True}
    manifest = {**manifest, "revision": revision}; target = root/"releases"/release_id; target.mkdir(parents=True, exist_ok=True)
    for name, content in (("history.json", (folder/"history.json").read_bytes()), ("research.json", (folder/"research.json").read_bytes()), ("manifest.json", encode(manifest))):
        if (target/name).exists() and (target/name).read_bytes() != content: raise ValueError("immutable diagnostic release conflict")
        (target/name).write_bytes(content)
    atomic_json(root/"revisions"/(release_id+".json"), revision, immutable=True)
    last = rows[-1]
    if any(m["value"] is not None for m in last["metrics"].values()):
        ledger = root/"publications"/(last["date"]+".json")
        if not ledger.exists(): atomic_json(ledger, {"observation_date": last["date"], "first_published_at": datetime.now(timezone.utc).isoformat(), "release_id": release_id,
                                                    "methodology_version": VERSION, "values": last["metrics"], "historical_backfill_is_as_published": False}, immutable=True)
    atomic_json(root/"latest.json", {"schema_version": "1.0.0", "release_id": release_id, "methodology_version": VERSION,
                                   "manifest_url": f"/data/diagnostics/releases/{release_id}/manifest.json", "manifest_sha256": digest(encode(manifest))})
    return "published" if not previous else "revised"


def status(public, outcome, stage=None):
    root = public/"data/diagnostics"; pointer = read_json(root/"latest.json") if (root/"latest.json").exists() else None
    atomic_json(root/"status.json", {"methodology_version": VERSION, "last_attempt_at": datetime.now(timezone.utc).isoformat(), "outcome": outcome,
                                  "release_id": pointer["release_id"] if pointer else None, "failure_stage": stage, "schedule_vi": "Sau batch Core 10:17/14:17 và network 10:47/14:47 giờ Việt Nam"})


def daily(public=ROOT/"public", output=ROOT/"data/computed/diagnostics"):
    stage = "verified_parent_restore"
    try:
        protocol(); references = _parents(public); inputs = {}; output.mkdir(parents=True, exist_ok=True)
        for kind, reference in references.items():
            source = reference[1]; stamp = source["retrieved_at"]; day = stamp[:10]
            name = f"coinmetrics-{'backfill' if kind == 'core' else 'network-proxies'}-{day}-{stamp.replace(':', '').replace('.', '')}"
            result = subprocess.run(["node", str(ROOT/"scripts/restore-private-snapshot-r2.mjs"), "raw/coinmetrics/"+name, source["snapshot_sha256"]], cwd=ROOT, check=True, capture_output=True, text=True, timeout=600)
            receipt = output/(kind+"-readback.json"); receipt.write_bytes(result.stdout.encode("utf-8"))
            inputs[kind] = {"snapshot": read_json(receipt)["snapshot_directory"], "receipt": str(receipt.resolve())}
        stage = "compute_validate"; folder = build(public, output, inputs)
        stage = "publish"; outcome = publish(folder, public); status(public, outcome)
        print(encode({"outcome": outcome, "release_id": folder.name, "coverage": read_json(folder/"manifest.json")["coverage"]}).decode(), end="")
        return 0
    except Exception:
        status(public, "failed", stage)
        print("Diagnostic update failed; retained the last verified publication.", file=sys.stderr)
        return 1


def main():
    parser = argparse.ArgumentParser(); parser.add_argument("command", choices=("daily", "build", "publish")); parser.add_argument("folder", nargs="?")
    parser.add_argument("--public", type=Path, default=ROOT/"public"); parser.add_argument("--output", type=Path, default=ROOT/"data/computed/diagnostics")
    for kind in ("core", "proxies"):
        parser.add_argument("--"+kind+"-snapshot", type=Path); parser.add_argument("--"+kind+"-receipt", type=Path)
    args = parser.parse_args()
    if args.command == "daily": return daily(args.public, args.output)
    if args.command == "publish":
        outcome = publish(Path(args.folder), args.public); status(args.public, outcome); print(outcome); return 0
    inputs = {k: {"snapshot": str(getattr(args, k+"_snapshot").resolve()), "receipt": str(getattr(args, k+"_receipt").resolve())} for k in ("core", "proxies")}
    folder = build(args.public, args.output, inputs); print(encode({"candidate": str(folder), "coverage": read_json(folder/"manifest.json")["coverage"]}).decode(), end=""); return 0


if __name__ == "__main__":
    raise SystemExit(main())
