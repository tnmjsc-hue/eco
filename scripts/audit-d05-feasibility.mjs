import { createHash } from 'node:crypto';
import { mkdir, writeFile } from 'node:fs/promises';
import { join } from 'node:path';
import { fileURLToPath } from 'node:url';

const root = fileURLToPath(new URL('../', import.meta.url));
const apiOrigin = 'https://community-api.coinmetrics.io';
const sampleStart = '2021-01-01';
const sampleEnd = '2021-01-03';
const candidateMetrics = [
  'CapRealUSD',
  'FeeTotNtv',
  'FeeTotUSD',
  'FeeBlobTotNtv',
  'FeePrioTotNtv',
  'SplyAct1yr',
  'TxTfrValAdjUSD',
];
const docs = [
  { id: 'glassnode_indicators', url: 'https://docs.glassnode.com/basic-api/endpoints/indicators', terms: ['RHODL', 'dormancy_account_based'] },
  { id: 'glassnode_supply', url: 'https://docs.glassnode.com/basic-api/endpoints/supply', terms: ['realized-cap', 'HODL'] },
  { id: 'glassnode_metadata', url: 'https://docs.glassnode.com/basic-api/metadata', terms: ['ETH', 'asset'] },
];
const headersToKeep = ['date', 'etag', 'last-modified', 'cache-control', 'retry-after', 'x-ratelimit-limit', 'x-ratelimit-remaining', 'x-ratelimit-reset'];
const hash = (body) => createHash('sha256').update(body).digest('hex');
const isoDate = (value) => {
  if (value === undefined) return new Date().toISOString().slice(0, 10);
  if (!/^\d{4}-\d{2}-\d{2}$/.test(value) || Number.isNaN(Date.parse(`${value}T00:00:00Z`))) {
    throw new Error('Usage: node scripts/audit-d05-feasibility.mjs [as-of-utc-date]');
  }
  return value;
};
const safeFile = (value) => value.replace(/[^a-z0-9._-]+/gi, '_');

const asOf = isoDate(process.argv[2]);
const retrievedAt = new Date().toISOString();
const runId = `d05-feasibility-${asOf}-${retrievedAt.replaceAll(':', '').replaceAll('.', '')}`;
const runDirectory = join(root, 'data', 'raw', 'd05', runId);
await mkdir(join(runDirectory, 'raw'), { recursive: true });

async function probe(id, url, kind, terms = [], valueField = null) {
  const requestedAt = new Date().toISOString();
  let status = null;
  let body = '';
  let fetchError = null;
  let responseHeaders = {};
  try {
    const response = await fetch(url, { headers: { accept: 'application/json,text/html' } });
    status = response.status;
    body = await response.text();
    responseHeaders = Object.fromEntries(headersToKeep
      .map((name) => [name, response.headers.get(name)])
      .filter(([, value]) => value !== null));
  } catch (error) {
    fetchError = error instanceof Error ? error.message : String(error);
  }
  const completedAt = new Date().toISOString();
  const rawFile = `${safeFile(id)}.${kind === 'documentation' ? 'html' : 'json'}`;
  await writeFile(join(runDirectory, 'raw', rawFile), body, 'utf8');

  const result = {
    id,
    kind,
    url,
    requested_at: requestedAt,
    completed_at: completedAt,
    http_status: status,
    response_headers: responseHeaders,
    response_sha256: hash(body),
    response_bytes: Buffer.byteLength(body),
    raw_file: `raw/${rawFile}`,
    fetch_error: fetchError,
  };

  if (kind === 'timeseries') {
    try {
      const payload = JSON.parse(body);
      const rows = Array.isArray(payload?.data) ? payload.data : [];
      result.summary = {
        row_count: rows.length,
        first_time: rows[0]?.time ?? null,
        last_time: rows.at(-1)?.time ?? null,
        asset_values: [...new Set(rows.map((row) => row.asset).filter(Boolean))],
        non_null_value_count: valueField
          ? rows.reduce((count, row) => count + (row[valueField] === null || row[valueField] === undefined ? 0 : 1), 0)
          : null,
        metric_fields: rows.length ? Object.keys(rows[0]).filter((key) => !['asset', 'time'].includes(key)) : [],
      };
    } catch (error) {
      result.parse_error = error instanceof Error ? error.message : String(error);
    }
  } else if (kind === 'catalog') {
    try {
      const payload = JSON.parse(body);
      const rows = [];
      for (const asset of payload?.data ?? []) {
        for (const metric of asset.metrics ?? []) {
          const frequency = (metric.frequencies ?? []).find(({ frequency: value }) => value === '1d');
          rows.push({
            asset: asset.asset,
            metric: metric.metric,
            frequency: frequency?.frequency ?? null,
            min_time: frequency?.min_time ?? null,
            max_time: frequency?.max_time ?? null,
          });
        }
      }
      result.summary = { one_day_entries: rows };
    } catch (error) {
      result.parse_error = error instanceof Error ? error.message : String(error);
    }
  } else if (kind === 'documentation') {
    const normalized = body.toLowerCase();
    result.summary = {
      term_hits: Object.fromEntries(terms.map((term) => [term, normalized.includes(term.toLowerCase())])),
    };
  }
  return result;
}

const probes = [];
const catalogUrl = new URL('/v4/catalog-all-v2/asset-metrics', apiOrigin);
catalogUrl.search = new URLSearchParams({ assets: 'eth', metrics: candidateMetrics.join(',') }).toString();
probes.push(await probe('coinmetrics_catalog_candidates', catalogUrl.toString(), 'catalog'));

for (const metric of candidateMetrics) {
  const url = new URL('/v4/timeseries/asset-metrics', apiOrigin);
  url.search = new URLSearchParams({
    assets: 'eth',
    metrics: metric,
    frequency: '1d',
    start_time: sampleStart,
    end_time: sampleEnd,
    page_size: '3',
    paging_from: 'start',
  }).toString();
  probes.push(await probe(`coinmetrics_timeseries_${metric}`, url.toString(), 'timeseries', [], metric));
}

for (const doc of docs) probes.push(await probe(doc.id, doc.url, 'documentation', doc.terms));

const manifest = {
  schema_version: '1.0.0',
  audit_id: 'D05',
  audit_version: 'metric-feasibility-v0.1.1',
  as_of_utc: asOf,
  retrieved_at: retrievedAt,
  authorization: 'no_api_key',
  storage_scope: 'private, git-ignored data/raw/d05',
  sample_window: { start: sampleStart, end: sampleEnd, asset: 'eth', frequency: '1d' },
  probes,
};
await writeFile(join(runDirectory, 'manifest.json'), `${JSON.stringify(manifest, null, 2)}\n`, 'utf8');

for (const probeResult of probes) {
  const summary = probeResult.summary?.one_day_entries?.length ?? probeResult.summary?.row_count ?? '';
  console.log(`${probeResult.id}: HTTP ${probeResult.http_status ?? 'NETWORK_ERROR'}; ${summary}; sha256=${probeResult.response_sha256}`);
}
console.log(`Manifest: ${join(runDirectory, 'manifest.json')}`);
