import copy
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
import urllib.error
from unittest.mock import patch

from eco import calendar as cal


class CalendarTests(unittest.TestCase):
    def test_transient_source_error_retries_but_403_does_not(self):
        class Response:
            headers = {}
            def __init__(self, url): self.url = url
            def __enter__(self): return self
            def __exit__(self, *_): return False
            def read(self, _): return b'official fixture'

        now = datetime(2026, 10, 23, tzinfo=timezone.utc)
        with tempfile.TemporaryDirectory() as folder, patch.object(cal.time, 'sleep') as sleep:
            transient = urllib.error.HTTPError(cal.SOURCES['bls'], 503, 'unavailable', {}, None)
            with patch.object(cal.urllib.request, 'urlopen', side_effect=[transient, Response(cal.SOURCES['bls'])]) as open_url:
                result = cal.fetch_source('bls', Path(folder), now, 0)
            self.assertEqual(result['sha256'], cal.digest(b'official fixture'))
            self.assertEqual(open_url.call_count, 2)
            sleep.assert_called_once_with(1)
            denied = urllib.error.HTTPError(cal.SOURCES['bea'], 403, 'denied', {}, None)
            with patch.object(cal.urllib.request, 'urlopen', side_effect=denied) as open_url:
                with self.assertRaisesRegex(ValueError, 'bea: HTTP 403'):
                    cal.fetch_source('bea', Path(folder), now, 0)
            self.assertEqual(open_url.call_count, 1)
            self.assertEqual(sleep.call_count, 1)

            throttled = urllib.error.HTTPError(cal.SOURCES['bea'], 429, 'slow down', {'Retry-After': '7'}, None)
            with patch.object(cal.urllib.request, 'urlopen', side_effect=[throttled, Response(cal.SOURCES['bea'])]) as open_url:
                cal.fetch_source('bea', Path(folder), now, 0)
            self.assertEqual(open_url.call_count, 2)
            sleep.assert_called_with(7)

    def test_private_backup_retries_transient_put_and_verifies_readback(self):
        class Response:
            def __init__(self, body): self.body = body
            def __enter__(self): return self
            def __exit__(self, *_): return False
            def read(self): return self.body

        with tempfile.TemporaryDirectory() as folder:
            snapshot = Path(folder) / 'snapshot'
            snapshot.mkdir()
            (snapshot / 'sample.json').write_bytes(b'fixture')
            missing = urllib.error.HTTPError('https://example.test', 404, 'missing', {}, None)
            transient = urllib.error.HTTPError('https://example.test', 500, 'temporary', {}, None)
            env = {'R2_ACCOUNT_ID': 'a' * 32, 'R2_BUCKET': 'eco-eth-private',
                   'R2_ACCESS_KEY_ID': 'fixture-id', 'R2_SECRET_ACCESS_KEY': 'fixture-secret'}
            with patch.dict(os.environ, env), patch.object(cal.time, 'sleep') as sleep, patch.object(
                    cal.urllib.request, 'urlopen', side_effect=[missing, transient, Response(b''), Response(b'fixture')]) as open_url:
                receipt = cal.backup_snapshot(snapshot)
            self.assertEqual(open_url.call_count, 4)
            sleep.assert_called_once_with(1)
            self.assertEqual(receipt[0]['sha256'], cal.digest(b'fixture'))
            self.assertTrue(receipt[0]['readback_verified'])

    def test_ics_folded_titles_and_dst(self):
        text = 'BEGIN:VCALENDAR\r\n'
        for day in range(10, 20):
            text += f'BEGIN:VEVENT\r\nDTSTART;TZID=US-Eastern:202610{day}T083000\r\nSUMMARY:Consumer Price \r\n Index\r\nEND:VEVENT\r\n'
        text += 'END:VCALENDAR\r\n'
        rows = cal.parse_ics(text.encode(), 'bls')
        self.assertEqual(rows[0]['scheduled_at'], '2026-10-10T12:30:00Z')
        self.assertEqual(rows[0]['actual'], None)
        winter = text.replace('202610', '202612')
        self.assertEqual(cal.parse_ics(winter.encode(), 'bls')[0]['scheduled_at'], '2026-12-10T13:30:00Z')
        with self.assertRaises(ValueError):
            cal.parse_ics(text.replace('US-Eastern', 'Mars').encode(), 'bls')
        with self.assertRaises(ValueError):
            cal.parse_ics(text.replace('END:VCALENDAR', '').encode(), 'bls')

    def test_bea_gdp_alias_crcrlf_utc(self):
        text = 'BEGIN:VCALENDAR\r\r\n'
        for day in range(10, 20):
            text += f'BEGIN:VEVENT\r\r\nDTSTART:202610{day}T123000Z\r\r\nSUMMARY:GDP (Advance Estimate)\\, 3rd Quarter 2026\r\r\nEND:VEVENT\r\r\n'
        text += 'END:VCALENDAR\r\r\n'
        rows = cal.parse_ics(text.encode(), 'bea')
        self.assertEqual(rows[0]['kind'], 'gdp')
        self.assertEqual(rows[0]['scheduled_at'], '2026-10-10T12:30:00Z')

    def test_fomc_cross_month_and_standard_time(self):
        body = '2026 FOMC Meetings'
        for month, days in [('January','27-28'),('March','17-18*'),('Apr/May','30-1'),('June','16-17'),('July','28-29'),('September','15-16'),('October','27-28'),('December','8-9')]:
            body += f'<div class="row fomc-meeting"><div class="fomc-meeting__month"><strong>{month}</strong></div><div class="fomc-meeting__date">{days}</div></div>'
        rows = cal.parse_fed(body.encode())
        self.assertEqual(rows[2]['scheduled_at'], '2026-05-01T18:00:00Z')
        self.assertEqual(rows[-1]['scheduled_at'], '2026-12-09T19:00:00Z')
        self.assertEqual(rows[-1]['time_basis'], 'standard_14_et_verify_with_statement')
        with self.assertRaises(ValueError):
            cal.parse_fed(b'<html>Access denied</html>')

    def sample_indicators(self):
        series = []
        for sid, _, _, _ in cal.SERIES.values():
            series.append({'seriesID': sid, 'data': [{'year':'2026','period':f'M{m:02d}','value':v,'footnotes':[{'code':'P'}]} for m,v in [(8,'110'),(7,'100'),(6,'80')]]})
        return {'status':'REQUEST_SUCCEEDED','Results':{'series':series}}

    def test_api_values_missing_month_and_no_event_assignment(self):
        payload = self.sample_indicators()
        rows = cal.parse_indicators(cal.encode(payload))
        self.assertEqual((rows[0]['value'],rows[0]['previous']), (10,25))
        self.assertEqual((rows[1]['value'],rows[1]['previous']), (10,20))
        self.assertEqual(rows[2]['value'], 110)
        self.assertEqual(rows[0]['reference_period'], '2026-08')
        payload['Results']['series'][0]['data'].pop(1)
        rows = cal.parse_indicators(cal.encode(payload))
        self.assertIsNone(rows[0]['value'])
        self.assertIsNone(rows[0]['previous'])
        self.assertNotIn('scheduled_at', rows[0])
        payload['status'] = 'REQUEST_FAILED'
        with self.assertRaises(ValueError):
            cal.parse_indicators(cal.encode(payload))

    def test_source_failure_keeps_last_good_pointer(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            pointer = root / 'public/data/calendar/latest.json'
            cal.write_json(pointer, {'release_id':'calendar-original'})
            before = pointer.read_bytes()
            with patch.object(cal, 'fetch_source', side_effect=ValueError('provider failure')):
                with self.assertRaises(ValueError):
                    cal.run(root, datetime(2026,10,8,tzinfo=timezone.utc))
            self.assertEqual(pointer.read_bytes(), before)
            status = json.loads((pointer.parent/'status.json').read_bytes())
            self.assertEqual(status['outcome'], 'source_error')
            self.assertEqual(status['failure_codes']['bls_data'], 'validation_or_pipeline_error')
            self.assertNotIn('provider failure', str(status))

    def test_dol_holiday_exception_and_initial_claims_only(self):
        schedule = b'Publication Schedule: Thursday morning at 8:30am EST. <td>Wednesday, November 25, 2026</td>'
        rows = cal.parse_dol_schedule(schedule, datetime(2026,11,23,tzinfo=timezone.utc), datetime(2026,11,28,tzinfo=timezone.utc))
        self.assertEqual([r['id'] for r in rows], ['dol-claims-2026-11-25'])
        self.assertEqual(rows[0]['scheduled_at'], '2026-11-25T13:30:00Z')
        row = cal.event('dol','claims','Claims','Unemployment Insurance Weekly Claims',datetime(2026,9,17,12,30,tzinfo=timezone.utc),'medium','labor','https://oui.doleta.gov/unemploy/claims_arch.asp')
        row['source_url']='https://oui.doleta.gov/press/2026/091726.pdf'
        body = ('EMBARGOED UNTIL 8:30 A.M. Thursday, September 17, 2026 UNEMPLOYMENT INSURANCE WEEKLY CLAIMS '
                'SEASONALLY ADJUSTED DATA In the week ending September 12, the advance figure for seasonally adjusted initial claims was 196,000, '
                "a decrease of 10,000 from the previous week's unrevised level of 206,000. The 4-week moving average was 203,250. "
                "The advance number for seasonally adjusted insured unemployment was 1,730,000. The previous week's level was revised to 1,769,000.")
        reader = SimpleNamespace(PdfReader=lambda _: SimpleNamespace(pages=[SimpleNamespace(extract_text=lambda: body)]))
        with patch.dict(sys.modules, {'pypdf': reader}):
            cal.parse_dol_report(row,b'fixture','2026-09-17T13:00:00Z')
        self.assertEqual((row['actual'],row['previous'],row['reference_period']), (196,206,'2026-09-12'))

    def test_latest_bls_period_matches_only_last_completed_release(self):
        now=datetime(2026,10,8,tzinfo=timezone.utc)
        rows=[cal.event('bls','cpi','CPI','Consumer Price Index',datetime(2026,m,d,tzinfo=timezone.utc),'high','inflation',cal.SOURCES['bls']) for m,d in [(8,12),(9,11),(10,14)]]
        indicators=[{'id':'cpi','reference_period':'2026-08','value':0.4,'previous':0.1,'unit':'percent','source_url':'https://data.bls.gov/timeseries/CUSR0000SA0'}]
        cal.attach_bls_results(rows,indicators,now,'2026-10-08T13:00:00Z')
        self.assertEqual([r['actual'] for r in rows],[None,0.4,None])
        self.assertEqual(rows[1]['data_status'],'current_vintage_period_match')

    def test_cached_body_tampering_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            cal.write_json(root/'bls.json', {'body':'bad','sha256':'0'*64,'checked_at':'2026-10-08T00:00:00Z'})
            with self.assertRaisesRegex(ValueError, 'checksum'):
                cal.fetch_source('bls', root, datetime(2026,10,8,tzinfo=timezone.utc), 86400)

    def test_backup_failure_keeps_pointer_and_no_fake_publication(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            now=datetime(2026,10,8,tzinfo=timezone.utc)
            p=root/'public/data/calendar/latest.json'
            cal.write_json(p, {'release_id':'calendar-original','content_sha256':'old'})
            before=p.read_bytes()
            events=[cal.event(provider,'jobs','Jobs','Employment', now, 'high','labor',cal.SOURCES[provider]) for provider in ['bls','bea','fed']]
            rows=[{**events[i%3], 'id':f'event-{i}', 'provider':['bls','bea','fed','dol'][i%4]} for i in range(36)]
            source={'body':'test', 'sha256':cal.digest(b'test'),'retrieved_at':cal.stamp(now),'checked_at':cal.stamp(now)}
            with patch.object(cal,'fetch_source',return_value=source), patch.object(cal,'fed_month_urls',return_value={}), patch.object(cal,'parse_ics',return_value=rows), patch.object(cal,'parse_fed',return_value=[]), patch.object(cal,'parse_dol_schedule',return_value=[]), patch.object(cal,'parse_bea_schedule',return_value={}), patch.object(cal,'parse_indicators',return_value=[]), patch.object(cal,'attach_bls_results'), patch.object(cal,'backup_snapshot',side_effect=ValueError('backup failed')):
                with self.assertRaisesRegex(ValueError,'backup failed'):
                    cal.run(root,now)
            self.assertEqual(p.read_bytes(),before)
            self.assertFalse((p.parent/'releases').exists())
            self.assertEqual(json.loads((p.parent/'status.json').read_bytes())['outcome'],'pipeline_error')


if __name__ == '__main__':
    unittest.main()
