"""Fixed acceptance examples for the macro specification, not production engine tests."""
from collections import Counter
from copy import deepcopy
from itertools import permutations, product
import json
import re
import unittest

from scripts import check_macro_cross_spec as spec


class MacroCrossSpecTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.text = spec.SPEC_PATH.read_text(encoding="utf-8")
        cls.fixture = json.loads(spec.FIXTURE_PATH.read_text(encoding="utf-8"))
        cls.matrix = spec.read_matrix(cls.text)

    def test_version_and_changed_markdown_fixtures_are_linked(self):
        self.assertIn(f'| Ruleset đề xuất | `{self.fixture["ruleset_version"]}` |', self.text)
        self.assertIn(f'| Schema đầu ra đề xuất | `{self.fixture["schema_version"]}` |', self.text)
        for row in self.fixture["routing_regressions"]:
            line = next(s for s in self.text.splitlines() if s.startswith(f'| `{row["id"]}` |'))
            self.assertIn(f'I={row["I"]}; L={row["L"]}; G={row["G"]}', line)
            self.assertIn(row["regime"], line)
        self.assertEqual(len(set(re.findall(r'^\| `(T\d+)` \|', self.text, re.M))), 48)
        self.assertIn('"previous_assessment_id": previous_assessment.assessment_id hoặc null', self.text)
        self.assertIn('last_successful_source_check_at <= known_at <= as_of', self.text)
        self.assertIn('số lượng input lớn hơn một tự nó không đủ', self.text)

    def test_fixed_oracle_covers_all_125_regimes_and_assets(self):
        states = self.fixture["states"]
        self.assertEqual(states, list(spec.STATES))
        self.assertEqual(set(self.fixture["regime_grid"]), set(states))
        count = Counter()
        for i in states:
            grid = self.fixture["regime_grid"][i]
            self.assertEqual(len(grid), 5)
            for li, l in enumerate(states):
                self.assertEqual(len(grid[li]), 5)
                for gi, g in enumerate(states):
                    with self.subTest(I=i, L=l, G=g):
                        expected = grid[li][gi]
                        regime, assets = spec.route(i, l, g, self.matrix)
                        self.assertEqual(regime, expected)
                        self.assertEqual(list(assets), self.fixture["regime_assets"][expected])
                        count[regime] += 1
        self.assertEqual(sum(count.values()), 125)
        self.assertEqual(count["R_CONFLICT"], 66)
        self.assertEqual(count["R_ACTIVITY_ONLY"], 7)
        self.assertEqual(count["R_INSUFFICIENT"], 13)

    def test_pipeline_gate_overrides_all_125_states(self):
        for axes in product(spec.STATES, repeat=3):
            for pipeline in ("stale", "unknown"):
                with self.subTest(axes=axes, pipeline=pipeline):
                    self.assertEqual(spec.route(*axes, self.matrix, pipeline=pipeline),
                                     ("R_STALE", ("insufficient_evidence",) * 3))

    def test_insufficient_gate_precedes_mixed(self):
        for axes in (("mixed", "unknown", "unknown"),
                     ("unknown", "mixed", "unknown"), ("unknown", "unknown", "mixed")):
            self.assertEqual(spec.route(*axes, self.matrix)[0], "R_INSUFFICIENT")

    def test_negative_level_override_never_creates_support(self):
        for axes in product(spec.STATES, repeat=3):
            original = spec.route(*axes, self.matrix)
            overridden = spec.route(*axes, self.matrix, negative_level=True)
            expected_crypto = "mixed" if original[1][2] == "supportive" else original[1][2]
            self.assertEqual(overridden, (original[0], (*original[1][:2], expected_crypto)))

    def test_reducer_permutations_unknown_duplicate_and_split(self):
        for values in product(spec.STATES, repeat=3):
            expected = spec.reduce_directions(values)
            for reordered in permutations(values):
                self.assertEqual(spec.reduce_directions(reordered), expected)
            self.assertEqual(spec.reduce_directions((*values, "unknown", *values)), expected)
        self.assertEqual(spec.reduce_directions(("positive", "negative")), "mixed")
        self.assertEqual(spec.reduce_directions(()), "unknown")
        with self.assertRaises(ValueError):
            spec.route("neutral", "flat", "flat", self.matrix)

    def test_t15_activity_only_and_t43_conflict(self):
        for row in self.fixture["routing_regressions"]:
            self.assertEqual(spec.route(row["I"], row["L"], row["G"], self.matrix)[0], row["regime"])

    def test_t38_t44_transitions_use_batch_membership_not_count(self):
        for row in self.fixture["transition_regressions"]:
            with self.subTest(row=row):
                self.assertEqual(spec.transition_relation(row["changed_event_ids"],
                                 row["latest_event_ids"], row["has_previous"]), row["expected"])

    def test_pipeline_cutoff_and_48h_boundaries(self):
        for row in self.fixture["pipeline_regressions"]:
            status = dict(known_at=row["known_at"], last_successful_source_check_at=row["check_at"])
            with self.subTest(name=row["name"]):
                self.assertEqual(spec.pipeline_status(status, "2026-10-09T00:00:00Z"),
                                 (row["state"], row["reason"]))
        with self.assertRaises(ValueError):
            spec.pipeline_status({}, "2026-10-09")

    def test_batch_replacements_pair_old_observations_to_new_event(self):
        before = {metric: dict(observation_id=metric + "-aug", event_id="jobs-aug")
                  for metric in ("nfp", "unemployment")}
        after = {metric: dict(observation_id=metric + "-sep", event_id="jobs-sep")
                 for metric in ("nfp", "unemployment")}
        changes, ids = spec.pair_changes(before, after)
        self.assertEqual(ids, ["nfp-aug", "nfp-sep", "unemployment-aug", "unemployment-sep"])
        self.assertEqual(spec.transition_relation([c["trigger_event_id"] for c in changes],
                                                 ["jobs-sep"], True), "latest_batch_only")
        after.pop("unemployment")
        changes, ids = spec.pair_changes(before, after)
        self.assertEqual(changes[1]["after_observation_id"], None)
        self.assertEqual(spec.transition_relation([c["trigger_event_id"] for c in changes],
                                                 ["jobs-sep"], True), "multiple_inputs_changed")
        self.assertEqual(spec.pair_changes(before, before), ([], []))

    def test_future_status_cannot_refresh_past_cutoff(self):
        old = dict(batch_status_id="status-old", batch_status_sha256="a" * 64,
                   known_at="2026-10-06T00:00:00Z", last_successful_source_check_at="2026-10-06T00:00:00Z")
        future = dict(batch_status_id="status-future", batch_status_sha256="b" * 64,
                      known_at="2026-10-10T00:00:00Z", last_successful_source_check_at="2026-10-10T00:00:00Z")
        cutoff = "2026-10-09T00:00:00Z"
        for sequence in ([old], [old, future], [future, old]):
            selected = spec.select_status_vintage(sequence, cutoff)
            self.assertEqual(selected, old)
            self.assertEqual(spec.pipeline_status(selected, cutoff)[0], "stale")
        self.assertIsNone(spec.select_status_vintage([future], cutoff))
        ambiguous = dict(old, batch_status_id="conflicting", batch_status_sha256="c" * 64)
        self.assertIsNone(spec.select_status_vintage([old, ambiguous], cutoff))

    def candidate(self, pipeline="fresh", as_of="2026-10-09T00:00:00Z"):
        return dict(ruleset_version=self.fixture["ruleset_version"], ruleset_sha256="a" * 64,
                    schema_version=self.fixture["schema_version"], history_mode="latest_vintage_context",
                    calendar_release_id="fixture-calendar", calendar_sha256="b" * 64,
                    observation_bundle_sha256="c" * 64,
                    batch_status_id="fixture-status", batch_status_sha256="d" * 64,
                    pipeline_state=pipeline, pipeline_reason=None if pipeline == "fresh" else "source_check_expired",
                    as_of=as_of, generated_at=as_of, context_transition="context_only",
                    change_reason="pipeline_status_changed",
                    signals=[dict(metric_id="fixture-cpi", observation_id="cpi-v1", actual="0.3"),
                             dict(metric_id="fixture-jobs", observation_id="jobs-v1", actual="25")],
                    warnings=[], triggered_rules=[], changed_observations=[], changed_observation_ids=[])

    def test_t45_fresh_stale_fresh_has_three_immutable_publications(self):
        store = {}
        initial = self.candidate()
        initial.update(context_transition="not_computable", change_reason="initial_assessment")
        a = spec.materialize_fixture(initial, None, store)
        first_bytes = json.dumps(store[a["assessment_id"]], sort_keys=True)
        b = spec.materialize_fixture(self.candidate("stale", "2026-10-11T01:00:00Z"), a, store)
        c = spec.materialize_fixture(self.candidate("fresh", "2026-10-11T02:00:00Z"), b, store)
        self.assertEqual(a["state_id"], c["state_id"])
        self.assertEqual(len({a["assessment_id"], b["assessment_id"], c["assessment_id"]}), 3)
        self.assertEqual(c["previous_assessment_id"], b["assessment_id"])
        self.assertEqual(c["change_reason"], "pipeline_status_changed")
        self.assertEqual(c["context_transition"], "context_only")
        self.assertEqual(json.dumps(store[a["assessment_id"]], sort_keys=True), first_bytes)

    def test_t46_replay_and_current_cache_preserve_first_artifact(self):
        store = {}
        first = self.candidate()
        a = spec.materialize_fixture(first, None, store)
        later = self.candidate(as_of="2026-10-09T12:00:00Z")
        later.update(batch_status_id="new-equivalent-proof", batch_status_sha256="e" * 64)
        self.assertEqual(spec.materialize_fixture(later, a, store), a)
        self.assertEqual(spec.materialize_fixture(later, None, store), a)
        self.assertEqual(len(store), 1)
        self.assertEqual(first, self.candidate())  # Inputs not mutated.

    def test_identity_canonicalization_and_parent_hash_changes(self):
        first = self.candidate()
        reordered = dict(reversed(list(first.items())))
        reordered["signals"] = list(reversed(first["signals"]))
        self.assertEqual(spec.publication_identity(first, None), spec.publication_identity(reordered, None))
        changed = dict(first, calendar_sha256="e" * 64)
        self.assertNotEqual(spec.publication_identity(first, None)[0], spec.publication_identity(changed, None)[0])
        with self.assertRaises(ValueError):
            spec.digest({"actual": 0.1})

    def test_future_or_incompatible_predecessor_rejected(self):
        previous = spec.materialize_fixture(self.candidate(), None, {})
        with self.assertRaises(ValueError):
            spec.publication_identity(self.candidate(as_of="2026-10-08T00:00:00Z"), previous)
        incompatible = dict(self.candidate(), ruleset_version="macro-cross-v2.0.0")
        with self.assertRaises(ValueError):
            spec.publication_identity(incompatible, previous)

    def test_existing_identity_with_different_body_is_not_overwritten(self):
        store = {}
        candidate = self.candidate()
        a = spec.materialize_fixture(candidate, None, store)
        store[a["assessment_id"]]["calendar_sha256"] = "f" * 64
        before = deepcopy(store)
        with self.assertRaises(ValueError):
            spec.materialize_fixture(candidate, None, store)
        self.assertEqual(store, before)

    def test_stored_artifact_after_cutoff_is_rejected(self):
        store = {}
        spec.materialize_fixture(self.candidate(), None, store)
        with self.assertRaises(ValueError):
            spec.materialize_fixture(self.candidate(as_of="2026-10-08T23:59:59Z"), None, store)


if __name__ == "__main__":
    unittest.main()
