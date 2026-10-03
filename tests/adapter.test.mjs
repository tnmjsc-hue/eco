import test from 'node:test';
import assert from 'node:assert/strict';
import { mkdtemp, readFile, rm } from 'node:fs/promises';
import { join } from 'node:path';
import { tmpdir } from 'node:os';
import { backfill, requestPage, validateNextUrl } from '../scripts/backfill-coinmetrics.mjs';

const row = date => ({ asset: 'eth', time: `${date}T00:00:00Z`, PriceUSD: '1', CapMrktCurUSD: '100', SplyCur: '100', CapMVRVCur: '2' });
test('200, forbidden, bounded 429/500/network retry and schema mismatch', async () => {
  const url = 'https://community-api.coinmetrics.io/v4/timeseries/asset-metrics';
  const response = await requestPage(url, { fetcher: async () => new Response('{"data":[]}') });
  assert.deepEqual(response.payload.data, []);
  let calls = 0;
  await assert.rejects(requestPage(url, { fetcher: async () => { calls++; return new Response('private', { status: 403 }); } }), /HTTP 403/);
  assert.equal(calls, 1);
  const delays = [];
  calls = 0;
  await requestPage(url, { fetcher: async () => ++calls < 3 ? new Response('', { status: 429, headers: { 'retry-after': '999999' } }) : new Response('{"data":[]}'), sleep: async ms => delays.push(ms) });
  assert.deepEqual(delays, [30000, 30000]);
  calls = 0;
  await assert.rejects(requestPage(url, { fetcher: async () => { calls++; throw new Error('offline'); }, sleep: async () => {} }), /offline/);
  assert.equal(calls, 4);
  calls = 0;
  await assert.rejects(requestPage(url, { fetcher: async () => { calls++; return new Response('', { status: 500 }); }, sleep: async () => {} }), /HTTP 500/);
  assert.equal(calls, 4);
  for (const body of ['{"rows":[]}', 'not-json']) await assert.rejects(requestPage(url, { fetcher: async () => new Response(body) }));
});

test('pagination keeps ETH query; closed UTC dates, duplicates and bad metrics rejected', async t => {
  const root = await mkdtemp(join(tmpdir(), 'eco-adapter-'));
  t.after(() => rm(root, { recursive: true, force: true }));
  const options = { outputRoot: root, sleep: async () => {}, now: () => new Date('2026-10-03T03:17:00Z') };
  let calls = 0;
  options.request = async url => {
    const next = new URL(url);
    next.searchParams.set('next_page_token', 'page-2');
    const payload = { data: [row(++calls === 1 ? '2026-10-01' : '2026-10-02')], next_page_url: calls === 1 ? next.href : null };
    return { payload, body: JSON.stringify(payload), requestedAt: '2026-10-03T03:17:00Z', completedAt: '2026-10-03T03:17:01Z', headers: {}, status: 200 };
  };
  const dir = await backfill('2026-10-01', '2026-10-03', options);
  const manifest = JSON.parse(await readFile(join(dir, 'manifest.json')));
  assert.equal(manifest.snapshot.row_count, 2);
  assert.equal(manifest.quality.missing_row_date_count, 0);
  assert.equal(manifest.pages.length, 2);
  await assert.rejects(backfill('2026-10-01', '2026-10-04', options), /future/);
  const first = new URL('https://community-api.coinmetrics.io/v4/timeseries/asset-metrics?assets=eth');
  assert.throws(() => validateNextUrl(first.href.replace('eth', 'btc'), first));
  assert.throws(() => validateNextUrl('https://example.com/'));
  for (const [index, data] of [[row('2026-10-01'), row('2026-10-01')], [{ ...row('2026-10-01'), asset: 'btc' }], [{ ...row('2026-10-01'), PriceUSD: -1 }], [{ ...row('2026-10-01'), PriceUSD: true }], [{ asset: 'eth', time: '2026-10-01T00:00:00Z' }]].entries()) {
    await assert.rejects(backfill('2026-10-01', '2026-10-03', { ...options, now: () => new Date(`2026-10-03T03:18:0${index}Z`), request: async () => ({ payload: { data }, body: JSON.stringify({ data }), headers: {}, status: 200 }) }), /contract/);
  }
});

test('candidate metric backfill keeps a separate one-field contract', async t => {
  const root = await mkdtemp(join(tmpdir(), 'eco-fee-adapter-'));
  t.after(() => rm(root, { recursive: true, force: true }));
  const options = {
    outputRoot: root,
    metrics: ['FeeTotNtv'],
    runPrefix: 'coinmetrics-fee-backfill',
    allowZeroMetrics: ['FeeTotNtv'],
    sleep: async () => {},
    now: () => new Date('2026-10-03T03:17:00Z'),
    request: async () => ({
      payload: { data: [{ asset: 'eth', time: '2026-10-01T00:00:00Z', FeeTotNtv: '0' }] },
      body: JSON.stringify({ data: [{ asset: 'eth', time: '2026-10-01T00:00:00Z', FeeTotNtv: '0' }] }),
      requestedAt: '2026-10-03T03:17:00Z', completedAt: '2026-10-03T03:17:01Z', headers: {}, status: 200,
    }),
  };
  const dir = await backfill('2026-10-01', '2026-10-03', options);
  const manifest = JSON.parse(await readFile(join(dir, 'manifest.json')));
  assert.deepEqual(manifest.metrics, ['FeeTotNtv']);
  assert.equal(manifest.snapshot.row_count, 1);
  assert.equal(manifest.quality.fields.FeeTotNtv.first_valid_date, '2026-10-01');
});
