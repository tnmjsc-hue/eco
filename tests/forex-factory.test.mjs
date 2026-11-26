import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
import { readFile } from 'node:fs/promises';
import test from 'node:test';
import { verifyForexCalendar, verifyForexPointer, forexEventStatus } from '../public/forex-factory-model.js';
import { groupCalendarDays, selectEvents } from '../public/calendar-model.js';

test('Forex Factory published release matches its immutable pointer and has verified private backup', async () => {
  const pointer = JSON.parse(await readFile('public/data/forex-factory/latest.json'));
  verifyForexPointer(pointer);
  const bytes = await readFile('public' + pointer.url);
  assert.equal(createHash('sha256').update(bytes).digest('hex'),pointer.sha256);
  const data = verifyForexCalendar(JSON.parse(bytes),pointer);
  assert.ok(data.events.some(event => event.actual !== null && event.forecast !== null));
  assert.ok(data.events.some(event => event.currency !== 'USD'));
  assert.ok(data.events.some(event => event.scheduled_at === null));
  assert.throws(() => verifyForexPointer({...pointer,url:'https://example.com/'}));
  assert.throws(() => verifyForexCalendar({...data,events:[data.events[0],data.events[0]]},pointer));
  assert.throws(() => verifyForexCalendar({...data,private_backup:[]},pointer));
});

test('Forex Factory waiting and range filters respect release status, timezones and masked dates', () => {
  const event = { title:'Example GDP', impact:'high', currency:'AUD', scheduled_at:'2026-11-26T19:00:00Z',
    actual:null, expects_actual:true, source_day:'2026-11-26' };
  const minute = 60_000;
  const scheduled = Date.parse(event.scheduled_at);
  assert.equal(forexEventStatus(event,scheduled-minute),'upcoming');
  assert.equal(forexEventStatus(event,scheduled),'waiting');
  assert.equal(forexEventStatus(event,scheduled+61*minute),'missing');
  assert.equal(forexEventStatus({...event,actual:'0'},scheduled),'released');
  const masked = {...event,scheduled_at:null};
  assert.equal(forexEventStatus(masked,scheduled),'unscheduled');
  const query = {start:'2026-11-27',end:'2026-11-27',zone:'Asia/Ho_Chi_Minh',currency:'AUD',search:'gdp'};
  assert.deepEqual(selectEvents([event,masked],query),[event]);
  assert.deepEqual(selectEvents([event,masked],{...query,start:'2026-11-26',end:'2026-11-26'}),[masked]);
  assert.deepEqual(selectEvents([event],{...query,currency:'USD'}),[]);
});

test('Vietnam calendar date groups split at 17:00 UTC and put date-only events first', () => {
  const endOfDay = { id:1, scheduled_at:'2026-11-26T16:59:00Z', source_day:'2026-11-26' };
  const startOfDay = { id:2, scheduled_at:'2026-11-26T17:00:00Z', source_day:'2026-11-26' };
  const next = { id:3, scheduled_at:'2026-11-27T00:30:00Z', source_day:'2026-11-27' };
  const allDay = { id:4, scheduled_at:null, source_day:'2026-11-27' };
  const events = [next,startOfDay,allDay,endOfDay];
  assert.deepEqual(groupCalendarDays(events),[
    { day:'2026-11-26', events:[endOfDay] },
    { day:'2026-11-27', events:[allDay,startOfDay,next] },
  ]);
  assert.deepEqual(selectEvents(events,{start:'2026-11-26',end:'2026-11-26'}),[endOfDay]);
  assert.deepEqual(groupCalendarDays([]),[]);
});
