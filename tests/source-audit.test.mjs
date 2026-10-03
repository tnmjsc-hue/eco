import test from 'node:test';
import assert from 'node:assert/strict';
import { mkdtemp, readFile, rm } from 'node:fs/promises';
import { join } from 'node:path';
import { tmpdir } from 'node:os';
import { runAudit } from '../scripts/audit-remaining-source-gates.mjs';

test('remaining source probe records coverage, access and no-key evidence without secrets', async t => {
  const outputRoot = await mkdtemp(join(tmpdir(), 'eco-source-gates-'));
  const evidencePath = join(outputRoot, 'evidence.json');
  t.after(() => rm(outputRoot, { recursive: true, force: true }));
  const calls = [];
  const fetcher = async (url, init) => {
    calls.push({ url, init });
    const parsed = new URL(url);
    if (parsed.hostname === 'community-api.coinmetrics.io' && parsed.pathname.includes('catalog')) {
      return new Response(JSON.stringify({ data: [{ asset: 'eth', metrics: [
        { metric: 'SplyAct1yr', frequencies: [{ frequency: '1d', min_time: '2015-07-30', max_time: '2026-10-02' }] },
        { metric: 'TxTfrValAdjUSD', frequencies: [{ frequency: '1d', min_time: '2015-08-08', max_time: '2026-10-02' }] },
      ] }] }), { status: 200 });
    }
    if (parsed.hostname === 'community-api.coinmetrics.io') return new Response('forbidden', { status: 403 });
    if (parsed.hostname === 'api.glassnode.com') return new Response('unauthorized', { status: 401 });
    if (parsed.pathname.includes('active-supply')) return new Response('SplyAct1Yr sum of unique native units', { status: 200 });
    if (parsed.pathname.includes('indicators')) return new Response('RHODL dormancy_account_based API key asset id - BTC', { status: 200 });
    if (parsed.pathname.includes('supply')) return new Response('realized-cap HODL API key asset', { status: 200 });
    return new Response('ETH asset metadata', { status: 200 });
  };

  const result = await runAudit({
    asOf: '2026-10-03',
    outputRoot,
    evidencePath,
    fetcher,
    now: () => new Date('2026-10-03T03:00:00.000Z'),
  });
  const evidence = JSON.parse(await readFile(evidencePath, 'utf8'));
  assert.equal(result.manifest.probes.length, 10);
  assert.deepEqual(evidence.findings.map(({ task, status }) => [task, status]), [
    ['E3-01', 'blocked'],
    ['E8-01', 'blocked'],
    ['E9-01', 'blocked'],
  ]);
  assert.equal(evidence.coinmetrics.sample_status.SplyAct1yr.http_status, 403);
  assert.equal(evidence.coinmetrics.sample_status.SplyAct1yr.row_count, 0);
  assert.match(evidence.coinmetrics.sample_status.SplyAct1yr.response_sha256, /^[0-9a-f]{64}$/);
  assert.equal(evidence.coinmetrics.sample_status.TxTfrValAdjUSD.http_status, 403);
  assert.equal(evidence.coinmetrics.sample_status.TxTfrValAdjUSD.row_count, 0);
  assert.match(evidence.coinmetrics.sample_status.TxTfrValAdjUSD.response_sha256, /^[0-9a-f]{64}$/);
  assert.deepEqual(evidence.glassnode.no_key_probes.map(({ http_status }) => http_status), [401, 401, 401]);
  assert.ok(evidence.coinmetrics.catalog.one_day_entries.every(({ asset }) => asset === 'eth'));
  assert.ok(calls.every(({ url }) => !/[?&](api_key|token|secret)=/i.test(url)));
  const manifest = JSON.parse(await readFile(join(result.runDirectory, 'manifest.json'), 'utf8'));
  assert.equal(manifest.authorization, 'no_api_key_no_paid_subscription');
});
