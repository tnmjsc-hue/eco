"""Verified private inputs -> immutable, licensed ETH proxy research releases."""
import argparse
from datetime import date, datetime, timedelta, timezone
import json
import math
from pathlib import Path
from urllib.parse import urlparse, parse_qs
import shutil
import subprocess
from .pipeline import ROOT, digest, encode, read_json, load_snapshot, verify_release
from .proxies import VERSION, PROTOCOL, INPUTS, METRICS, compute_proxies, evaluate_proxies, coverage

PROTOCOL_HASH = "4f3b9ebdf2ce0c69704174c47cd5183731942b1051321e33596d80d39f71af2c"
SOURCE_EVIDENCE_HASH = "5d35aa2fa85e6a8ef7d6e538d8f7fc8ac456f366b3efedac54cd01b07200e72d"
SOURCE_EVIDENCE = ROOT / "docs/evidence/network-proxies-source-2026-10-03.json"
ATTRIBUTION = {"source": "Coin Metrics Community Data", "licence": "CC BY-NC 4.0",
               "licence_url": "https://creativecommons.org/licenses/by-nc/4.0/",
               "source_url": "https://gitbook-docs.coinmetrics.io/packages/coin-metrics-community-data",
               "scope": "noncommercial_research_preview", "changes": "SMA, ratios, logarithms and causal q05/q95 normalization",
               "disclaimer": "Dữ liệu và phép dẫn xuất không được bảo đảm; điểm không phải xác suất."}

def same_row(left, right):
    if any(left.get(k) != right.get(k) for k in ("date","source_row_present")):
        return False
    for metric in METRICS:
        a,b = left["metrics"][metric],right["metrics"][metric]
        if any(a.get(k) != b.get(k) for k in ("raw_reason","score_reason","source_flags")):
            return False
        for key in ("raw","value","score"):
            if a[key] is None or b[key] is None:
                if a[key] != b[key]: return False
            elif not math.isclose(a[key],b[key],rel_tol=1e-12 if key=="value" else 0,
                                  abs_tol=1e-8 if key=="score" else 1e-12):
                return False
    return True

def _protocol():
    config = read_json(ROOT / "configs/research/network-proxies-v0.1.0.json")
    if digest(encode(config)) != PROTOCOL_HASH:
        raise ValueError("frozen network proxy protocol changed")
    if digest(SOURCE_EVIDENCE.read_bytes()) != SOURCE_EVIDENCE_HASH:
        raise ValueError("source/licence evidence changed")
    evidence = read_json(SOURCE_EVIDENCE)
    if (not evidence["access_verified"] or not evidence["licence"]["derived_research_publication"]
            or evidence["licence"]["scope"] != "noncommercial_research_preview"
            or evidence["metrics"] != list(INPUTS)):
        raise ValueError("Community research licence gate failed")
    return config

def verified_snapshot(folder, receipt_path):
    rows, manifest = load_snapshot(folder)
    if manifest["metrics"] != list(INPUTS) or manifest["start_date_requested"] != "2015-07-30":
        raise ValueError("proxy source contract mismatch")
    expected = (date.fromisoformat(manifest["end_date_requested"])-date(2015,7,30)).days+1
    if len(rows) != expected or manifest["quality"]["missing_row_date_count"] != 0:
        raise ValueError("incomplete proxy calendar coverage")
    if manifest.get("source_rights") != {"licence": "CC BY-NC 4.0", "scope": "noncommercial_research_preview", "policy": "ADR-005"}:
        raise ValueError("snapshot research rights metadata mismatch")
    catalog_file = manifest["community_catalog"]["file"]
    if catalog_file != "community-catalog.json" or digest((folder/catalog_file).read_bytes()) != manifest["community_catalog"]["sha256"]:
        raise ValueError("available Community catalog checksum mismatch")
    catalog = read_json(folder/catalog_file)
    available = next((r["metrics"] for r in catalog["data"] if r.get("asset") == "eth"), [])
    if any(not any(m["metric"] == field and any(f["frequency"] == "1d" and f.get("community") is True
           for f in m["frequencies"]) for m in available) for field in INPUTS):
        raise ValueError("snapshot fields not available in Community")
    raw = {}
    for page in manifest["pages"]:
        url = urlparse(page["request_url"])
        query = parse_qs(url.query)
        if (url.scheme != "https" or url.netloc != "community-api.coinmetrics.io"
                or url.path != "/v4/timeseries/asset-metrics" or query.get("assets") != ["eth"]
                or query.get("frequency") != ["1d"] or query.get("metrics") != [",".join(INPUTS)]
                or "api_key" in query):
            raise ValueError("proxy raw request does not use frozen Community contract")
        for row in read_json(folder/page["raw_file"])["data"]:
            if row["time"][:10] in raw:
                raise ValueError("duplicate raw date")
            raw[row["time"][:10]] = (row,page)
    for row in rows:
        source,page = raw[row["observation_date"]]
        statuses = {m:{"status":source.get(m+"-status"),"status_time":source.get(m+"-status-time")} for m in INPUTS}
        if (row["metrics"] != {m:source.get(m) for m in INPUTS} or row.get("metric_status") != statuses
                or row["source_page_sha256"] != page["response_sha256"] or row["retrieved_at"] != page["completed_at"]
                or row["asset"] != source["asset"] or row["source_timestamp"] != source["time"]):
            raise ValueError("canonical proxy row does not match its raw provenance")
        if any(s["status"] is not None and not isinstance(s["status"],str) for s in statuses.values()):
            raise ValueError("invalid source status flag")
    receipt = read_json(receipt_path)
    if (receipt.get("status") != "uploaded_private_snapshot" or receipt.get("bucket") != "eco-eth-private"
            or receipt.get("snapshot_sha256") != manifest["snapshot"]["canonical_sha256"]):
        raise ValueError("private backup is unverified")
    files = {p.name:p for p in folder.iterdir() if p.is_file()}
    objects = receipt.get("objects", [])
    prefix = f"raw/coinmetrics/{folder.name}/"
    if (len(objects) != len(files) or receipt.get("file_count") != len(files)
            or len({o["object_key"] for o in objects}) != len(files)):
        raise ValueError("backup receipt must cover every snapshot object exactly once")
    for item in objects:
        key = item["object_key"]
        filename = key.removeprefix(prefix)
        if (not key.startswith(prefix) or filename not in files or not item.get("readback_verified")
                or item["sha256"] != digest(files[filename].read_bytes()) or item["bytes"] != files[filename].stat().st_size):
            raise ValueError("private readback checksum mismatch")
    return rows, manifest

def build(snapshot, receipt, core_release, output, *, replicates=10000):
    config = _protocol()
    rows, source = verified_snapshot(snapshot, receipt)
    core_manifest = verify_release(core_release)
    if core_manifest.get("methodology_version") != "core-v0.1.0" or core_manifest.get("series_type") != "reconstructed":
        raise ValueError("wrong Core evaluation baseline")
    core_history = read_json(core_release / "history.json")
    engine_hash = digest(b"".join((ROOT/p).read_bytes() for p in (
        "eco/proxies.py", "eco/proxy_pipeline.py", "eco/core.py", "eco/research.py")))
    identity = {"methodology_version": VERSION, "snapshot_sha256": source["snapshot"]["canonical_sha256"],
                "protocol_sha256": PROTOCOL_HASH, "engine_sha256": engine_hash,
                "core_history_sha256": core_manifest["files"]["history.json"], "bootstrap_replicates": replicates,
                "source_evidence_sha256": SOURCE_EVIDENCE_HASH}
    release_id = "proxy-" + digest(encode(identity))[:20]
    target = output / release_id
    computed = compute_proxies(rows, source["end_date_requested"])
    research = evaluate_proxies(core_history["rows"], computed, replicates=replicates)
    history = {"schema_version": "1.0.0", "release_id": release_id, "methodology_version": VERSION,
               "asset": "eth", "series_type": "reconstructed", "composite_score": None,
               "attribution": ATTRIBUTION, "metric_definitions": config["metrics"], "rows": computed}
    files = {"history.json": encode(history), "research.json": encode(research)}
    manifest = {"schema_version": "1.0.0", "release_id": release_id, **identity, "protocol": PROTOCOL,
                "asset": "eth", "series_type": "reconstructed", "research_only": True, "core_promotion": False,
                "rows": len(computed), "first_observation_date": computed[0]["date"], "last_observation_date": computed[-1]["date"],
                "retrieved_at": source["retrieved_at"], "computed_at": datetime.now(timezone.utc).isoformat(),
                "source_available_at": None, "coverage": coverage(computed), "metric_definitions": config["metrics"],
                "private_backup": {"bucket": "eco-eth-private", "all_objects_readback_verified": True, "file_count": read_json(receipt)["file_count"],
                                   "receipt_sha256": digest(receipt.read_bytes())},
                "source_manifest_sha256": digest((snapshot/"manifest.json").read_bytes()),
                "community_catalog_sha256": source["community_catalog"]["sha256"],
                "source_quality": source["quality"], "core_baseline_release": core_manifest["release_id"],
                "attribution": ATTRIBUTION, "limitations": config["limitations"],
                "files": {name:digest(content) for name,content in files.items()}}
    if target.exists():
        old = verify_release(target)
        if old.get("files") != manifest["files"] or any(old.get(k) != v for k,v in identity.items()):
            raise ValueError("immutable proxy release conflict")
        return target
    target.mkdir(parents=True)
    for name,content in files.items():
        (target/name).write_bytes(content)
    (target/"manifest.json").write_bytes(encode(manifest))
    verify_release(target)
    return target

def publish(folder, public):
    _protocol()
    manifest = verify_release(folder)
    release_id = manifest["release_id"]
    if (not release_id.startswith("proxy-") or len(release_id) != 26
            or any(c not in "0123456789abcdef" for c in release_id[6:]) or set(manifest["files"]) != {"history.json","research.json"}
            or manifest.get("methodology_version") != VERSION or manifest.get("protocol") != PROTOCOL
            or manifest.get("asset") != "eth" or manifest.get("series_type") != "reconstructed"
            or manifest.get("protocol_sha256") != PROTOCOL_HASH or manifest.get("source_evidence_sha256") != SOURCE_EVIDENCE_HASH
            or manifest.get("bootstrap_replicates") != 10000 or manifest.get("core_promotion") is not False
            or manifest.get("attribution") != ATTRIBUTION or manifest.get("research_only") is not True
            or not manifest.get("private_backup",{}).get("all_objects_readback_verified")):
        raise ValueError("proxy research publication gate failed")
    history = read_json(folder/"history.json")
    research = read_json(folder/"research.json")
    if (history.get("methodology_version") != VERSION or history.get("release_id") != release_id
            or history.get("composite_score") is not None or history.get("asset") != "eth"
            or research.get("protocol") != PROTOCOL or research.get("bootstrap",{}).get("replicates") != 10000
            or research.get("decision") != "publish_research_metrics_only_no_core_promotion"):
        raise ValueError("proxy data publication contract failed")
    root = public / "data/network-proxies"
    pointer_path = root / "latest.json"
    previous = read_json(pointer_path) if pointer_path.exists() else None
    target = root / "releases" / release_id
    if previous and previous["release_id"] == release_id:
        if digest((target/"manifest.json").read_bytes()) != previous["manifest_sha256"]:
            raise ValueError("public proxy manifest changed")
        verify_release(target)
        return "unchanged"
    # Attach revision metadata only to the new public manifest, preserve previous assets.
    revision = None
    if previous:
        old_folder = root/"releases"/previous["release_id"]
        if digest((old_folder/"manifest.json").read_bytes()) != previous["manifest_sha256"]:
            raise ValueError("previous manifest checksum mismatch")
        verify_release(old_folder)
        old_manifest = read_json(old_folder/"manifest.json")
        before = {r["date"]:r for r in read_json(old_folder/"history.json")["rows"]}
        after = read_json(folder/"history.json")["rows"]
        dates = {r["date"] for r in after}
        if set(before)-dates or any(before[r["date"]]["metrics"][m]["score"] is not None
           and r["metrics"][m]["score"] is None for r in after if r["date"] in before for m in METRICS):
            raise ValueError("provider lost previously usable proxy observations")
        changed = [r["date"] for r in after if r["date"] in before and not same_row(r,before[r["date"]])]
        added = sorted(dates-set(before))
        same_engine = manifest["engine_sha256"] == old_manifest["engine_sha256"]
        same_baseline = manifest["core_history_sha256"] == old_manifest["core_history_sha256"]
        if not changed and not added and same_engine and same_baseline:
            return "unchanged"
        # Carry prior published numbers verbatim across equivalent runtime rounding.
        for i,row in enumerate(after):
            if row["date"] in before and same_row(row,before[row["date"]]):
                after[i] = before[row["date"]]
        history["rows"] = after
        revision = {"previous_release_id":previous["release_id"], "changed_dates":changed,
                    "added_dates":added,
                    "reason":"source_or_engine_revision" if changed else "new_closed_days" if added else "engine_or_baseline_revision"}
    if target.exists():
        raise ValueError("existing immutable public release must not be repointed silently")
    manifest["revision"] = revision
    target.mkdir(parents=True)
    (target/"history.json").write_bytes(encode(history))
    manifest["files"]["history.json"] = digest((target/"history.json").read_bytes())
    shutil.copyfile(folder/"research.json",target/"research.json")
    (target/"manifest.json").write_bytes(encode(manifest))
    verify_release(target)
    pointer = {"release_id":release_id, "methodology_version": VERSION,
               "manifest_url":f"/data/network-proxies/releases/{release_id}/manifest.json",
               "manifest_sha256":digest((target/"manifest.json").read_bytes())}
    temp = root/"latest.tmp"
    temp.write_bytes(encode(pointer)); temp.replace(pointer_path)
    return "revised" if revision and revision["changed_dates"] else "published"

def _status(public, outcome, release_id=None, failure_stage=None):
    folder = public/"data/network-proxies"; folder.mkdir(parents=True,exist_ok=True)
    content = {"methodology_version":VERSION,"last_attempt_at":datetime.now(timezone.utc).isoformat(),
               "outcome":outcome,"release_id":release_id,"schedule_utc":"47 3,7 * * *",
               "schedule_vi":"10:47 và 14:47 giờ Việt Nam", "failure_stage":failure_stage}
    (folder/"status.json").write_bytes(encode(content))

def daily(public):
    stage = "fetch"
    try:
        fetched = subprocess.run(["node",str(ROOT/"scripts/proxy-coinmetrics.mjs"),"backfill"],cwd=ROOT,
                                 check=True,capture_output=True,text=True,timeout=600)
        marker = next(line for line in fetched.stdout.splitlines() if line.startswith("PROXY_SNAPSHOT="))
        snapshot = Path(marker.split("=",1)[1]); stage = "private_backup"
        backup = subprocess.run(["node",str(ROOT/"scripts/upload-private-snapshot-r2.mjs"),str(snapshot)],cwd=ROOT,
                                check=True,capture_output=True,text=True,timeout=600)
        receipt = ROOT/"data/computed"/(snapshot.name+"-backup.json")
        receipt.parent.mkdir(parents=True,exist_ok=True); receipt.write_text(backup.stdout,encoding="utf-8")
        core_pointer = read_json(public/"data/latest.json")
        core_release = public/"data/releases"/core_pointer["release_id"]
        if digest((core_release/"manifest.json").read_bytes()) != core_pointer["manifest_sha256"]:
            raise ValueError("Core baseline pointer checksum mismatch")
        stage = "compute_evaluate"
        folder = build(snapshot,receipt,core_release,ROOT/"data/computed/network-proxies")
        stage = "publish"; outcome = publish(folder,public)
        current = read_json(public/"data/network-proxies/latest.json")["release_id"]
        _status(public,outcome,current)
        print(json.dumps({"status":outcome,"release_id":current}))
    except Exception:
        # Upstream errors/URLs stay private. Keep the last verified public pointer.
        pointer = public/"data/network-proxies/latest.json"
        _status(public,"failed",read_json(pointer)["release_id"] if pointer.exists() else None,stage)
        raise RuntimeError(f"network proxy update failed at {stage}; previous release preserved") from None

def main():
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command",required=True)
    b = sub.add_parser("build"); b.add_argument("snapshot",type=Path); b.add_argument("receipt",type=Path)
    b.add_argument("core_release",type=Path); b.add_argument("--output",type=Path,default=ROOT/"data/computed/network-proxies")
    p = sub.add_parser("publish"); p.add_argument("folder",type=Path); p.add_argument("--public",type=Path,default=ROOT/"public")
    d = sub.add_parser("daily"); d.add_argument("--public",type=Path,default=ROOT/"public")
    args = parser.parse_args()
    if args.command == "build": print(build(args.snapshot,args.receipt,args.core_release,args.output))
    elif args.command == "publish": print(publish(args.folder,args.public))
    else: daily(args.public)

if __name__ == "__main__":
    main()
