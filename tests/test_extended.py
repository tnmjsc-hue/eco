from datetime import date, timedelta
import math
import unittest

from eco.extended import compute_fee_activity, evaluate_fee_activity


def fee_fixture(n=900):
    start = date(2015, 7, 30)
    return [{
        "asset": "eth",
        "observation_date": (start + timedelta(days=i)).isoformat(),
        "metrics": {"FeeTotNtv": 0 if i < 8 else 100 + 20 * math.sin(i / 25)},
    } for i in range(n)]


class FeeCandidateTest(unittest.TestCase):
    def test_formula_guard_and_warmup(self):
        result = compute_fee_activity(fee_fixture())
        self.assertIsNone(result[363]["raw"])
        self.assertEqual(result[363]["raw_reason"], "insufficient_history_or_calendar_gap")
        self.assertIsNotNone(result[364]["raw"])
        self.assertIsNone(result[364]["score"])

    def test_calendar_gap_does_not_become_zero(self):
        source = [row for i, row in enumerate(fee_fixture()) if i != 500]
        result = compute_fee_activity(source)
        self.assertFalse(result[500]["source_row_present"])
        self.assertIsNone(result[500]["raw"])
        self.assertIsNone(result[501]["raw"])

    def test_future_shock_keeps_prefix(self):
        source = fee_fixture()
        altered = fee_fixture()
        altered[-1]["metrics"]["FeeTotNtv"] = 1e12
        self.assertEqual(compute_fee_activity(source)[:-1], compute_fee_activity(altered)[:-1])

    def test_invalid_input_rejected(self):
        bad = fee_fixture(400)
        bad[100]["metrics"]["FeeTotNtv"] = -1
        with self.assertRaises(ValueError):
            compute_fee_activity(bad)

    def test_evaluation_is_explicitly_exploratory(self):
        source = fee_fixture(2400)
        fee = compute_fee_activity(source)
        core = []
        for row in fee:
            core.append({
                "date": row["date"], "score": 50.0,
                "components": {"E1": 50.0, "E5": 50.0, "E6": 50.0, "E7": 50.0},
                "price_usd": 100.0,
            })
        result = evaluate_fee_activity(core, fee)
        self.assertEqual(result["status"], "exploratory_reconstructed_only")
        self.assertIn("new_holdout", result["decision"])
