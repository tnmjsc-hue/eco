from copy import deepcopy
from datetime import timedelta
import json
from pathlib import Path
import tempfile
import unittest

from eco.core import ORIGIN
from eco.pipeline import digest, encode, load_snapshot, publish, verify_release


class PipelineTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.addCleanup(self.temp.cleanup)
        self.row = {"asset": "eth", "source_timestamp": "2015-08-08T00:00:00Z",
                    "observation_date": ORIGIN.isoformat(), "period_end_utc": "2015-08-09T00:00:00Z",
                    "source_available_at": None,
                    "metrics": {"PriceUSD": "1", "CapMrktCurUSD": "100", "SplyCur": "100", "CapMVRVCur": "2"}}
        (self.root / "canonical.jsonl").write_bytes(encode(self.row))
        (self.root / "page.json").write_bytes(encode({"data": [self.row]}))
        self.manifest = {"status": "complete", "asset": "eth", "frequency": "1d", "provider": "coinmetrics_community_api",
                         "as_of_utc": "2015-08-09", "retrieved_at": "2015-08-09T01:00:00Z", "snapshot": {"canonical_file": "canonical.jsonl",
                         "canonical_sha256": digest(encode(self.row)), "row_count": 1,
                         "first_observation_date": "2015-08-08", "last_observation_date": "2015-08-08"},
                         "pages": [{"raw_file": "page.json", "response_sha256": digest(encode({"data": [self.row]}))}]}
        self.save()

    def save(self):
        (self.root / "manifest.json").write_bytes(encode(self.manifest))

    def test_load_and_checksum(self):
        self.assertEqual(load_snapshot(self.root)[0], [self.row])
        (self.root / "canonical.jsonl").write_bytes(b"changed")
        with self.assertRaisesRegex(ValueError, "SHA-256"):
            load_snapshot(self.root)

    def test_raw_integrity_and_path_escape(self):
        self.manifest["pages"][0]["raw_file"] = "../page.json"
        self.save()
        with self.assertRaises(ValueError):
            load_snapshot(self.root)

    def test_open_day_and_period_rejected(self):
        self.manifest["as_of_utc"] = "2015-08-08"
        self.save()
        with self.assertRaisesRegex(ValueError, "timestamp"):
            load_snapshot(self.root)

    def test_publisher_rights_gated_atomic_and_immutable(self):
        folder = self.root / "core-example"
        folder.mkdir()
        history = encode({"rows": []})
        manifest = {"release_id": "core-example", "methodology_version": "core-v0.1.0", "series_type": "reconstructed",
                    "files": {"history.json": digest(history), "research.json": digest(history)}}
        (folder / "history.json").write_bytes(history)
        (folder / "research.json").write_bytes(history)
        (folder / "manifest.json").write_bytes(encode(manifest))
        (folder / "engine-private.json").write_bytes(b"never publish")
        policy_path = self.root / "policy.json"
        policy_path.write_bytes(encode({"status": "pending"}))
        with self.assertRaisesRegex(ValueError, "blocked"):
            publish(folder, policy_path, self.root / "public")
        self.assertFalse((self.root / "public").exists())
        policy_path.write_bytes(encode({"status": "approved_noncommercial_research", "operator_confirmation": "test",
                                       "license": "CC BY-NC 4.0", "policy_version": "test"}))
        public = self.root / "public"
        publish(folder, policy_path, public)
        first = (public / "data/latest.json").read_bytes()
        publish(folder, policy_path, public)
        self.assertEqual(first, (public / "data/latest.json").read_bytes())
        self.assertFalse((public / "data/releases/core-example/engine-private.json").exists())
        (public / "data/releases/core-example/history.json").write_bytes(b"corrupt")
        with self.assertRaisesRegex(ValueError, "checksum"):
            publish(folder, policy_path, public)

    def test_source_closed_at_actual_retrieval_not_local_as_of(self):
        self.manifest["as_of_utc"] = "2015-08-10"
        self.manifest["retrieved_at"] = "2015-08-08T23:00:00Z"
        self.save()
        with self.assertRaisesRegex(ValueError, "timestamp"):
            load_snapshot(self.root)

    def test_raw_cannot_be_added_to_public_allowlist(self):
        folder = self.root / "core-example"
        folder.mkdir()
        (folder / "raw.json").write_bytes(b"{}")
        (folder / "manifest.json").write_bytes(encode({"release_id": "core-example", "files": {"raw.json": digest(b"{}")}}))
        policy = self.root / "policy.json"
        policy.write_bytes(encode({"status": "approved_noncommercial_research", "operator_confirmation": "test", "license": "CC BY-NC 4.0"}))
        with self.assertRaisesRegex(ValueError, "allowlist"):
            publish(folder, policy, self.root / "public")


if __name__ == "__main__":
    unittest.main()
