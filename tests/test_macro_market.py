from datetime import datetime, timezone
from decimal import Decimal
from hashlib import sha256
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from eco import macro_market as m
from eco.macro_pipeline import body, write

ROOT = Path(__file__).resolve().parents[1]
PROTOCOL = json.loads((ROOT / "configs/macro/macro-market-v1.0.0.json").read_bytes())
AS_OF = "2026-10-09T03:00:00+00:00"
SOURCE = {"provider": "fed", "url": m.SOURCES["fed_yields"], "retrieved_at": AS_OF, "sha256": "a" * 64}


class MarketTests(unittest.TestCase):
    def measure(self, points, metric="treasury_2y", as_of=AS_OF, source=SOURCE):
        return m.measure(metric, points, source, as_of, PROTOCOL)

    def test_frozen_protocol_and_decimal_units(self):
        self.assertEqual(sha256(body(PROTOCOL)).hexdigest(), m.PROTOCOL_SHA)
        self.assertEqual(self.measure([("2026-10-07", "4.77"), ("2026-10-08", "4.82")])["change"], "5.00")
        result = self.measure([("2026-10-07", "100"), ("2026-10-08", "101.5")], "usd_broad")
        self.assertEqual(Decimal(result["change"]), Decimal("1.5"))
        self.assertEqual(self.measure([("2026-10-07", "-0.1"), ("2026-10-08", "-0.2")], "real_yield_10y")["change"], "-10.0")

    def test_cutoff_does_not_use_future_or_current_day(self):
        result = self.measure([("2026-10-07", "1"), ("2026-10-08", "2"), ("2026-10-09", "50"), ("2026-10-10", "60")])
        self.assertEqual(result["latest_date"], "2026-10-08")
        with self.assertRaisesRegex(ValueError, "future"):
            self.measure([("2026-10-08", "1")], source={**SOURCE, "retrieved_at": "2026-10-10T00:00:00Z"})

    def test_missing_latest_blocks_old_pair_and_zero_is_not_missing(self):
        result = self.measure([("2026-10-06", "1"), ("2026-10-07", "2"), ("2026-10-08", None)])
        self.assertEqual(result["reason"], "missing_latest_value")
        self.assertIsNone(result["change"])
        self.assertEqual(self.measure([("2026-10-07", "0.1"), ("2026-10-08", "0")])["change"], "-10.0")
        self.assertEqual(self.measure([("2026-10-07", "0"), ("2026-10-08", "1")], "usd_broad")["reason"], "invalid_price_or_index")

    def test_freshness_boundary_and_weekend_gap(self):
        points = [("2026-10-01", "1"), ("2026-10-02", "2")]
        self.assertEqual(self.measure(points)["status"], "measured")
        self.assertEqual(self.measure(points, as_of="2026-10-10T00:00:00Z")["status"], "stale")
        self.assertEqual(self.measure([("2026-10-02", "1"), ("2026-10-05", "2")])["change"], "100")
        self.assertEqual(self.measure([("2026-09-25", "1"), ("2026-10-08", "2")])["reason"], "pair_gap")

    def test_invalid_decimal_date_duplicate_and_metadata_fail_closed(self):
        for value in [True, "NaN", "Infinity", "1e3", "1,000"]:
            with self.assertRaises(ValueError):
                m.decimal(value)
        with self.assertRaises(ValueError):
            self.measure([("2026-02-30", "1")])
        with self.assertRaisesRegex(ValueError, "ambiguous"):
            self.measure([("2026-10-08", "1"), ("2026-10-08", "2")])
        raw = b'"Series Description","2y"\n"Unit:","Percent:_Per_Year"\n"Multiplier:","1"\n"Unique Identifier: ","H15/H15/RIFLGFCY02_N.B"\n"Time Period","RIFLGFCY02_N.B"\n2026-10-07,4.77\n2026-10-08,4.82\n'
        self.assertEqual(m.parse_fed(raw, "RIFLGFCY02_N.B", "percent")[-1], ("2026-10-08", "4.82"))
        for bad in [raw.replace(b'"1"', b'"100"'), raw.replace(b'4.82', b'NaN'), raw.replace(b'4.82', b'4.82,3')]:
            with self.assertRaises(ValueError):
                m.parse_fed(bad, "RIFLGFCY02_N.B", "percent")

    def test_treasury_real_series_not_nominal_and_null(self):
        raw = b'<feed xmlns="http://www.w3.org/2005/Atom" xmlns:d="http://schemas.microsoft.com/ado/2007/08/dataservices" xmlns:m="http://schemas.microsoft.com/ado/2007/08/dataservices/metadata"><title>DailyTreasuryRealYieldCurveRateData</title><entry><content><m:properties><d:NEW_DATE>2026-10-08T00:00:00</d:NEW_DATE><d:TC_10YEAR>-0.20</d:TC_10YEAR></m:properties></content></entry></feed>'
        self.assertEqual(m.parse_real_yield(raw), [("2026-10-08", "-0.20")])
        with self.assertRaises(ValueError):
            m.parse_real_yield(raw.replace(b'TC_10YEAR', b'BC_10YEAR'))
        self.assertEqual(m.parse_real_yield(raw.replace(b'>-0.20<', b' m:null="true"><')), [("2026-10-08", None)])

    def test_publication_requires_complete_backup_is_immutable_and_locked(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp);snapshot = root / "data/raw/macro-market/test"
            write(snapshot / "raw.json", {"body": "fixture"})
            inputs = {"metrics": [], "eth_parent": {}}
            def backup(value):
                write(snapshot / "normalized.json", value)
                write(snapshot / "manifest.json", {"protocol_version": m.VERSION, "files": {p.name: sha256(p.read_bytes()).hexdigest() for p in snapshot.iterdir() if p.name != "manifest.json"}})
                return [{"object_key": f"raw/macro-market/test/{p.name}", "sha256": sha256(p.read_bytes()).hexdigest(), "readback_verified": True} for p in snapshot.iterdir()]
            receipt = backup(inputs)
            with self.assertRaisesRegex(ValueError, "incomplete"):
                m.publish(root, inputs, PROTOCOL, snapshot, receipt[:1], AS_OF)
            with self.assertRaisesRegex(ValueError, "does not match"):
                m.publish(root, {**inputs, "unbacked_input": True}, PROTOCOL, snapshot, receipt, AS_OF)
            first = m.publish(root, inputs, PROTOCOL, snapshot, receipt, AS_OF)
            folder = root / "public/data/macro-market"
            artifact = folder / "releases" / first["release_id"] / "market.json"
            before = artifact.read_bytes()
            again = m.publish(root, inputs, PROTOCOL, snapshot, receipt, "2026-10-09T04:00:00Z")
            self.assertEqual(again["outcome"], "unchanged")
            self.assertEqual(before, artifact.read_bytes())
            revised = {**inputs, "fixture_revision": True}
            second = m.publish(root, revised, PROTOCOL, snapshot, backup(revised), "2026-10-09T05:00:00Z")
            receipt = backup(inputs)
            restored = m.publish(root, inputs, PROTOCOL, snapshot, receipt, "2026-10-09T06:00:00Z")
            self.assertNotEqual(restored["release_id"], first["release_id"])
            self.assertNotEqual(restored["release_id"], second["release_id"])
            self.assertEqual(before, artifact.read_bytes())
            current = folder / "releases" / restored["release_id"] / "market.json"
            with self.assertRaisesRegex(ValueError, "future"):
                m.publish(root, inputs, PROTOCOL, snapshot, receipt, AS_OF)
            with m.publication_lock(folder), self.assertRaisesRegex(ValueError, "busy"):
                m.publish(root, inputs, PROTOCOL, snapshot, receipt, AS_OF)
            current.write_bytes(b'{}')
            with self.assertRaisesRegex(ValueError, "checksum"):
                m.publish(root, inputs, PROTOCOL, snapshot, receipt, AS_OF)

    def test_source_failure_retains_pointer_and_reports_error_without_raw(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            write(root / f"configs/macro/{m.VERSION}.json", PROTOCOL)
            pointer = root / "public/data/macro-market/latest.json"
            write(pointer, {"release_id": "fixture"})
            before = pointer.read_bytes()
            with patch.object(m, "fetch_source", side_effect=ValueError("upstream private detail")), self.assertRaises(ValueError):
                m.run(root, datetime(2026, 10, 9, 3, tzinfo=timezone.utc))
            self.assertEqual(pointer.read_bytes(), before)
            status = json.loads(pointer.with_name("status.json").read_bytes())
            self.assertEqual(status["outcome"], "error")
            self.assertNotIn("private detail", str(status))

    def test_cold_runner_recovers_original_retrieval_only_for_verified_same_hash(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            base = "/data/macro-market/releases/market-" + "a" * 20
            original = {"url": m.SOURCES["fed_yields"], "sha256": "b" * 64, "retrieved_at": "2026-10-08T01:00:00Z"}
            inputs = {"protocol_version": m.VERSION, "metrics": [{"source": original}]}
            write(root / "public" / (base + "/inputs.json").lstrip("/"), inputs)
            input_hash = sha256(body(inputs)).hexdigest()
            manifest = {"release_id": "market-" + "a" * 20, "inputs": {"url": base + "/inputs.json", "sha256": input_hash}}
            write(root / "public" / (base + "/manifest.json").lstrip("/"), manifest)
            write(root / "public/data/macro-market/latest.json", {"release_id": manifest["release_id"], "manifest": {"url": base + "/manifest.json", "sha256": sha256(body(manifest)).hexdigest()}})
            sources = {"fed_yields": {**original, "retrieved_at": AS_OF, "body": "fixture"}}
            m.retain_source_vintage(root, sources, m.utc(AS_OF))
            self.assertEqual(sources["fed_yields"]["retrieved_at"], original["retrieved_at"])
            sources["fed_yields"].update(sha256="c" * 64, retrieved_at=AS_OF)
            m.retain_source_vintage(root, sources, m.utc(AS_OF))
            self.assertEqual(sources["fed_yields"]["retrieved_at"], AS_OF)
            (root / "public" / (base + "/inputs.json").lstrip("/")).write_bytes(b"{}")
            with self.assertRaisesRegex(ValueError, "checksum"):
                m.retain_source_vintage(root, sources, m.utc(AS_OF))


if __name__ == "__main__":
    unittest.main()
