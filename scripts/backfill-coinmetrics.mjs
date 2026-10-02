import { createHash } from 'node:crypto';
import { mkdir, writeFile } from 'node:fs/promises';
import { join } from 'node:path';
import { fileURLToPath } from 'node:url';

const root = fileURLToPath(new URL('../', import.meta.url));
const apiOrigin = 'https://community-api.coinmetrics.io';
const endpoint = '/v4/timeseries/asset-metrics';
const metrics = ['PriceUSD', 'CapMrktCurUSD', 'SplyCur', 'CapMVRVCur'];
const headersToKeep = ['date', 'etag', 'last-modified', 'cache-control', 'retry-after', 'x-ratelimit-limit', 'x-ratelimit-remaining', 'x-ratelimit-reset'];
const pause = (ms) => new Promise((resolve) => setTimeout(resolve, ms));
const hash = (value) => createHash('sha256').update(value).digest('hex');

function parseDate(value) {
  if (!/^\d{4}-\d{2}-\d{2}$/.test(value) || Number.isNaN(Date.parse(`${value}T00:00:00.000Z`))
    || isoDate(new Date(`${value}T00:00:00.000Z`)) !== value) {
    throw new Error('Usage: node scripts/backfill-coinmetrics.mjs [start-utc-date] [as-of-utc-date]');
  }
  return new Date(`${value}T00:00:00.000Z`);
}

function isoDate(date) {
  return date.toISOString().slice(0, 10);
}

function nextDate(value) {
  const date = parseDate(value);
  date.setUTCDate(date.getUTCDate() + 1);
  return isoDate(date);
}

function numericValue(value) {
  if (value === null || value === undefined || value === '') return null;
  const number = typeof value === 'number' ? value : Number(value);
  return Number.isFinite(number) ? number : undefined;
}

function isDailyTimestamp(value) {
  if (typeof value !== 'string' || !/^\d{4}-\d{2}-\d{2}T00:00:00(?:\.\d+)?Z$/.test(value)) return false;
  const date = value.slice(0, 10);
  return isoDate(new Date(`${date}T00:00:00.000Z`)) === date;
}

function validateNextUrl(value) {
  if (!value) return null;
  const url = new URL(value);
  if (url.origin !== apiOrigin || url.pathname !== endpoint || url.searchParams.has('api_key')) {
    throw new Error('Coin Metrics returned an unexpected pagination URL; refusing to follow it.');
  }
  return url;
}

async function requestPage(url) {
  for (let attempt = 0; attempt < 4; attempt += 1) {
    const requestedAt = new Date().toISOString();
    let response;
    try {
      response = await fetch(url, { headers: { accept: 'application/json' } });
    } catch (error) {
      if (attempt === 3) throw error;
      await pause(1000 * (attempt + 1));
      continue;
    }

    const body = await response.text();
    if ((response.status === 429 || response.status >= 500) && attempt < 3) {
      const retryAfter = Number(response.headers.get('retry-after'));
      await pause(Number.isFinite(retryAfter) && retryAfter > 0 ? retryAfter * 1000 : 1000 * (attempt + 1));
      continue;
    }
    if (!response.ok) throw new Error(`Coin Metrics HTTP ${response.status}: ${body.slice(0, 300)}`);
    let payload;
    try {
      payload = JSON.parse(body);
    } catch {
      throw new Error('Coin Metrics returned invalid JSON.');
    }
    if (!Array.isArray(payload.data)) throw new Error('Coin Metrics payload has no data array.');
    return {
      body,
      payload,
      requestedAt,
      completedAt: new Date().toISOString(),
      headers: Object.fromEntries(headersToKeep
        .map((name) => [name, response.headers.get(name)])
        .filter(([, value]) => value !== null)),
      status: response.status,
    };
  }
  throw new Error('Coin Metrics request failed after retries.');
}

function qualityReport(rows, start, end) {
  const byDate = new Map();
  let invalidTimestamps = 0;
  let wrongAssets = 0;
  let duplicateRows = 0;
  let outOfOrderRows = 0;
  let previous = null;
  const fieldStats = Object.fromEntries(metrics.map((metric) => [metric, {
    missing_field_count: 0,
    null_count: 0,
    invalid_count: 0,
    zero_count: 0,
    negative_count: 0,
    first_valid_date: null,
    last_valid_date: null,
    revision_status_counts: {},
  }]));

  for (const row of rows) {
    if (row.asset !== 'eth') wrongAssets += 1;
    if (!isDailyTimestamp(row.time)) {
      invalidTimestamps += 1;
      continue;
    }
    const date = row.time.slice(0, 10);
    if (previous && date < previous) outOfOrderRows += 1;
    previous = date;
    if (byDate.has(date)) duplicateRows += 1;
    else byDate.set(date, row);

    for (const metric of metrics) {
      const stats = fieldStats[metric];
      const value = numericValue(row[metric]);
      if (!Object.hasOwn(row, metric)) stats.missing_field_count += 1;
      else if (row[metric] === null) stats.null_count += 1;
      else if (value === undefined) stats.invalid_count += 1;
      else {
        if (value === 0) stats.zero_count += 1;
        if (value < 0) stats.negative_count += 1;
        if (stats.first_valid_date === null) stats.first_valid_date = date;
        stats.last_valid_date = date;
      }
      const status = row[`${metric}-status`];
      if (typeof status === 'string') stats.revision_status_counts[status] = (stats.revision_status_counts[status] ?? 0) + 1;
    }
  }

  const missingDates = [];
  for (let date = start; date <= end; date = nextDate(date)) {
    if (!byDate.has(date)) missingDates.push(date);
  }
  return {
    response_row_count: rows.length,
    unique_date_count: byDate.size,
    duplicate_row_count: duplicateRows,
    out_of_order_row_count: outOfOrderRows,
    invalid_timestamp_count: invalidTimestamps,
    wrong_asset_count: wrongAssets,
    missing_row_date_count: missingDates.length,
    missing_row_dates: missingDates,
    fields: fieldStats,
  };
}

const startArg = process.argv[2] ?? '2015-08-01';
const asOf = process.argv[3] ?? isoDate(new Date());
const startDate = parseDate(startArg);
const asOfDate = parseDate(asOf);
if (startDate >= asOfDate) throw new Error('start-utc-date must be earlier than as-of-utc-date.');
const endDate = new Date(asOfDate);
endDate.setUTCDate(endDate.getUTCDate() - 1);
const start = isoDate(startDate);
const end = isoDate(endDate);
const retrievedAt = new Date().toISOString();
const runId = `coinmetrics-backfill-${asOf}-${retrievedAt.replaceAll(':', '').replaceAll('.', '')}`;
const runDirectory = join(root, 'data', 'raw', 'coinmetrics', runId);
await mkdir(runDirectory, { recursive: true });

const firstUrl = new URL(endpoint, apiOrigin);
firstUrl.search = new URLSearchParams({
  assets: 'eth',
  metrics: metrics.join(','),
  frequency: '1d',
  start_time: start,
  end_time: end,
  page_size: '1000',
  paging_from: 'start',
}).toString();

const manifest = {
  schema_version: '1.0.0',
  provider: 'coinmetrics_community_api',
  endpoint,
  asset: 'eth',
  frequency: '1d',
  metrics,
  start_date_requested: start,
  end_date_requested: end,
  as_of_utc: asOf,
  retrieved_at: retrievedAt,
  authorization: 'none',
  storage_scope: 'private, git-ignored data/raw',
  time_mapping: {
    source_timestamp_field: 'time',
    observation_date: 'UTC date component of source time label',
    period_end_utc: 'exclusive next-midnight boundary for the labeled UTC day',
    source_available_at: null,
    note: 'Coin Metrics daily metric documentation describes these values as end-of-UTC-day; the API time label is preserved verbatim.',
  },
  pages: [],
};

const rows = [];
let url = firstUrl;
while (url) {
  const page = await requestPage(url);
  const pageIndex = manifest.pages.length + 1;
  const rawFile = `page-${String(pageIndex).padStart(4, '0')}.json`;
  await writeFile(join(runDirectory, rawFile), page.body, 'utf8');
  rows.push(...page.payload.data.map((row) => ({
    ...row,
    _retrieved_at: page.completedAt,
    _source_page_sha256: hash(page.body),
  })));
  manifest.pages.push({
    page: pageIndex,
    request_url: url.toString(),
    requested_at: page.requestedAt,
    completed_at: page.completedAt,
    http_status: page.status,
    response_headers: page.headers,
    response_sha256: hash(page.body),
    response_bytes: Buffer.byteLength(page.body),
    row_count: page.payload.data.length,
    first_time: page.payload.data[0]?.time ?? null,
    last_time: page.payload.data.at(-1)?.time ?? null,
    raw_file: rawFile,
  });
  console.log(`page ${pageIndex}: ${page.payload.data.length} rows; sha256=${hash(page.body)}`);
  url = validateNextUrl(page.payload.next_page_url);
  if (url) await pause(1000);
}

rows.sort((a, b) => String(a.time).localeCompare(String(b.time)));
const startText = start;
const endText = end;
const quality = qualityReport(rows, startText, endText);
const canonicalRecords = rows.map((row) => ({
  asset: row.asset,
  source_timestamp: row.time,
  observation_date: typeof row.time === 'string' ? row.time.slice(0, 10) : null,
  period_end_utc: isDailyTimestamp(row.time) ? `${nextDate(row.time.slice(0, 10))}T00:00:00Z` : null,
  source_available_at: null,
  retrieved_at: row._retrieved_at,
  source_page_sha256: row._source_page_sha256,
  metrics: Object.fromEntries(metrics.map((metric) => [metric, row[metric] ?? null])),
}));
const canonicalBody = canonicalRecords.map((record) => JSON.stringify(record)).join('\n') + (canonicalRecords.length ? '\n' : '');
const canonicalFile = 'canonical.jsonl';
await writeFile(join(runDirectory, canonicalFile), canonicalBody, 'utf8');

manifest.status = 'complete';
manifest.snapshot = {
  canonical_file: canonicalFile,
  canonical_sha256: hash(canonicalBody),
  canonical_bytes: Buffer.byteLength(canonicalBody),
  row_count: canonicalRecords.length,
  unique_date_count: quality.unique_date_count,
  first_observation_date: canonicalRecords[0]?.observation_date ?? null,
  last_observation_date: canonicalRecords.at(-1)?.observation_date ?? null,
};
manifest.quality = quality;
const reportPath = join(runDirectory, 'manifest.json');
await writeFile(reportPath, `${JSON.stringify(manifest, null, 2)}\n`, 'utf8');
console.log(`Audit: ${JSON.stringify({
  status: manifest.status,
  pages: manifest.pages.length,
  row_count: quality.response_row_count,
  missing_row_dates: quality.missing_row_date_count,
  duplicate_rows: quality.duplicate_row_count,
  invalid_timestamps: quality.invalid_timestamp_count,
  fields: Object.fromEntries(metrics.map((metric) => [metric, {
    first_valid_date: quality.fields[metric].first_valid_date,
    last_valid_date: quality.fields[metric].last_valid_date,
    null_count: quality.fields[metric].null_count,
    invalid_count: quality.fields[metric].invalid_count,
  }])),
  canonical_sha256: manifest.snapshot.canonical_sha256,
})}`);
console.log(`Manifest: ${reportPath}`);
