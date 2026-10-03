from copy import deepcopy
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from eco.daily import SCHEDULE, atomic_json, changes, prepare_release, record_publication, run, update_status
from eco.pipeline import digest, encode, read_json


class DailyTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.public = self.root / "public"
        self.row = {"date": "2026-10-01", "price_usd": 100., "score": 40., "coverage": 4,
                    "components": {"E1": 40., "E5": 40., "E6": 40., "E7": 40.},
                    "reasons": {}, "source_row_present": True, "period_closed_at_retrieval": True}
        self.old = self.release("core-" + "0" * 20, [self.row], self.public / "data/releases")
        atomic_json(self.public / "data/status.json", {"progress": {}})
        atomic_json(self.public / "data/latest.json", {"release_id": self.old.name,
                                                       "manifest_sha256": digest((self.old / "manifest.json").read_bytes())})

    def release(self, name, rows, output):
        folder = output / name
        folder.mkdir(parents=True)
        history = {"release_id": name, "rows": rows}
        manifest = {"release_id": name, "methodology_version": "core-v0.1.0", "series_type": "reconstructed",
                    "retrieved_at": "2026-10-03T03:17:00Z", "snapshot_sha256": "abc",
                    "last_valid_score_date": rows[-1]["date"], "last_valid_score": rows[-1]["score"],
                    "last_observation_date": rows[-1]["date"], "source_rows": len(rows), "missing_dates": [],
                    "closed_before_utc": "2026-10-03", "files": {"history.json": digest(encode(history)), "research.json": digest(b"{}\n")}}
        (folder / "history.json").write_bytes(encode(history))
        (folder / "research.json").write_bytes(b"{}\n")
        (folder / "manifest.json").write_bytes(encode(manifest))
        return folder

    def test_identical_inputs_are_idempotent_and_ignore_pending_tail(self):
        new = self.release("core-new", [self.row], self.root)
        self.assertIsNone(prepare_release(new, self.old, self.public, "2026-10-03T03:17:00Z"))
        pending = {**self.row, "date": "2026-10-02", "source_row_present": False, "score": None}
        self.assertEqual(changes([self.row, pending], [self.row]), ([], []))

    def test_append_creates_first_publication_without_rewriting_prior_release(self):
        before = (self.old / "history.json").read_bytes()
        added = {**self.row, "date": "2026-10-02", "score": 42.}
        new = self.release("core-new", [self.row, added], self.root)
        folder = prepare_release(new, self.old, self.public, "2026-10-03T03:17:00Z")
        record_publication(folder, self.old, self.public)
        path = self.public / "data/publications/2026-10-02.json"
        first = path.read_bytes()
        record_publication(folder, self.old, self.public)
        self.assertEqual(first, path.read_bytes())
        self.assertFalse((self.public / "data/publications/2026-10-01.json").exists())
        self.assertEqual((self.old / "history.json").read_bytes(), before)
        self.assertEqual(read_json(path)["record_type"], "first_publication")

    def test_source_revision_is_explicit_and_never_overwrites_first_publication(self):
        changed = deepcopy(self.row)
        changed["components"]["E7"] = 44.
        new = self.release("core-new", [changed], self.root)
        folder = prepare_release(new, self.old, self.public, "2026-10-03T03:17:00Z")
        manifest = read_json(folder / "manifest.json")
        self.assertEqual(manifest["revision"]["reason"], "provider_revised_inputs")
        self.assertEqual(manifest["revision"]["changed_dates"], ["2026-10-01"])
        with self.assertRaisesRegex(ValueError, "immutable"):
            path = self.root / "record.json"
            atomic_json(path, {"score": 40}, immutable=True)
            atomic_json(path, {"score": 44}, immutable=True)

    def test_provider_regression_rejected(self):
        with self.assertRaisesRegex(ValueError, "lost"):
            changes([self.row], [])
        with self.assertRaisesRegex(ValueError, "lost"):
            changes([self.row], [{**self.row, "source_row_present": False}])

    def test_cross_runtime_roundoff_keeps_original_published_values(self):
        equivalent = deepcopy(self.row)
        equivalent["score"] += 1e-9
        equivalent["components"] = dict(reversed(list(equivalent["components"].items())))
        equivalent["components"]["E7"] += 1e-9
        self.assertEqual(changes([self.row], [equivalent]), ([], []))
        added = {**self.row, "date": "2026-10-02"}
        new = self.release("core-new", [equivalent, added], self.root)
        folder = prepare_release(new, self.old, self.public, "2026-10-03T03:17:00Z")
        self.assertEqual(read_json(folder / "history.json")["rows"][0], self.row)
        equivalent["components"]["E7"] += .001
        self.assertEqual(changes([self.row], [equivalent])[0], ["2026-10-01"])

    def test_failure_keeps_last_success_and_data_date_not_zero(self):
        manifest = read_json(self.old / "manifest.json")
        update_status(self.public, "2026-10-03T03:17:00+00:00", "source_pending", manifest)
        update_status(self.public, "2026-10-03T07:17:00+00:00", "failed", manifest, failure_stage="fetch_backup")
        status = read_json(self.public / "data/status.json")
        self.assertEqual(status["daily_update"]["last_success_at"], "2026-10-03T03:17:00+00:00")
        self.assertEqual(status["last_valid_score"], 40.)
        self.assertEqual(status["last_valid_score_date"], "2026-10-01")
        self.assertEqual(status["daily_update"]["target_observation_date"], "2026-10-02")

    def test_source_failure_preserves_pointer_and_release(self):
        before = (self.public / "data/latest.json").read_bytes()
        with patch("eco.daily.subprocess.run", side_effect=RuntimeError("private response body")):
            self.assertEqual(run(public=self.public), 1)
        self.assertEqual(before, (self.public / "data/latest.json").read_bytes())
        status = read_json(self.public / "data/status.json")
        self.assertEqual(status["daily_update"]["outcome"], "failed")
        self.assertNotIn("private response", encode(status).decode())

    def test_backup_hash_gate_blocks_compute_and_preserves_pointer(self):
        before = (self.public / "data/latest.json").read_bytes()
        snapshot = self.root / "snapshot"
        atomic_json(snapshot / "manifest.json", {"snapshot": {"canonical_sha256": "abc"}})
        atomic_json(self.root / "data/computed/daily-fetch.json", {
            "snapshot": str(snapshot), "backup": {"status": "uploaded_private_snapshot", "snapshot_sha256": "bad", "objects": []}})
        with patch("eco.daily.ROOT", self.root), patch("eco.daily.build") as compute:
            self.assertEqual(run(public=self.public, fetch=False), 1)
            compute.assert_not_called()
        self.assertEqual(before, (self.public / "data/latest.json").read_bytes())

    def test_scheduler_contract_matches_workflow(self):
        workflow = Path(__file__).resolve().parents[1] / ".github/workflows/daily-update.yml"
        self.assertIn("cron: '" + SCHEDULE["cron_utc"] + "'", workflow.read_text())
        self.assertEqual(SCHEDULE["local_times"], ["10:17", "14:17"])
