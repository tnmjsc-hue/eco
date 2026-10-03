import { createHash } from 'node:crypto';
import { mkdir, writeFile } from 'node:fs/promises';
import { dirname, join, resolve } from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';

const root = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const coinMetricsOrigin = 'https://community-api.coinmetrics.io';
const glassnodeApiOrigin = 'https://api.glassnode.com';
const defaultEvidencePath = join(root, 'docs', 'evidence', 'remaining-source-audit-2026-10-03.json');
const headersToKeep = ['date', 'etag', 'last-modified', 'cache-control', 'retry-after'];

const candidateMetrics = ['SplyAct1yr', 'TxTfrValAdjUSD'];
const docs = [
  { id: 'glassnode_indicators', url: 'https://docs.glassnode.com/basic-api/endpoints/indicators', terms: ['RHODL', 'dormancy_account_based'] },
  { id: 'glassnode_supply', url: 'https://docs.glassnode.com/basic-api/endpoints/supply', terms: ['realized-cap', 'HODL'] },
  { id: 'glassnode_metadata', url: 'https://docs.glassnode.com/basic-api/metadata', terms: ['ETH', 'asset'] },
  { id: 'coinmetrics_active_supply', url: 'https://gitbook-docs.coinmetrics.io/network-data/network-data-overview/supply/active-supply', terms: ['sum of unique native units', 'SplyAct1Yr'] },
];
const noKeyApiProbes = [
  { id: 'glassnode_dormancy_account_based', path: '/v1/metrics/indicators/dormancy_account_based', params: { a: 'ETH', i: '24h', f: 'json' } },
  { id: 'glassnode_realized_cap_hodl_waves', path: '/v1/metrics/supply/rcap_hodl_waves', params: { a: 'ETH', i: '24h', f: 'json' } },
  { id: 'glassnode_rhodl_ratio', path: '/v1/metrics/indicators/rhodl_ratio', params: { a: 'ETH', i: '24h', f: 'json' } },
];

const sha256 = body => createHash('sha256').update(body).digest('hex');
const safeFile = value => value.replace(/[^a-z0-9._-]+/gi, '_');
const isoDate = value => {
  if (value === undefined) return new Date().toISOString().slice(0, 10);
  if (!/^\d{4}-\d{2}-\d{2}$/.test(value) || Number.isNaN(Date.parse(`${value}T00:00:00Z`))) {
    throw new Error('Usage: node scripts/audit-remaining-source-gates.mjs [as-of-utc-date] [--evidence-out path]');
  }
  return value;
};

const urlWithParams = (origin, path, params) => {
  const url = new URL(path, origin);
  url.search = new URLSearchParams(params).toString();
  return url;
};

async function requestProbe({ id, url, kind, rawDirectory, fetcher = fetch, terms = [] }) {
  const requestedAt = new Date().toISOString();
  let status = null;
  let body = '';
  let responseHeaders = {};
  let fetchError = null;
  try {
    const response = await fetcher(url, { headers: { accept: 'application/json,text/html' } });
    status = response.status;
    body = await response.text();
    responseHeaders = Object.fromEntries(headersToKeep
      .map(name => [name, response.headers.get(name)])
      .filter(([, value]) => value !== null));
  } catch (error) {
    fetchError = error instanceof Error ? error.message : String(error);
  }
  const completedAt = new Date().toISOString();
  const extension = kind === 'documentation' ? 'html' : 'json';
  const rawFile = `${safeFile(id)}.${extension}`;
  await writeFile(join(rawDirectory, rawFile), body, 'utf8');
  const result = {
    id,
    kind,
    url,
    requested_at: requestedAt,
    completed_at: completedAt,
    http_status: status,
    response_headers: responseHeaders,
    response_sha256: sha256(body),
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
        asset_values: [...new Set(rows.map(row => row.asset).filter(Boolean))],
        metric_fields: rows.length ? Object.keys(rows[0]).filter(key => !['asset', 'time'].includes(key)) : [],
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
      term_hits: Object.fromEntries(terms.map(term => [term, normalized.includes(term.toLowerCase())])),
      api_key_required: /api[_ -]?key|required by candidate provider|apikeyauth/i.test(body),
    };
  }
  return result;
}

function timeseriesUrl(metric) {
  return urlWithParams(coinMetricsOrigin, '/v4/timeseries/asset-metrics', {
    assets: 'eth',
    metrics: metric,
    frequency: '1d',
    start_time: '2021-01-01',
    end_time: '2021-01-03',
    page_size: '3',
    paging_from: 'start',
  }).toString();
}

function catalogUrl() {
  return urlWithParams(coinMetricsOrigin, '/v4/catalog-all-v2/asset-metrics', {
    assets: 'eth',
    metrics: candidateMetrics.join(','),
  }).toString();
}

function buildEvidence({ asOf, retrievedAt, probes, runId }) {
  const byId = Object.fromEntries(probes.map(probe => [probe.id, probe]));
  const activeSupply = byId.coinmetrics_active_supply;
  const cmSply = byId.coinmetrics_timeseries_SplyAct1yr;
  const cmTransfer = byId.coinmetrics_timeseries_TxTfrValAdjUSD;
  const dormancy = byId.glassnode_dormancy_account_based;
  const rcap = byId.glassnode_realized_cap_hodl_waves;
  const rhodl = byId.glassnode_rhodl_ratio;
  const indicators = byId.glassnode_indicators;
  const supply = byId.glassnode_supply;
  const catalog = byId.coinmetrics_catalog_candidates;
  return {
    audit_id: 'E3-01/E8-01/E9-01',
    audit_version: 'remaining-source-gate-v0.1.0',
    as_of_utc: asOf,
    retrieved_at_utc: retrievedAt,
    authorization: 'no_api_key_no_paid_subscription',
    private_run: `data/raw/remaining-source-gates/${runId}/manifest.json`,
    scope: {
      asset: 'eth',
      frequency: '1d',
      no_btc_substitution: true,
      public_release: 'blocked_until_metric_specific_rights_and_methodology',
    },
    coinmetrics: {
      catalog: { http_status: catalog.http_status, response_sha256: catalog.response_sha256, one_day_entries: catalog.summary?.one_day_entries ?? [] },
      sample_window: { start: '2021-01-01', end: '2021-01-03' },
      sample_status: {
        SplyAct1yr: { http_status: cmSply.http_status, row_count: cmSply.summary?.row_count ?? 0, response_sha256: cmSply.response_sha256 },
        TxTfrValAdjUSD: { http_status: cmTransfer.http_status, row_count: cmTransfer.summary?.row_count ?? 0, response_sha256: cmTransfer.response_sha256 },
      },
      active_supply_semantics: {
        source: activeSupply.url,
        http_status: activeSupply.http_status,
        response_sha256: activeSupply.response_sha256,
        finding: 'SplyAct1Yr is trailing active supply of native units that transacted at least once; it is not a dormancy measure.',
      },
    },
    glassnode: {
      documentation: [indicators, supply, byId.glassnode_metadata].map(probe => ({
        id: probe.id,
        url: probe.url,
        http_status: probe.http_status,
        response_sha256: probe.response_sha256,
        facts: probe.id === 'glassnode_indicators'
          ? ['The documentation lists dormancy_account_based and requires an API key for endpoint requests.', 'The RHODL Ratio endpoint documentation specifies BTC as its asset scope; this does not establish ETH coverage.']
          : probe.id === 'glassnode_supply'
            ? ['The documentation lists Realized Cap HODL Waves and requires an API key plus an asset parameter.', 'Documentation alone does not establish an entitled ETH daily history, unit, vintage, or redistribution right.']
            : ['Metadata endpoint is documented, but no credentialed asset/metric entitlement query was performed.'],
      })),
      no_key_probes: [dormancy, rcap, rhodl].map(probe => ({ endpoint: probe.url.split('?')[0], asset: 'ETH', http_status: probe.http_status, response_sha256: probe.response_sha256 })),
    },
    findings: [
      {
        task: 'E3-01',
        status: 'blocked',
        finding: 'No ETH age-band/RHODL series, daily coverage, units, revision policy, or metric-specific rights were verified.',
        decision: 'Do not implement; require an entitled ETH endpoint and a source contract before E3-02.',
      },
      {
        task: 'E8-01',
        status: 'blocked',
        finding: 'Glassnode documents an account-based dormancy endpoint but the no-key request is unauthorized; Coin Metrics SplyAct1yr sample is 403 and its definition is active supply, not dormancy.',
        decision: 'Do not relabel active supply; require entitled ETH dormancy/spending history and rights before E8-02.',
      },
      {
        task: 'E9-01',
        status: 'blocked',
        finding: 'Coin Metrics catalog lists TxTfrValAdjUSD for ETH, but the Community timeseries sample is 403; adjusted-transfer filters, history, vintage, and derived/public rights remain unverified.',
        decision: 'Do not implement NVT proxy; require access or a specifically vetted alternative before E9-02.',
      },
    ],
    interpretation: [
      'HTTP 401/403 proves the attempted unauthenticated or Community request did not provide data; it does not prove that no paid or entitled source exists.',
      'No account was created and no email was accessed because no source gate can be cleared without an explicit provider entitlement and licence decision.',
      'No metric, score, probability, zero fill, or public release was created from these blocked candidates.',
    ],
  };
}

export async function runAudit({
  asOf,
  outputRoot = join(root, 'data', 'raw', 'remaining-source-gates'),
  evidencePath = defaultEvidencePath,
  fetcher = fetch,
  now = () => new Date(),
  writeEvidence = true,
} = {}) {
  const resolvedAsOf = isoDate(asOf);
  const retrievedAt = now().toISOString();
  const runId = `remaining-source-gates-${resolvedAsOf}-${retrievedAt.replaceAll(':', '').replaceAll('.', '')}`;
  const runDirectory = join(outputRoot, runId);
  const rawDirectory = join(runDirectory, 'raw');
  await mkdir(rawDirectory, { recursive: true });
  const probes = [];
  probes.push(await requestProbe({ id: 'coinmetrics_catalog_candidates', url: catalogUrl(), kind: 'catalog', rawDirectory, fetcher }));
  for (const metric of candidateMetrics) probes.push(await requestProbe({ id: `coinmetrics_timeseries_${metric}`, url: timeseriesUrl(metric), kind: 'timeseries', rawDirectory, fetcher }));
  for (const doc of docs) probes.push(await requestProbe({ ...doc, kind: 'documentation', rawDirectory, fetcher }));
  for (const probe of noKeyApiProbes) {
    const url = urlWithParams(glassnodeApiOrigin, probe.path, probe.params).toString();
    probes.push(await requestProbe({ id: probe.id, url, kind: 'api_access', rawDirectory, fetcher }));
  }
  const manifest = {
    schema_version: '1.0.0',
    audit_id: 'E3-01/E8-01/E9-01',
    audit_version: 'remaining-source-gate-v0.1.0',
    as_of_utc: resolvedAsOf,
    retrieved_at_utc: retrievedAt,
    authorization: 'no_api_key_no_paid_subscription',
    storage_scope: 'private, git-ignored data/raw/remaining-source-gates',
    sample_window: { start: '2021-01-01', end: '2021-01-03', asset: 'eth', frequency: '1d' },
    probes,
  };
  await writeFile(join(runDirectory, 'manifest.json'), `${JSON.stringify(manifest, null, 2)}\n`, 'utf8');
  const evidence = buildEvidence({ asOf: resolvedAsOf, retrievedAt, probes, runId });
  if (writeEvidence) await writeFile(evidencePath, `${JSON.stringify(evidence, null, 2)}\n`, 'utf8');
  return { runDirectory, manifest, evidence };
}

async function main() {
  const args = process.argv.slice(2);
  const asOf = args.find(arg => /^\d{4}-\d{2}-\d{2}$/.test(arg));
  const evidenceIndex = args.indexOf('--evidence-out');
  const evidencePath = evidenceIndex >= 0 ? resolve(args[evidenceIndex + 1]) : defaultEvidencePath;
  const result = await runAudit({ asOf, evidencePath });
  for (const probe of result.manifest.probes) {
    const count = probe.summary?.one_day_entries?.length ?? probe.summary?.row_count ?? '';
    console.log(`${probe.id}: HTTP ${probe.http_status ?? 'NETWORK_ERROR'}; ${count}; sha256=${probe.response_sha256}`);
  }
  console.log(`Manifest: ${join(result.runDirectory, 'manifest.json')}`);
  console.log(`Evidence: ${evidencePath}`);
}

if (process.argv[1] && pathToFileURL(resolve(process.argv[1])).href === import.meta.url) await main();
