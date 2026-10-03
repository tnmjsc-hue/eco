from datetime import date, timedelta
import hashlib
import json
import math
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from eco.nvt import METRICS, compute_nvt, evaluate_nvt
from eco.nvt_pipeline import load_nvt_snapshot, verify_rights
import eco.nvt_pipeline as nvt_pipeline
from eco.pipeline import ROOT, encode


def fixture(n=1000):
    first = date(2015, 8, 8)
    return [{"asset": "eth", "observation_date": (first + timedelta(days=i)).isoformat(),
             "metrics": {"CapMrktCurUSD": 1000 + 200*math.sin(i/19) + i,
                         "TxTfrValAdjUSD": 10 + 2*math.cos(i/23)}} for i in range(n)]


class NvtEngineTest(unittest.TestCase):
    def test_formula_inclusive_calendar_and_past_normalizer_warmup(self):
        source = fixture(600)
        for i, row in enumerate(source):
            row["metrics"] = {"CapMrktCurUSD": 900 + i, "TxTfrValAdjUSD": 1 + i}
        result = compute_nvt(source)
        self.assertIsNone(result[88]["raw"])
        self.assertAlmostEqual(result[89]["sma90_adjusted_transfer_usd"], 45.5)
        self.assertAlmostEqual(result[89]["raw"], math.log(989/45.5))
        self.assertIsNone(result[453]["score"])
        self.assertEqual(result[453]["normalizer"]["history_count"], 364)
        self.assertIsNotNone(result[454]["score"])
        self.assertEqual(result[454]["normalizer"]["history_count"], 365)

    def test_missing_day_and_null_transfer_break_exactly_90_calendar_days(self):
        for use_gap in (True, False):
            source = fixture()
            if use_gap:
                source.pop(500)
            else:
                source[500]["metrics"]["TxTfrValAdjUSD"] = None
            result = compute_nvt(source)
            self.assertEqual(result[500]["source_row_present"], not use_gap)
            self.assertTrue(all(row["raw"] is None for row in result[500:590]))
            self.assertIsNotNone(result[590]["raw"])

    def test_zero_retained_missing_cap_current_day_and_degenerate_not_50(self):
        source = fixture(600)
        for row in source:
            row["metrics"] = {"CapMrktCurUSD": 1000, "TxTfrValAdjUSD": 0}
        result = compute_nvt(source)
        self.assertEqual(result[-1]["adjusted_transfer_usd"], 0)
        self.assertEqual(result[-1]["raw_reason"], "nonpositive_transfer_mean")
        self.assertIsNone(result[-1]["score"])
        for row in source:
            row["metrics"]["TxTfrValAdjUSD"] = 10
        result = compute_nvt(source)
        self.assertEqual(result[-1]["score_reason"], "degenerate_normalizer")
        self.assertIsNone(result[-1]["score"])
        source[500]["metrics"]["CapMrktCurUSD"] = None
        result = compute_nvt(source)
        self.assertEqual(result[500]["raw_reason"], "missing_market_cap")
        self.assertIsNotNone(result[501]["raw"])

    def test_future_shock_append_and_quantile_bounds_keep_prefix(self):
        source = fixture()
        baseline = compute_nvt(source)
        self.assertEqual(compute_nvt(source[:800]), baseline[:800])
        source[-1]["metrics"]["CapMrktCurUSD"] = 1e100
        shocked = compute_nvt(source)
        self.assertEqual(baseline[:-1], shocked[:-1])
        self.assertEqual(baseline[-1]["normalizer"]["upper"], shocked[-1]["normalizer"]["upper"])
        self.assertEqual(shocked[-1]["score"], 100)

    def test_invalid_metrics_values_duplicate_asset_and_end_rejected(self):
        for metric, value in [("CapMrktCurUSD", 0), ("CapMrktCurUSD", True), ("TxTfrValAdjUSD", -1),
                              ("TxTfrValAdjUSD", float("inf")), ("TxTfrValAdjUSD", "")]:
            source = fixture(100)
            source[0]["metrics"][metric] = value
            with self.assertRaises(ValueError):
                compute_nvt(source)
        for change in ({"asset": "btc"}, {"metrics": {"CapMrktCurUSD": 100, "TxTfrValUSD": 10}}):
            source = fixture(100)
            source[0].update(change)
            with self.assertRaises(ValueError):
                compute_nvt(source)
        with self.assertRaises(ValueError):
            compute_nvt(fixture(100) + fixture(1))
        with self.assertRaises(ValueError):
            compute_nvt(fixture(100), end="2015-08-09")
        with self.assertRaises(ValueError):
            compute_nvt([])

    def test_finite_extreme_inputs_do_not_overflow_log_ratio_or_mean(self):
        source = fixture(90)
        for row in source:
            row["metrics"] = {"CapMrktCurUSD": 1e308, "TxTfrValAdjUSD": 1e308}
        self.assertAlmostEqual(compute_nvt(source)[-1]["raw"], 0)
        for row in source:
            row["metrics"]["TxTfrValAdjUSD"] = 1e-200
        self.assertTrue(math.isfinite(compute_nvt(source)[-1]["raw"]))

    def test_calendar_expiry_of_normalizer_and_restart_after_gap(self):
        source = fixture(2050)
        source = [row for i, row in enumerate(source) if i < 500 or i >= 2000]
        result = compute_nvt(source)
        self.assertEqual(result[2000]["normalizer"]["history_count"], 0)
        self.assertIsNone(result[-1]["score"])

    def test_exploratory_composite_ablation_and_label_alignment(self):
        nvt = compute_nvt(fixture(1500))
        core = [{"date": row["date"], "price_usd": 100 + 80*math.sin(i/60), "score": 60,
                 "components": {"E1": 30, "E5": 30, "E6": 30, "E7": 90}}
                for i, row in enumerate(nvt)]
        result = evaluate_nvt(core, nvt, primary_start="2015-08-08", replicates=30)
        self.assertEqual(result["n"], 1500 - 365 - 454)
        self.assertEqual(result["status"], "exploratory_reconstructed_only")
        self.assertEqual(result["ablation"]["remove_E9"], "core")
        self.assertFalse(result["public_release_allowed"])
        self.assertIn("new_holdout", result["decision"])
        self.assertGreater(result["positive_labels"], 0)
        self.assertLess(result["positive_labels"], result["n"])
        self.assertEqual(result["bootstrap"]["replicates"], 30)
        self.assertEqual(result["bootstrap_deltas"]["with_E9_vs_core"]["valid_replicates"], 30)
        with self.assertRaisesRegex(ValueError, "continuous"):
            evaluate_nvt(core[:100] + core[101:], nvt)
        with self.assertRaisesRegex(ValueError, "insufficient"):
            evaluate_nvt(core[:100], nvt[:100])


def sha(content):
    return hashlib.sha256(content).hexdigest()


class NvtSnapshotTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="eco-e9-licence-fixture-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.evidence = b"SYNTHETIC TEST GRANT; no real entitlement."
        (self.root / "grant.txt").write_bytes(self.evidence)
        self.rights = {"verification_status": "verified", "provider": "coinmetrics_network_data", "asset": "eth",
                       "frequency": "1d", "metrics": list(METRICS), "private_cache": True, "private_research": True,
                       "valid_from": "2026-10-01", "valid_until": "2026-10-31", "evidence_file": "grant.txt",
                       "evidence_sha256": sha(self.evidence)}
        self.rights_file = self.root / "rights.json"
        self.rights_file.write_text(json.dumps(self.rights), encoding="utf-8")
        timestamp = "2026-10-02T00:00:00Z"
        self.raw = {"data": [{"asset": "eth", "time": timestamp, "CapMrktCurUSD": "100", "TxTfrValAdjUSD": "10"}]}
        raw = json.dumps(self.raw).encode()
        (self.root / "page.json").write_bytes(raw)
        self.rows = [{"asset": "eth", "source_timestamp": timestamp, "observation_date": "2026-10-02",
                      "period_end_utc": "2026-10-03T00:00:00Z", "source_available_at": None,
                      "retrieved_at": "2026-10-03T04:00:01Z", "source_page_sha256": sha(raw),
                      "metrics": {metric: self.raw["data"][0][metric] for metric in METRICS}}]
        content = (json.dumps(self.rows[0]) + "\n").encode()
        (self.root / "canonical.jsonl").write_bytes(content)
        self.manifest = {"status": "complete", "provider": "coinmetrics_network_data", "asset": "eth", "frequency": "1d",
                         "metrics": list(METRICS), "authorization": "api_key_environment_server_only",
                         "source_rights": {"rights_file_sha256": sha(self.rights_file.read_bytes()),
                                           "evidence_sha256": sha(self.evidence), "private_cache": True, "private_research": True},
                         "retrieved_at": "2026-10-03T04:00:00Z", "as_of_utc": "2026-10-03",
                         "start_date_requested": "2026-10-02", "end_date_requested": "2026-10-02",
                         "snapshot": {"canonical_file": "canonical.jsonl", "canonical_sha256": sha(content), "row_count": 1,
                                      "first_observation_date": "2026-10-02", "last_observation_date": "2026-10-02"},
                         "pages": [{"raw_file": "page.json", "response_sha256": sha(raw), "completed_at": "2026-10-03T04:00:01Z",
                                    "http_status": 200, "request_url": "https://api.coinmetrics.io/v4/timeseries/asset-metrics?assets=eth&metrics=CapMrktCurUSD,TxTfrValAdjUSD&frequency=1d"}]}
        self.write_manifest()

    def write_manifest(self):
        (self.root / "manifest.json").write_text(json.dumps(self.manifest), encoding="utf-8")

    def load(self):
        return load_nvt_snapshot(self.root, self.rights_file, date(2026, 10, 3))

    def update_canonical(self):
        content = ("\n".join(json.dumps(row) for row in self.rows) + "\n").encode()
        (self.root / "canonical.jsonl").write_bytes(content)
        self.manifest["snapshot"]["canonical_sha256"] = sha(content)
        self.write_manifest()

    def test_licensed_snapshot_raw_and_canonical_match(self):
        rows, manifest = self.load()
        self.assertEqual(rows, self.rows)
        self.assertEqual(manifest["provider"], "coinmetrics_network_data")

    def test_licence_evidence_expiry_and_manifest_binding(self):
        with self.assertRaises(ValueError):
            verify_rights(self.rights_file, date(2026, 11, 1))
        self.manifest["source_rights"]["rights_file_sha256"] = "0"*64
        self.write_manifest()
        with self.assertRaisesRegex(ValueError, "licence"):
            self.load()
        (self.root / "grant.txt").write_bytes(b"tampered")
        with self.assertRaisesRegex(ValueError, "checksum"):
            verify_rights(self.rights_file, date(2026, 10, 3))

    def test_raw_tamper_and_canonical_forgery_rejected(self):
        self.rows[0]["metrics"]["TxTfrValAdjUSD"] = "999"
        self.update_canonical()
        with self.assertRaisesRegex(ValueError, "provenance"):
            self.load()
        (self.root / "page.json").write_text("{}")
        with self.assertRaisesRegex(ValueError, "checksum"):
            self.load()

    def test_open_day_wrong_schema_and_unadjusted_substitution_rejected(self):
        self.rows[0]["period_end_utc"] = "2026-10-04T00:00:00Z"
        self.update_canonical()
        with self.assertRaisesRegex(ValueError, "calendar/schema/vintage"):
            self.load()
        self.manifest["metrics"] = ["CapMrktCurUSD", "TxTfrValUSD"]
        self.write_manifest()
        with self.assertRaisesRegex(ValueError, "pair contract"):
            self.load()

    def test_secret_request_and_path_escape_rejected(self):
        self.manifest["pages"][0]["request_url"] += "&api_key=fixture-only"
        self.write_manifest()
        with self.assertRaisesRegex(ValueError, "request contract"):
            self.load()
        self.manifest["snapshot"]["canonical_file"] = "../canonical.jsonl"
        self.write_manifest()
        with self.assertRaisesRegex(ValueError, "filename"):
            self.load()

    def test_private_build_is_immutable_bound_to_inputs_and_frozen_protocol(self):
        core_folder = self.root / "core"
        core_folder.mkdir()
        core_rows, api_rows, e9_api = [], [], []
        for i, item in enumerate(fixture(2400)):
            day = date.fromisoformat(item["observation_date"])
            timestamp = day.isoformat() + "T00:00:00Z"
            price = 100 + 80*math.sin(i/60)
            core_metrics = {"PriceUSD": str(price), "CapMrktCurUSD": str(price*100),
                            "SplyCur": "100", "CapMVRVCur": str(2 + math.sin(i/33))}
            api_rows.append({"asset": "eth", "time": timestamp, **core_metrics})
            core_rows.append({"asset": "eth", "observation_date": day.isoformat(), "source_timestamp": timestamp,
                              "period_end_utc": (day + timedelta(days=1)).isoformat() + "T00:00:00Z",
                              "source_available_at": None, "metrics": core_metrics})
            e9_api.append({"asset": "eth", "time": timestamp, "CapMrktCurUSD": core_metrics["CapMrktCurUSD"],
                           "TxTfrValAdjUSD": str(item["metrics"]["TxTfrValAdjUSD"])})
        canonical = b"".join(encode(row) for row in core_rows)
        core_raw = encode({"data": api_rows})
        (core_folder / "canonical.jsonl").write_bytes(canonical)
        (core_folder / "page.json").write_bytes(core_raw)
        core_manifest = {"status": "complete", "provider": "coinmetrics_community_api", "asset": "eth", "frequency": "1d",
                         "retrieved_at": "2026-10-03T04:00:00Z", "as_of_utc": "2026-10-03",
                         "snapshot": {"canonical_file": "canonical.jsonl", "canonical_sha256": sha(canonical),
                                      "row_count": len(core_rows), "first_observation_date": core_rows[0]["observation_date"],
                                      "last_observation_date": core_rows[-1]["observation_date"]},
                         "pages": [{"raw_file": "page.json", "response_sha256": sha(core_raw)}]}
        (core_folder / "manifest.json").write_bytes(encode(core_manifest))
        e9_raw = encode({"data": e9_api})
        (self.root / "page.json").write_bytes(e9_raw)
        self.rows = [{"asset": "eth", "observation_date": row["time"][:10], "source_timestamp": row["time"],
                      "period_end_utc": (date.fromisoformat(row["time"][:10]) + timedelta(days=1)).isoformat() + "T00:00:00Z",
                      "source_available_at": None, "retrieved_at": "2026-10-03T04:00:01Z", "source_page_sha256": sha(e9_raw),
                      "metrics": {metric: row[metric] for metric in METRICS}} for row in e9_api]
        self.manifest["pages"][0]["response_sha256"] = sha(e9_raw)
        self.manifest.update(start_date_requested=self.rows[0]["observation_date"], end_date_requested=self.rows[-1]["observation_date"])
        self.manifest["snapshot"].update(row_count=len(self.rows), first_observation_date=self.rows[0]["observation_date"],
                                         last_observation_date=self.rows[-1]["observation_date"])
        self.update_canonical()
        project = self.root / "project"
        (project / "configs/research").mkdir(parents=True)
        protocol_path = Path("configs/research/e9-nvt-candidate-v0.1.0.json")
        (project / protocol_path).write_bytes((ROOT / protocol_path).read_bytes())
        (project / "eco").mkdir()
        for name in ("core", "research", "nvt", "nvt_pipeline"):
            (project / f"eco/{name}.py").write_bytes((ROOT / f"eco/{name}.py").read_bytes())
        # Fixture uses 30 replicates and a fixed clock; production fixes 10000.
        with patch.object(nvt_pipeline, "ROOT", project), patch.object(nvt_pipeline, "verify_rights",
                side_effect=lambda path, *_: verify_rights(path, date(2026, 10, 3))), patch.object(nvt_pipeline, "evaluate_nvt",
                side_effect=lambda core, candidate: evaluate_nvt(core, candidate, replicates=30)) as evaluation:
            folder = nvt_pipeline.build_e9(core_folder, self.root, self.rights_file)
            self.assertTrue(folder.is_relative_to(project / "data/computed"))
            result = json.loads((folder / "research-private.json").read_text())
            self.assertFalse(result["public_release_allowed"])
            self.assertGreater(result["n"], 90)
            self.assertEqual(nvt_pipeline.build_e9(core_folder, self.root, self.rights_file), folder)
            self.assertEqual(evaluation.call_count, 1)
            (folder / "research-private.json").write_bytes(b"tampered")
            with self.assertRaisesRegex(ValueError, "checksum"):
                nvt_pipeline.build_e9(core_folder, self.root, self.rights_file)
            protocol = json.loads((project / protocol_path).read_text())
            protocol["normalizer"]["min_raw_observations"] = 100
            (project / protocol_path).write_bytes(encode(protocol))
            with self.assertRaisesRegex(ValueError, "frozen protocol"):
                nvt_pipeline.build_e9(core_folder, self.root, self.rights_file)


if __name__ == "__main__":
    unittest.main()
