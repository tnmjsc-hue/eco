"""Daily private backup, immutable research revisions and publication ledger."""

import argparse
from datetime import datetime, timedelta, timezone
from pathlib import Path
import re
import math
import subprocess
import sys

from .pipeline import ROOT, build, digest, encode, publish, read_json, verify_release

SCHEDULE = {"provider": "github_actions", "timezone": "Asia/Ho_Chi_Minh",
            "local_times": ["10:17", "14:17"], "cron_utc": "17 3,7 * * *"}


def atomic_json(path, value, immutable=False):
    content = encode(value)
    if immutable and path.exists():
        if path.read_bytes() != content:
            raise ValueError("publication/revision record is immutable")
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_bytes(content)
    temporary.replace(path)


def changes(previous, current):
    old = {row["date"]: row for row in previous}
    new = {row["date"]: row for row in current}
    if any(row["source_row_present"] and (day not in new or not new[day]["source_row_present"])
           for day, row in old.items()):
        raise ValueError("provider lost previously available observations; retain last good release")
    revisions, added = [], []
    for day, row in new.items():
        if day not in old or not old[day]["source_row_present"]:
            if row["source_row_present"]:
                added.append(day)
        elif not same_values(old[day], row):
            revisions.append(day)
    return revisions, added


def same_values(left, right):
    if any(left[key] != right[key] for key in ("price_usd", "coverage", "reasons", "source_row_present")):
        return False
    if set(left["components"]) != set(right["components"]):
        return False
    for a, b in [(left["score"], right["score"]), *[(left["components"][key], right["components"][key]) for key in left["components"]]]:
        if a is None or b is None:
            if a != b:
                return False
        elif not math.isclose(a, b, rel_tol=0, abs_tol=1e-8):
            return False
    return True


def prepare_release(candidate, previous, public, timestamp):
    manifest = verify_release(candidate)
    old_manifest = verify_release(previous)
    current = read_json(candidate / "history.json")
    old = read_json(previous / "history.json")
    revised, added = changes(old["rows"], current["rows"])
    if not revised and not added:
        return None
    # Preserve previously published bytes for equivalent cross-runtime floating-point results.
    old_rows = {row["date"]: row for row in old["rows"]}
    current["rows"] = [old_rows[row["date"]] if row["date"] in old_rows and old_rows[row["date"]]["source_row_present"] and same_values(old_rows[row["date"]], row)
                       else row for row in current["rows"]]
    valid = [row for row in current["rows"] if row["score"] is not None]
    manifest.update(last_valid_score=valid[-1]["score"], last_valid_score_date=valid[-1]["date"])
    publisher_hash = digest(Path(__file__).read_text(encoding="utf-8").encode("utf-8"))
    release_id = "core-" + digest(encode({"candidate": manifest["release_id"], "previous": old_manifest["release_id"],
                                        "publisher": publisher_hash}))[:20]
    folder = candidate.parent / release_id
    revision = {"previous_release_id": old_manifest["release_id"],
                "reason": "provider_revised_inputs" if revised else "new_closed_utc_observations",
                "changed_dates": revised, "new_observation_dates": added,
                "previous_releases_preserved": True}
    current["release_id"] = release_id
    manifest.update(release_id=release_id, publisher_sha256=publisher_hash, revision=revision,
                    release_prepared_at=timestamp,
                    data_vintage_policy="Reconstructed history in immutable releases; corrections have explicit revisions. First-publication daily records are separate, not a historical as-published backtest.")
    manifest["files"]["history.json"] = digest(encode(current))
    if folder.exists():
        existing = verify_release(folder)
        if existing["files"] != manifest["files"] or existing["revision"] != revision:
            raise ValueError("daily release collision")
        return folder
    folder.mkdir()
    (folder / "history.json").write_bytes(encode(current))
    (folder / "research.json").write_bytes((candidate / "research.json").read_bytes())
    (folder / "manifest.json").write_bytes(encode(manifest))
    verify_release(folder)
    return folder


def record_publication(folder, previous, public):
    manifest = verify_release(folder)
    old = read_json(previous / "history.json")
    existing = {r["date"] for r in old["rows"] if r["score"] is not None}
    rows = read_json(folder / "history.json")["rows"]
    for row in rows:
        target = public / "data/publications" / (row["date"] + ".json")
        if row["score"] is None or row["date"] in existing or target.exists():
            continue
        record = {"schema_version": "1.0.0", "record_type": "first_publication", "methodology_version": manifest["methodology_version"],
                  "date": row["date"], "score": row["score"], "components": row["components"],
                  "recorded_at": manifest["release_prepared_at"], "public_available_at": None, "retrieved_at": manifest["retrieved_at"],
                  "source_available_at": None, "release_id": manifest["release_id"],
                  "snapshot_sha256": manifest["snapshot_sha256"]}
        atomic_json(target, record, immutable=True)
    atomic_json(public / "data/revisions" / (manifest["release_id"] + ".json"), {
        "release_id": manifest["release_id"], "recorded_at": manifest["release_prepared_at"], **manifest["revision"]}, immutable=True)


def update_status(public, timestamp, outcome, manifest, **details):
    path = public / "data/status.json"
    status = read_json(path)
    previous_success = status.get("daily_update", {}).get("last_success_at")
    status.update(scheduler_available=True, updated_at=timestamp, release_id=manifest["release_id"],
                  last_valid_score_date=manifest["last_valid_score_date"], last_valid_score=manifest["last_valid_score"])
    status["daily_update"] = {**SCHEDULE, "enabled": True, "last_attempt_at": timestamp,
                              "last_success_at": previous_success if outcome == "failed" else timestamp,
                              "outcome": outcome, "target_observation_date": (datetime.fromisoformat(timestamp).date() - timedelta(days=1)).isoformat(),
                              "last_valid_score_date": manifest["last_valid_score_date"], **details}
    if outcome != "failed":
        status["progress"].update(private_snapshot_storage="private_r2_verified",
                                   closed_before_at_retrieval_utc=manifest["closed_before_utc"],
                                   pending_open_at_retrieval_dates=manifest.get("pending_dates", []))
        probe = status["progress"].get("core_capability_probe", {})
        probe.update(full_history_row_count=manifest["source_rows"], full_history_last_available_date=manifest["last_observation_date"],
                     missing_requested_end_dates=len(manifest["missing_dates"]))
    atomic_json(path, status)


def run(public=ROOT / "public", fetch=True):
    now = datetime.now(timezone.utc).isoformat()
    pointer = read_json(public / "data/latest.json")
    if not re.fullmatch(r"core-[a-f0-9]{20}", pointer["release_id"]):
        raise ValueError("invalid previous release pointer")
    previous = public / "data/releases" / pointer["release_id"]
    manifest = verify_release(previous)
    if digest((previous / "manifest.json").read_bytes()) != pointer["manifest_sha256"]:
        raise ValueError("previous pointer checksum mismatch")
    stage = "fetch_backup"
    try:
        if fetch:
            subprocess.run(["node", "scripts/daily-fetch.mjs"], cwd=ROOT, check=True, timeout=900)
        report = read_json(ROOT / "data/computed/daily-fetch.json")
        snapshot = Path(report["snapshot"])
        source = read_json(snapshot / "manifest.json")
        backup = report["backup"]
        if (backup["status"] != "uploaded_private_snapshot" or backup["snapshot_sha256"] != source["snapshot"]["canonical_sha256"]
                or len(backup["objects"]) != len(source["pages"]) + 2 or not all(o["readback_verified"] for o in backup["objects"])):
            raise ValueError("R2 backup gate failed")
        stage = "compute_validate"
        candidate = build(snapshot, ROOT / "data/computed")
        folder = prepare_release(candidate, previous, public, datetime.now(timezone.utc).isoformat())
        if folder is None:
            outcome = "unchanged"
        else:
            stage = "publish"
            record_publication(folder, previous, public)
            publish(folder, ROOT / "configs/release-policy.json", public)
            manifest = verify_release(folder)
            outcome = "revised" if manifest["revision"]["changed_dates"] else "published"
        release_action = outcome
        if manifest["last_valid_score_date"] < (datetime.fromisoformat(now).date() - timedelta(days=1)).isoformat():
            outcome = "source_pending"
        update_status(public, now, outcome, manifest, release_action=release_action, snapshot_sha256=source["snapshot"]["canonical_sha256"],
                      private_backup_verified=True, run_url=run_url())
        print(encode({"outcome": outcome, "release_id": manifest["release_id"], "last_score_date": manifest["last_valid_score_date"]}).decode(), end="")
        return 0
    except Exception:
        # Never include provider bodies, process environment or signed URLs in public errors.
        update_status(public, now, "failed", manifest, failure_stage=stage,
                      message="Cập nhật thất bại; giữ release hợp lệ gần nhất.", run_url=run_url())
        print(f"Daily update failed at {stage}; retained verified release.", file=sys.stderr)
        return 1


def run_url():
    import os
    repository, run_id = os.environ.get("GITHUB_REPOSITORY"), os.environ.get("GITHUB_RUN_ID")
    return f"https://github.com/{repository}/actions/runs/{run_id}" if repository and run_id else None


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--verified-fetch-report", action="store_true", help="Reuse the private readback report for an offline operator replay")
    args = parser.parse_args()
    sys.exit(run(fetch=not args.verified_fetch_report))
