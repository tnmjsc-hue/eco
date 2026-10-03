from datetime import timedelta
import math
import unittest
import numpy as np

from eco.core import COMPONENTS, ORIGIN, Normalizer, aggregate, compute, nupl_diagnostic, positive, quantile
from eco.research import (ablation_analysis, ap, auc, component_correlations,
                          labels, regime_analysis, spearman)


def fixture(n=1200):
    return [{"asset": "eth", "observation_date": (ORIGIN + timedelta(days=i)).isoformat(),
             "metrics": {"PriceUSD": 10 + i * .02 + 3 * math.sin(i / 30),
                         "CapMrktCurUSD": 1000 + i * 8 + 90 * math.cos(i / 11),
                         "CapMVRVCur": 1.5 + .6 * math.sin(i / 35), "SplyCur": 100}} for i in range(n)]


class CoreTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = fixture()
        cls.result = compute(cls.source)

    def test_hand_sma(self):
        prices = [r["metrics"]["PriceUSD"] for r in self.source]
        self.assertIsNone(self.result[348]["components"]["E1"]["raw"])
        self.assertAlmostEqual(self.result[349]["components"]["E1"]["raw"], math.log(np.mean(prices[239:350]) / (2 * np.mean(prices[:350]))))
        self.assertIsNone(self.result[728]["components"]["E5"]["raw"])
        self.assertAlmostEqual(self.result[729]["components"]["E5"]["raw"], math.log(prices[729] / np.mean(prices[:730])))

    def test_calendar_gap_breaks_sma_not_removed_row(self):
        gap = [r for i, r in enumerate(self.source) if i != 1100]
        result = compute(gap)
        self.assertEqual(len(result), len(self.source))
        self.assertFalse(result[1100]["source_row_present"])
        self.assertIsNone(result[1100]["score"])
        self.assertIsNone(result[1199]["components"]["E5"]["raw"])

    def test_ols_excludes_current(self):
        prices = np.array([r["metrics"]["PriceUSD"] for r in self.source[:730]])
        design = np.column_stack([np.ones(730), np.log(np.arange(1, 731))])
        a, b = np.linalg.lstsq(design, np.log(prices), rcond=None)[0]
        r = self.result[730]
        expected = math.log(self.source[730]["metrics"]["PriceUSD"]) - a - b * math.log(731)
        self.assertAlmostEqual(r["components"]["E6"]["raw"], expected, places=10)
        self.assertIsNone(self.result[729]["components"]["E6"]["raw"])
        self.assertEqual(r["e6_fit"]["observations"], 730)

    def test_e7_population_past_and_nupl_not_vote(self):
        cap = [r["metrics"]["CapMrktCurUSD"] for r in self.source[:365]]
        current = self.source[365]["metrics"]
        expected = (current["CapMrktCurUSD"] - current["CapMrktCurUSD"] / current["CapMVRVCur"]) / np.std(cap, ddof=0)
        self.assertAlmostEqual(self.result[365]["components"]["E7"]["raw"], expected)
        self.assertIsNone(self.result[364]["components"]["E7"]["raw"])
        self.assertAlmostEqual(self.result[365]["nupl_diagnostic"], 1 - 1 / current["CapMVRVCur"])
        self.assertEqual(set(self.result[-1]["components"]), set(COMPONENTS))

    def test_nupl_diagnostic_contract(self):
        self.assertEqual(nupl_diagnostic(None), {"value": None, "reason": "missing_input"})
        self.assertEqual(nupl_diagnostic(0), {"value": None, "reason": "invalid_input"})
        self.assertEqual(nupl_diagnostic(-1), {"value": None, "reason": "invalid_input"})
        self.assertEqual(nupl_diagnostic("bad"), {"value": None, "reason": "invalid_input"})
        self.assertAlmostEqual(nupl_diagnostic(2)["value"], 0.5)
        self.assertIsNone(self.result[364]["nupl_reason"])

    def test_prefix_invariance_and_repeatability(self):
        self.assertEqual(compute(self.source[:1150]), self.result[:1150])
        self.assertEqual(compute(self.source), self.result)

    def test_extreme_future_never_changes_prefix(self):
        altered = fixture()
        altered[-1]["metrics"]["PriceUSD"] = 1e9
        changed = compute(altered)
        self.assertEqual(changed[:-1], self.result[:-1])
        self.assertEqual(changed[-1]["e6_fit"], self.result[-1]["e6_fit"])
        self.assertEqual(changed[-1]["components"]["E5"]["lower"], self.result[-1]["components"]["E5"]["lower"])

    def test_validation_and_origin(self):
        for bad in ("NaN", "Infinity", "x", 0, -1):
            with self.assertRaises(ValueError):
                positive(bad)
        self.assertIsNone(positive(None))
        for source in ([self.source[0], self.source[0]], self.source[1:]):
            with self.assertRaises(ValueError):
                compute(source)

    def test_normalizer_linear_clip_current_excluded(self):
        normalizer = Normalizer()
        for i in range(365):
            self.assertIsNone(normalizer.compute(ORIGIN + timedelta(days=i), float(i))["score"])
        result = normalizer.compute(ORIGIN + timedelta(days=365), 100000.)
        self.assertAlmostEqual(result["lower"], 18.2)
        self.assertAlmostEqual(result["upper"], 345.8)
        self.assertEqual(result["score"], 100)
        self.assertEqual(result["history_count"], 365)
        self.assertEqual(normalizer.compute(ORIGIN + timedelta(days=366), -100.)["score"], 0)
        self.assertEqual(quantile([0, 10], .05), .5)

    def test_normalizer_calendar_boundary_and_degenerate(self):
        normalizer = Normalizer()
        for i in range(1461):
            result = normalizer.compute(ORIGIN + timedelta(days=i), 1.)
        self.assertEqual(result["history_count"], 1460)
        self.assertEqual(result["reason"], "degenerate_normalizer")
        result = normalizer.compute(ORIGIN + timedelta(days=2000), None)
        self.assertEqual(result["history_count"], 921)
        self.assertIsNone(result["score"])

    def test_aggregation_strict_null_weights_custom_empty(self):
        scores = dict(E1=0., E5=30., E6=60., E7=100.)
        self.assertAlmostEqual(aggregate(scores), 65.)
        self.assertEqual(aggregate(scores, ()), None)
        self.assertAlmostEqual(aggregate(scores, ("E1", "E7")), 75.)
        scores["E6"] = None
        self.assertIsNone(aggregate(scores))
        self.assertEqual(aggregate(scores, ("E1",)), 0.)
        with self.assertRaises(ValueError):
            aggregate(scores, ("E2",))

    def test_full_score_bounds_and_warmup(self):
        self.assertTrue(all(r["score"] is None for r in self.result[:1095]))
        self.assertIsNotNone(self.result[1095]["score"])
        self.assertTrue(all(r["score"] is None or 0 <= r["score"] <= 100 for r in self.result))


class ResearchTest(unittest.TestCase):
    def test_ap_ties_and_ranking(self):
        self.assertAlmostEqual(ap([1, 0, 1], [3, 2, 1]), 5 / 6)
        self.assertAlmostEqual(ap([1, 0, 1], [1, 1, 1]), 2 / 3)
        self.assertEqual(ap([0, 0], [1, 2]), None)
        self.assertAlmostEqual(ap([1, 0, 1], [3, 2, 1], [2, 1, 1]), 11 / 12)
        self.assertEqual(auc([1, 0], [1, 1]), .5)
        self.assertEqual(auc([1, 0], [3, 1]), 1.)

    def test_label_next_day_completed_horizon_and_null(self):
        rows = [{"date": (ORIGIN + timedelta(days=i)).isoformat(), "price_usd": p} for i, p in enumerate([100, 70, 50, 25, 20])]
        result = labels(rows, horizon=2)
        self.assertEqual(list(result.values()), [1, 1, 1])
        self.assertEqual(len(result), 3)
        rows[1]["price_usd"] = None
        self.assertEqual(len(labels(rows, horizon=2)), 1)

    def test_spearman_is_tie_aware_and_component_matrix_keeps_core_only(self):
        self.assertAlmostEqual(spearman([1, 2, 2, 4], [10, 20, 30, 40]), 0.9486832980505138)
        rows = []
        for i in range(4):
            value = float(i * 20)
            rows.append({"date": (ORIGIN + timedelta(days=i)).isoformat(), "score": value,
                         "components": {k: {"score": value + j} for j, k in enumerate(("E1", "E5", "E6", "E7"))},
                         "nupl_diagnostic": value})
        result = component_correlations(rows)
        self.assertEqual(result["components"], ["E1", "E5", "E6", "E7"])
        self.assertNotIn("E2", result["matrix"])
        self.assertEqual(result["matrix"]["E1"]["E7"]["n"], 4)
        self.assertAlmostEqual(result["matrix"]["E1"]["E1"]["rho"], 1.)

    def test_ablation_retains_frozen_weights_and_regime_boundaries(self):
        components = {"E1": 20., "E5": 40., "E6": 60., "E7": 80.}
        rows = []
        labels_by_date = {}
        for i, day in enumerate(("2020-01-01", "2021-08-05", "2022-09-15", "2024-03-13")):
            rows.append({"date": day, "score": 56.66666666666667 + i,
                         "components": {k: {"score": value + i} for k, value in components.items()}})
            labels_by_date[day] = int(i % 2 == 0)
        ablation = ablation_analysis(rows, np.array([labels_by_date[r["date"]] for r in rows]))
        self.assertEqual(ablation["method"], "frozen_component_weights_renormalized_after_selection")
        self.assertEqual(ablation["models"]["without_E7"]["components"], ["E1", "E5", "E6"])
        self.assertEqual(ablation["models"]["valuation_group_only"]["components"], ["E7"])
        regimes = regime_analysis(rows, labels_by_date)
        self.assertEqual(regimes["regimes"]["pre_london"]["n"], 1)
        self.assertEqual(regimes["regimes"]["london_to_merge"]["n"], 1)
        self.assertEqual(regimes["regimes"]["post_merge_pre_dencun"]["n"], 1)
        self.assertEqual(regimes["regimes"]["post_dencun"]["n"], 1)


if __name__ == "__main__":
    unittest.main()
