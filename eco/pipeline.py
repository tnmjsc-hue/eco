"""Offline computation and gated, immutable static research releases."""

import argparse
from datetime import date, datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
import shutil

from .core import COMPONENTS, ORIGIN, VERSION, compute
from .research import evaluate

ROOT = Path(__file__).resolve().parents[1]
PROTOCOL_HASH = "da76f0d4357f54fc319d49e57323e95f3bd33338a2b5774a5cda54e228ce7d09"


def digest(data):
    return hashlib.sha256(data).hexdigest()


def encode(value):
    return (json.dumps(value, ensure_ascii=False, allow_nan=False, separators=(",", ":")) + "\n").encode("utf-8")


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def load_snapshot(directory):
    manifest = read_json(directory / "manifest.json")
    if (manifest.get("status"), manifest.get("asset"), manifest.get("frequency"), manifest.get("provider")) != (
            "complete", "eth", "1d", "coinmetrics_community_api"):
        raise ValueError("snapshot must be complete ETH/1d Coin Metrics Community")
    canonical_name = manifest["snapshot"]["canonical_file"]
    if Path(canonical_name).name != canonical_name:
        raise ValueError("canonical path must be a filename")
    content = (directory / canonical_name).read_bytes()
    if digest(content) != manifest["snapshot"]["canonical_sha256"]:
        raise ValueError("canonical SHA-256 mismatch")
    for page in manifest["pages"]:
        filename = page["raw_file"]
        if Path(filename).name != filename or digest((directory / filename).read_bytes()) != page["response_sha256"]:
            raise ValueError("raw page SHA-256 mismatch")
    rows = [json.loads(line) for line in content.splitlines() if line]
    if len(rows) != manifest["snapshot"]["row_count"]:
        raise ValueError("row count mismatch")
    dates = [r["observation_date"] for r in rows]
    if dates != sorted(set(dates)):
        raise ValueError("non-monotonic or duplicate date")
    if (dates[0], dates[-1]) != (manifest["snapshot"]["first_observation_date"], manifest["snapshot"]["last_observation_date"]):
        raise ValueError("snapshot range mismatch")
    retrieved = datetime.fromisoformat(manifest["retrieved_at"].replace("Z", "+00:00"))
    if retrieved.tzinfo is None:
        raise ValueError("retrieval timestamp must have timezone")
    closed_before = min(date.fromisoformat(manifest["as_of_utc"]), retrieved.astimezone(timezone.utc).date())
    for row in rows:
        day = date.fromisoformat(row["observation_date"])
        end = (day + timedelta(days=1)).isoformat() + "T00:00:00Z"
        timestamp = datetime.fromisoformat(row["source_timestamp"].replace("Z", "+00:00"))
        if (day >= closed_before or row.get("period_end_utc") != end
                or not row["source_timestamp"].endswith("Z") or timestamp.isoformat() != day.isoformat() + "T00:00:00+00:00"
                or row.get("source_available_at") is not None):
            raise ValueError("unexpected timestamp/vintage contract")
    return rows, manifest


def verify_release(directory):
    manifest = read_json(directory / "manifest.json")
    for name, sha in manifest["files"].items():
        if Path(name).name != name or digest((directory / name).read_bytes()) != sha:
            raise ValueError("release checksum mismatch")
    return manifest


def build(snapshot, output):
    protocol = encode(read_json(ROOT / "configs/research/core-v0.1.0.json"))
    if digest(protocol) != PROTOCOL_HASH:
        raise ValueError("frozen protocol changed; explicit new version required")
    rows, source = load_snapshot(snapshot)
    end = min(date.fromisoformat(source["end_date_requested"]), date.fromisoformat(source["as_of_utc"]) - timedelta(days=1))
    closed_before = min(date.fromisoformat(source["as_of_utc"]), datetime.fromisoformat(source["retrieved_at"].replace("Z", "+00:00")).astimezone(timezone.utc).date())
    full = compute(rows, end=end)
    last_source = source["snapshot"]["last_observation_date"]
    research = evaluate([r for r in full if r["date"] <= last_source])
    engine_hash = digest(b"".join((ROOT / f"eco/{name}.py").read_text(encoding="utf-8").encode("utf-8") for name in ("core", "research", "pipeline")))
    release_id = "core-" + digest(encode({"input": source["snapshot"]["canonical_sha256"],
                                       "protocol": PROTOCOL_HASH, "engine": engine_hash}))[:20]
    folder = output / release_id
    if folder.exists():
        verify_release(folder)
        print(json.dumps({"release_id": release_id, "idempotent": True}))
        return folder
    valid = [r for r in full if r["score"] is not None]
    if not valid:
        raise ValueError("no complete Core observations")
    slim = [{"date": r["date"], "price_usd": r["price_usd"], "score": r["score"],
             "coverage": r["coverage"], "components": {k: r["components"][k]["score"] for k in COMPONENTS},
             "reasons": {k: r["components"][k]["reason"] for k in COMPONENTS},
             "source_row_present": r["source_row_present"], "period_closed_at_retrieval": r["date"] < closed_before.isoformat()} for r in full]
    history = {"schema_version": "1.0.0", "release_id": release_id, "methodology_version": VERSION,
               "series_type": "reconstructed", "asset": "eth", "frequency": "1d", "rows": slim}
    timestamp = datetime.now(timezone.utc).isoformat()
    manifest = {"schema_version": "1.0.0", "release_id": release_id, "methodology_version": VERSION,
                "series_type": "reconstructed", "release_label": "Experimental research preview",
                "computed_at": timestamp, "retrieved_at": source["retrieved_at"], "source_available_at": None,
                "snapshot_sha256": source["snapshot"]["canonical_sha256"], "protocol_sha256": PROTOCOL_HASH,
                "engine_sha256": engine_hash, "price_origin": ORIGIN.isoformat(),
                "source": "Coin Metrics Community API", "source_url": "https://docs.coinmetrics.io/packages/coin-metrics-community-data",
                "license": "CC BY-NC 4.0", "license_url": "https://creativecommons.org/licenses/by-nc/4.0/",
                "attribution": "Nguồn dữ liệu: Coin Metrics Community Data. ECO chuyển đổi thành điểm Core và tái dựng lịch sử. Coin Metrics không bảo trợ ECO. Dữ liệu không được bảo đảm chính xác.",
                "rows": len(full), "source_rows": len(rows), "first_date": full[0]["date"],
                "last_observation_date": last_source, "last_requested_date": full[-1]["date"],
                "first_score_date": valid[0]["date"], "last_valid_score": valid[-1]["score"],
                "last_valid_score_date": valid[-1]["date"], "score_rows": len(valid),
                "closed_before_utc": closed_before.isoformat(),
                "missing_dates": [r["date"] for r in full if not r["source_row_present"] and r["date"] < closed_before.isoformat()],
                "pending_dates": [r["date"] for r in full if r["date"] >= closed_before.isoformat()],
                "incremental_utility_demonstrated": research["success"],
                "data_vintage_policy": "Reconstructed only; not as-published. Future source revisions create a new release.",
                "files": {"history.json": digest(encode(history)), "research.json": digest(encode(research))}}
    output.mkdir(parents=True, exist_ok=True)
    temporary = output / (release_id + ".partial")
    temporary.mkdir(exist_ok=False)
    for name, value in (("history.json", history), ("research.json", research), ("manifest.json", manifest), ("engine-private.json", full)):
        (temporary / name).write_bytes(encode(value))
    verify_release(temporary)
    temporary.rename(folder)
    print(json.dumps({"release_id": release_id, "rows": len(full), "first_score": valid[0]["date"],
                      "last_score_date": valid[-1]["date"], "last_score": valid[-1]["score"],
                      "research_success": research["success"]}))
    return folder


def publish(folder, policy_path, public):
    policy = read_json(policy_path)
    if (policy.get("status") != "approved_noncommercial_research" or not policy.get("operator_confirmation")
            or policy.get("license") != "CC BY-NC 4.0"):
        raise ValueError("public release blocked: explicit noncommercial research rights confirmation required")
    manifest = verify_release(folder)
    if (set(manifest["files"]) != {"history.json", "research.json"}
            or manifest.get("methodology_version") != VERSION or manifest.get("series_type") != "reconstructed"):
        raise ValueError("public allowlist accepts only Core reconstructed history and research")
    release_id = manifest["release_id"]
    if release_id != folder.name or not release_id.startswith("core-"):
        raise ValueError("invalid release identity")
    destination = public / "data/releases" / release_id
    if destination.exists():
        existing = verify_release(destination)
        if encode(existing) != encode(manifest):
            raise ValueError("published release is immutable")
    else:
        temporary = destination.with_name(release_id + ".partial")
        temporary.mkdir(parents=True, exist_ok=False)
        for name in (*manifest["files"], "manifest.json"):
            shutil.copyfile(folder / name, temporary / name)
        verify_release(temporary)
        temporary.rename(destination)
    pointer = {"schema_version": "1.0.0", "release_id": release_id,
               "manifest_url": f"/data/releases/{release_id}/manifest.json",
               "manifest_sha256": digest((destination / "manifest.json").read_bytes()),
               "rights_policy": policy["policy_version"]}
    temporary_pointer = public / "data/latest.json.tmp"
    temporary_pointer.write_bytes(encode(pointer))
    temporary_pointer.replace(public / "data/latest.json")
    print(json.dumps({"published": release_id, "raw_published": False}))


def main():
    parser = argparse.ArgumentParser(description="ECO offline research pipeline")
    sub = parser.add_subparsers(dest="command", required=True)
    calc = sub.add_parser("compute")
    calc.add_argument("snapshot", type=Path)
    calc.add_argument("--output", type=Path, default=ROOT / "data/computed")
    pub = sub.add_parser("publish")
    pub.add_argument("release", type=Path)
    pub.add_argument("--policy", type=Path, default=ROOT / "configs/release-policy.json")
    pub.add_argument("--public", type=Path, default=ROOT / "public")
    args = parser.parse_args()
    if args.command == "compute":
        build(args.snapshot, args.output)
    else:
        publish(args.release, args.policy, args.public)


if __name__ == "__main__":
    main()
