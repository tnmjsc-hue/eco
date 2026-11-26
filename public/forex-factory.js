import { translate as t, numberLocale } from './i18n.js?v=calendar-vn-days-1';
import { VIETNAM_TIME_ZONE, dayInZone, selectEvents, groupCalendarDays } from './calendar-model.js?v=calendar-vn-days-1';
import { verifyForexPointer, verifyForexCalendar, forexEventStatus } from './forex-factory-model.js?v=forex-factory-feed-1';

const SOURCE = 'https://calendar.forexfactory.com';
const REFRESH_MS = 60_000;
const labels = {
  released: 'Đã có số liệu',
  upcoming: 'Sắp diễn ra',
  waiting: 'Đang chờ số thực tế',
  missing: 'Chưa có số thực tế',
  unscheduled: 'Chưa rõ giờ',
  elapsed: 'Đã qua giờ dự kiến',
};
const impacts = {high:'Cao', medium:'Vừa', low:'Thấp', holiday:'Ngày nghỉ'};
const $ = id => document.getElementById(id);
const state = {data:null, hash:null, checked:0, busy:false, health:null, selected:null, statuses:[], watch:null};

function node(tag, text, className) {
  const element = document.createElement(tag);
  if (text !== undefined) element.textContent = text;
  if (className) element.className = className;
  return element;
}

function addDays(day, count) {
  return new Date(Date.parse(day + 'T12:00:00Z') + count * 86400000).toISOString().slice(0,10);
}

function setRange(kind) {
  const today = dayInZone(new Date().toISOString());
  let start = today, end = today;
  if (kind === 'week' || kind === 'next') {
    const day = new Date(today + 'T12:00:00Z').getUTCDay();
    start = addDays(today, -((day + 6) % 7) + (kind === 'next' ? 7 : 0));
    end = addDays(start,6);
  }
  if (kind === 'month') end = addDays(today,30);
  if (kind === 'past') start = addDays(today,-30);
  $('cal-start').value = start;
  $('cal-end').value = end;
  document.querySelectorAll('[data-cal-range]').forEach(button => {
    button.setAttribute('aria-pressed', String(button.dataset.calRange === kind));
  });
  render();
}

function updateClocks() {
  const now = Date.now();
  for (const [event, element] of state.statuses) {
    const status = forexEventStatus(event, now);
    const label = t(labels[status]);
    if (element.textContent !== label) element.textContent = label;
    element.dataset.status = status;
  }
  if (!state.watch) return;
  const status = forexEventStatus(state.watch, now);
  const label = status === 'released'
    ? t(labels[status]) + ' · ' + state.watch.actual
    : t(labels[status]);
  const statusElement = $('ff-watch-status');
  if (statusElement.textContent !== label) statusElement.textContent = label;
  statusElement.dataset.status = status;
  const countdown = $('ff-countdown');
  const delta = Date.parse(state.watch.scheduled_at) - now;
  countdown.hidden = status !== 'upcoming' || delta > 86400000;
  if (!countdown.hidden) {
    const seconds = Math.max(0,Math.ceil(delta / 1000));
    const parts = [Math.floor(seconds / 3600),Math.floor(seconds / 60) % 60,seconds % 60];
    countdown.textContent = parts.map(part => String(part).padStart(2,'0')).join(':');
  }
}

function renderWatch(rows) {
  const now = Date.now();
  const selected = rows.find(event => event.id === state.selected);
  const next = rows.find(event => event.scheduled_at && event.expects_actual && event.impact === 'high'
    && ['upcoming','waiting'].includes(forexEventStatus(event,now)))
    ?? rows.find(event => event.scheduled_at && event.expects_actual
      && ['upcoming','waiting'].includes(forexEventStatus(event,now)));
  state.watch = selected ?? next ?? null;
  $('ff-watch').hidden = state.watch === null;
  if (state.watch) $('ff-watch-title').textContent = state.watch.currency + ' · ' + state.watch.title;
  updateClocks();
}

function addReading(row, key, label, event) {
  const value = event[key];
  const cell = node('td', value ?? '—', value === null ? 'muted' : 'cal-value');
  cell.dataset.label = t(label);
  if (key === 'previous' && event.previous_initial !== null) {
    const revision = node('small', t('Trước điều chỉnh') + ' ' + event.previous_initial, 'ff-initial');
    cell.append(revision);
  }
  row.append(cell);
}

function render() {
  for (const id of ['cal-impact','ff-currency']) {
    for (const option of $(id).options) {
      option.dataset.sourceLabel ??= option.textContent;
      option.textContent = t(option.dataset.sourceLabel);
    }
  }
  if (!state.data) return;
  const start = $('cal-start').value, end = $('cal-end').value;
  const validRange = Boolean(start && end && start <= end);
  $('cal-range-error').hidden = validRange;
  const rows = validRange ? selectEvents(state.data.events, {
    start, end, impact:$('cal-impact').value, currency:$('ff-currency').value, search:$('cal-search').value,
  }) : [];
  $('cal-count').textContent = rows.length + ' ' + t('sự kiện') + ' · ' + t('Việt Nam (UTC+7)');
  const stale = !state.health || state.health.outcome !== 'ok'
    || Date.now() - Date.parse(state.health.last_success_at) > 30 * 3600000;
  const freshness = $('ff-freshness');
  const dateTime = new Intl.DateTimeFormat(numberLocale(), {timeZone:VIETNAM_TIME_ZONE, dateStyle:'medium',timeStyle:'short'});
  freshness.textContent = t('Snapshot Forex Factory') + ' · ' + dateTime.format(new Date(state.data.source.retrieved_at))
    + ' · ' + t('Phạm vi lịch') + ' ' + state.data.coverage_start + ' → ' + state.data.coverage_end
    + (stale ? ' · ' + t('Dữ liệu có thể đã cũ') : '');
  freshness.classList.toggle('negative',stale);
  const dateFormat = new Intl.DateTimeFormat(numberLocale(), {timeZone:VIETNAM_TIME_ZONE,dateStyle:'full'});
  const timeFormat = new Intl.DateTimeFormat(numberLocale(), {timeZone:VIETNAM_TIME_ZONE,hour:'2-digit',minute:'2-digit',hourCycle:'h23'});
  const fragment = document.createDocumentFragment();
  const statuses = [];
  const days = groupCalendarDays(rows);
  for (const {day,events} of days) {
    const group = node('tbody');
    group.dataset.calDay = day;
    const heading = node('tr',undefined,'cal-day-heading');
    const header = node('th');
    header.scope = 'rowgroup';
    header.colSpan = 8;
    const date = node('time',dateFormat.format(new Date(day + 'T12:00:00Z')));
    date.dateTime = day;
    header.append(date);
    heading.append(header);
    group.append(heading);

    for (const event of events) {
      const row = node('tr');
      row.dataset.ffEvent = event.id;
      for (const label of ['Giờ','Tiền tệ','Ảnh hưởng']) {
        const cell = node('td');
        cell.dataset.label = t(label);
        row.append(cell);
      }
      const scheduled = event.scheduled_at ? new Date(event.scheduled_at) : null;
      if (scheduled) {
        const time = node('time',timeFormat.format(scheduled),'cal-event-time');
        time.dateTime = event.scheduled_at;
        row.cells[0].append(time);
      } else {
        row.cells[0].append(node('span',t(event.time_label || 'Chưa rõ giờ'),'small muted'));
      }
      row.cells[1].append(node('span',event.currency,'badge'));
      row.cells[2].append(node('span',t(impacts[event.impact]),'cal-impact ' + event.impact));
      const name = node('td',undefined,'cal-event');
      const button = node('button',event.title,'cal-event-button');
      button.type = 'button';
      button.dataset.calEvent = String(event.id);
      button.setAttribute('aria-pressed',String(event.id === state.selected));
      name.append(button);
      if (event.source_path) {
        const link = node('a','Forex Factory ↗');
        link.href = SOURCE + event.source_path;
        link.target = '_blank';
        link.rel = 'noreferrer';
        name.append(link);
      }
      row.append(name);
      addReading(row,'actual','Thực tế',event);
      addReading(row,'forecast','Dự báo',event);
      addReading(row,'previous','Kỳ trước',event);
      const statusCell = node('td');
      statusCell.dataset.label = t('Trạng thái');
      const status = node('span',undefined,'small ff-status');
      statusCell.append(status);
      row.append(statusCell);
      statuses.push([event,status]);
      group.append(row);
    }
    fragment.append(group);
  }
  const table = $('cal-rows');
  for (const body of [...table.tBodies]) body.remove();
  table.append(fragment);
  $('cal-empty').hidden = !validRange || rows.length > 0;
  state.statuses = statuses;
  renderWatch(days.flatMap(group => group.events));
}

async function fetchJson(path) {
  const response = await fetch(path,{cache:'no-cache',signal:AbortSignal.timeout(12000)});
  if (!response.ok) throw Error('Chưa tải được lịch Forex Factory.');
  return response.json();
}

export async function refreshForexCalendar(force = false) {
  if (state.busy || (!force && Date.now() - state.checked < REFRESH_MS)) return;
  state.busy = true;
  state.checked = Date.now();
  try {
    const [pointer, health] = await Promise.all([
      fetchJson('/data/forex-factory/latest.json'), fetchJson('/data/forex-factory/status.json'),
    ]);
    verifyForexPointer(pointer);
    if (state.data?.release_id === pointer.release_id && state.hash !== pointer.sha256) {
      throw Error('Checksum lịch không khớp');
    }
    if (state.data?.release_id !== pointer.release_id) {
      const response = await fetch(pointer.url,{signal:AbortSignal.timeout(15000)});
      if (!response.ok) throw Error('Chưa tải được lịch Forex Factory.');
      const bytes = await response.arrayBuffer();
      const hash = [...new Uint8Array(await crypto.subtle.digest('SHA-256',bytes))]
        .map(byte => byte.toString(16).padStart(2,'0')).join('');
      if (hash !== pointer.sha256) throw Error('Checksum lịch không khớp');
      state.data = verifyForexCalendar(JSON.parse(new TextDecoder().decode(bytes)),pointer);
      state.hash = hash;
      const picker = $('ff-currency');
      const previous = picker.value;
      const currencies = [...new Set(state.data.events.map(event => event.currency))].sort();
      picker.replaceChildren(new Option(t('Tất cả'),'all'),...currencies.map(currency => new Option(currency,currency)));
      picker.options[0].dataset.sourceLabel = 'Tất cả';
      if (currencies.includes(previous)) picker.value = previous;
      $('ff-content').hidden = false;
      render();
    }
    const previousHealth = state.health;
    state.health = health.outcome === 'ok' && health.release_id === pointer.release_id && Number.isFinite(Date.parse(health.last_success_at)) ? health : null;
    if (state.health?.last_success_at !== previousHealth?.last_success_at) render();
    $('ff-error').hidden = state.health !== null;
    $('ff-error-text').textContent = t('Nguồn Forex Factory đang lỗi. Bảng giữ bản gần nhất đã xác minh.');
  } catch {
    state.health = null;
    $('ff-error').hidden = false;
    $('ff-error-text').textContent = t(state.data ? 'Nguồn Forex Factory đang lỗi. Bảng giữ bản gần nhất đã xác minh.' : 'Chưa tải được lịch Forex Factory.');
    render();
  } finally {
    $('ff-loading').hidden = true;
    state.busy = false;
  }
}

export function initForexCalendar() {
  setRange('week');
  document.querySelectorAll('[data-cal-range]').forEach(button => {
    button.addEventListener('click',() => setRange(button.dataset.calRange));
  });
  for (const id of ['cal-start','cal-end','cal-impact','ff-currency']) $(id).addEventListener('change',render);
  $('cal-search').addEventListener('input',render);
  $('cal-rows').addEventListener('click',event => {
    const button = event.target.closest('[data-cal-event]');
    if (!button) return;
    state.selected = Number(button.dataset.calEvent);
    render();
    $('cal-rows').querySelector('[data-cal-event="' + state.selected + '"]')?.focus();
  });
  $('ff-retry').addEventListener('click',() => refreshForexCalendar(true));
  document.addEventListener('eco-language-changed',render);
  const active = () => !document.hidden && !$('view-calendar').hidden;
  setInterval(() => { if (active()) updateClocks(); },1000);
  setInterval(() => { if (active()) refreshForexCalendar(); },REFRESH_MS);
  document.addEventListener('visibilitychange',() => {
    if (active()) {
      updateClocks();
      refreshForexCalendar();
    }
  });
}
