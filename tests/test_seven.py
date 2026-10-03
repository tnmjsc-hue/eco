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
        last = rows[-1]
        expected = .75*last["core_score"]+.25*sum(last["components"][m] for m in IDS[4:])/3
        self.assertAlmostEqual(expected,last["score"],places=12)
        self.assertEqual(last["coverage"],7)
        self.assertEqual(last["components"]["exchange_share"],0)
        self.assertIn("flash",last["source_flags"]["exchange_share"])
        self.assertEqual([r["core_score"] for r in rows],[r["score"] for r in self.core])

    def test_source_lag_never_forward_fills(self):
        row = join(self.core,self.proxy[:-1])[-1]
        self.assertEqual(row["coverage"],4)
        self.assertIsNone(row["score"])
        self.assertEqual(row["core_score"],self.core[-1]["score"])
        self.assertTrue(all(row["reasons"][m]=="parent_date_unavailable" for m in IDS[4:]))

    def test_causal_join_prefix_ignores_future_shock(self):
        prefix = join(self.core[:-1],self.proxy[:-1])
        future = copy.deepcopy(self.proxy)
        future[-1]["metrics"]["exchange_share"]["score"] = 100
        self.assertEqual(prefix,join(self.core,future)[:-1])

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
        invalid[-1]["metrics"]["address_activity"]["score"] = True
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
