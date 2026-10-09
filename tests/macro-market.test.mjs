import test from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import {loadMarket,marketAsset,validateMarket} from '../public/macro-market-model.js';
const local=async url=>new Response(await readFile(`public${url}`));
test('market publication verifies source inputs, protocol, backup and ETH parent',async()=>{
  const result=await loadMarket(local);
  assert.equal(result.data.metrics.length,6);
  assert.equal(result.data.consensus.status,'unavailable');
  assert.equal(result.data.event_reaction.status,'not_measured');
  assert.equal(result.data.comparison_basis,'daily_change');
  assert.equal(result.data.metrics.find(m=>m.metric_id==='gold_usd').latest,null);
});
test('unsafe paths and corrupt market or full ETH parent fail verification',async()=>{
  const p=JSON.parse(await readFile('public/data/macro-market/latest.json'));
  await assert.rejects(marketAsset({...p,url:'/data/../secret.json'},local));
  await assert.rejects(marketAsset({...p,sha256:'0'.repeat(64)},local),/Checksum/);
  for(const path of ['/market.json','/history.json','/inputs.json','/protocol.json']){
    await assert.rejects(loadMarket(async url=>url.endsWith(path)?new Response('{}'):local(url)),/Checksum/);
  }
});
test('wrong units, bps, future retrieval, date, enum or consensus cannot be relabeled',async()=>{
  const good=await loadMarket(local);
  const inputs=await marketAsset(good.manifest.inputs,local),protocol=await marketAsset(good.manifest.protocol,local);
  for(const mutate of [m=>m.change='10000',m=>m.unit='USD',m=>m.status='confirmed',m=>m.latest_date='2026-02-30',m=>m.latest_date='2099-01-01',m=>m.source.retrieved_at='2099-01-01T00:00:00Z',m=>m.source.usable_at='2099-01-01T00:00:00Z']){
    const bad=structuredClone(good.data);mutate(bad.metrics[0]);const bundle=structuredClone(inputs);bundle.metrics=bad.metrics;
    assert.throws(()=>validateMarket(bad,bundle,protocol,good.status));
  }
  for(const key of ['consensus','event_reaction']){
    const bad=structuredClone(good.data);bad[key].status='measured';
    assert.throws(()=>validateMarket(bad,inputs,protocol,good.status));
  }
});
