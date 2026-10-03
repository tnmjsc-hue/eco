import copy
from datetime import date, timedelta
import math
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from eco.pipeline import encode, digest, read_json
from eco.proxies import INPUTS, METRICS, compute_proxies, evaluate_proxies
from eco import proxy_pipeline as pipeline

def fixture(n=700):
    first=date(2015,7,30)
    return [{"asset":"eth","observation_date":(first+timedelta(days=i)).isoformat(),
             "metrics":{"AdrActCnt":100+i,"AdrBalCnt":1000+i,"CapMrktCurUSD":10000+30*i,
                        "SplyCur":10000+i,"SplyExNtv":1000+2*i,"TxTfrCnt":10+i},
             "metric_status":{"SplyExNtv":{"status":"flash","status_time":"2026-10-01T00:00:00Z"}}} for i in range(n)]

def baseline(source):
    result=[]
    for i,row in enumerate(source):
        values={k:50+20*math.sin(i/(23+q)) for q,k in enumerate(("E1","E5","E6","E7"))}
        result.append({"date":row["observation_date"],"price_usd":100+65*math.sin(i/30),
                       "score":sum(values[k]/6 for k in ("E1","E5","E6"))+values["E7"]/2,"components":values})
    return result

def write_snapshot(folder, source):
    folder.mkdir()
    completed="2026-10-03T09:00:00Z"
    raw=[]
    for row in source:
        obj={"asset":"eth","time":row["observation_date"]+"T00:00:00Z",**row["metrics"]}
        for m,v in row.get("metric_status",{}).items():
            obj[m+"-status"]=v["status"];obj[m+"-status-time"]=v["status_time"]
        raw.append(obj)
    page=encode({"data":raw});(folder/"page-0001.json").write_bytes(page)
    canonical=[]
    for row,obj in zip(source,raw):
        end=(date.fromisoformat(row["observation_date"])+timedelta(days=1)).isoformat()+"T00:00:00Z"
        canonical.append({**row,"source_timestamp":obj["time"],"period_end_utc":end,"source_available_at":None,
                          "retrieved_at":completed,"source_page_sha256":digest(page),
                          "metric_status":{m:{"status":obj.get(m+"-status"),"status_time":obj.get(m+"-status-time")} for m in INPUTS}})
    body=b"".join(encode(row) for row in canonical);(folder/"canonical.jsonl").write_bytes(body)
    catalog=encode({"data":[{"asset":"eth","metrics":[{"metric":m,"frequencies":[{"frequency":"1d","community":True}]} for m in INPUTS]}]})
    (folder/"community-catalog.json").write_bytes(catalog)
    manifest={"status":"complete","asset":"eth","frequency":"1d","provider":"coinmetrics_community_api","metrics":list(INPUTS),
              "start_date_requested":source[0]["observation_date"],"end_date_requested":source[-1]["observation_date"],
              "retrieved_at":completed,"as_of_utc":"2026-10-03",
              "pages":[{"raw_file":"page-0001.json","response_sha256":digest(page),"completed_at":completed,
                        "request_url":"https://community-api.coinmetrics.io/v4/timeseries/asset-metrics?assets=eth&frequency=1d&metrics="+','.join(INPUTS)}],
              "snapshot":{"canonical_file":"canonical.jsonl","canonical_sha256":digest(body),"row_count":len(source),
                          "first_observation_date":source[0]["observation_date"],"last_observation_date":source[-1]["observation_date"]},
              "source_rights":{"licence":"CC BY-NC 4.0","scope":"noncommercial_research_preview","policy":"ADR-005"},
              "quality":{"missing_row_date_count":0},"community_catalog":{"file":"community-catalog.json","sha256":digest(catalog)}}
    (folder/"manifest.json").write_bytes(encode(manifest))
    receipt={"status":"uploaded_private_snapshot","bucket":"eco-eth-private","snapshot_sha256":digest(body),"file_count":4,
             "objects":[{"object_key":f"raw/coinmetrics/{folder.name}/{p.name}","sha256":digest(p.read_bytes()),
                          "bytes":p.stat().st_size,"readback_verified":True} for p in folder.iterdir()]}
    path=folder.parent/"receipt.json";path.write_bytes(encode(receipt))
    return path

class ProxyEngineTest(unittest.TestCase):
    def test_three_hand_calculated_formulas_and_warmup(self):
        source=fixture();result=compute_proxies(source)
        self.assertIsNone(result[28]["metrics"]["exchange_share"]["raw"])
        expected=sum((1000+2*i)/(10000+i) for i in range(30))/30
        self.assertAlmostEqual(result[29]["metrics"]["exchange_share"]["raw"],math.log(expected))
        self.assertAlmostEqual(result[29]["metrics"]["address_activity"]["value"],114.5/1029)
        self.assertAlmostEqual(result[89]["metrics"]["value_per_transfer"]["value"],12670/54.5)
        for m,first in (("exchange_share",394),("address_activity",394),("value_per_transfer",454)):
            self.assertIsNone(result[first-1]["metrics"][m]["score"])
            self.assertIsNotNone(result[first]["metrics"][m]["score"])
        self.assertEqual(result[600]["metrics"]["exchange_share"]["source_flags"],["flash"])

    def test_missing_calendar_days_break_windows_and_do_not_become_zero(self):
        for remove in (True,False):
            source=fixture()
            if remove: source.pop(500)
            else: source[500]["metrics"]["SplyExNtv"]=None;source[500]["metrics"]["AdrActCnt"]=None;source[500]["metrics"]["TxTfrCnt"]=None
            result=compute_proxies(source)
            for m,width in (("exchange_share",30),("address_activity",30),("value_per_transfer",90)):
                self.assertTrue(all(r["metrics"][m]["raw"] is None for r in result[500:500+width]))
                self.assertIsNotNone(result[500+width]["metrics"][m]["raw"])
            self.assertEqual(result[500]["source_row_present"],not remove)

    def test_future_cannot_change_prior_scores_and_today_does_not_set_bounds(self):
        source=fixture();prefix=compute_proxies(source[:510]);full=compute_proxies(source)
        self.assertEqual(prefix,full[:510])
        changed=copy.deepcopy(source);changed[509]["metrics"]["CapMrktCurUSD"]=1e200
        alternative=compute_proxies(changed)
        self.assertEqual(full[:509],alternative[:509])
        self.assertEqual(alternative[509]["metrics"]["value_per_transfer"]["score"],100)

    def test_zero_inputs_and_flat_history_preserve_nulls(self):
        source=fixture()
        for r in source:
            r["metrics"].update(AdrActCnt=0,SplyExNtv=0,TxTfrCnt=0)
        result=compute_proxies(source)
        self.assertTrue(all(r["metrics"][m]["score"] is None for r in result for m in METRICS))
        self.assertEqual(result[600]["metrics"]["value_per_transfer"]["raw_reason"],"nonpositive_log_argument")
        source=fixture()
        for r in source:r["metrics"]=copy.deepcopy(source[0]["metrics"])
        self.assertEqual(compute_proxies(source)[600]["metrics"]["exchange_share"]["score_reason"],"degenerate_normalizer")

    def test_reject_substitutions_duplicates_wrong_asset_and_invalid_units(self):
        for mutation in (lambda r:r[0].update(asset="btc"),lambda r:r.append(copy.deepcopy(r[0])),
                         lambda r:r[0]["metrics"].update(TxTfrValAdjUSD=1),lambda r:r[0]["metrics"].update(TxTfrCnt=1.5),
                         lambda r:r[0]["metrics"].update(SplyCur=0),lambda r:r[0]["metrics"].update(SplyExNtv=10001),
                         lambda r:r[0]["metrics"].update(AdrActCnt=float('nan'))):
            source=fixture();mutation(source)
            with self.assertRaises(ValueError):compute_proxies(source)
        with self.assertRaises(ValueError):compute_proxies(fixture()[1:])

    def test_current_denominator_missing_and_flag_window_expiry(self):
        source=fixture();source[500]["metrics"]["AdrBalCnt"]=None
        source[500]["metrics"]["CapMrktCurUSD"]=None
        result=compute_proxies(source)
        for m in ("address_activity","value_per_transfer"):
            self.assertIsNone(result[500]["metrics"][m]["raw"])
            self.assertIsNotNone(result[501]["metrics"][m]["raw"])
        for r in source:r["metric_status"]={}
        source[500]["metric_status"]={"SplyExNtv":{"status":"flash"}}
        result=compute_proxies(source)
        self.assertEqual(result[529]["metrics"]["exchange_share"]["source_flags"],["flash"])
        self.assertEqual(result[530]["metrics"]["exchange_share"]["source_flags"],[])

    def test_paired_evaluation_models_coverage_regimes_and_replay(self):
        source=fixture(2400);rows=compute_proxies(source);core=baseline(source)
        a=evaluate_proxies(core,rows,replicates=20);b=evaluate_proxies(core,rows,replicates=20)
        self.assertEqual(a,b);self.assertEqual(a["bootstrap"]["replicates"],20)
        self.assertEqual(len(a["statistics"]),9);self.assertEqual(len(a["comparisons"]),12)
        self.assertEqual(set(a["coverage"]),set(METRICS))
        self.assertEqual(sum(r["n"] for r in a["regime_analysis"].values()),a["n"])
        for c in a["comparisons"].values():self.assertEqual(c["valid_replicates"],20)
        with self.assertRaises(ValueError):evaluate_proxies(core,rows[:100])
        with self.assertRaises(ValueError):evaluate_proxies(core[:-2]+core[-1:],rows)

class ProxyPipelineTest(unittest.TestCase):
    def test_public_revisions_unchanged_vintage_and_runtime_rounding_keep_published_values(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);public=root/"public"
            def candidate(identifier,score=41.,engine="a",extra=False):
                folder=root/identifier;folder.mkdir()
                rows=compute_proxies(fixture(600));rows[-1]["metrics"]["exchange_share"]["score"]=score
                if extra:
                    row=copy.deepcopy(rows[-1]);row["date"]=(date.fromisoformat(row["date"])+timedelta(days=1)).isoformat();rows.append(row)
                history={"release_id":identifier,"methodology_version":pipeline.VERSION,"asset":"eth","composite_score":None,"rows":rows}
                research={"protocol":pipeline.PROTOCOL,"bootstrap":{"replicates":10000},"decision":"publish_research_metrics_only_no_core_promotion"}
                for name,content in (("history.json",history),("research.json",research)):(folder/name).write_bytes(encode(content))
                manifest={"release_id":identifier,"methodology_version":pipeline.VERSION,"protocol":pipeline.PROTOCOL,
                    "asset":"eth","series_type":"reconstructed","protocol_sha256":pipeline.PROTOCOL_HASH,
                    "source_evidence_sha256":pipeline.SOURCE_EVIDENCE_HASH,"bootstrap_replicates":10000,"core_promotion":False,
                    "attribution":pipeline.ATTRIBUTION,"research_only":True,"private_backup":{"all_objects_readback_verified":True},
                    "engine_sha256":engine,"core_history_sha256":"baseline",
                    "files":{name:digest((folder/name).read_bytes()) for name in ("history.json","research.json")}}
                (folder/"manifest.json").write_bytes(encode(manifest));return folder
            first=candidate("proxy-"+"1"*20);self.assertEqual(pipeline.publish(first,public),"published")
            pointer=public/"data/network-proxies/latest.json";original=pointer.read_bytes()
            original_history=(public/"data/network-proxies/releases"/first.name/"history.json").read_bytes()
            same=candidate("proxy-"+"2"*20,score=41.+1e-10)
            self.assertEqual(pipeline.publish(same,public),"unchanged");self.assertEqual(pointer.read_bytes(),original)
            added=candidate("proxy-"+"3"*20,score=41.+1e-10,extra=True)
            self.assertEqual(pipeline.publish(added,public),"published")
            current=read_json(public/"data/network-proxies/releases"/added.name/"history.json")
            self.assertEqual(current["rows"][-2]["metrics"]["exchange_share"]["score"],41.)
            revised=candidate("proxy-"+"4"*20,score=55.,extra=True)
            self.assertEqual(pipeline.publish(revised,public),"revised")
            self.assertEqual((public/"data/network-proxies/releases"/first.name/"history.json").read_bytes(),original_history)
            regression=candidate("proxy-"+"5"*20,score=None,extra=True)
            with self.assertRaisesRegex(ValueError,"lost previously"):pipeline.publish(regression,public)

    def test_schedule_has_public_allowlist_and_existing_bucket_credentials_only(self):
        text=(pipeline.ROOT/".github/workflows/network-proxies-update.yml").read_text()
        self.assertIn("cron: '47 3,7 * * *'",text)
        self.assertIn("group: daily-eth-publication",text)
        self.assertIn("R2_BUCKET: eco-eth-private",text)
        self.assertIn("git add -- public/data/network-proxies/latest.json public/data/network-proxies/releases",text)
        self.assertNotIn("git add .",text)

    def test_raw_status_provenance_and_all_backup_objects_are_required(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);folder=root/"snapshot";receipt=write_snapshot(folder,fixture())
            rows,manifest=pipeline.verified_snapshot(folder,receipt)
            self.assertEqual(len(rows),700)
            r=read_json(receipt);r["objects"][0]["readback_verified"]=False;receipt.write_bytes(encode(r))
            with self.assertRaisesRegex(ValueError,"readback"):pipeline.verified_snapshot(folder,receipt)
            r["objects"][0]["readback_verified"]=True;r["objects"].pop();receipt.write_bytes(encode(r))
            with self.assertRaisesRegex(ValueError,"every snapshot"):pipeline.verified_snapshot(folder,receipt)

    def test_canonical_cannot_forge_raw_even_if_manifest_and_receipt_rehashed(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);folder=root/"snapshot";receipt=write_snapshot(folder,fixture())
            rows=[json_line for json_line in (folder/"canonical.jsonl").read_text().splitlines()]
            import json
            row=json.loads(rows[50]);row["metrics"]["TxTfrCnt"]=999999;rows[50]=encode(row).decode().strip()
            data=('\n'.join(rows)+'\n').encode();(folder/"canonical.jsonl").write_bytes(data)
            manifest=read_json(folder/"manifest.json");manifest["snapshot"]["canonical_sha256"]=digest(data)
            (folder/"manifest.json").write_bytes(encode(manifest))
            r=read_json(receipt);r["snapshot_sha256"]=digest(data)
            for item in r["objects"]:
                p=folder/item["object_key"].split('/')[-1];item.update(sha256=digest(p.read_bytes()),bytes=p.stat().st_size)
            receipt.write_bytes(encode(r))
            with self.assertRaisesRegex(ValueError,"raw provenance"):pipeline.verified_snapshot(folder,receipt)

    def test_build_replay_private_fixture_and_real_public_gate(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);source=fixture(2400);snapshot=root/"snapshot";receipt=write_snapshot(snapshot,source)
            core=root/"core";core.mkdir();data=encode({"rows":baseline(source)})
            (core/"history.json").write_bytes(data)
            (core/"manifest.json").write_bytes(encode({"release_id":"core-fixture","methodology_version":"core-v0.1.0",
                "series_type":"reconstructed","files":{"history.json":digest(data)}}))
            folder=pipeline.build(snapshot,receipt,core,root/"computed",replicates=20)
            self.assertEqual(folder,pipeline.build(snapshot,receipt,core,root/"computed",replicates=20))
            with self.assertRaisesRegex(ValueError,"publication gate"):pipeline.publish(folder,root/"public")
            (folder/"history.json").write_bytes(b'{}')
            with self.assertRaisesRegex(ValueError,"checksum"):pipeline.build(snapshot,receipt,core,root/"computed",replicates=20)

    def test_failure_preserves_public_pointer_and_records_failed_stage(self):
        with tempfile.TemporaryDirectory() as temp:
            public=Path(temp);folder=public/"data/network-proxies";folder.mkdir(parents=True)
            pointer=encode({"release_id":"proxy-fixture"});(folder/"latest.json").write_bytes(pointer)
            with patch.object(pipeline.subprocess,"run",side_effect=RuntimeError("fixture failure")):
                with self.assertRaisesRegex(RuntimeError,"previous release preserved"):pipeline.daily(public)
            self.assertEqual((folder/"latest.json").read_bytes(),pointer)
            status=read_json(folder/"status.json");self.assertEqual(status["outcome"],"failed");self.assertEqual(status["failure_stage"],"fetch")

if __name__=="__main__":unittest.main()
