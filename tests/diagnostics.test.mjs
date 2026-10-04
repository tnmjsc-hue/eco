import test from 'node:test';
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { createHash } from 'node:crypto';
import { DIAGNOSTICS, validateDiagnosticPointer, validateDiagnosticRelease, diagnosticRange, exportDiagnosticCSV } from '../public/diagnostic-model.js';
const sha=b=>createHash('sha256').update(b).digest('hex');
const pointer=JSON.parse(await readFile('public/data/diagnostics/latest.json'));
const base=`public/data/diagnostics/releases/${pointer.release_id}/`;
const mb=await readFile(base+'manifest.json'),manifest=JSON.parse(mb);
const hb=await readFile(base+'history.json'),history=JSON.parse(hb);
const rb=await readFile(base+'research.json'),research=JSON.parse(rb);
test('diagnostic release hashes, ETH units, frozen definitions and exact parent lineage',async()=>{
  validateDiagnosticPointer(pointer);validateDiagnosticRelease(history,manifest,research);
  assert.equal(sha(mb),pointer.manifest_sha256);assert.equal(sha(hb),manifest.files['history.json']);assert.equal(sha(rb),manifest.files['research.json']);
  assert.equal(manifest.role,'raw_diagnostics_only');assert.equal(manifest.composite_score,null);
  for(const [kind,p] of Object.entries(manifest.parents)) {
    const bytes=await readFile('public'+p.manifest_url),m=JSON.parse(bytes);
    assert.equal(sha(bytes),p.manifest_sha256);assert.equal(m.files['history.json'],p.history_sha256);
    assert.equal(m.snapshot_sha256,manifest.private_inputs_verified[kind].canonical_sha256);
  }
  assert.deepEqual(DIAGNOSTICS.map(d=>d.unit),['ratio','percent','ETH']);
  assert.ok(history.rows.some(r=>r.metrics.nupl_diagnostic.value<0));
  assert.ok(history.rows.some(r=>r.metrics.supply_change_30d.value<0));
  assert.ok(history.rows.some(r=>r.metrics.exchange_balance_change_30d.value<0));
  assert.ok(history.rows.at(-1).metrics.exchange_balance_change_30d.source_flags.includes('flash'));
});
test('raw contract rejects path injection, scores, misleading forecast claims, units and null replacement',()=>{
  for(const bad of [{...pointer,release_id:'../../raw'},{...pointer,manifest_url:'https://example.com/raw'},{...pointer,methodology_version:'core-v0.1.0'}]) assert.throws(()=>validateDiagnosticPointer(bad));
  const mutations=[
    (h,m)=>m.normalizer={window:365},(h,m)=>m.composite_score=50,(h,m,r)=>r.predictive_utility_claim=true,
    (h,m)=>h.metric_definitions.nupl_diagnostic.independent_vote=true,(h,m)=>h.metric_definitions.supply_change_30d.window_days=30,
    h=>h.rows[0].metrics.supply_change_30d.value=0,h=>h.rows[0].metrics.supply_change_30d.unit='ratio',
    h=>h.rows[0].metrics.nupl_diagnostic.value=NaN,h=>h.rows[0].metrics.nupl_diagnostic.value=1,
    h=>h.rows[1].date=h.rows[0].date,h=>h.rows[0].metrics.exchange_balance_change_30d.source_flags=['flash','flash'],
    (h,m,r)=>r.coverage.nupl_diagnostic.negative_rows=0,(h,m)=>m.private_inputs_verified.core.objects_readback_verified=false
  ];
  for(const mutate of mutations) {
    const [h,m,r]=structuredClone([history,manifest,research]);mutate(h,m,r);assert.throws(()=>validateDiagnosticRelease(h,m,r));
  }
});
test('inclusive calendar ranges and raw CSV preserve values, units, null reasons, flags and snapshot lineage',()=>{
  const rows=diagnosticRange(history.rows,'1y');assert.equal(rows.length,366);
  const start=history.rows[0].date,end=history.rows[3].date;
  assert.equal(diagnosticRange(history.rows,'custom',start,end).length,4);
  assert.throws(()=>diagnosticRange(history.rows,'custom',end,start));
  assert.throws(()=>diagnosticRange(history.rows,'custom','2015-02-31',end));
  const csv=exportDiagnosticCSV(rows,manifest),lines=csv.trim().split('\n');
  assert.equal(lines.length,369);assert.match(csv,/CC BY-NC 4.0/);assert.match(lines[2],/nupl_diagnostic_unit/);
  assert.match(csv,/"ratio"/);assert.match(csv,/"percent"/);assert.match(csv,/"ETH"/);assert.match(csv,/"flash"/);
  const lastValid=rows.findLast(r=>r.metrics.exchange_balance_change_30d.value!==null);
  assert.ok(csv.includes(String(lastValid.metrics.exchange_balance_change_30d.value)));
  assert.ok(csv.includes(manifest.private_inputs_verified.core.canonical_sha256));
  const warmup=exportDiagnosticCSV(history.rows.slice(0,1),manifest);assert.match(warmup,/"","percent","window_warmup"/);
  assert.doesNotMatch(lines[2],/score|probability/);
  const pending=structuredClone(rows.at(-1));
  Object.assign(pending.metrics.exchange_balance_change_30d,{value:null,reason:'parent_date_unavailable'});
  assert.match(exportDiagnosticCSV([pending],manifest),/"","ETH","parent_date_unavailable"/);
});
