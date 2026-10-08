import test from 'node:test';
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { createHash } from 'node:crypto';
import { dayInZone, selectEvents, validateCalendar } from '../public/calendar-model.js';

test('calendar timezone dates cover Vietnam rollover and New York DST',()=>{
  assert.equal(dayInZone('2026-10-28T18:00:00Z','Asia/Ho_Chi_Minh'),'2026-10-29');
  assert.equal(dayInZone('2026-10-28T18:00:00Z','America/New_York'),'2026-10-28');
  const events=[{scheduled_at:'2026-10-28T18:00:00Z',impact:'high',title:'FOMC',source_title:'FOMC',provider:'fed'}];
  assert.equal(selectEvents(events,{start:'2026-10-29',end:'2026-10-29',zone:'Asia/Ho_Chi_Minh',impact:'high',search:'fomc'}).length,1);
  assert.equal(selectEvents(events,{start:'2026-10-28',end:'2026-10-28',zone:'Asia/Ho_Chi_Minh'}).length,0);
  assert.equal(selectEvents(events,{start:'2026-10-29',end:'2026-10-29',zone:'Asia/Ho_Chi_Minh',impact:'medium'}).length,0);
});

test('public calendar hash, provenance and missing consensus contract',async()=>{
  const pointer=JSON.parse(await readFile('public/data/calendar/latest.json'));
  const bytes=await readFile(`public${pointer.url}`);
  assert.equal(createHash('sha256').update(bytes).digest('hex'),pointer.sha256);
  const data=validateCalendar(JSON.parse(bytes));
  assert.equal(data.release_id,pointer.release_id);
  assert.ok(data.private_backup.objects.every(o=>o.readback_verified));
  assert.deepEqual(new Set(data.events.map(e=>e.provider)),new Set(['bls','bea','fed']));
  assert.ok(data.events.every(e=>e.forecast===null&&e.actual===null));
  const bad=structuredClone(data);bad.events[0].source_url='https://evil.example/';
  assert.throws(()=>validateCalendar(bad));
  const duplicate=structuredClone(data);duplicate.events.push(duplicate.events[0]);assert.throws(()=>validateCalendar(duplicate));
  const fake=structuredClone(data);fake.events[0].forecast=50;assert.throws(()=>validateCalendar(fake));
  const noSource=structuredClone(data);delete noSource.sources;assert.throws(()=>validateCalendar(noSource));
  const noBackup=structuredClone(data);noBackup.private_backup.objects[0].readback_verified=false;assert.throws(()=>validateCalendar(noBackup));
});
