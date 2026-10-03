import { createHash } from 'node:crypto';
import { mkdir, readFile, writeFile } from 'node:fs/promises';
import { join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { backfill, requestPage } from './backfill-coinmetrics.mjs';

const root = fileURLToPath(new URL('../', import.meta.url));
const base = 'https://community-api.coinmetrics.io/v4';
const hash = data => createHash('sha256').update(data).digest('hex');
const config = JSON.parse(await readFile(join(root, 'configs/research/network-proxies-v0.1.0.json'), 'utf8'));
export const PROXY_METRICS = config.source_metrics;
export function assertCommunityCatalog(payload) {
  const metrics = payload.data?.find(row => row.asset === 'eth')?.metrics;
  if (!metrics || PROXY_METRICS.some(id => !metrics.some(m => m.metric === id
      && m.frequencies.some(f => f.frequency === '1d' && f.community === true)))) {
    throw new Error('The frozen ETH daily fields are no longer in Community coverage.');
  }
}
export async function backfillProxies(asOf = new Date().toISOString().slice(0, 10), options = {}) {
  const request = options.request ?? requestPage;
  const catalog = await request(new URL(`${base}/catalog-v2/asset-metrics?assets=eth`));
  assertCommunityCatalog(catalog.payload);
  const folder = await backfill(config.origin_date, asOf, { ...options, request,
    origin: 'https://community-api.coinmetrics.io', provider: 'coinmetrics_community_api', authorization: 'none',
    metrics: PROXY_METRICS, allowZeroMetrics: config.allow_zero_metrics,
    preserveMetricStatus: true, runPrefix: 'coinmetrics-network-proxies',
    sourceRights: { licence: 'CC BY-NC 4.0', scope: 'noncommercial_research_preview', policy: 'ADR-005' } });
  // The available catalog is frozen next to this run, not assumed from catalog-all.
  await writeFile(join(folder, 'community-catalog.json'), catalog.body, 'utf8');
  const manifest = JSON.parse(await readFile(join(folder, 'manifest.json'), 'utf8'));
  manifest.community_catalog = { file: 'community-catalog.json', sha256: hash(catalog.body),
    requested_at: catalog.requestedAt, completed_at: catalog.completedAt, http_status: catalog.status };
  await writeFile(join(folder, 'manifest.json'), `${JSON.stringify(manifest, null, 2)}\n`);
  return folder;
}
export async function auditProxies(destination, { fetcher = fetch, now = () => new Date() } = {}) {
  const stamp = now().toISOString();
  const folder = join(root, 'data/raw/network-proxy-source', stamp.replaceAll(':', '').replaceAll('.', ''));
  await mkdir(folder, { recursive: true });
  const docs = 'https://gitbook-docs.coinmetrics.io';
  const urls = [
    `${base}/catalog-v2/asset-metrics?assets=eth`, `${base}/catalog/metrics`,
    ...['2015-08-08', '2021-01-01', '2026-09-29'].map(start => {
      const end = new Date(Date.parse(start) + 2*86400000).toISOString().slice(0,10);
      return `${base}/timeseries/asset-metrics?assets=eth&metrics=${PROXY_METRICS.join(',')}&frequency=1d&start_time=${start}&end_time=${end}&page_size=100`;
    }),
    `${docs}/packages/coin-metrics-community-data.md`,
    ...['exchange/exchange-supply', 'addresses/active-addresses', 'addresses/address-balances', 'transactions/transfers']
      .map(path => `${docs}/network-data/network-data-overview/${path}.md`),
    'https://raw.githubusercontent.com/coinmetrics/data/master/README.md',
  ];
  const records = [];
  for (const [index, url] of urls.entries()) {
    const requested = now().toISOString();
    const response = await fetcher(url, { signal: AbortSignal.timeout(30000), redirect: 'error' });
    const bytes = Buffer.from(await response.arrayBuffer());
    const filename = `response-${String(index+1).padStart(2, '0')}.txt`;
    await writeFile(join(folder, filename), bytes);
    const record = { url, http_status: response.status, requested_at: requested, retrieved_at: now().toISOString(),
      bytes: bytes.length, sha256: hash(bytes), raw_file: filename };
    if (index === 0 && response.ok) {
      const catalog = JSON.parse(bytes); assertCommunityCatalog(catalog);
      record.coverage = catalog.data.find(r => r.asset === 'eth').metrics.filter(m => PROXY_METRICS.includes(m.metric));
    }
    if (index === 1 && response.ok) record.definitions = JSON.parse(bytes).data.filter(m => PROXY_METRICS.includes(m.metric));
    if (index >= 2 && index <= 4 && response.ok) {
      const rows = JSON.parse(bytes).data;
      record.rows = rows.length;
      record.field_non_null = Object.fromEntries(PROXY_METRICS.map(m => [m, rows.filter(r => r[m] != null).length]));
      record.source_status = [...new Set(rows.flatMap(r => PROXY_METRICS.map(m => r[`${m}-status`]).filter(Boolean)))];
    }
    records.push(record);
  }
  const licenceText = await readFile(join(folder, 'response-06.txt'), 'utf8');
  const verified = records.every(r => r.http_status === 200) && licenceText.includes('creativecommons.org/licenses/by-nc/4.0/');
  const evidence = { schema_version: '1.0.0', audit: 'network-proxies-source-v1', observed_at: stamp,
    asset: 'eth', authorization: 'none', methodology_version: config.methodology_version,
    metrics: PROXY_METRICS, records, access_verified: verified,
    full_history_verified: false, licence: { id: 'CC BY-NC 4.0', community_licence_link_verified: verified,
      scope: 'noncommercial_research_preview', user_authorization: 'ADR-002; ADR-005', private_raw_cache: verified,
      derived_research_publication: verified, commercial_use: false },
    conclusions: ['sample_access_is_not_full_history', 'proxies_are_new_definitions_not_replications', 'source_flash_flags_are_provisional'] };
  await writeFile(destination, `${JSON.stringify(evidence, null, 2)}\n`, { flag: 'wx' });
  await writeFile(join(folder, 'evidence.json'), `${JSON.stringify(evidence, null, 2)}\n`);
  if (!verified) throw new Error('Source audit did not verify Community access and licence.');
  console.log(JSON.stringify({ status: 'verified_samples_and_community_licence', evidence: destination,
    sha256: hash(await readFile(destination)), requests: records.length }));
  return evidence;
}
if (process.argv[1] && resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  if (process.argv[2] === 'audit') await auditProxies(process.argv[3] ?? join(root, 'docs/evidence/network-proxies-source-2026-10-03.json'));
  else if (process.argv[2] === 'backfill') console.log(`PROXY_SNAPSHOT=${await backfillProxies(process.argv[3])}`);
  else throw new Error('Usage: node scripts/proxy-coinmetrics.mjs audit [new-evidence-file] | backfill [as-of-UTC-date]');
}
