import test from 'node:test';
import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
import { mkdtemp, readFile, writeFile, readdir, rm } from 'node:fs/promises';
import { join } from 'node:path';
import { tmpdir } from 'node:os';
import { auditE9, backfillE9, createE9Requester, E9_METRICS, loadE9Rights } from '../scripts/e9-coinmetrics.mjs';

const now = () => new Date('2026-10-03T04:00:00Z');
const digest = text => createHash('sha256').update(text).digest('hex');
const apiKey = 'fixture-test-api-key';
const row = date => ({ asset: 'eth', time: `${date}T00:00:00Z`, CapMrktCurUSD: '100', TxTfrValAdjUSD: '10' });
async function workspace(t) {
  const directory = await mkdtemp(join(tmpdir(), 'eco-e9-fixture-'));
  t.after(() => rm(directory, { recursive: true, force: true }));
  const evidence = 'SYNTHETIC TEST GRANT; never a real licence or entitlement.';
  await writeFile(join(directory, 'grant.txt'), evidence);
  const rights = { verification_status: 'verified', provider: 'coinmetrics_network_data', asset: 'eth', frequency: '1d',
    metrics: E9_METRICS, private_cache: true, private_research: true, valid_from: '2026-10-01', valid_until: '2026-10-31',
    evidence_file: 'grant.txt', evidence_sha256: digest(evidence) };
  const rightsFile = join(directory, 'rights.json');
  await writeFile(rightsFile, JSON.stringify(rights));
  return { directory, rights, rightsFile };
}

test('E9 source probe uses observed statuses, not a hardcoded blocked/success claim', async t => {
  const { directory } = await workspace(t);
  for (const allowed of [false, true]) {
    const result = await auditE9({ outputRoot: join(directory, String(allowed)), sleep: async () => {}, now,
      fetcher: async url => {
        const parsed = new URL(url);
        if (parsed.pathname.includes('catalog')) return new Response(JSON.stringify({ data: [] }));
        const metric = parsed.searchParams.get('metrics');
        if (!allowed && metric !== 'CapMrktCurUSD') return new Response('{"error":"forbidden"}', { status: 403 });
        return new Response(JSON.stringify({ data: ['2021-01-01', '2021-01-02', '2021-01-03'].map(date =>
          ({ asset: 'eth', time: `${date}T00:00:00Z`, [metric]: '1' })) }));
      } });
    assert.equal(result.technical_pair_access, allowed);
    assert.equal(result.full_history_verified, false);
    assert.equal(result.private_cache_rights, 'unverified');
    assert.equal(result.source_gate, allowed ? 'sample_access_only_requires_full_history_and_licence' : 'blocked_source_entitlement');
  }
});

test('E9 paginated licensed backfill keeps secrets out of every stored file and records redaction hashes', async t => {
  const { directory, rightsFile } = await workspace(t);
  let calls = 0;
  const result = await backfillE9('2026-10-01', '2026-10-03', { apiKey, rightsFile, outputRoot: join(directory, 'raw'), now,
    sleep: async () => {}, fetcher: async (url, options) => {
      assert.equal(options.redirect, 'error');
      const parsed = new URL(url);
      assert.equal(parsed.searchParams.get('api_key'), apiKey);
      const data = [row(++calls === 1 ? '2026-10-01' : '2026-10-02')];
      parsed.searchParams.set('next_page_token', 'fixture-page-2');
      return new Response(JSON.stringify({ data, next_page_url: calls === 1 ? parsed.href : null }),
        { headers: { etag: apiKey } });
    } });
  const manifest = JSON.parse(await readFile(join(result, 'manifest.json')));
  assert.equal(manifest.provider, 'coinmetrics_network_data');
  assert.deepEqual(manifest.metrics, E9_METRICS);
  assert.equal(manifest.snapshot.row_count, 2);
  assert.equal(manifest.pages[0].credentials_redacted_before_storage, true);
  assert.notEqual(manifest.pages[0].transport_response_sha256, manifest.pages[0].response_sha256);
  assert.equal(manifest.source_rights.public_candidate_release, 'blocked_pending_separate_review');
  for (const name of await readdir(result)) {
    const body = await readFile(join(result, name), 'utf8');
    assert.ok(!body.includes(apiKey) && !body.includes('api_key='), name);
  }
});

test('E9 rights, expiry, metric scope and licence hash are checked before network access', async t => {
  const { rightsFile, rights } = await workspace(t);
  await assert.rejects(loadE9Rights(undefined, now()), /requires/);
  for (const change of [{ private_cache: false }, { private_research: false }, { valid_until: '2026-10-02' },
    { valid_from: '2026-11-01' }, { metrics: ['CapMrktCurUSD', 'TxTfrValUSD'] }, { asset: 'btc' },
    { evidence_sha256: 'a'.repeat(64) }]) {
    await writeFile(rightsFile, JSON.stringify({ ...rights, ...change }));
    await assert.rejects(backfillE9('2026-10-01', '2026-10-03', { apiKey, rightsFile, now,
      fetcher: async () => { assert.fail('unauthorized network call'); } }));
  }
});

test('E9 refuses query changes, credential redirects, unexpected keys and never echoes network errors', async () => {
  const first = 'https://api.coinmetrics.io/v4/timeseries/asset-metrics?assets=eth&metrics=CapMrktCurUSD%2CTxTfrValAdjUSD&frequency=1d';
  for (const next of ['https://example.com/?api_key=' + apiKey, first + '&api_key=other-key', first + '&redirect=https://example.com']) {
    const request = createE9Requester({ apiKey, fetcher: async () => new Response(JSON.stringify({ data: [], next_page_url: next })) });
    await assert.rejects(request(first), /pagination/);
  }
  let calls = 0;
  const request = createE9Requester({ apiKey, sleep: async () => {}, fetcher: async () => {
    calls++; throw new Error('network failed with ' + apiKey);
  } });
  await assert.rejects(request(first), error => !error.message.includes(apiKey) && /4 attempts/.test(error.message));
  assert.equal(calls, 4);
  await assert.rejects(request('https://community-api.coinmetrics.io/v4/timeseries/asset-metrics'), /unexpected/);
});

test('E9 denied sample and bounded rate-limit retries never become a completed snapshot', async t => {
  const { directory, rightsFile } = await workspace(t);
  const delays = [];
  let calls = 0;
  const request = createE9Requester({ apiKey, sleep: async ms => delays.push(ms), fetcher: async () =>
    ++calls < 3 ? new Response('{"error":"retry"}', { status: 429, headers: { 'retry-after': '999999' } }) : new Response('{"data":[]}') });
  await request('https://api.coinmetrics.io/v4/timeseries/asset-metrics');
  assert.deepEqual(delays, [30000, 30000]);
  await assert.rejects(backfillE9('2026-10-01', '2026-10-03', { apiKey, rightsFile, outputRoot: join(directory, 'raw'), now,
    fetcher: async () => new Response('{"error":"forbidden"}', { status: 403 }) }), /HTTP 403/);
  for (const run of await readdir(join(directory, 'raw'))) {
    assert.ok(!(await readdir(join(directory, 'raw', run))).includes('manifest.json'));
  }
});
