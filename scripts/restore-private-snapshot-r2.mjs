import { createHash, createHmac } from 'node:crypto';
import { readFile, writeFile, mkdir, readdir, lstat } from 'node:fs/promises';
import { resolve, relative, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const repository = fileURLToPath(new URL('../', import.meta.url));
const hash = bytes => createHash('sha256').update(bytes).digest('hex');
const awsEncode = value => encodeURIComponent(value).replace(/[!'()*]/g, c=>`%${c.charCodeAt(0).toString(16).toUpperCase()}`);
const hmac = (key, value) => createHmac('sha256',key).update(value).digest();

export async function restoreSnapshot(prefix, expectedHash, { root=repository, env=process.env, fetcher=fetch }={}) {
  if (!/^raw\/coinmetrics\/coinmetrics-[A-Za-z0-9_-]+$/.test(prefix) || !/^[a-f0-9]{64}$/.test(expectedHash)) throw new Error('Invalid private snapshot identity.');
  const account=env.R2_ACCOUNT_ID, bucket=env.R2_BUCKET, access=env.R2_ACCESS_KEY_ID, secret=env.R2_SECRET_ACCESS_KEY;
  if (!/^[a-f0-9]{32}$/i.test(account??'') || bucket!=='eco-eth-private' || !access || !secret) throw new Error('Existing private bucket credentials are required in the process environment.');
  const rawRoot=resolve(root,'data/raw/coinmetrics'), directory=resolve(rawRoot,prefix.split('/').at(-1));
  if (relative(rawRoot,directory).startsWith('..') || !relative(rawRoot,directory)) throw new Error('Restore target must stay inside private raw storage.');
  for (const location of [resolve(root,'data'),resolve(root,'data/raw'),rawRoot,directory]) {
    try { if ((await lstat(location)).isSymbolicLink()) throw new Error('Symbolic links are not allowed in private restore paths.'); }
    catch (error) { if (error.code!=='ENOENT') throw error; }
  }
  async function get(key) {
    const stamp=new Date().toISOString().replace(/[:-]|\.\d{3}/g,''), day=stamp.slice(0,8), payload=hash(Buffer.alloc(0));
    const host=`${account}.r2.cloudflarestorage.com`, uri=`/${awsEncode(bucket)}/${key.split('/').map(awsEncode).join('/')}`;
    const headers=`host:${host}\nx-amz-content-sha256:${payload}\nx-amz-date:${stamp}\n`, signed='host;x-amz-content-sha256;x-amz-date';
    const canonical=`GET\n${uri}\n\n${headers}\n${signed}\n${payload}`, scope=`${day}/auto/s3/aws4_request`;
    const signing=hmac(hmac(hmac(hmac('AWS4'+secret,day),'auto'),'s3'),'aws4_request');
    const signature=createHmac('sha256',signing).update(`AWS4-HMAC-SHA256\n${stamp}\n${scope}\n${hash(canonical)}`).digest('hex');
    const response=await fetcher(`https://${host}${uri}`,{method:'GET',signal:AbortSignal.timeout(30000),headers:{authorization:`AWS4-HMAC-SHA256 Credential=${access}/${scope}, SignedHeaders=${signed}, Signature=${signature}`,'x-amz-date':stamp,'x-amz-content-sha256':payload}});
    if (!response.ok) { await response.body?.cancel(); throw new Error(`Private snapshot readback failed (HTTP ${response.status}).`); }
    const bytes=Buffer.from(await response.arrayBuffer());
    if (bytes.length>64*1024*1024) throw new Error('Private snapshot object exceeds restore limit.');
    return bytes;
  }
  const manifestBytes=await get(prefix+'/manifest.json'), manifest=JSON.parse(manifestBytes.toString('utf8'));
  if (manifest.status!=='complete' || manifest.provider!=='coinmetrics_community_api' || manifest.asset!=='eth' || manifest.frequency!=='1d' || manifest.snapshot?.canonical_sha256!==expectedHash || manifest.snapshot.canonical_file!=='canonical.jsonl') throw new Error('Private manifest does not match the pinned ETH snapshot.');
  if (!Array.isArray(manifest.pages) || !manifest.pages.length || manifest.pages.length>64) throw new Error('Invalid private snapshot page list.');
  const expected=new Map([['canonical.jsonl',expectedHash]]);
  for (const page of manifest.pages) {
    if (!/^[A-Za-z0-9_-]+\.json$/.test(page.raw_file) || ['manifest.json','community-catalog.json'].includes(page.raw_file)
        || !/^[a-f0-9]{64}$/.test(page.response_sha256) || expected.has(page.raw_file)) throw new Error('Unsafe or duplicate raw object filename.');
    expected.set(page.raw_file,page.response_sha256);
  }
  if (manifest.community_catalog) {
    if (manifest.community_catalog.file!=='community-catalog.json' || !/^[a-f0-9]{64}$/.test(manifest.community_catalog.sha256)) throw new Error('Invalid Community catalogue identity.');
    expected.set('community-catalog.json',manifest.community_catalog.sha256);
  }
  expected.set('manifest.json',hash(manifestBytes));
  await mkdir(directory,{recursive:true});
  const existing=await readdir(directory);
  if (existing.some(name=>!expected.has(name))) throw new Error('Restore directory contains unexpected files; no files were removed.');
  const objects=[];
  for (const [name,checksum] of expected) {
    const bytes=name==='manifest.json'?manifestBytes:await get(prefix+'/'+name);
    if (hash(bytes)!==checksum) throw new Error('Private object readback checksum mismatch.');
    const destination=join(directory,name);
    try {
      if (!(await lstat(destination)).isFile() || (await lstat(destination)).isSymbolicLink()) throw new Error('Unsafe local snapshot object.');
      if (hash(await readFile(destination))!==checksum) throw new Error('Existing private snapshot object is immutable.');
    } catch(error) { if (error.code!=='ENOENT') throw error; await writeFile(destination,bytes,{flag:'wx'}); }
    objects.push({object_key:prefix+'/'+name,bytes:bytes.length,sha256:checksum,readback_verified:true});
  }
  return {status:'restored_private_snapshot',operation:'readback_existing_objects',bucket,file_count:objects.length,snapshot_sha256:expectedHash,snapshot_directory:directory,remote_write_operations:0,objects};
}

if (process.argv[1] && resolve(process.argv[1])===fileURLToPath(import.meta.url)) {
  try {
    const [prefix,hashValue,...extra]=process.argv.slice(2);
    if (extra.length) throw new Error('Usage: restore-private-snapshot-r2.mjs <raw/coinmetrics/run-id> <canonical-sha256>');
    console.log(JSON.stringify(await restoreSnapshot(prefix,hashValue)));
  } catch(error) { console.error(error.message); process.exitCode=1; }
}
