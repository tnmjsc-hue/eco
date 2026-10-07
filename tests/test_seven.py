import copy
import json
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch
from eco.pipeline import ROOT, read_json, digest, encode
from eco.seven import IDS, CORE_IDS, WEIGHTS, VERSION, aggregate, join, parent, protocol, update, daily

PUBLIC = ROOT/"public"

def current(root, prefix=""):
    p = read_json(root/"data"/prefix/"latest.json")
    return root/"data"/prefix/"releases"/p["release_id"]

class ExtendedTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.core = read_json(current(PUBLIC)/"history.json")["rows"]
        cls.proxy = read_json(current(PUBLIC,"network-proxies")/"history.json")["rows"]

    def test_protocol_and_original_parent_weights_unchanged(self):
        self.assertEqual(protocol()["methodology_version"],VERSION)
        self.assertAlmostEqual(sum(WEIGHTS.values()),1)
        self.assertEqual([WEIGHTS[m] for m in CORE_IDS],[.125,.125,.125,.375])

    def test_same_day_real_join_matches_formula_and_keeps_core(self):
        rows = join(self.core,self.proxy)
        last = next(r for r in reversed(rows) if r["score"] is not None)
        expected = .75*last["core_score"]+.25*sum(last["components"][m] for m in IDS[4:])/3
        self.assertAlmostEqual(expected,last["score"],places=12)
        self.assertEqual(last["coverage"],7)
        proxy = next(r for r in self.proxy if r["date"] == last["date"])
        self.assertEqual(last["components"]["exchange_share"],proxy["metrics"]["exchange_share"]["score"])
        self.assertEqual(last["source_flags"]["exchange_share"],proxy["metrics"]["exchange_share"]["source_flags"])
        self.assertEqual([r["core_score"] for r in rows],[r["score"] for r in self.core])

    def test_source_lag_never_forward_fills(self):
        # Remove the Core tail date itself, even when proxies run further ahead.
        row = join(self.core,[r for r in self.proxy if r["date"] < self.core[-1]["date"]])[-1]
        self.assertEqual(row["coverage"],sum(v is not None for v in self.core[-1]["components"].values()))
        self.assertIsNone(row["score"])
        self.assertEqual(row["core_score"],self.core[-1]["score"])
        self.assertTrue(all(row["reasons"][m]=="parent_date_unavailable" for m in IDS[4:]))

    def test_causal_join_prefix_ignores_future_shock(self):
        common = min(self.core[-1]["date"],self.proxy[-1]["date"])
        cutoff = next(r["date"] for r in reversed(self.core) if r["date"] < common)
        prefix = join([r for r in self.core if r["date"] <= cutoff],
                      [r for r in self.proxy if r["date"] <= cutoff])
        for metric in IDS[4:]:
            for raw_reason,score_reason in ((None,None),
                                           ("missing_input_or_window","raw_unavailable"),
                                           (None,"normalizer_warmup")):
                with self.subTest(metric=metric,raw_reason=raw_reason,score_reason=score_reason):
                    future = copy.deepcopy(self.proxy)
                    item = next(r for r in future if r["date"] == common)["metrics"][metric]
                    initial_score = None if raw_reason or score_reason else 50
                    item.update(score=initial_score,raw_reason=raw_reason,score_reason=score_reason)
                    rows = join(self.core,future)
                    current = next(r for r in rows if r["date"] == common)
                    self.assertEqual(current["components"][metric],initial_score)
                    self.assertEqual(current["reasons"][metric],raw_reason or score_reason)
                    self.assertEqual(prefix,[r for r in rows if r["date"] <= cutoff])
                    # A synthetic normalized score must have no missing-data reason.
                    item.update(score=100,raw_reason=None,score_reason=None)
                    rows = join(self.core,future)
                    self.assertEqual(next(r for r in rows if r["date"] == common)["components"][metric],100)
                    self.assertEqual(prefix,[r for r in rows if r["date"] <= cutoff])

    def test_non_null_proxy_score_with_missing_reason_rejected(self):
        common = min(self.core[-1]["date"],self.proxy[-1]["date"])
        for metric in IDS[4:]:
            for reason_field in ("raw_reason","score_reason"):
                with self.subTest(metric=metric,reason_field=reason_field):
                    invalid = copy.deepcopy(self.proxy)
                    item = next(r for r in invalid if r["date"] == common)["metrics"][metric]
                    item.update(score=100,raw_reason=None,score_reason=None)
                    item[reason_field] = "missing_input_or_window" if reason_field == "raw_reason" else "normalizer_warmup"
                    with self.assertRaisesRegex(ValueError,"invalid parent component/reason/flags"):
                        join(self.core,invalid)

    def test_join_handles_both_parent_calendar_directions(self):
        complete = next(r for r in reversed(join(self.core,self.proxy)) if r["score"] is not None)
        core = [r for r in self.core if r["date"] <= complete["date"]]
        proxies = [r for r in self.proxy if r["date"] <= complete["date"]]
        with self.subTest(ahead="core"):
            rows = join(core,proxies[:-1])
            self.assertEqual(rows[-1]["coverage"],4)
            self.assertIsNone(rows[-1]["score"])
            self.assertEqual(rows[-1]["core_score"],core[-1]["score"])
            self.assertTrue(all(rows[-1]["components"][m] is None for m in IDS[4:]))
            self.assertEqual(rows[:-1],join(core[:-1],proxies[:-1]))
        with self.subTest(ahead="proxies"):
            self.assertEqual(join(core[:-1],proxies),join(core[:-1],proxies[:-1]))

    def test_custom_empty_duplicates_missing_and_real_zero(self):
        r = dict.fromkeys(IDS,0)
        self.assertEqual(aggregate(r),0)
        for selected in ([],["E2"],["E7","E7"]): self.assertIsNone(aggregate(r,selected))
        r["address_activity"] = None
        self.assertIsNone(aggregate(r))
        r["E7"] = 100
        self.assertEqual(aggregate(r,["E7"]),100)
        self.assertEqual(aggregate(r,CORE_IDS),50)

    def test_bad_calendar_and_components_rejected(self):
        for rows in (self.proxy[1:10]+self.proxy[1:2],self.proxy[:3]+self.proxy[4:10]):
            with self.assertRaises(ValueError): join(self.core,rows)
        invalid = copy.deepcopy(self.proxy)
        common = min(self.core[-1]["date"],self.proxy[-1]["date"])
        next(r for r in invalid if r["date"] == common)["metrics"]["address_activity"]["score"] = True
        with self.assertRaises(ValueError): join(self.core,invalid)

    def copy_parents(self, public):
        for prefix in ("","network-proxies"):
            root = public/"data"/prefix; root.mkdir(parents=True,exist_ok=True)
            shutil.copyfile(PUBLIC/"data"/prefix/"latest.json",root/"latest.json")
            folder = current(PUBLIC,prefix)
            shutil.copytree(folder,root/"releases"/folder.name)

    def test_parent_hash_asset_and_licence_gate(self):
        with tempfile.TemporaryDirectory() as tmp:
            public = Path(tmp)/"public"; self.copy_parents(public)
            file = current(public,"network-proxies")/"history.json"
            file.write_bytes(file.read_bytes()+b" ")
            with self.assertRaisesRegex(ValueError,"checksum"):
                parent(public,"network-proxies","network-proxies-v0.1.0",r"proxy-[a-f0-9]{20}")
            self.assertFalse((public/"data/extended/latest.json").exists())
        for mutation in ("asset","licence"):
            with self.subTest(mutation=mutation),tempfile.TemporaryDirectory() as tmp:
                public = Path(tmp)/"public"; self.copy_parents(public)
                folder = current(public,"network-proxies")
                manifest = read_json(folder/"manifest.json")
                if mutation == "asset":
                    history = read_json(folder/"history.json"); history["asset"] = "btc"
                    (folder/"history.json").write_bytes(encode(history))
                    manifest["files"]["history.json"] = digest((folder/"history.json").read_bytes())
                else: manifest["attribution"]["licence"] = "unknown"
                (folder/"manifest.json").write_bytes(encode(manifest))
                pointer_path = public/"data/network-proxies/latest.json"
                pointer = read_json(pointer_path); pointer["manifest_sha256"] = digest((folder/"manifest.json").read_bytes())
                pointer_path.write_bytes(encode(pointer))
                with self.assertRaises(ValueError):
                    parent(public,"network-proxies","network-proxies-v0.1.0",r"proxy-[a-f0-9]{20}")

    def test_publication_idempotency_failure_preserves_exact_bytes(self):
        with tempfile.TemporaryDirectory() as tmp:
            public = Path(tmp)/"public"; output = Path(tmp)/"computed"; self.copy_parents(public)
            outcome,release_id = update(public,output)
            self.assertEqual(outcome,"published")
            pointer = public/"data/extended/latest.json"; original = pointer.read_bytes()
            before = {p.name:digest(p.read_bytes()) for p in current(public,"extended").iterdir()}
            self.assertEqual(update(public,output),("unchanged",release_id))
            self.assertEqual(pointer.read_bytes(),original)
            with patch("eco.seven.parent",side_effect=ValueError("secret upstream URL")):
                with self.assertRaisesRegex(RuntimeError,"previous release preserved"): daily(public,output)
            status = read_json(public/"data/extended/status.json")
            self.assertEqual(status["outcome"],"failed")
            self.assertNotIn("secret",json.dumps(status))
            self.assertEqual(pointer.read_bytes(),original)
            self.assertEqual(before,{p.name:digest(p.read_bytes()) for p in current(public,"extended").iterdir()})

    def test_reduced_bootstrap_cannot_publish(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(ValueError,"10000"):
                update(Path(tmp)/"public",Path(tmp)/"computed",replicates=10)

if __name__ == "__main__": unittest.main()
