import test from 'node:test';
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { createHash } from 'node:crypto';
import { CORE_METRICS, CORE_VERSION, CORE_PROTOCOL_HASH, CORE_GROUPS, NEW_FEATURES, coreScore, validateCorePointer, validateCore, validateCoreParents, exportCoreCSV } from '../public/core-model.js';
const hash=b=>createHash('sha256').update(b).digest('hex');
const read=async path=>JSON.parse(await readFile('public'+path,'utf8'));
const pointer=await read('/data/core-v2/latest.json'), manifest=await read(pointer.manifest_url);
const base=pointer.manifest_url.replace('manifest.json','');
const history=await read(base+'history.json'), research=await read(base+'research.json');
const parents=Object.fromEntries(await Promise.all(Object.entries(manifest.parents).map(async ([kind,ref])=>[kind,await read(ref.manifest_url)])));

test('Core 10 frozen protocol, all hashes and original information-family budgets', async()=>{
  const config=JSON.parse(await readFile('configs/research/core-v0.2.0.json','utf8'));
  assert.equal(hash(Buffer.from(JSON.stringify(config)+'\n')),CORE_PROTOCOL_HASH);
  validateCorePointer(pointer); validateCore(history,manifest,research); validateCoreParents(manifest,parents);
  assert.equal(hash(await readFile('public'+pointer.manifest_url)),pointer.manifest_sha256);
  for(const [name,sha] of Object.entries(manifest.files)) assert.equal(hash(await readFile('public'+base+name)),sha);
  assert.deepEqual(config.groups,CORE_GROUPS); assert.deepEqual(config.new_features,NEW_FEATURES);
  assert.equal(CORE_METRICS.reduce((s,m)=>s+m.weight,0),1);
  assert.equal(CORE_METRICS.filter(m=>['E7','E2'].includes(m.id)).reduce((s,m)=>s+m.weight,0),.375);
  assert.equal(CORE_METRICS.filter(m=>['exchange_share','exchange_balance_pressure'].includes(m.id)).reduce((s,m)=>s+m.weight,0),.0625);
  assert.equal(manifest.last_valid_score,coreScore(history.rows.at(-1)));
  assert.ok(Math.abs(research.comparisons.core.ap_delta-(research.statistics.core_ten.average_precision-research.statistics.core.average_precision))<1e-12);
});

test('Every legacy point and raw input stays equal to pinned parents; independent causal quantile boundary checks',async()=>{
  const legacy=await read(manifest.parents.extended.manifest_url.replace('manifest.json','history.json'));
  const raw=await read(manifest.parents.diagnostics.manifest_url.replace('manifest.json','history.json'));
  const byDate=new Map(raw.rows.map(r=>[r.date,r]));
  for(let i=0;i<history.rows.length;i++) {
    const r=history.rows[i], old=legacy.rows[i];
    assert.equal(r.core_score,old.core_score); assert.equal(r.extended_score,old.score);
    for(const [id,spec] of Object.entries(NEW_FEATURES)) {
      assert.equal(r.new_features[id].input_value,byDate.get(r.date).metrics[spec.input].value);
      assert.deepEqual(r.source_flags[id],byDate.get(r.date).metrics[spec.input].source_flags);
    }
  }
  const days=['2015-08-01','2016-08-07','2016-08-28','2018-08-07','2021-08-05','2022-09-15','2024-03-13',history.rows.at(-1).date];
  const q=(sorted,p)=>{const h=(sorted.length-1)*p,lo=Math.floor(h);return sorted[lo]+(sorted[Math.ceil(h)]-sorted[lo])*(h-lo);};
  for(const day of days) for(const [id,spec] of Object.entries(NEW_FEATURES)) {
    const cutoff=Date.parse(day)-1460*86400000;
    const past=raw.rows.filter(r=>r.date<day && Date.parse(r.date)>=cutoff).map(r=>r.metrics[spec.input].value).filter(v=>v!==null).map(v=>spec.sign*v).sort((a,b)=>a-b);
    const f=history.rows.find(r=>r.date===day).new_features[id];
    assert.equal(f.history_count,past.length);
    if(past.length>=365) {assert.ok(Math.abs(f.lower-q(past,.05))<1e-8); assert.ok(Math.abs(f.upper-q(past,.95))<1e-8);}
    else assert.equal(f.score,null);
  }
});

test('Malformed weights, methodology, feature units/signed raw and lineage are rejected',()=>{
  for(const mutate of [m=>m.weights.E2=.2,m=>m.groups.valuation.weight=.5,m=>m.research_only=false,m=>m.source_available_at='2015-08-01',m=>m.new_features.supply_scarcity.sign=1]) {
    const m=structuredClone(manifest);mutate(m);assert.throws(()=>validateCore(history,m,research));
  }
  for(const mutate of [r=>r.components.E2=true,r=>r.new_features.E2.input_unit='USD',r=>r.new_features.supply_scarcity.raw=-1,r=>r.coverage=9,r=>r.extended_score=50]) {
    const h=structuredClone(history);mutate(h.rows.at(-1));assert.throws(()=>validateCore(h,manifest,research));
  }
  const p=structuredClone(parents);p.diagnostics.parents.core.history_sha256='0'.repeat(64);
  assert.throws(()=>validateCoreParents(manifest,p));
  const r=structuredClone(research);r.decision='validated_predictive_model';assert.throws(()=>validateCore(history,manifest,r));
  assert.throws(()=>validateCorePointer({...pointer,manifest_url:'/data/extended/latest.json'}));
});

test('CSV includes all ten scores, signed units and lineage; empty/missing custom selection stays null',()=>{
  const row=history.rows.at(-1);
  assert.equal(coreScore(row,[]),null);assert.equal(coreScore(row,['E2','E2']),null);
  assert.equal(coreScore(row,['E2']),row.components.E2);assert.equal(coreScore(history.rows[0]),null);
  const csv=exportCoreCSV([row],['E2','supply_scarcity'],'custom',manifest);
  for(const term of [CORE_VERSION,'CC BY-NC 4.0','core_ten_score','extended_score','core_four_score','E2_input_value','supply_scarcity_input_unit','exchange_balance_pressure_oriented_raw',String(row.new_features.exchange_balance_pressure.input_value),manifest.parents.diagnostics.release_id]) assert.ok(csv.includes(term),term);
  assert.equal(csv.split('\r\n').length,2);
});
