from copy import deepcopy
from datetime import datetime, timedelta, timezone
from decimal import localcontext
from hashlib import sha256
import json
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch

from eco import macro_probability as m
from eco.macro_pipeline import body

ROOT = Path(__file__).resolve().parents[1]
PROTOCOL = json.loads((ROOT / 'configs/macro/macro-probability-v1.0.0.json').read_bytes())
AS_OF = '2026-10-09T05:00:00Z'


def synthetic_rows(n=183, independent=False):
    start = datetime(2020, 1, 1, tzinfo=timezone.utc)
    rows = []
    for i in range(n):
        issued = start + timedelta(days=7 * i)
        regime = ['R01', 'R02', 'R03'][i % 3]
        label = ['up', 'down', 'flat'][(i // 3 if independent else i) % 3]
        rows.append({'case_id': 'test-' + str(i), 'issued_at': issued.isoformat(), 'regime_id': regime,
                     'resolved_at': (issued + timedelta(days=8)).isoformat(), 'label': label})
    return rows


class ProbabilityTests(unittest.TestCase):
    def test_protocol_and_exact_outcome_boundaries(self):
        self.assertEqual(m.digest(PROTOCOL), m.PROTOCOL_SHA)
        for end, expected in [('99', 'flat'), ('101', 'flat'), ('98.999', 'down'), ('101.001', 'up')]:
            self.assertEqual(m.classify('100', end, PROTOCOL)[0], expected)
        for value in ['0', '-1', 'NaN', True, None]:
            with self.assertRaises(ValueError):
                m.classify(value, '1', PROTOCOL)

    def test_empty_and_missing_never_become_prior_probability(self):
        self.assertIsNone(m.evaluate([], 'R03', PROTOCOL)['probabilities'])
        rows = synthetic_rows()
        rows[0].pop('label')
        result = m.evaluate(rows, 'R03', PROTOCOL)
        self.assertEqual(result['state'], 'collecting')
        self.assertEqual(result['train_n'], 89)
        self.assertIsNone(result['probabilities'])

    def test_shrinkage_and_proper_scores_hand_calculated(self):
        baseline, groups = m.fit([{'label': 'up', 'regime_id': 'R03'}], PROTOCOL)
        self.assertEqual(baseline, [0.25, 0.25, 0.5])
        self.assertEqual(groups['R01'], baseline)
        self.assertAlmostEqual(float(groups['R03'][2]), 7/13)
        scores, _ = m.scores([{'label': 'up'}], [[0.2, 0.3, 0.5]])
        self.assertAlmostEqual(float(scores['brier']), 0.38)
        self.assertAlmostEqual(float(scores['log_loss']), 0.693147180559945)
        with self.assertRaises(ValueError):
            m.scores([{'label': 'up'}], [[0.2, 0.3, 0.4]])

    def test_temporal_embargo_and_prefix_invariance(self):
        rows = synthetic_rows()
        # 90 train, skip case 90 (issued before the last train label), 45 cal,
        # skip case 136, then 45 held out: 182 records required.
        self.assertEqual(m.evaluate(rows[:181], 'R03', PROTOCOL)['state'], 'awaiting_test')
        first = m.evaluate(rows[:182], 'R03', PROTOCOL)
        later = m.evaluate(rows + synthetic_rows()[0:0], 'R03', PROTOCOL)
        self.assertEqual(first, later)
        with localcontext() as context:
            context.prec = 8
            self.assertEqual(first, m.evaluate(rows, 'R03', PROTOCOL))
        self.assertEqual(first['state'], 'validated_holdout')
        self.assertEqual(first['temperature'], '0.5')
        self.assertEqual(first['regime_counts'], {'train': 30, 'calibration': 15, 'test': 15})
        self.assertAlmostEqual(sum(map(float, first['probabilities'].values())), 1)
        delayed = deepcopy(rows)
        delayed[89]['resolved_at'] = rows[-1]['resolved_at']
        self.assertEqual(m.evaluate(delayed, 'R03', PROTOCOL)['state'], 'awaiting_calibration')

    def test_failed_skill_and_sparse_regime_withhold(self):
        independent = m.evaluate(synthetic_rows(independent=True), 'R03', PROTOCOL)
        self.assertEqual(independent['state'], 'validation_failed')
        self.assertIn('global_brier_no_improvement', independent['failures'])
        self.assertIsNone(independent['probabilities'])
        sparse = m.evaluate(synthetic_rows(), 'R09', PROTOCOL)
        self.assertIn('insufficient_regime_train', sparse['failures'])
        self.assertIsNone(sparse['probabilities'])

    def workspace(self, root):
        shutil.copytree(ROOT / 'configs/macro', root / 'configs/macro')
        for name in ['calendar', 'macro-assessment', 'core-v2']:
            shutil.copytree(ROOT / 'public/data' / name, root / 'public/data' / name)
        # Pin immutable real source fixtures; future rolling pointers must not
        # make this historical-cutoff regression fail for unrelated new data.
        folder = root / 'public/data/macro-assessment'
        assessment_url = '/data/macro-assessment/releases/macro-1f6d30e129063d7f8d49/assessment.json'
        manifest_url = assessment_url.replace('assessment.json', 'manifest.json')
        manifest = json.loads((root / 'public' / manifest_url.lstrip('/')).read_bytes())
        assessment = json.loads((root / 'public' / assessment_url.lstrip('/')).read_bytes())
        pointer = {'assessment_id': assessment['assessment_id'], 'url': assessment_url, 'sha256': manifest['assessment_sha256'],
                   'manifest': {'url': manifest_url, 'sha256': sha256((root / 'public' / manifest_url.lstrip('/')).read_bytes()).hexdigest()}}
        (folder / 'latest.json').write_bytes(body(pointer))
        (folder / 'status.json').write_bytes(body({'assessment_id': assessment['assessment_id'], 'outcome': 'published',
                                                 'checked_at': assessment['as_of'], 'batch_status': manifest['batch_status']}))
        (root / 'public/data/calendar/latest.json').write_bytes(body(manifest['calendar']))
        eth_url = '/data/core-v2/releases/core10-e76805a7e3a9a76f7224/manifest.json'
        (root / 'public/data/core-v2/latest.json').write_bytes(body({'release_id': 'core10-e76805a7e3a9a76f7224', 'manifest_url': eth_url, 'manifest_sha256': sha256((root / 'public' / eth_url.lstrip('/')).read_bytes()).hexdigest()}))

    def test_publication_replay_immutable_and_error_retention(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.workspace(root)
            result = m.run(root, AS_OF)
            folder = root / 'public/data/macro-probability'
            pointer = (folder / 'latest.json').read_bytes()
            record = next((folder / 'records').glob('*.json'))
            original = record.read_bytes()
            self.assertEqual(result['model_state'], 'collecting')
            self.assertEqual(m.run(root, '2026-10-09T06:00:00Z')['outcome'], 'unchanged')
            self.assertEqual(pointer, (folder / 'latest.json').read_bytes())
            self.assertEqual(original, record.read_bytes())
            (folder / '.publication.lock').touch()
            status = (folder / 'status.json').read_bytes()
            with self.assertRaisesRegex(ValueError, 'busy'):
                m.run(root, AS_OF)
            self.assertEqual(status, (folder / 'status.json').read_bytes())
            (folder / '.publication.lock').unlink()
            record.write_bytes(original + b' ')
            with self.assertRaisesRegex(ValueError, 'checksum'):
                m.run(root, '2026-10-09T07:00:00Z')
            self.assertEqual(pointer, (folder / 'latest.json').read_bytes())
            self.assertEqual(json.loads((folder / 'status.json').read_bytes())['outcome'], 'error')

    def test_future_context_stale_context_and_parent_tamper(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.workspace(root)
            with self.assertRaisesRegex(ValueError, 'future'):
                m.run(root, '2026-10-08T00:00:00Z')
            m.run(root, '2026-10-12T00:00:00Z')
            self.assertEqual(len(list((root / 'public/data/macro-probability/records').glob('*.json'))), 0)
            latest = json.loads((root / 'public/data/calendar/latest.json').read_bytes())
            path = root / 'public' / latest['url'].lstrip('/')
            path.write_bytes(path.read_bytes() + b' ')
            with self.assertRaisesRegex(ValueError, 'checksum'):
                m.run(root, '2026-10-12T01:00:00Z')

    def test_interrupted_publish_preserves_original_time(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.workspace(root)
            actual_write = m.write
            def interrupted(path, value, immutable=False):
                if path.name == 'latest.json' and 'macro-probability' in str(path):
                    raise OSError('interrupted')
                return actual_write(path, value, immutable)
            with patch.object(m, 'write', side_effect=interrupted), self.assertRaises(OSError):
                m.run(root, AS_OF)
            original = next((root / 'public/data/macro-probability/releases').glob('*/report.json')).read_bytes()
            m.run(root, '2026-10-09T06:00:00Z')
            replay = next((root / 'public/data/macro-probability/releases').glob('*/report.json')).read_bytes()
            self.assertEqual(replay, original)

    def test_untrusted_paths_rejected(self):
        with self.assertRaises(ValueError):
            m.asset(ROOT, {'url': '/data/../secret.json', 'sha256': 'a' * 64})

    def test_exact_future_endpoints_missing_and_revision_retention(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.workspace(root)
            m.run(root, AS_OF)
            # Synthetic price parents are confined to this temporary test root.
            def parent(suffix, end_value):
                release_id = 'core10-' + suffix * 20
                base = root / 'public/data/core-v2/releases/core10-e76805a7e3a9a76f7224'
                history = json.loads((base / 'history.json').read_bytes())
                history['release_id'] = release_id
                rows = []
                for date, value in [('2026-10-10', 100.0), ('2026-10-17', end_value)]:
                    row = deepcopy(history['rows'][-1])
                    row.update(date=date, price_usd=value, period_closed_at_retrieval=True)
                    rows.append(row)
                history['rows'] += rows
                manifest = json.loads((base / 'manifest.json').read_bytes())
                manifest.update(release_id=release_id, computed_at='2026-10-17T12:00:00Z')
                history_bytes = (json.dumps(history, sort_keys=True, separators=(',', ':'), allow_nan=False) + '\n').encode()
                manifest['files']['history.json'] = sha256(history_bytes).hexdigest()
                target = root / 'public/data/core-v2/releases' / release_id
                target.mkdir(parents=True)
                (target / 'history.json').write_bytes(history_bytes)
                manifest_bytes = (json.dumps(manifest, sort_keys=True, separators=(',', ':'), allow_nan=False) + '\n').encode()
                (target / 'manifest.json').write_bytes(manifest_bytes)
                m.write(root / 'public/data/core-v2/latest.json', {'release_id': release_id,
                        'manifest_url': '/data/core-v2/releases/' + release_id + '/manifest.json', 'manifest_sha256': sha256(manifest_bytes).hexdigest()})
            parent('1', None)
            m.run(root, '2026-10-18T00:00:00Z')
            folder = root / 'public/data/macro-probability/outcomes'
            self.assertEqual(len(list(folder.glob('*.json'))), 0)
            parent('2', 101.1)
            m.run(root, '2026-10-18T01:00:00Z')
            outcome = next(folder.glob('*.json'))
            old = outcome.read_bytes()
            self.assertEqual(json.loads(old)['label'], 'up')
            self.assertEqual(json.loads(old)['resolved_at'], '2026-10-18T01:00:00Z')
            parent('3', 80.0)
            m.run(root, '2026-10-19T00:00:00Z')
            self.assertEqual(outcome.read_bytes(), old)
            self.assertEqual(len(list(folder.glob('*.json'))), 1)


if __name__ == '__main__':
    unittest.main()
