import { createHash } from 'node:crypto';
import { mkdir, readFile, writeFile } from 'node:fs/promises';
import { dirname, join, relative, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { backfill, qualityReport } from './backfill-coinmetrics.mjs';

const root = resolve(dirname(fileURLToPath(import.meta.url)), '..');
export const E9_METRICS = ['CapMrktCurUSD', 'TxTfrValAdjUSD'];
const community = 'https://community-api.coinmetrics.io';
const pro = 'https://api.coinmetrics.io';
const pause = ms => new Promise(resolve => setTimeout(resolve, ms));
const hash = body => createHash('sha256').update(body).digest('hex');
const dayPattern = /^\d{4}-\d{2}-\d{2}$/;

function validDay(value) {
  return typeof value === 'string' && dayPattern.test(value)
    && !Number.isNaN(Date.parse(`${value}T00:00:00Z`))
    && new Date(`${value}T00:00:00Z`).toISOString().slice(0, 10) === value;
}

export async function loadE9Rights(path, now = new Date()) {
  if (!path) throw new Error('E9 requires a verified private-cache/research rights file; access alone is insufficient.');
  const bytes = await readFile(path);
  let rights;
  try { rights = JSON.parse(bytes); } catch { throw new Error('E9 rights file must be valid JSON.'); }
  if (rights.verification_status !== 'verified' || rights.provider !== 'coinmetrics_network_data'
    || rights.asset !== 'eth' || rights.frequency !== '1d'
    || JSON.stringify(rights.metrics) !== JSON.stringify(E9_METRICS)
    || rights.private_cache !== true || rights.private_research !== true
    || !validDay(rights.valid_from) || !validDay(rights.valid_until)
    || rights.valid_from > now.toISOString().slice(0, 10) || rights.valid_until < now.toISOString().slice(0, 10)
    || !rights.evidence_file || !/^[0-9a-f]{64}$/.test(rights.evidence_sha256 ?? '')) {
    throw new Error('E9 rights contract is missing, expired or does not cover this ETH metric pair.');
  }
  const evidence = await readFile(resolve(dirname(resolve(path)), rights.evidence_file));
  if (hash(evidence) !== rights.evidence_sha256) throw new Error('E9 licence evidence checksum mismatch.');
  return { provider: rights.provider, asset: rights.asset, frequency: rights.frequency, metrics: E9_METRICS,
    verification_status: 'verified', private_cache: true, private_research: true,
    valid_from: rights.valid_from, valid_until: rights.valid_until,
    rights_file_sha256: hash(bytes), evidence_sha256: rights.evidence_sha256,
    public_candidate_release: 'blocked_pending_separate_review' };
}

// The transport URL exists only in memory. Persist/log the URL without the key.
// Never follow a provider redirect with the credential, or print a fetch error
// that might include its URL. Coin Metrics documents api_key query auth.
export function createE9Requester({ apiKey = '', fetcher = fetch, sleep = pause, now = () => new Date() } = {}) {
  const origin = apiKey ? pro : community;
  return async cleanUrl => {
    const url = new URL(cleanUrl);
    if (url.origin !== origin || url.username || url.password || url.searchParams.has('api_key')
      || !['/v4/timeseries/asset-metrics', '/v4/catalog-v2/asset-metrics', '/v4/catalog-all-v2/asset-metrics'].includes(url.pathname)) {
      throw new Error('E9 refuses an unexpected API URL or credential in a stored URL.');
    }
    const transportUrl = new URL(url);
    if (apiKey) transportUrl.searchParams.set('api_key', apiKey);
    for (let attempt = 0; attempt < 4; attempt++) {
      const requestedAt = now().toISOString();
      let response, transportBody;
      try {
        response = await fetcher(transportUrl, { headers: { accept: 'application/json' },
          redirect: 'error', signal: AbortSignal.timeout(30000) });
        transportBody = await response.text();
      } catch {
        if (attempt === 3) throw new Error('E9 source network request failed after 4 attempts.');
        await sleep(1000 * (attempt + 1));
        continue;
      }
      if ((response.status === 429 || response.status >= 500) && attempt < 3) {
        const retry = Number(response.headers.get('retry-after'));
        await sleep(Math.min(30000, retry > 0 ? retry * 1000 : 1000 * (attempt + 1)));
        continue;
      }
      let credentialsRedacted = false;
      function sanitize(value) {
        if (typeof value === 'string') {
          let clean = value;
          if (apiKey) for (const spelling of [apiKey, encodeURIComponent(apiKey)]) {
            if (clean.includes(spelling)) { clean = clean.replaceAll(spelling, '[REDACTED]'); credentialsRedacted = true; }
          }
          return clean;
        }
        if (Array.isArray(value)) return value.map(sanitize);
        if (value && typeof value === 'object') return Object.fromEntries(Object.entries(value)
          .filter(([name]) => { if (/^(api_key|authorization)$/i.test(name)) { credentialsRedacted = true; return false; } return true; })
          .map(([name, item]) => {
            if (name === 'next_page_url' && item) {
              let next;
              try { next = new URL(item); } catch { throw new Error('Invalid E9 pagination URL.'); }
              if (next.origin !== origin || next.pathname !== '/v4/timeseries/asset-metrics'
                || next.username || next.password) throw new Error('E9 pagination changed the API origin.');
              if (next.searchParams.has('api_key')) {
                if (next.searchParams.get('api_key') !== apiKey) throw new Error('E9 pagination contains an unexpected credential.');
                next.searchParams.delete('api_key'); credentialsRedacted = true;
              }
              const allowed = new Set([...url.searchParams.keys(), 'next_page_token']);
              if ([...next.searchParams.keys()].some(key => !allowed.has(key))) throw new Error('E9 pagination added an unexpected query parameter.');
              item = next.href;
            }
            return [name, sanitize(item)];
          }));
        return value;
      }
      let payload;
      try { payload = sanitize(JSON.parse(transportBody)); }
      catch (error) {
        if (error instanceof SyntaxError) throw new Error(`E9 source HTTP ${response.status} returned invalid JSON.`);
        throw error;
      }
      const headers = Object.fromEntries(['date', 'etag', 'last-modified', 'cache-control']
        .map(name => [name, response.headers.get(name)]).filter(([, v]) => v !== null)
        .map(([name, value]) => [name, sanitize(value)]));
      const body = credentialsRedacted ? JSON.stringify(payload) : transportBody;
      return { payload, body, status: response.status, requestedAt, completedAt: now().toISOString(),
        headers,
        transportSha256: hash(transportBody), credentialsRedacted };
    }
    throw new Error('E9 source request exhausted retries.');
  };
}

export async function backfillE9(start = '2015-08-08', asOf = new Date().toISOString().slice(0, 10), {
  apiKey = process.env.COINMETRICS_API_KEY ?? '', rightsFile,
  outputRoot = join(root, 'data/raw/coinmetrics'), fetcher = fetch, sleep = pause, now = () => new Date(),
} = {}) {
  const sourceRights = await loadE9Rights(rightsFile, now());
  if (!apiKey) throw new Error('E9 backfill requires COINMETRICS_API_KEY with ETH adjusted-transfer entitlement.');
  const request = createE9Requester({ apiKey, fetcher, sleep, now });
  return backfill(start, asOf, { outputRoot, sleep, now, metrics: E9_METRICS,
    runPrefix: 'coinmetrics-e9-nvt-backfill', allowZeroMetrics: ['TxTfrValAdjUSD'],
    origin: pro, provider: 'coinmetrics_network_data', authorization: 'api_key_environment_server_only', sourceRights,
    request: async url => {
      const page = await request(url);
      if (page.status !== 200) throw new Error(`E9 source HTTP ${page.status}; entitlement not verified.`);
      return page;
    } });
}

export async function auditE9({ outputRoot = join(root, 'data/raw/e9-source'), evidencePath,
  fetcher = fetch, sleep = pause, now = () => new Date() } = {}) {
  const retrievedAt = now().toISOString();
  const run = `e9-source-${retrievedAt.replaceAll(':', '').replaceAll('.', '')}`;
  const directory = join(outputRoot, run);
  await mkdir(directory, { recursive: true });
  const request = createE9Requester({ fetcher, sleep, now });
  const probes = [];
  const summary = { audit_id: 'E9-01', schema_version: '1.0.0', retrieved_at: retrievedAt,
    authorization: 'none', asset: 'eth', frequency: '1d', probes: [],
    full_history_verified: false, private_cache_rights: 'unverified', public_rights: 'unverified' };
  for (const [id, path, params] of [
    ['catalog_available', '/v4/catalog-v2/asset-metrics', { assets: 'eth' }],
    ['catalog_all', '/v4/catalog-all-v2/asset-metrics', { assets: 'eth', metrics: [...E9_METRICS, 'TxTfrValAdjNtv', 'NVTAdj90', 'NVTAdj', 'NVTAdjFF90'].join(',') }],
    ...[...E9_METRICS, 'TxTfrValAdjNtv', 'NVTAdj90', 'NVTAdj', 'NVTAdjFF90'].map(metric => [metric, '/v4/timeseries/asset-metrics',
      { assets: 'eth', metrics: metric, frequency: '1d', start_time: '2021-01-01', end_time: '2021-01-03' }]),
  ]) {
    const url = new URL(path, community); url.search = new URLSearchParams(params).toString();
    let page;
    try { page = await request(url); } catch { page = { status: null, body: '', payload: {}, headers: {}, requestedAt: now().toISOString(), completedAt: now().toISOString(), transportSha256: hash(''), credentialsRedacted: false }; }
    await writeFile(join(directory, `${id}.json`), page.body);
    let details;
    if (id.startsWith('catalog')) {
      const entries = (page.payload.data ?? []).filter(item => item.asset === 'eth').flatMap(item =>
        (item.metrics ?? []).filter(item => [...E9_METRICS, 'TxTfrValAdjNtv', 'NVTAdj90', 'NVTAdj', 'NVTAdjFF90'].includes(item.metric))
          .flatMap(metric => (metric.frequencies ?? []).filter(f => f.frequency === '1d').map(f =>
            ({ metric: metric.metric, frequency: f.frequency, first_time: f.min_time, last_time: f.max_time }))));
      details = { entries, catalog_is_not_entitlement_proof: id === 'catalog_all' };
    } else {
      const rows = Array.isArray(page.payload.data) ? page.payload.data : [];
      const quality = qualityReport(rows, '2021-01-01', '2021-01-03', [id]);
      details = { rows: rows.length, quality, technical_sample_access: page.status === 200 && rows.length === 3
        && !quality.wrong_asset_count && !quality.duplicate_row_count && !quality.out_of_order_row_count && !quality.invalid_timestamp_count
        && !quality.missing_row_date_count && !quality.fields[id].missing_field_count
        && !quality.fields[id].null_count && !quality.fields[id].invalid_count && !quality.fields[id].negative_count
        && (id === 'TxTfrValAdjUSD' || quality.fields[id].zero_count === 0)
        && rows.every(row => row[id] !== null && row[id] !== '' && ['number', 'string'].includes(typeof row[id])
          && Number.isFinite(Number(row[id])) && Number(row[id]) >= 0) };
    }
    const record = { id, url: url.href, http_status: page.status, requested_at: page.requestedAt,
      completed_at: page.completedAt, response_sha256: hash(page.body), raw_file: `${id}.json`, ...details };
    probes.push({ ...record, response_headers: page.headers });
    summary.probes.push(record);
    await sleep(800);
  }
  const pairAccessible = E9_METRICS.every(metric => summary.probes.find(p => p.id === metric)?.technical_sample_access);
  const docs = [
    ['nvt_definition', 'https://gitbook-docs.coinmetrics.io/network-data/network-data-overview/economics/valuation.md'],
    ['transfer_definition', 'https://gitbook-docs.coinmetrics.io/network-data/network-data-overview/transactions/transfer-value.md'],
    ['community_archive_licence', 'https://raw.githubusercontent.com/coinmetrics/data/master/README.md'],
    ['current_eth_csv', 'https://raw.githubusercontent.com/coinmetrics/data/master/csv/eth.csv'],
    ['academic_access', 'https://www.talos.com/academic-program'],
  ];
  summary.documentation_probes = [];
  for (const [id, url] of docs) {
    let status = null, body = '', finalUrl = url;
    try {
      const response = await fetcher(url, { signal: AbortSignal.timeout(30000) });
      status = response.status; body = await response.text(); finalUrl = response.url || url;
    } catch { /* An unavailable documentation page is recorded, never assumed verified. */ }
    const rawFile = `${id}.${id === 'current_eth_csv' ? 'csv' : 'txt'}`;
    await writeFile(join(directory, rawFile), body);
    const record = { id, url, final_url: finalUrl, http_status: status, response_sha256: hash(body), raw_file: rawFile };
    if (id === 'current_eth_csv') {
      record.header = body.split(/\r?\n/)[0].split(',');
      record.required_fields_present = E9_METRICS.every(metric => record.header.includes(metric));
    }
    summary.documentation_probes.push(record);
  }
  summary.technical_pair_access = pairAccessible;
  summary.source_gate = pairAccessible ? 'sample_access_only_requires_full_history_and_licence' : 'blocked_source_entitlement';
  summary.decision = 'do_not_publish_or_invent_E9_score';
  const manifestBody = `${JSON.stringify({ ...summary, probes, status: 'probe_complete_source_gate_not_complete' }, null, 2)}\n`;
  await writeFile(join(directory, 'manifest.json'), manifestBody);
  summary.manifest_sha256 = hash(manifestBody);
  summary.private_snapshot_directory = relative(root, directory).replaceAll('\\', '/');
  if (evidencePath) await writeFile(evidencePath, `${JSON.stringify(summary, null, 2)}\n`, { flag: 'wx' });
  return summary;
}

if (process.argv[1] && resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  const [command, ...args] = process.argv.slice(2);
  if (command === 'audit') {
    const evidenceIndex = args.indexOf('--evidence-out');
    const result = await auditE9({ evidencePath: evidenceIndex >= 0 ? args[evidenceIndex + 1] : undefined });
    console.log(JSON.stringify({ source_gate: result.source_gate, technical_pair_access: result.technical_pair_access,
      manifest_sha256: result.manifest_sha256, private_snapshot_directory: result.private_snapshot_directory }));
  } else if (command === 'backfill') {
    const index = args.indexOf('--rights-file');
    await backfillE9(args[0], args[1], { rightsFile: index >= 0 ? args[index + 1] : undefined });
  } else throw new Error('Usage: node scripts/e9-coinmetrics.mjs audit [--evidence-out path] | backfill start as-of --rights-file private-path');
}
