import test from 'node:test';
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { createHash } from 'node:crypto';
import { EXTENDED_METRICS, extendedScore, validateExtendedPointer, validateExtended, exportExtendedCSV } from '../public/extended-model.js';
const sha = b=>createHash('sha256').update(b).digest('hex');
const pointer = JSON.parse(await readFile('public/data/extended/latest.json'));
const base = `public/data/extended/releases/${pointer.release_id}/`;
const mb = await readFile(base+'manifest.json'), manifest = JSON.parse(mb);
const hb = await readFile(base+'history.json'), history = JSON.parse(hb);
const rb = await readFile(base+'research.json'), research = JSON.parse(rb);
test('seven-component release hashes, frozen weights and parent lineage', async()=>{
  validateExtendedPointer(pointer); validateExtended(history,manifest,research);
  assert.equal(sha(mb),pointer.manifest_sha256);
  assert.equal(sha(hb),manifest.files['history.json']); assert.equal(sha(rb),manifest.files['research.json']);
  for (const p of Object.values(manifest.parents)) {
    const bytes = await readFile('public'+p.manifest_url), m = JSON.parse(bytes);
    assert.equal(sha(bytes),p.manifest_sha256); assert.equal(m.files['history.json'],p.history_sha256);
  }
  assert.equal(EXTENDED_METRICS.length,7);
  const last = history.rows.at(-1);
  assert.equal(last.coverage,7); assert.equal(last.components.exchange_share,0);
  assert.ok(Math.abs(last.score-(.75*last.core_score+.25*(last.components.exchange_share+last.components.address_activity+last.components.value_per_transfer)/3))<1e-10);
  assert.equal(Object.keys(research.ablation).length,7);
  assert.equal(research.comparisons.core.valid_replicates,10000);
});
test('seven-component custom preserves null, weights and zero',()=>{
  const row = {components:Object.fromEntries(EXTENDED_METRICS.map(m=>[m.id,0]))};
  assert.equal(extendedScore(row),0); assert.equal(extendedScore(row,[]),null);
  assert.equal(extendedScore(row,['E7','E7']),null); assert.equal(extendedScore(row,['E2']),null);
  row.components.address_activity=null; assert.equal(extendedScore(row),null);
  row.components.E7=100; assert.equal(extendedScore(row,['E1','E7']),75);
});
test('tampered score, coverage, protocol, flags and unknown parent rejected',()=>{
  for (const change of [h=>h.rows.at(-1).score=99,h=>h.rows.at(-1).components.exchange_share=null,
    h=>h.weights.E7=.5,h=>h.rows.at(-1).source_flags.exchange_share=[3],h=>h.rows.pop()]) {
    const bad = structuredClone(history); change(bad); assert.throws(()=>validateExtended(bad,manifest,research));
  }
  const bad = structuredClone(manifest); bad.parents.core.manifest_url='/data/raw/source.json';
  assert.throws(()=>validateExtended(history,bad,research));
});
test('CSV includes all seven scores, missing reasons, flags and parent hashes context',()=>{
  const csv = exportExtendedCSV([history.rows[0],history.rows.at(-1)],['E7'],'custom',manifest);
  for (const text of ['exchange_share','address_activity','value_per_transfer','flash','core_score','extended_score',manifest.parents.core.release_id,'CC BY-NC 4.0','reconstructed']) assert.ok(csv.includes(text));
  assert.ok(!csv.includes('NaN')); assert.equal(csv.split('\r\n').length,3);
});
