"""Verify licensed E9 snapshots and produce immutable private research only."""

import argparse
from datetime import date, datetime, timedelta, timezone
import json
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from .core import compute
from .nvt import METRICS, PROTOCOL, VERSION, compute_nvt, evaluate_nvt
from .pipeline import ROOT, digest, encode, load_snapshot, read_json

PROTOCOL_HASH = "f7c2efc2882de1dc6073ecf49ffe811894ccd5418cc18415f3bb61f4c74d7f85"


def verify_rights(path, now=None):
    now = now or datetime.now(timezone.utc).date()
    content = Path(path).read_bytes()
    rights = json.loads(content)
    if (rights.get("verification_status") != "verified" or rights.get("provider") != "coinmetrics_network_data"
            or rights.get("asset") != "eth" or rights.get("frequency") != "1d"
            or rights.get("metrics") != list(METRICS) or rights.get("private_cache") is not True
            or rights.get("private_research") is not True
            or not date.fromisoformat(rights["valid_from"]) <= now <= date.fromisoformat(rights["valid_until"])):
        raise ValueError("E9 licence scope is missing, expired or incompatible")
    evidence = (Path(path).resolve().parent / rights["evidence_file"]).read_bytes()
    if digest(evidence) != rights.get("evidence_sha256"):
        raise ValueError("E9 licence evidence checksum mismatch")
    return rights, digest(content)


def load_nvt_snapshot(directory, rights_file, now=None):
    directory = Path(directory)
    rights, rights_hash = verify_rights(rights_file, now)
    manifest = read_json(directory / "manifest.json")
    if (manifest.get("status"), manifest.get("provider"), manifest.get("asset"), manifest.get("frequency"),
            manifest.get("metrics"), manifest.get("authorization")) != (
            "complete", "coinmetrics_network_data", "eth", "1d", list(METRICS), "api_key_environment_server_only"):
        raise ValueError("E9 snapshot requires its own licensed ETH/1d adjusted USD pair contract")
    grant = manifest.get("source_rights", {})
    if (grant.get("rights_file_sha256") != rights_hash or grant.get("evidence_sha256") != rights["evidence_sha256"]
            or grant.get("private_cache") is not True or grant.get("private_research") is not True):
        raise ValueError("E9 snapshot is not bound to the verified licence")

    def checked_file(name, checksum):
        if not isinstance(name, str) or Path(name).name != name or "/" in name or "\\" in name:
            raise ValueError("E9 snapshot file path must be a filename")
        content = (directory / name).read_bytes()
        if digest(content) != checksum:
            raise ValueError("E9 snapshot checksum mismatch")
        return content

    canonical = checked_file(manifest["snapshot"]["canonical_file"], manifest["snapshot"]["canonical_sha256"])
    rows = [json.loads(line) for line in canonical.splitlines() if line]
    if not rows or len(rows) != manifest["snapshot"]["row_count"]:
        raise ValueError("E9 snapshot row count mismatch")
    source_rows = {}
    for page in manifest["pages"]:
        raw = checked_file(page["raw_file"], page["response_sha256"])
        url = urlparse(page["request_url"])
        params = parse_qs(url.query)
        if (url.scheme != "https" or url.netloc != "api.coinmetrics.io"
                or url.path != "/v4/timeseries/asset-metrics" or url.username or url.password
                or params.get("assets") != ["eth"] or params.get("metrics") != [",".join(METRICS)]
                or params.get("frequency") != ["1d"] or "api_key" in params or page.get("http_status") != 200):
            raise ValueError("E9 raw page request contract mismatch")
        payload = json.loads(raw)
        if "api_key" in payload or "api_key=" in (payload.get("next_page_url") or ""):
            raise ValueError("E9 raw page contains a credential field")
        for row in payload["data"]:
            if row["time"] in source_rows or row.get("asset") != "eth":
                raise ValueError("E9 raw pages have duplicate dates or wrong asset")
            source_rows[row["time"]] = (row, page)
    if len(source_rows) != len(rows):
        raise ValueError("E9 raw/canonical row count mismatch")
    retrieved = datetime.fromisoformat(manifest["retrieved_at"].replace("Z", "+00:00"))
    if retrieved.tzinfo is None:
        raise ValueError("E9 retrieval time requires timezone")
    closed_before = min(date.fromisoformat(manifest["as_of_utc"]), retrieved.astimezone(timezone.utc).date())
    if not rights["valid_from"] <= retrieved.date().isoformat() <= rights["valid_until"]:
        raise ValueError("E9 snapshot was retrieved outside the licence period")
    previous = None
    for row in rows:
        day = date.fromisoformat(row["observation_date"])
        timestamp = datetime.fromisoformat(row["source_timestamp"].replace("Z", "+00:00"))
        if (day >= closed_before or (previous is not None and day - previous != timedelta(days=1))
                or not row["source_timestamp"].endswith("Z")
                or timestamp.isoformat() != day.isoformat() + "T00:00:00+00:00"
                or row.get("period_end_utc") != (day + timedelta(days=1)).isoformat() + "T00:00:00Z"
                or row.get("source_available_at") is not None or set(row.get("metrics", {})) != set(METRICS)
                or row.get("asset") != "eth"):
            raise ValueError("E9 canonical calendar/schema/vintage contract mismatch")
        raw_row, page = source_rows.get(row["source_timestamp"], ({}, {}))
        if (row["metrics"] != {metric: raw_row.get(metric) for metric in METRICS}
                or row.get("source_page_sha256") != page.get("response_sha256")
                or row.get("retrieved_at") != page.get("completed_at")):
            raise ValueError("E9 canonical values or provenance differ from raw pages")
        previous = day
    if ((rows[0]["observation_date"], rows[-1]["observation_date"])
            != (manifest["snapshot"]["first_observation_date"], manifest["snapshot"]["last_observation_date"])
            or rows[0]["observation_date"] != manifest["start_date_requested"]
            or rows[-1]["observation_date"] != manifest["end_date_requested"]):
        raise ValueError("E9 full requested range is incomplete")
    return rows, manifest


def build_e9(core_snapshot, nvt_snapshot, rights_file):
    protocol = read_json(ROOT / "configs/research/e9-nvt-candidate-v0.1.0.json")
    if (digest(encode(protocol)) != PROTOCOL_HASH
            or protocol["methodology_version"] != VERSION or protocol["research_protocol_version"] != PROTOCOL
            or protocol["raw_feature"]["formula"] != "ln(CapMrktCurUSD / SMA90(TxTfrValAdjUSD))"
            or protocol["input"]["metrics"] != list(METRICS)):
        raise ValueError("E9 frozen protocol changed; a new version is required")
    source, manifest = load_nvt_snapshot(nvt_snapshot, rights_file)
    if manifest["start_date_requested"] != protocol["input"]["start_date"]:
        raise ValueError("E9 full-history start differs from frozen protocol")
    core_source, core_manifest = load_snapshot(Path(core_snapshot))
    protocol_hash = digest(encode(protocol))
    engine_hash = digest(b"".join((ROOT / f"eco/{name}.py").read_text(encoding="utf-8").encode()
                                for name in ("core", "research", "nvt", "nvt_pipeline")))
    identity = {"e9_snapshot_sha256": manifest["snapshot"]["canonical_sha256"],
                "e9_source_manifest_sha256": digest((Path(nvt_snapshot) / "manifest.json").read_bytes()),
                "core_snapshot_sha256": core_manifest["snapshot"]["canonical_sha256"],
                "protocol_sha256": protocol_hash, "engine_sha256": engine_hash,
                "rights_file_sha256": manifest["source_rights"]["rights_file_sha256"]}
    folder = ROOT / "data/computed" / ("e9-" + digest(encode(identity))[:20])
    if folder.exists():
        saved = read_json(folder / "manifest.json")
        if saved.get("identity") != identity:
            raise ValueError("E9 immutable result identity mismatch")
        for name, checksum in saved["files"].items():
            if Path(name).name != name or digest((folder / name).read_bytes()) != checksum:
                raise ValueError("E9 immutable result checksum mismatch")
        return folder
    candidate = compute_nvt(source)
    result = evaluate_nvt(compute(core_source), candidate)
    result["identity"] = identity
    files = {"candidate-private.json": encode(candidate), "research-private.json": encode(result)}
    summary = {"methodology_version": VERSION, "protocol": PROTOCOL, "identity": identity,
               "series_type": "reconstructed", "public_release_allowed": False,
               "files": {name: digest(content) for name, content in files.items()}}
    folder.parent.mkdir(parents=True, exist_ok=True)
    temporary = folder.with_name(folder.name + ".partial")
    temporary.mkdir()
    for name, content in files.items():
        (temporary / name).write_bytes(content)
    (temporary / "manifest.json").write_bytes(encode(summary))
    temporary.rename(folder)
    return folder


def main():
    parser = argparse.ArgumentParser(description="Verify/evaluate E9 privately; no publishing command")
    parser.add_argument("core_snapshot")
    parser.add_argument("e9_snapshot")
    parser.add_argument("--rights-file", required=True)
    args = parser.parse_args()
    folder = build_e9(args.core_snapshot, args.e9_snapshot, args.rights_file)
    report = read_json(folder / "research-private.json")
    print(json.dumps({"output": str(folder), "status": report["status"], "n": report["n"],
                      "start": report["start"], "end": report["end"], "decision": report["decision"],
                      "public_release_allowed": False}))


if __name__ == "__main__":
    main()
