import test from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import {loadAssessment,verifiedAsset,METRICS} from '../public/macro-model.js';
const fetchLocal=async url=>new Response(await readFile(`public${url}`),{status:200});

test('published macro verifies assessment, manifest, parent and all input hashes',async()=>{
  const result=await loadAssessment(fetchLocal);const a=result.assessment;
  assert.equal(a.ruleset_version,'macro-cross-v1.0.1');assert.equal(a.signals.length,10);
  assert.ok(a.signals.every(s=>METRICS[s.metric_id]));assert.equal(a.surprise.status,'unavailable');
  assert.equal(a.market_confirmation.status,'not_measured');assert.equal(a.history_mode,'latest_vintage_context');
  assert.equal(a.calendar_release_id,result.calendar.release_id);
});
test('corrupt or truncated asset and unsafe paths fail verification',async()=>{
  const p=JSON.parse(await readFile('public/data/macro-assessment/latest.json'));
  await assert.rejects(verifiedAsset({...p,sha256:'0'.repeat(64)},fetchLocal),/Checksum/);
  await assert.rejects(verifiedAsset({...p,url:'/data/../secret.json'},fetchLocal));
  await assert.rejects(loadAssessment(async url=>url.endsWith('/assessment.json')?new Response('{'):fetchLocal(url)),/Checksum/);
});
test('calendar parent mismatch and unsupported ruleset reject the whole assessment',async()=>{
  const mutatePointer=mutate=>async url=>{if(url==='/data/macro-assessment/latest.json'){const p=JSON.parse(await readFile(`public${url}`));mutate(p);return Response.json(p);}return fetchLocal(url);};
  await assert.rejects(loadAssessment(mutatePointer(p=>p.calendar_release_id='calendar-'+'0'.repeat(20))));
  await assert.rejects(loadAssessment(mutatePointer(p=>p.ruleset_version='macro-cross-v9')));
});
test('actual table stays neutral and hypothetical consensus templates are absent',async()=>{
  const html=await readFile('public/index.html','utf8'),js=await readFile('public/calendar.js','utf8');
  assert.ok(!js.includes('usdReferenceBias'));assert.ok(!html.includes('cal-scenarios'));assert.ok(!html.includes('USD bull'));
  for(const id of ['macro-latest-rows','macro-peers','macro-axes','macro-assets','macro-manifest'])assert.ok(html.includes(`id="${id}"`));
});
