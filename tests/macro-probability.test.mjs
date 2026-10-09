import test from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import {loadProbability,probabilityAsset,validateProbability} from '../public/macro-probability-model.js';
const local=async url=>new Response(await readFile(`public${url}`));
test('real prospective model pins parents and withholds uncalibrated probabilities',async()=>{
  const r=await loadProbability(local);
  assert.equal(r.data.asset,'eth');assert.equal(r.data.horizon_days,7);
  assert.equal(r.data.consensus,'not_market_consensus');
  if(r.data.evaluation.state!=='validated_holdout')assert.equal(r.data.evaluation.probabilities,null);
  assert.ok(r.data.cases_count>=1);
  if(r.data.latest_case.model_state!=='validated_holdout')assert.equal(r.data.latest_case.probabilities,null);
});
test('tampered full parents, inputs and unsafe paths fail closed',async()=>{
  const p=JSON.parse(await readFile('public/data/macro-probability/latest.json'));
  await assert.rejects(probabilityAsset({...p,url:'/data/../secret.json'},local));
  for(const suffix of ['/report.json','/inputs.json','/history.json','/assessment.json','/protocol.json','/calendar.json']){
    await assert.rejects(loadProbability(url=>url.endsWith(suffix)?new Response('{}'):local(url)),/Checksum|checksum/);
  }
});
test('no percentage, wrong horizon, future case or false gate can pass validation',async()=>{
  const r=await loadProbability(local),inputs=await probabilityAsset(r.manifest.inputs,local),protocol=await probabilityAsset(r.manifest.protocol,local);
  for(const mutation of [d=>d.horizon_days=1,d=>d.asset='btc',d=>d.evaluation.probabilities={down:'0.5',flat:'0.25',up:'0.25'},d=>d.evaluation.state='validated_holdout',d=>d.latest_case.issued_at='2099-01-01T00:00:00Z',d=>d.cases_count=999,d=>d.latest_case.end_date=d.latest_case.base_date]){
    const d=structuredClone(r.data);mutation(d);assert.throws(()=>validateProbability(d,inputs,protocol,r.status));
  }
});
