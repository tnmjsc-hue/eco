import test from 'node:test';
import assert from 'node:assert/strict';
import { readFile, mkdtemp, rm } from 'node:fs/promises';
import { createHash } from 'node:crypto';
import { join } from 'node:path';
import { tmpdir } from 'node:os';
import { PROXIES, validateProxyPointer, validateProxyRelease, exportProxyCSV } from '../public/proxy-model.js';
import { PROXY_METRICS, assertCommunityCatalog, backfillProxies } from '../scripts/proxy-coinmetrics.mjs';
const hash=b=>createHash('sha256').update(b).digest('hex');

test('proxy adapter requires available ETH Community daily fields and retains source flags',async t=>{
  const catalog={data:[{asset:'eth',metrics:PROXY_METRICS.map(metric=>({metric,frequencies:[{frequency:'1d',community:true}]}))}]};
  assertCommunityCatalog(catalog);
  assert.throws(()=>assertCommunityCatalog({data:[]}),/Community/);
  const pro=structuredClone(catalog);pro.data[0].metrics[0].frequencies[0].community=false;
  assert.throws(()=>assertCommunityCatalog(pro),/Community/);
  const temp=await mkdtemp(join(tmpdir(),'eth-proxies-'));t.after(()=>rm(temp,{recursive:true,force:true}));
  const now=()=>new Date('2015-07-31T01:00:00Z');
  const request=async url=>{
    const payload=url.pathname.includes('catalog')?catalog:{data:[{asset:'eth',time:'2015-07-30T00:00:00Z',
      ...Object.fromEntries(PROXY_METRICS.map(m=>[m,m==='CapMrktCurUSD'?null:'1'])),
      'SplyExNtv-status':'flash','SplyExNtv-status-time':'2015-07-31T00:00:00Z'}]};
    return {body:JSON.stringify(payload),payload,status:200,headers:{},requestedAt:now().toISOString(),completedAt:now().toISOString()};
  };
  const folder=await backfillProxies('2015-07-31',{outputRoot:temp,request,now});
  const row=JSON.parse((await readFile(join(folder,'canonical.jsonl'),'utf8')).trim());
  assert.equal(row.metric_status.SplyExNtv.status,'flash');assert.equal(row.metrics.CapMrktCurUSD,null);
  const manifest=JSON.parse(await readFile(join(folder,'manifest.json')));
  assert.equal(manifest.community_catalog.sha256,hash(await readFile(join(folder,'community-catalog.json'))));
  assert.deepEqual(manifest.metrics,PROXY_METRICS);assert.equal(manifest.authorization,'none');
});

test('real public proxy release checksums, formulas, coverage, nulls and CSV',async()=>{
  const root=new URL('../public/data/network-proxies/',import.meta.url);
  const pointer=JSON.parse(await readFile(new URL('latest.json',root)));validateProxyPointer(pointer);
  const base=new URL(`releases/${pointer.release_id}/`,root);
  const bytes=await readFile(new URL('manifest.json',base));assert.equal(hash(bytes),pointer.manifest_sha256);
  const manifest=JSON.parse(bytes);const data={};
  for(const n of ['history.json','research.json']) {const b=await readFile(new URL(n,base));assert.equal(hash(b),manifest.files[n]);data[n]=JSON.parse(b);}
  validateProxyRelease(data['history.json'],manifest,data['research.json']);
  assert.equal(PROXIES.length,3);assert.equal(data['history.json'].rows[0].metrics.exchange_share.score,null);
  const csv=exportProxyCSV(data['history.json'].rows.slice(-366),manifest);
  assert.ok(csv.includes('CC BY-NC 4.0'));assert.ok(csv.includes('value_per_transfer_score'));
  assert.equal(csv.trim().split('\n').length,369);
  const fake=structuredClone(data['history.json']);fake.rows[0].metrics.exchange_share.score=50;
  assert.throws(()=>validateProxyRelease(fake,manifest,data['research.json']),/không hợp lệ/);
  const renamed=structuredClone(manifest);renamed.metric_definitions.value_per_transfer.formula='NVTAdj90';
  assert.throws(()=>validateProxyRelease(data['history.json'],renamed,data['research.json']),/Công thức/);
  const gap=structuredClone(data['history.json']);gap.rows[100].date=gap.rows[101].date;
  assert.throws(()=>validateProxyRelease(gap,manifest,data['research.json']),/thiếu ngày/);
  const path=structuredClone(pointer);path.manifest_url='https://other.test/raw.json';assert.throws(()=>validateProxyPointer(path));
});
