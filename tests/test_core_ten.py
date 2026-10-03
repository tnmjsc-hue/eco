import copy
from datetime import date, timedelta
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch
from eco import core_ten as ten
from eco.pipeline import ROOT, read_json, encode, digest
from eco import seven


def current(public, prefix):
    pointer = read_json(public/"data"/prefix/"latest.json")
    return public/pointer["manifest_url"].lstrip("/").replace("/manifest.json", "")


def fixture(n=500):
    rows = []
    for i in range(n):
        values = {"nupl_diagnostic": (i % 101-50)/100, "supply_change_30d": (i % 31-15)/100,
                  "exchange_balance_change_30d": float(i % 63-31)}
        rows.append({"date": (date(2020, 1, 1)+timedelta(days=i)).isoformat(),
                     "metrics": {spec["input"]: {"value": values[spec["input"]], "unit": spec["unit"], "reason": None,
                       "source_flags": ["flash"] if m == "exchange_balance_pressure" else []} for m, spec in ten.protocol()["new_features"].items()}})
    return rows


class CoreTenTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rows, cls.parents, cls.proofs = ten.expected(ROOT/"public")

    def copy_parents(self, public):
        for prefix in ("", "network-proxies", "extended", "diagnostics"):
            root = public/"data"/prefix; root.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT/"public/data"/prefix/"latest.json", root/"latest.json")
            source = current(ROOT/"public", prefix)
            shutil.copytree(source, root/"releases"/source.name)

    def rehash(self, public, prefix, manifest):
        folder = current(public, prefix); (folder/"manifest.json").write_bytes(encode(manifest))
        path = public/"data"/prefix/"latest.json"; pointer = read_json(path)
        pointer["manifest_sha256"] = digest((folder/"manifest.json").read_bytes()); path.write_bytes(encode(pointer))

    def test_fixed_family_budgets_avoid_extra_MVRV_and_exchange_votes(self):
        config = ten.protocol(); self.assertEqual(sum(ten.WEIGHTS.values()), 1)
        self.assertEqual(sum(ten.WEIGHTS[m] for m in ("E7", "E2")), .375)
        self.assertEqual(sum(ten.WEIGHTS[m] for m in ("exchange_share", "exchange_balance_pressure")), .0625)
        self.assertEqual(sum(ten.WEIGHTS[m] for m in seven.CORE_IDS[:3]), .375)
        self.assertEqual(config["groups"]["network"]["weight"], .25)
        self.assertEqual(ten.aggregate(dict.fromkeys(ten.IDS, 100)), 100)
        self.assertEqual(ten.aggregate(dict.fromkeys(ten.IDS, 0)), 0)

    def test_normalization_has_365_past_values_and_excludes_current(self):
        raw = fixture(367); values = ten.normalize(raw)
        self.assertIsNone(values[raw[364]["date"]]["E2"]["score"])
        self.assertEqual(values[raw[365]["date"]]["E2"]["history_count"], 365)
        before = copy.deepcopy(raw); before[365]["metrics"]["nupl_diagnostic"]["value"] = .9999
        shock = ten.normalize(before)[raw[365]["date"]]["E2"]
        self.assertEqual(shock["lower"], values[raw[365]["date"]]["E2"]["lower"])
        self.assertEqual(shock["upper"], values[raw[365]["date"]]["E2"]["upper"])
        self.assertEqual(shock["score"], 100)

    def test_orientation_signed_zero_and_missing_values(self):
        raw = fixture(); last = raw[-1]
        last["metrics"]["supply_change_30d"]["value"] = -.1
        last["metrics"]["exchange_balance_change_30d"]["value"] = 0
        last["metrics"]["nupl_diagnostic"].update(value=None, reason="missing_input")
        item = ten.normalize(raw)[last["date"]]
        self.assertEqual(item["supply_scarcity"]["raw"], .1)
        self.assertEqual(item["supply_scarcity"]["input_value"], -.1)
        self.assertEqual(item["exchange_balance_pressure"]["raw"], 0)
        self.assertIsNotNone(item["exchange_balance_pressure"]["score"])
        self.assertEqual(item["exchange_balance_pressure"]["source_flags"], ["flash"])
        self.assertIsNone(item["E2"]["score"]); self.assertEqual(item["E2"]["reason"], "missing_input")

    def test_future_prefix_invariance_and_calendar_window_expiry(self):
        raw = fixture(1800); cutoff = raw[1500]["date"]
        prefix = ten.normalize(raw[:1501]); all_values = ten.normalize(raw)
        self.assertEqual(prefix, {k: v for k, v in all_values.items() if k <= cutoff})
        self.assertEqual(all_values[raw[-1]["date"]]["E2"]["history_count"], 1460)
        shock = copy.deepcopy(raw); shock[-1]["metrics"]["exchange_balance_change_30d"]["value"] = 1e100
        self.assertEqual(prefix, {k: v for k, v in ten.normalize(shock).items() if k <= cutoff})

    def test_degenerate_normalizer_stays_null(self):
        raw = fixture()
        for r in raw: r["metrics"]["supply_change_30d"]["value"] = 0
        item = ten.normalize(raw)[raw[-1]["date"]]["supply_scarcity"]
        self.assertIsNone(item["score"]); self.assertEqual(item["reason"], "degenerate_normalizer")

    def test_malformed_calendar_units_and_nonfinite_inputs_fail(self):
        raw = fixture(4)
        for bad in (raw[1:2]+raw[1:], raw[:2]+raw[3:]):
            with self.assertRaises(ValueError): ten.normalize(bad)
        for value in (True, float("nan"), float("inf"), "0.2", 1):
            bad = copy.deepcopy(raw); bad[-1]["metrics"]["nupl_diagnostic"]["value"] = value
            with self.assertRaises(ValueError): ten.normalize(bad)
        raw[-1]["metrics"]["exchange_balance_change_30d"]["unit"] = "USD"
        with self.assertRaises(ValueError): ten.normalize(raw)

    def test_real_join_preserves_all_legacy_scores_and_flags(self):
        public = ROOT/"public"; old = read_json(current(public, "extended")/"history.json")["rows"]
        self.assertEqual([r["extended_score"] for r in self.rows], [r["score"] for r in old])
        self.assertEqual([r["core_score"] for r in self.rows], [r["core_score"] for r in old])
        self.assertEqual(self.rows[-1]["coverage"], 10)
        self.assertAlmostEqual(self.rows[-1]["score"], sum(self.rows[-1]["components"][m]*ten.WEIGHTS[m] for m in ten.IDS), places=10)
        diagnostic = read_json(current(public, "diagnostics")/"history.json")["rows"][-1]
        self.assertEqual(self.rows[-1]["new_features"]["exchange_balance_pressure"]["input_value"], diagnostic["metrics"]["exchange_balance_change_30d"]["value"])
        self.assertIn("flash", self.rows[-1]["source_flags"]["exchange_balance_pressure"])
        self.assertIsNone(self.rows[0]["score"])

    def test_custom_selection_does_not_fill_missing_or_duplicate(self):
        components = dict.fromkeys(ten.IDS, 20); components["E2"] = None
        for selected in ([], ["E7", "E7"], ["unknown"]): self.assertIsNone(ten.aggregate(components, selected))
        self.assertIsNone(ten.aggregate(components)); self.assertEqual(ten.aggregate(components, ["E7"]), 20)
        components["E7"] = True
        with self.assertRaises(ValueError): ten.aggregate(components, ["E7"])

    def test_mixed_parent_lineage_and_bad_readback_never_publish(self):
        for mutation in ("lineage", "readback", "license"):
            with self.subTest(mutation=mutation), tempfile.TemporaryDirectory() as tmp:
                public = Path(tmp)/"public"; self.copy_parents(public); m = read_json(current(public, "diagnostics")/"manifest.json")
                if mutation == "lineage": m["parents"]["core"]["history_sha256"] = "0"*64
                if mutation == "readback": m["private_inputs_verified"]["proxies"]["objects_readback_verified"] = False
                if mutation == "license": m["attribution"]["licence"] = "unknown"
                self.rehash(public, "diagnostics", m)
                with self.assertRaises(ValueError): ten.build(public, Path(tmp)/"output")
                self.assertFalse((public/"data/core-v2/latest.json").exists())

    def test_publication_gate_rejects_rehashed_data_and_false_claim(self):
        with tempfile.TemporaryDirectory() as tmp:
            public = Path(tmp)/"public"; output = Path(tmp)/"private"; self.copy_parents(public)
            folder = ten.build(public, output); manifest = read_json(folder/"manifest.json"); history = read_json(folder/"history.json")
            original_history = (folder/"history.json").read_bytes(); original_manifest = (folder/"manifest.json").read_bytes()
            history["rows"][-1]["new_features"]["E2"]["input_value"] = .8
            (folder/"history.json").write_bytes(encode(history)); manifest["files"]["history.json"] = digest(encode(history))
            (folder/"manifest.json").write_bytes(encode(manifest))
            with self.assertRaisesRegex(ValueError, "verified parents"): ten.publish(folder, public)
            (folder/"history.json").write_bytes(original_history); (folder/"manifest.json").write_bytes(original_manifest)
            report = read_json(folder/"research.json"); report["decision"] = "validated_predictive_model"
            (folder/"research.json").write_bytes(encode(report)); manifest = read_json(folder/"manifest.json"); manifest["files"]["research.json"] = digest(encode(report))
            (folder/"manifest.json").write_bytes(encode(manifest))
            with self.assertRaisesRegex(ValueError, "evaluation differs"): ten.publish(folder, public)
            self.assertFalse((public/"data/core-v2/latest.json").exists())

    def test_publication_idempotency_failure_and_ledgers_are_immutable(self):
        with tempfile.TemporaryDirectory() as tmp:
            public = Path(tmp)/"public"; output = Path(tmp)/"private"; self.copy_parents(public)
            folder = ten.build(public, output); self.assertEqual(ten.publish(folder, public), "published")
            pointer_path = public/"data/core-v2/latest.json"; before = pointer_path.read_bytes()
            published = current(public, "core-v2"); hashes = {f.name: digest(f.read_bytes()) for f in published.iterdir()}
            ledger = public/"data/core-v2/publications"/(self.rows[-1]["date"]+".json"); ledger_bytes = ledger.read_bytes()
            self.assertEqual(ten.publish(folder, public), "unchanged"); self.assertEqual(pointer_path.read_bytes(), before)
            self.assertEqual(set(hashes), {"manifest.json", "research.json", "history.json"})
            self.assertEqual(len(list(ledger.parent.iterdir())), 1)
            with patch("eco.core_ten.expected", side_effect=ValueError("credential secret URL")):
                with self.assertRaisesRegex(RuntimeError, "previous release preserved"): ten.daily(public, output)
            self.assertEqual(pointer_path.read_bytes(), before); self.assertEqual(ledger.read_bytes(), ledger_bytes)
            self.assertEqual(hashes, {f.name: digest(f.read_bytes()) for f in published.iterdir()})
            status = read_json(public/"data/core-v2/status.json"); self.assertEqual(status["outcome"], "failed")
            self.assertNotIn("secret", str(status))

    def test_reduced_bootstrap_is_blocked_and_real_evaluation_is_honest(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(ValueError, "10000"): ten.build(ROOT/"public", Path(tmp), replicates=20)
        r = ten.evaluate(self.rows, 20)
        self.assertAlmostEqual(r["comparisons"]["core"]["ap_delta"], r["statistics"]["core_ten"]["average_precision"]-r["statistics"]["core"]["average_precision"], places=12)
        self.assertEqual(r["decision"], "publish_experimental_preview_no_predictive_validation_claim")
        self.assertEqual(len(r["ablation"]), 10); self.assertIn("reused_holdout_is_exploratory", r["limitations"])

    def test_engine_revision_preserves_previous_release_and_first_publication(self):
        with tempfile.TemporaryDirectory() as tmp:
            public = Path(tmp)/"public"; output = Path(tmp)/"private"; self.copy_parents(public)
            folder = ten.build(public, output); ten.publish(folder, public)
            old = current(public, "core-v2"); original = {f.name: f.read_bytes() for f in old.iterdir()}
            ledger = public/"data/core-v2/publications"/(self.rows[-1]["date"]+".json"); ledger_bytes = ledger.read_bytes()
            with patch("eco.core_ten.engine_hash", return_value="1"*64):
                revised = ten.build(public, output); self.assertEqual(ten.publish(revised, public), "revised")
            new = current(public, "core-v2"); self.assertNotEqual(new.name, old.name)
            revision = read_json(new/"manifest.json")["revision"]
            self.assertEqual(revision["previous_release_id"], old.name); self.assertEqual(revision["changed_dates"], [])
            self.assertEqual({f.name: f.read_bytes() for f in old.iterdir()}, original)
            self.assertEqual(ledger.read_bytes(), ledger_bytes)

    def test_coverage_regression_rejects_release_and_keeps_pointer(self):
        with tempfile.TemporaryDirectory() as tmp:
            public = Path(tmp)/"public"; output = Path(tmp)/"private"; self.copy_parents(public)
            folder = ten.build(public, output); ten.publish(folder, public)
            before = (public/"data/core-v2/latest.json").read_bytes(); lost = copy.deepcopy(self.rows)
            lost[-1]["components"]["E2"] = None; lost[-1]["reasons"]["E2"] = "missing_input"; lost[-1]["score"] = None; lost[-1]["coverage"] = 9
            lost[-1]["new_features"]["E2"].update(input_value=None, raw=None, score=None, reason="missing_input")
            with patch("eco.core_ten.engine_hash", return_value="2"*64), patch("eco.core_ten.expected", return_value=(lost, self.parents, self.proofs)):
                candidate = ten.build(public, output)
                with self.assertRaisesRegex(ValueError, "lost previously usable components"): ten.publish(candidate, public)
            self.assertEqual((public/"data/core-v2/latest.json").read_bytes(), before)


if __name__ == "__main__": unittest.main()
