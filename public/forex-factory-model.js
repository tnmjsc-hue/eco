const HASH = /^[a-f0-9]{64}$/;
const RELEASE = /^ff-calendar-[a-f0-9]{20}$/;
const SOURCE = 'https://calendar.forexfactory.com/calendar';
const VERSION = 'forex-factory-calendar-v1.0.0';
const DAY = /^\d{4}-\d{2}-\d{2}$/;
const TIMESTAMP = /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?Z$/;
const isTime = value => TIMESTAMP.test(value) && Number.isFinite(Date.parse(value));
const isReading = value => value === null || (typeof value === 'string' && value.length > 0 && value.length <= 80);

export function verifyForexPointer(pointer) {
  if (!RELEASE.test(pointer?.release_id) || !HASH.test(pointer.sha256) || !HASH.test(pointer.content_sha256)
    || pointer.url !== '/data/forex-factory/releases/' + pointer.release_id + '/calendar.json') {
    throw Error('Bản lịch Forex Factory không hợp lệ.');
  }
}

export function verifyForexCalendar(data, pointer) {
  if (data?.calendar_version !== VERSION || data.release_id !== pointer.release_id || data.content_sha256 !== pointer.content_sha256
    || !DAY.test(data.coverage_start) || !DAY.test(data.coverage_end) || data.coverage_end < data.coverage_start
    || !(new RegExp('^' + SOURCE.replaceAll('.', '\\.') + '\\?range=[a-z]{3}\\d{1,2}\\.\\d{4}-[a-z]{3}\\d{1,2}\\.\\d{4}$')).test(data.source?.url)
    || !HASH.test(data.source.sha256) || !isTime(data.source.retrieved_at)
    || (data.revision_of !== null && !RELEASE.test(data.revision_of))
    || !Array.isArray(data.events) || data.events.length === 0
    || !Array.isArray(data.private_backup) || data.private_backup.length !== 3) {
    throw Error('Bản lịch Forex Factory không hợp lệ.');
  }
  const backedUp = new Set(data.private_backup.map(object => {
    const prefix = 'raw/forex-factory/' + data.release_id + '/';
    if (!object.object_key.startsWith(prefix) || !HASH.test(object.sha256) || object.readback_verified !== true) {
      throw Error('Bản lịch Forex Factory không hợp lệ.');
    }
    return object.object_key.slice(prefix.length);
  }));
  if (!['calendar.html.gz','calendar.json','manifest.json'].every(name => backedUp.has(name))) {
    throw Error('Bản lịch Forex Factory không hợp lệ.');
  }
  const ids = new Set();
  for (const event of data.events) {
    if (!Number.isSafeInteger(event.id) || event.id <= 0 || ids.has(event.id)
      || typeof event.title !== 'string' || !event.title || event.title.length > 180
      || !/^(?:[A-Z]{3}|All)$/.test(event.currency) || !['high','medium','low','holiday'].includes(event.impact)
      || !DAY.test(event.source_day) || event.source_day < data.coverage_start || event.source_day > data.coverage_end
      || !(event.scheduled_at === null ? typeof event.time_label === 'string' && event.time_label.length <= 48 : isTime(event.scheduled_at) && event.time_label === null)
      || typeof event.expects_actual !== 'boolean'
      || ![event.actual,event.forecast,event.previous,event.previous_initial].every(isReading)
      || (event.source_path !== null && !/^\/calendar\/\d+-[a-z0-9-]+$/.test(event.source_path))) {
      throw Error('Bản lịch Forex Factory không hợp lệ.');
    }
    ids.add(event.id);
  }
  return data;
}

export function forexEventStatus(event, now) {
  if (event.actual !== null) return 'released';
  if (event.scheduled_at === null) return 'unscheduled';
  const delta = Date.parse(event.scheduled_at) - now;
  if (delta > 0) return 'upcoming';
  if (!event.expects_actual) return 'elapsed';
  return delta >= -3600000 ? 'waiting' : 'missing';
}
