import { createHash } from 'node:crypto';
import { mkdir, writeFile } from 'node:fs/promises';
import { join } from 'node:path';
import { fileURLToPath } from 'node:url';

const root = fileURLToPath(new URL('../', import.meta.url));
const baseUrl = 'https://community-api.coinmetrics.io/v4/timeseries/asset-metrics';
const metrics = ['PriceUSD', 'CapMrktCurUSD', 'SplyCur', 'CapMVRVCur'];
const pause = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

function utcDate(date) {
  return date.toISOString().slice(0, 10);
}

function ranges(asOf) {
  const recentEnd = new Date(`${asOf}T00:00:00.000Z`);
  recentEnd.setUTCDate(recentEnd.getUTCDate() - 1);
  const recentStart = new Date(recentEnd);
  recentStart.setUTCDate(recentStart.getUTCDate() - 2);
  return [
    { id: 'inception', start: '2015-08-01', end: '2015-08-12' },
    { id: 'cycle-2018', start: '2018-01-01', end: '2018-01-03' },
    { id: 'recent', start: utcDate(recentStart), end: utcDate(recentEnd) },
  ];
}

function summarizeRows(payload, metric) {
  const rows = Array.isArray(payload?.data) ? payload.data : [];
  const values = rows.map((row) => row[metric]).filter((value) => value !== null && value !== undefined);
  return {
    row_count: rows.length,
    valid_value_count: values.length,
    first_time: rows[0]?.time ?? null,
    last_time: rows.at(-1)?.time ?? null,
    status: rows.length === 0 ? 'no_rows' : values.length === 0 ? 'rows_without_values' : 'available',
  };
}

const asOf = process.argv[2] ?? utcDate(new Date());
if (!/^\d{4}-\d{2}-\d{2}$/.test(asOf) || Number.isNaN(Date.parse(`${asOf}T00:00:00Z`))) {
  throw new Error('Usage: node scripts/audit-coinmetrics.mjs [as-of-utc-date]');
}

const retrievedAt = new Date().toISOString();
const runId = `coinmetrics-${asOf}-${retrievedAt.replaceAll(':', '').replaceAll('.', '')}`;
const runDirectory = join(root, 'data', 'raw', 'coinmetrics', runId);
await mkdir(runDirectory, { recursive: true });

const manifest = {
  schema_version: '1.0.0',
  provider: 'coinmetrics_community_api',
  asset: 'eth',
  frequency: '1d',
  as_of_utc: asOf,
  retrieved_at: retrievedAt,
  authorization: 'none',
  data_directory: 'private, git-ignored data/raw',
  probes: [],
};

for (const metric of metrics) {
  for (const range of ranges(asOf)) {
    const url = new URL(baseUrl);
    url.search = new URLSearchParams({
      assets: 'eth',
      metrics: metric,
      frequency: '1d',
      start_time: range.start,
      end_time: range.end,
      page_size: '100',
      paging_from: 'start',
    }).toString();

    const requestedAt = new Date().toISOString();
    let statusCode = null;
    let responseBody = '';
    let fetchError = null;
    let responseHeaders = {};
    try {
      const response = await fetch(url, { headers: { accept: 'application/json' } });
      statusCode = response.status;
      responseBody = await response.text();
      responseHeaders = Object.fromEntries(
        ['date', 'etag', 'last-modified', 'cache-control', 'retry-after', 'x-ratelimit-limit', 'x-ratelimit-remaining', 'x-ratelimit-reset']
          .map((name) => [name, response.headers.get(name)])
          .filter(([, value]) => value !== null),
      );
    } catch (error) {
      fetchError = error instanceof Error ? error.message : String(error);
    }
    const completedAt = new Date().toISOString();

    const rawHash = createHash('sha256').update(responseBody).digest('hex');
    const rawFile = `${metric}-${range.id}.json`;
    const rawPath = join(runDirectory, rawFile);
    await writeFile(rawPath, responseBody, 'utf8');
    let summary = null;
    let jsonParseError = null;
    try {
      summary = summarizeRows(JSON.parse(responseBody), metric);
    } catch (error) {
      jsonParseError = error instanceof Error ? error.message : String(error);
    }

    manifest.probes.push({
      metric,
      range,
      request_url: url.toString(),
      requested_at: requestedAt,
      completed_at: completedAt,
      http_status: statusCode,
      access_status: fetchError ? 'network_error' : statusCode === 200 ? 'http_200_inspect_payload' : `http_${statusCode}`,
      response_headers: responseHeaders,
      response_sha256: rawHash,
      response_bytes: Buffer.byteLength(responseBody),
      raw_file: rawFile,
      summary,
      fetch_error: fetchError,
      json_parse_error: jsonParseError,
    });
    console.log(`${metric} ${range.id}: HTTP ${statusCode ?? 'NETWORK_ERROR'}; ${summary?.valid_value_count ?? 0} values; sha256=${rawHash}`);
    await pause(700);
  }
}

const manifestPath = join(runDirectory, 'manifest.json');
await writeFile(manifestPath, `${JSON.stringify(manifest, null, 2)}\n`, 'utf8');
console.log(`Manifest: ${manifestPath}`);
