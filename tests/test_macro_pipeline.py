"""Pinned adapter metadata and failure/replay publication checks (T34–T36/T46)."""
from copy import deepcopy
from pathlib import Path
import json
import tempfile
import unittest
from unittest.mock import patch

from eco import calendar as cal
from eco import macro_adapter as adapter
from eco import macro_assessment as m
from eco import macro_pipeline as p
from test_macro_assessment import fixture,status,RULES,NOW,CPI,NFP,CORE,HEAD


class MacroPublicationTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name)
        self.bundle,self.calendar=fixture({CPI:('0.4','0.1'),NFP:('150','100')})
        self.folder=self.root/'public/data/macro-assessment'

    def publish(self,proof=None,cutoff=NOW):return p.publish(self.root,self.bundle,self.calendar,proof or status(),cutoff,RULES)

    def test_T35_cache_hit_keeps_every_immutable_byte_and_ledger(self):
        self.publish();original={str(f.relative_to(self.folder)):f.read_bytes() for f in self.folder.rglob('*.json') if f.name!='status.json' and f.parent.name!='inputs'}
        self.assertEqual(self.publish(status('2026-10-08T16:00:00Z','2026-10-08T16:00:00Z'),'2026-10-08T16:00:00Z')['outcome'],'unchanged')
        current={str(f.relative_to(self.folder)):f.read_bytes() for f in self.folder.rglob('*.json') if f.name!='status.json' and f.parent.name!='inputs'}
        self.assertEqual(original,current)

    def test_T34_bad_hash_retains_pointer_and_no_record(self):
        self.publish();pointer=(self.folder/'latest.json').read_bytes();count=len(list((self.folder/'records').glob('*')))
        self.bundle['calendar_sha256']='0'*64
        with self.assertRaises(ValueError):self.publish()
        self.assertEqual((self.folder/'latest.json').read_bytes(),pointer);self.assertEqual(len(list((self.folder/'records').glob('*'))),count)

    def test_T36_T45_pipeline_state_changes_add_immutable_records(self):
        first=self.publish();later='2026-10-11T16:00:00Z'
        stale=self.publish(status(NOW,later),later);restored=self.publish(status(later,later),later)
        self.assertNotEqual(first['assessment_id'],restored['assessment_id']);self.assertNotEqual(stale['assessment_id'],restored['assessment_id'])
        self.assertEqual(len(list((self.folder/'records').glob('*'))),3)
        pointer=p.read_json(self.folder/'latest.json');assessment=p.read_asset(self.root,pointer);manifest=p.read_asset(self.root,pointer['manifest'])
        self.assertEqual(manifest['previous_assessment_id'],stale['assessment_id']);self.assertEqual(assessment['change_reason'],'pipeline_status_changed')

    def test_T46_interrupted_pointer_commit_replays_original_bytes_and_proof(self):
        self.publish();first_pointer=(self.folder/'latest.json').read_bytes();later='2026-10-11T16:00:00Z'
        stale=self.publish(status(NOW,later),later)
        artifact=self.folder/'releases'/stale['assessment_id']/'assessment.json';original=artifact.read_bytes()
        (self.folder/'latest.json').write_bytes(first_pointer)
        result=self.publish(status(NOW,'2026-10-11T17:00:00Z'),'2026-10-11T17:00:00Z')
        self.assertEqual(result['assessment_id'],stale['assessment_id']);self.assertEqual(original,artifact.read_bytes());self.assertEqual(len(list((self.folder/'records').glob('*'))),2)

    def test_lock_and_path_checksum_guards(self):
        self.publish();pointer=p.read_json(self.folder/'latest.json')
        with p.publication_lock(self.folder):
            with self.assertRaisesRegex(ValueError,'busy'):self.publish()
        with self.assertRaises(ValueError):p.read_asset(self.root,{'url':'/data/../../secret','sha256':'0'*64})
        pointer['sha256']='0'*64
        with self.assertRaisesRegex(ValueError,'checksum'):p.read_asset(self.root,pointer)

    def test_run_truncated_parent_retains_last_good_and_writes_error(self):
        self.publish();before=(self.folder/'latest.json').read_bytes()
        path=self.root/'public/data/calendar/latest.json';path.parent.mkdir(parents=True);path.write_bytes(b'{')
        with self.assertRaises(ValueError):p.run(self.root,m.utc(NOW))
        self.assertEqual((self.folder/'latest.json').read_bytes(),before);self.assertEqual(p.read_json(self.folder/'status.json')['outcome'],'error')

    def test_failed_source_uses_latest_verified_refresh_proof_not_old_artifact_proof(self):
        self.calendar['private_backup']['snapshot_id']='fixture'
        self.bundle['calendar_sha256']=cal.digest(cal.encode(self.calendar))
        self.publish();fresh='2026-10-08T16:00:00Z';self.publish(status(fresh,fresh),fresh)
        calendar_path=self.root/f'public/data/calendar/releases/{self.calendar["release_id"]}/calendar.json'
        p.write(calendar_path,self.calendar,True)
        p.write(self.root/'public/data/calendar/latest.json',{'url':f'/data/calendar/releases/{self.calendar["release_id"]}/calendar.json','sha256':self.bundle['calendar_sha256']})
        p.write(self.root/'public/data/calendar/status.json',{'outcome':'source_error'})
        p.write(self.root/'configs/macro/macro-cross-v1.0.1.json',RULES)
        result=p.run(self.root,m.utc('2026-10-10T15:30:00Z'))
        self.assertEqual(result['outcome'],'unchanged');self.assertEqual(p.read_json(self.folder/'status.json')['pipeline_state'],'fresh')
        self.assertEqual(p.read_json(self.folder/'status.json')['last_successful_source_check_at'],fresh)

    def test_interrupted_manifest_write_recovers_original_status_proof(self):
        self.publish();later='2026-10-11T16:00:00Z';real_write=p.write
        def fail_manifest(path,value,immutable=False):
            if path.name=='manifest.json':raise OSError('injected interrupted write')
            return real_write(path,value,immutable)
        with patch.object(p,'write',side_effect=fail_manifest):
            with self.assertRaises(OSError):self.publish(status(NOW,later),later)
        result=self.publish(status(NOW,'2026-10-11T17:00:00Z'),'2026-10-11T17:00:00Z')
        pointer=p.read_json(self.folder/'latest.json');manifest=p.read_asset(self.root,pointer['manifest']);original=p.read_asset(self.root,manifest['batch_status'])
        self.assertEqual(original['data']['known_at'],later);self.assertEqual(result['assessment_id'],pointer['assessment_id'])


class MacroAdapterTests(unittest.TestCase):
    def pce_fixture(self,heading='[Percent change from preceding month] July August'):
        e=cal.event('bea','pce','PCE','Personal Income and Outlays, August 2026',m.utc('2026-09-30T12:30:00Z'),'high','inflation','https://www.bea.gov/news/2026/personal-income-and-outlays-august-2026')
        raw=f'<h1>Personal Income and Outlays, August 2026</h1> EMBARGOED UNTIL RELEASE AT 8:30 a.m. EDT, Wednesday, September 30, 2026 From the preceding month, the PCE price index for August increased 0.3 percent. Personal Income and Related Measures {heading} PCE price index 0.1 0.3 PCE price index excluding food and energy 0.1 0.2'
        source={'body':raw,'sha256':cal.digest(raw.encode()),'source_url':e['source_url'],'retrieved_at':NOW,'checked_at':NOW}
        cal.parse_bea_report(e,raw.encode(),NOW)
        c={'release_id':'calendar-'+'a'*20,'generated_at':NOW,'events':[e],'indicators':[],'sources':{'bea_report_bea_pce_2026_09_30':source,'bls_data':{'sha256':'0'*64,'source_url':cal.SOURCES['bls_data']}},'private_backup':{'verified':True}}
        return c,{'bea_report_bea_pce_2026_09_30':source}

    def test_pce_id_mapping_core_decimal_previous_month_and_definition(self):
        c,s=self.pce_fixture();b=adapter.normalize(c,cal.digest(cal.encode(c)),s,RULES,NOW)
        rows={o['metric_id']:o for o in b['observations']}
        self.assertEqual((rows[CORE]['actual'],rows[CORE]['previous']),('0.2','0.1'));self.assertEqual(rows[CORE]['seasonal_adjustment'],'SA')
        self.assertEqual(rows[HEAD]['previous_period'],'2026-07');self.assertEqual(rows[CORE]['definition_source_url'],adapter.PIO_DEFINITION_URL)
        refreshed=adapter.normalize(c,b['calendar_sha256'],s,RULES,'2026-10-08T16:00:00Z',b)
        self.assertEqual(b,refreshed)

    def test_wrong_table_cannot_prove_monthly_metadata(self):
        c,s=self.pce_fixture('[Percent change from same month one year ago] July August');b=adapter.normalize(c,cal.digest(cal.encode(c)),s,RULES,NOW)
        self.assertTrue(all(o['seasonal_adjustment'] is None for o in b['observations']))

    def test_raw_tamper_fails_whole_bundle_missing_source_stays_unknown(self):
        c,s=self.pce_fixture();bad=deepcopy(s);next(iter(bad.values()))['body']+='tampered'
        with self.assertRaisesRegex(RuntimeError,'checksum'):adapter.normalize(c,cal.digest(cal.encode(c)),bad,RULES,NOW)
        missing=adapter.normalize(c,cal.digest(cal.encode(c)),{},RULES,NOW)
        self.assertTrue(all(o['seasonal_adjustment'] is None for o in missing['observations']))

    def test_new_vintage_gets_new_first_seen_and_revision_ledger(self):
        c,s=self.pce_fixture();b=adapter.normalize(c,cal.digest(cal.encode(c)),s,RULES,NOW)
        c2,s2=self.pce_fixture();e=c2['events'][0];key='bea_report_bea_pce_2026_09_30'
        s2[key]['body']=s2[key]['body'].replace('0.1 0.2','0.1 0.3');s2[key]['sha256']=cal.digest(s2[key]['body'].encode());c2['sources'][key]=s2[key]
        c2['release_id']='calendar-'+'b'*20;c2['generated_at']='2026-10-08T16:00:00Z'
        newer=adapter.normalize(c2,cal.digest(cal.encode(c2)),s2,RULES,c2['generated_at'],b)
        core=next(o for o in newer['observations'] if o['metric_id']==CORE);old=next(o for o in b['observations'] if o['metric_id']==CORE)
        self.assertEqual(core['first_seen_at'],c2['generated_at']);self.assertEqual(core['revision_of'],old['observation_id']);self.assertNotEqual(core['observation_id'],old['observation_id'])


if __name__=='__main__':unittest.main()
