import { createHash, createHmac } from 'node:crypto';
import { readFile, readdir, stat } from 'node:fs/promises';
import { basename, isAbsolute, join, relative, resolve, sep } from 'node:path';
import { fileURLToPath } from 'node:url';

const root = fileURLToPath(new URL('../', import.meta.url));
const rawRoot = resolve(root, 'data/raw/coinmetrics');
const [snapshotArgument, ...flags] = process.argv.slice(2);
const dryRun = flags.includes('--dry-run');
const unknownFlags = flags.filter((flag) => flag !== '--dry-run');

if (!snapshotArgument || unknownFlags.length) {
  throw new Error('Usage: node scripts/upload-private-snapshot-r2.mjs <data/raw/coinmetrics/run-id> [--dry-run]');
}

const snapshotDirectory = resolve(isAbsolute(snapshotArgument) ? snapshotArgument : join(root, snapshotArgument));
const relativeToRawRoot = relative(rawRoot, snapshotDirectory);
if (!relativeToRawRoot || relativeToRawRoot.startsWith(`..${sep}`) || relativeToRawRoot === '..') {
  throw new Error('Snapshot directory must be a child of data/raw/coinmetrics.');
}
if (!(await stat(snapshotDirectory)).isDirectory()) throw new Error('Snapshot path must be a directory.');

const accountId = process.env.R2_ACCOUNT_ID;
const bucket = process.env.R2_BUCKET;
const accessKeyId = process.env.R2_ACCESS_KEY_ID;
const secretAccessKey = process.env.R2_SECRET_ACCESS_KEY;
const requiredCredentials = { R2_ACCOUNT_ID: accountId, R2_BUCKET: bucket, R2_ACCESS_KEY_ID: accessKeyId, R2_SECRET_ACCESS_KEY: secretAccessKey };
if (!dryRun && Object.values(requiredCredentials).some((value) => !value)) {
  throw new Error('Set R2_ACCOUNT_ID, R2_BUCKET, R2_ACCESS_KEY_ID, and R2_SECRET_ACCESS_KEY in the process environment.');
}
if (!dryRun && (!/^[a-f0-9]{32}$/i.test(accountId) || !/^[a-z0-9][a-z0-9-]{1,61}[a-z0-9]$/.test(bucket))) {
  throw new Error('R2 account ID or bucket name has an invalid format.');
}

async function collectFiles(directory, prefix = '') {
  const entries = await readdir(directory, { withFileTypes: true });
  const files = [];
  for (const entry of entries) {
    if (entry.isSymbolicLink()) throw new Error(`Symbolic links are not allowed in a snapshot: ${join(prefix, entry.name)}`);
    const relativePath = join(prefix, entry.name);
    const absolutePath = join(directory, entry.name);
    if (entry.isDirectory()) files.push(...await collectFiles(absolutePath, relativePath));
    else if (entry.isFile()) files.push({ relativePath, absolutePath });
    else throw new Error(`Unsupported filesystem entry in snapshot: ${relativePath}`);
  }
  return files;
}

function awsEncode(value) {
  return encodeURIComponent(value).replace(/[!'()*]/g, (character) => `%${character.charCodeAt(0).toString(16).toUpperCase()}`);
}

function hmac(key, value, encoding) {
  return createHmac('sha256', key).update(value, 'utf8').digest(encoding);
}

function signatureKey(secret, date) {
  const dateKey = hmac(`AWS4${secret}`, date);
  const regionKey = createHmac('sha256', dateKey).update('auto', 'utf8').digest();
  const serviceKey = createHmac('sha256', regionKey).update('s3', 'utf8').digest();
  return createHmac('sha256', serviceKey).update('aws4_request', 'utf8').digest();
}

async function signedRequest(method, objectKey, body) {
  const now = new Date();
  const amzDate = now.toISOString().replace(/[:-]|\.\d{3}/g, '');
  const dateStamp = amzDate.slice(0, 8);
  const payloadHash = createHash('sha256').update(body ?? Buffer.alloc(0)).digest('hex');
  const host = `${accountId}.r2.cloudflarestorage.com`;
  const path = `/${awsEncode(bucket)}/${objectKey.split('/').map(awsEncode).join('/')}`;
  const canonicalHeaders = `host:${host}\nx-amz-content-sha256:${payloadHash}\nx-amz-date:${amzDate}\n`;
  const signedHeaders = 'host;x-amz-content-sha256;x-amz-date';
  const canonicalRequest = `${method}\n${path}\n\n${canonicalHeaders}\n${signedHeaders}\n${payloadHash}`;
  const scope = `${dateStamp}/auto/s3/aws4_request`;
  const stringToSign = `AWS4-HMAC-SHA256\n${amzDate}\n${scope}\n${createHash('sha256').update(canonicalRequest).digest('hex')}`;
  const signature = createHmac('sha256', signatureKey(secretAccessKey, dateStamp)).update(stringToSign, 'utf8').digest('hex');
  const authorization = `AWS4-HMAC-SHA256 Credential=${accessKeyId}/${scope}, SignedHeaders=${signedHeaders}, Signature=${signature}`;
  return fetch(`https://${host}${path}`, {
    method,
    headers: {
      authorization,
      'x-amz-content-sha256': payloadHash,
      'x-amz-date': amzDate,
      ...(method === 'PUT' ? { 'content-type': 'application/json' } : {}),
    },
    ...(body ? { body } : {}),
  });
}

async function putObject(objectKey, body, checksum) {
  const response = await signedRequest('PUT', objectKey, body);
  if (!response.ok) {
    await response.body?.cancel();
    throw new Error(`R2 upload failed with HTTP ${response.status} for object ${objectKey}.`);
  }
  await response.body?.cancel();

  const readback = await signedRequest('GET', objectKey);
  if (!readback.ok) {
    await readback.body?.cancel();
    throw new Error(`R2 read-back failed with HTTP ${readback.status} for object ${objectKey}.`);
  }
  const downloaded = Buffer.from(await readback.arrayBuffer());
  if (createHash('sha256').update(downloaded).digest('hex') !== checksum) {
    throw new Error(`R2 read-back checksum mismatch for object ${objectKey}.`);
  }
}

const manifestFile = join(snapshotDirectory, 'manifest.json');
const manifest = JSON.parse(await readFile(manifestFile, 'utf8'));
if (manifest.status !== 'complete' || manifest.provider !== 'coinmetrics_community_api') {
  throw new Error('Only completed Coin Metrics snapshots can be uploaded.');
}

const files = await collectFiles(snapshotDirectory);
if (files.length === 0 || !files.some((file) => file.relativePath === 'canonical.jsonl')) {
  throw new Error('Snapshot must include canonical.jsonl and its manifest.');
}
files.sort((left, right) => {
  if (left.relativePath === 'manifest.json') return 1;
  if (right.relativePath === 'manifest.json') return -1;
  return left.relativePath.localeCompare(right.relativePath);
});

const prefix = `raw/coinmetrics/${basename(snapshotDirectory)}`;
const results = [];
for (const file of files) {
  const body = await readFile(file.absolutePath);
  const objectKey = `${prefix}/${file.relativePath.split(sep).join('/')}`;
  const checksum = createHash('sha256').update(body).digest('hex');
  if (!dryRun) await putObject(objectKey, body, checksum);
  results.push({ object_key: objectKey, bytes: body.byteLength, sha256: checksum, readback_verified: !dryRun });
}

console.log(JSON.stringify({
  status: dryRun ? 'dry_run' : 'uploaded_private_snapshot',
  bucket: dryRun ? (bucket ?? 'eco-eth-private') : bucket,
  file_count: results.length,
  snapshot_sha256: manifest.snapshot.canonical_sha256,
  objects: results,
}, null, 2));
