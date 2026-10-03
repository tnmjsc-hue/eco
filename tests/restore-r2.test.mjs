import test from 'node:test';
import assert from 'node:assert/strict';
import { mkdtemp, mkdir, readFile, writeFile } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { createHash } from 'node:crypto';
import { restoreSnapshot } from '../scripts/restore-private-snapshot-r2.mjs';
const sha=bytes=>createHash('sha256').update(bytes).digest('hex');
const env={R2_ACCOUNT_ID:'a'.repeat(32),R2_BUCKET:'eco-eth-private',R2_ACCESS_KEY_ID:'fixture-id',R2_SECRET_ACCESS_KEY:'fixture-secret'};
async function fixture(edit=m=>m) {
  const root=await mkdtemp(join(tmpdir(),'eco-r2-restore-')),prefix='raw/coinmetrics/coinmetrics-fixture';
  const canonical=Buffer.from('{"asset":"eth"}\n'),page=Buffer.from('{"data":[]}\n');
  const manifest=edit({status:'complete',provider:'coinmetrics_community_api',asset:'eth',frequency:'1d',snapshot:{canonical_file:'canonical.jsonl',canonical_sha256:sha(canonical)},pages:[{raw_file:'page-0001.json',response_sha256:sha(page)}]});
  const objects=new Map([['manifest.json',Buffer.from(JSON.stringify(manifest))],['canonical.jsonl',canonical],['page-0001.json',page]]),requests=[];
  const fetcher=async(url,options)=>{
    requests.push({url,options});const name=url.split('/').at(-1),bytes=objects.get(name);
    return new Response(bytes??'',{status:bytes?200:404});
  };
  return {root,prefix,expectedHash:sha(canonical),objects,requests,fetcher};
}
test('private restore issues GET only, verifies every checksum and is idempotent',async()=>{
  const f=await fixture();const options={root:f.root,env,fetcher:f.fetcher};
  const result=await restoreSnapshot(f.prefix,f.expectedHash,options);
  assert.equal(result.file_count,3);assert.equal(result.remote_write_operations,0);assert.ok(result.objects.every(o=>o.readback_verified));
  assert.ok(f.requests.every(r=>r.options.method==='GET' && !r.url.includes('fixture-secret') && !r.url.includes('fixture-id') && !new URL(r.url).search));
  assert.ok(f.requests.every(r=>r.options.headers.authorization.startsWith('AWS4-HMAC-SHA256 Credential=fixture-id/')));
  assert.equal((await readFile(join(result.snapshot_directory,'canonical.jsonl'))).toString(),f.objects.get('canonical.jsonl').toString());
  assert.deepEqual(await restoreSnapshot(f.prefix,f.expectedHash,options),result);
});
test('wrong ETH snapshot or checksum cannot be restored',async()=>{
  for(const edit of [m=>({...m,asset:'btc'}),m=>({...m,status:'partial'}),m=>({...m,snapshot:{...m.snapshot,canonical_sha256:'0'.repeat(64)}})]) {
    const f=await fixture(edit);await assert.rejects(restoreSnapshot(f.prefix,f.expectedHash,{root:f.root,env,fetcher:f.fetcher}),/pinned ETH snapshot/);
  }
  const f=await fixture();f.objects.set('canonical.jsonl',Buffer.from('changed'));
  await assert.rejects(restoreSnapshot(f.prefix,f.expectedHash,{root:f.root,env,fetcher:f.fetcher}),/checksum/);
});
test('unsafe prefixes, filenames and reserved manifest pages are rejected',async()=>{
  const f=await fixture();const options={root:f.root,env,fetcher:f.fetcher};
  for(const prefix of ['../outside','raw/coinmetrics/coinmetrics-../x','raw/coinmetrics/coinmetrics-test/../../outside']) {
    await assert.rejects(restoreSnapshot(prefix,f.expectedHash,options),/identity/);
  }
  for(const name of ['../page.json','manifest.json','community-catalog.json']) {
    const f=await fixture(m=>({...m,pages:[{raw_file:name,response_sha256:'a'.repeat(64)}]}));
    await assert.rejects(restoreSnapshot(f.prefix,f.expectedHash,{root:f.root,env,fetcher:f.fetcher}),/filename/);
  }
});
test('existing snapshot objects cannot be overwritten and unknown local files remain intact',async()=>{
  const f=await fixture();const directory=join(f.root,'data/raw/coinmetrics/coinmetrics-fixture');await mkdir(directory,{recursive:true});
  await writeFile(join(directory,'canonical.jsonl'),'immutable old bytes');
  await assert.rejects(restoreSnapshot(f.prefix,f.expectedHash,{root:f.root,env,fetcher:f.fetcher}),/immutable/);
  assert.equal(await readFile(join(directory,'canonical.jsonl'),'utf8'),'immutable old bytes');
  await writeFile(join(directory,'unrelated.txt'),'preserve');
  await assert.rejects(restoreSnapshot(f.prefix,f.expectedHash,{root:f.root,env,fetcher:f.fetcher}),/unexpected files/);
  assert.equal(await readFile(join(directory,'unrelated.txt'),'utf8'),'preserve');
});
test('failed readback does not echo credentials or a signed URL',async()=>{
  const f=await fixture();await assert.rejects(restoreSnapshot(f.prefix,f.expectedHash,{root:f.root,env,fetcher:async()=>new Response('',{status:403})}),error=>{
    assert.match(error.message,/HTTP 403/);assert.ok(!error.message.includes('fixture-id'));assert.ok(!error.message.includes('fixture-secret'));assert.ok(!error.message.includes('http'));return true;
  });
});
