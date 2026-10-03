import copy
from datetime import date, timedelta
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from eco import diagnostic_pipeline as pipeline
from eco.diagnostics import IDS, VERSION, PROTOCOL_HASH, compute_diagnostics, describe, validate_history
from eco.core import compute as compute_core
from eco.pipeline import digest, encode, read_json


def fixture(n=65):
    start=date(2015,8,8)
    core=[{"asset":"eth","observation_date":(start+timedelta(days=i)).isoformat(),
           "metrics":{"PriceUSD":10+i,"CapMrktCurUSD":10000+i,"SplyCur":1000+i,"CapMVRVCur":.5+i/50}} for i in range(n)]
    network=[{"asset":"eth","observation_date":r["observation_date"],
              "metrics":{"AdrActCnt":100+i,"AdrBalCnt":1000+i,"CapMrktCurUSD":10000+i,"SplyCur":1000-i,"SplyExNtv":500-i,"TxTfrCnt":10+i},
              "metric_status":{"SplyExNtv":{"status":"flash","status_time":"2026-10-01T00:00:00Z"}}} for i,r in enumerate(core)]
    return core,network


def snapshot(root,kind,source):
    folder=root/('coinmetrics-'+kind);folder.mkdir()
    fields=pipeline.CORE_FIELDS if kind=='core' else pipeline.NETWORK_FIELDS
    stamp='2026-10-03T09:00:00Z'
    raw=[]
    for r in source:
        obj={"asset":"eth","time":r["observation_date"]+'T00:00:00Z',**r['metrics']}
        for field in fields:
            obj[field+'-status']=r.get('metric_status',{}).get(field,{}).get('status')
            obj[field+'-status-time']=r.get('metric_status',{}).get(field,{}).get('status_time')
        raw.append(obj)
    page=encode({'data':raw});(folder/'page-0001.json').write_bytes(page)
    rows=[{**r,'source_timestamp':obj['time'],'period_end_utc':(date.fromisoformat(r['observation_date'])+timedelta(days=1)).isoformat()+'T00:00:00Z',
           'source_available_at':None,'retrieved_at':stamp,'source_page_sha256':digest(page),
           'metric_status':{f:{'status':obj[f+'-status'],'status_time':obj[f+'-status-time']} for f in fields}} for r,obj in zip(source,raw)]
    body=b''.join(encode(r) for r in rows);(folder/'canonical.jsonl').write_bytes(body)
    manifest={'status':'complete','asset':'eth','frequency':'1d','provider':'coinmetrics_community_api','metrics':list(fields),
              'retrieved_at':stamp,'as_of_utc':'2026-10-03','end_date_requested':rows[-1]['observation_date'],
              'pages':[{'raw_file':'page-0001.json','response_sha256':digest(page),'completed_at':stamp,
                        'request_url':'https://community-api.coinmetrics.io/v4/timeseries/asset-metrics?assets=eth&frequency=1d&metrics='+','.join(fields)}],
              'snapshot':{'canonical_file':'canonical.jsonl','canonical_sha256':digest(body),'row_count':len(rows),
                          'first_observation_date':rows[0]['observation_date'],'last_observation_date':rows[-1]['observation_date']}}
    if kind=='proxies':
        catalog=encode({'data':[{'asset':'eth','metrics':[{'metric':f,'frequencies':[{'frequency':'1d','community':True}]} for f in fields]}]})
        (folder/'community-catalog.json').write_bytes(catalog)
        manifest['community_catalog']={'file':'community-catalog.json','sha256':digest(catalog)}
        manifest['source_rights']={'licence':'CC BY-NC 4.0','scope':'noncommercial_research_preview','policy':'ADR-005'}
    (folder/'manifest.json').write_bytes(encode(manifest))
    receipt=root/(kind+'-receipt.json')
    def refresh_receipt():
        receipt.write_bytes(encode({'status':'restored_private_snapshot','bucket':'eco-eth-private','snapshot_sha256':manifest['snapshot']['canonical_sha256'],
          'file_count':len(list(folder.iterdir())),'objects':[{'object_key':'raw/coinmetrics/'+folder.name+'/'+p.name,'bytes':p.stat().st_size,
          'sha256':digest(p.read_bytes()),'readback_verified':True} for p in folder.iterdir()]}))
    refresh_receipt()
    reference={'release_id':('core-' if kind=='core' else 'proxy-')+('1' if kind=='core' else '2')*20,'methodology_version':('core-v0.1.0' if kind=='core' else 'network-proxies-v0.1.0'),
               'manifest_url':'fixture','manifest_sha256':'a'*64,'history_sha256':'b'*64,'last_observation_date':rows[-1]['observation_date']}
    parent_manifest={'snapshot_sha256':manifest['snapshot']['canonical_sha256'],'retrieved_at':stamp,'last_requested_date':rows[-1]['observation_date'],
                     'source_manifest_sha256':digest((folder/'manifest.json').read_bytes())}
    full=compute_core(rows) if kind=='core' else []
    published=[{'date':r['date'],'price_usd':r['price_usd'],'score':r['score'],'components':{m:r['components'][m]['score'] for m in ('E1','E5','E6','E7')}} for r in full] if kind=='core' else [{'date':r['observation_date']} for r in rows]
    return {'snapshot':str(folder),'receipt':str(receipt)},(reference,parent_manifest,published),refresh_receipt


class DiagnosticEngineTest(unittest.TestCase):
    def test_signed_hand_calculations_and_zero(self):
        core,net=fixture();core[0]['metrics']['CapMVRVCur']=.5;core[1]['metrics']['CapMVRVCur']=1;core[2]['metrics']['CapMVRVCur']=2
        rows=compute_diagnostics(core,net)
        self.assertEqual([r['metrics'][IDS[0]]['value'] for r in rows[:3]],[-1,0,.5])
        self.assertAlmostEqual(rows[30]['metrics'][IDS[1]]['value'],-3)
        self.assertEqual(rows[30]['metrics'][IDS[2]]['value'],-30)
        net[30]['metrics']['SplyExNtv']=net[0]['metrics']['SplyExNtv']
        self.assertEqual(compute_diagnostics(core,net)[30]['metrics'][IDS[2]]['value'],0)

    def test_no_future_observations_change_prefix(self):
        core,net=fixture();expected=compute_diagnostics(core[:50],net[:50])
        core[50]['metrics']['CapMVRVCur']=1e10;net[50]['metrics']['SplyCur']=1e10
        self.assertEqual(compute_diagnostics(core,net)[:50],expected)

    def test_complete_calendar_window_interior_gap_and_recovery(self):
        core,net=fixture();net.pop(20);rows=compute_diagnostics(core,net)
        self.assertEqual(rows[20]['metrics'][IDS[2]]['reason'],'parent_day_unavailable')
        self.assertIsNone(rows[49]['metrics'][IDS[1]]['value'])
        self.assertIsNone(rows[50]['metrics'][IDS[2]]['value'])
        self.assertIsNotNone(rows[51]['metrics'][IDS[2]]['value'])

    def test_invalid_mvrv_supply_or_exchange_stays_null(self):
        for value in (None,0,-1,True,float('nan'),float('inf'),'bad'):
            core,net=fixture();core[31]['metrics']['CapMVRVCur']=value;net[10]['metrics']['SplyCur']=value
            rows=compute_diagnostics(core,net)
            self.assertIsNone(rows[31]['metrics'][IDS[0]]['value'])
            self.assertIsNone(rows[31]['metrics'][IDS[1]]['value'])
        core,net=fixture();net[10]['metrics']['SplyExNtv']=-1
        self.assertIsNone(compute_diagnostics(core,net)[31]['metrics'][IDS[2]]['value'])

    def test_warmup_is_30_null_days_flags_cover_interior(self):
        core,net=fixture();net[15]['metric_status']['SplyExNtv']['status']='revised'
        rows=compute_diagnostics(core,net)
        self.assertTrue(all(r['metrics'][IDS[1]]['reason']=='window_warmup' for r in rows[:30]))
        self.assertEqual(rows[30]['metrics'][IDS[2]]['source_flags'],['flash','revised'])
        self.assertEqual(rows[46]['metrics'][IDS[2]]['source_flags'],['flash'])

    def test_eth_only_no_duplicate_dates_no_calendar_truncation(self):
        core,net=fixture()
        with self.assertRaises(ValueError):compute_diagnostics(core+[core[0]],net)
        net[0]['asset']='btc'
        with self.assertRaises(ValueError):compute_diagnostics(core,net)
        core,net=fixture()
        with self.assertRaises(ValueError):compute_diagnostics(core,net,first=core[1]['observation_date'])

    def test_descriptive_coverage_includes_negative_zero_null_regimes(self):
        core,net=fixture();core[1]['metrics']['CapMVRVCur']=1
        report=describe(compute_diagnostics(core,net))
        self.assertEqual(report['coverage'][IDS[1]]['valid_rows'],35)
        self.assertEqual(report['coverage'][IDS[1]]['negative_rows'],35)
        self.assertEqual(report['coverage'][IDS[0]]['zero_rows'],2)
        self.assertEqual(report['regimes']['pre_london']['rows'],65)
        self.assertFalse(report['predictive_utility_claim'])


class DiagnosticPipelineTest(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name)
        core,net=fixture();self.inputs={};self.parents={};self.refresh={}
        for k,rows in (('core',core),('proxies',net)):
            self.inputs[k],self.parents[k],self.refresh[k]=snapshot(self.root,k,rows)
        self.mock=patch.object(pipeline,'_parents',return_value=self.parents);self.mock.start();self.addCleanup(self.mock.stop)
        self.public=self.root/'public';self.output=self.root/'computed'

    def test_core_replay_and_both_exact_pinned_private_inputs(self):
        rows,report,parents,proofs=pipeline.expected(self.public,self.inputs)
        self.assertEqual(len(rows),65);self.assertEqual(set(proofs),{'core','proxies'})
        self.assertTrue(all(v['objects_readback_verified'] for v in proofs.values()))
        altered=copy.deepcopy(self.parents['core']);altered[2][0]['price_usd']=999
        with self.assertRaisesRegex(ValueError,'replay'):pipeline.verified_input(**{'folder':self.inputs['core']['snapshot'],'receipt_path':self.inputs['core']['receipt'],'reference':altered,'kind':'core'})

    def test_mismatched_parent_snapshot_rejected(self):
        wrong=copy.deepcopy(self.parents['core']);wrong[1]['snapshot_sha256']='0'*64
        with self.assertRaisesRegex(ValueError,'pinned parent'):pipeline.verified_input(self.inputs['core']['snapshot'],self.inputs['core']['receipt'],wrong,'core')

    def test_every_private_object_readback_is_required(self):
        path=Path(self.inputs['proxies']['receipt']);r=read_json(path);r['objects'][0]['readback_verified']=False;path.write_bytes(encode(r))
        with self.assertRaisesRegex(ValueError,'readback'):pipeline.expected(self.public,self.inputs)
        r['objects'].pop();path.write_bytes(encode(r))
        with self.assertRaisesRegex(ValueError,'receipt'):pipeline.expected(self.public,self.inputs)

    def test_rehashed_canonical_cannot_forge_raw_or_flags(self):
        folder=Path(self.inputs['core']['snapshot']);rows=[__import__('json').loads(line) for line in (folder/'canonical.jsonl').read_text().splitlines()]
        rows[0]['metrics']['CapMVRVCur']=99;body=b''.join(encode(r) for r in rows);(folder/'canonical.jsonl').write_bytes(body)
        m=read_json(folder/'manifest.json');m['snapshot']['canonical_sha256']=digest(body);(folder/'manifest.json').write_bytes(encode(m))
        self.parents['core'][1]['snapshot_sha256']=digest(body);self.refresh['core']()
        with self.assertRaisesRegex(ValueError,'raw provenance'):pipeline.expected(self.public,self.inputs)

    def test_publish_is_idempotent_raw_private_inputs_never_public(self):
        folder=pipeline.build(self.public,self.output,self.inputs)
        self.assertEqual(folder,pipeline.build(self.public,self.output,self.inputs))
        self.assertEqual(pipeline.publish(folder,self.public),'published')
        pointer=(self.public/'data/diagnostics/latest.json').read_bytes()
        ledger=list((self.public/'data/diagnostics/publications').iterdir())[0];original=ledger.read_bytes()
        self.assertEqual(pipeline.publish(folder,self.public),'unchanged')
        self.assertEqual((self.public/'data/diagnostics/latest.json').read_bytes(),pointer);self.assertEqual(ledger.read_bytes(),original)
        published=self.public/'data/diagnostics/releases'/folder.name
        self.assertEqual({p.name for p in published.iterdir()},{'history.json','research.json','manifest.json'})
        self.assertNotIn(str(self.root),(published/'manifest.json').read_text())

    def test_tampered_derived_history_rejected_even_after_rehash(self):
        folder=pipeline.build(self.public,self.output,self.inputs);h=read_json(folder/'history.json');h['rows'][0]['metrics'][IDS[0]]['value']=0
        report=describe(h['rows']);m=read_json(folder/'manifest.json');m['coverage']=report['coverage']
        for name,obj in (('history.json',h),('research.json',report)):
            body=encode(obj);(folder/name).write_bytes(body);m['files'][name]=digest(body)
        (folder/'manifest.json').write_bytes(encode(m))
        with self.assertRaisesRegex(ValueError,'verified private parents'):pipeline.publish(folder,self.public)
        self.assertFalse((self.public/'data/diagnostics/latest.json').exists())

    def test_score_promotion_and_forecast_claim_rejected(self):
        folder=pipeline.build(self.public,self.output,self.inputs);h=read_json(folder/'history.json');m=read_json(folder/'manifest.json');r=read_json(folder/'research.json')
        m['composite_score']=50
        with self.assertRaises(ValueError):validate_history(h,m,r)
        m['composite_score']=None;r['predictive_utility_claim']=True
        with self.assertRaises(ValueError):validate_history(h,m,r)

    def test_revision_preserves_previous_history_and_first_publication(self):
        folder=pipeline.build(self.public,self.output,self.inputs);pipeline.publish(folder,self.public)
        old=self.public/'data/diagnostics/releases'/folder.name/'history.json';original=old.read_bytes()
        ledger=list((self.public/'data/diagnostics/publications').iterdir())[0];first=ledger.read_bytes()
        self.parents['core'][0]['manifest_sha256']='c'*64
        next_folder=pipeline.build(self.public,self.output,self.inputs)
        self.assertNotEqual(folder,next_folder);self.assertEqual(pipeline.publish(next_folder,self.public),'revised')
        self.assertEqual(old.read_bytes(),original);self.assertEqual(ledger.read_bytes(),first)
        revision=read_json(self.public/'data/diagnostics/revisions'/(next_folder.name+'.json'))
        self.assertEqual(revision['changed_dates'],[]);self.assertEqual(revision['reason'],'parent_lineage_or_observations_updated')

    def test_restore_failure_preserves_pointer_records_stage_without_secret(self):
        folder=pipeline.build(self.public,self.output,self.inputs);pipeline.publish(folder,self.public)
        path=self.public/'data/diagnostics/latest.json';original=path.read_bytes()
        with patch.object(pipeline.subprocess,'run',side_effect=RuntimeError('fixture SECRET')):
            self.assertEqual(pipeline.daily(self.public,self.output),1)
        self.assertEqual(path.read_bytes(),original)
        status=read_json(self.public/'data/diagnostics/status.json');self.assertEqual(status['failure_stage'],'verified_parent_restore')
        self.assertEqual(status['outcome'],'failed');self.assertNotIn('SECRET',encode(status).decode())


if __name__=='__main__':unittest.main()
