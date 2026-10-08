import { translate as t, numberLocale } from './i18n.js?v=calendar-20261008b';
import { dayInZone, selectEvents, validateCalendar, SCENARIOS } from './calendar-model.js?v=calendar-20261008b';

const $ = id => document.getElementById(id);
const state = { data: null, status: null, selected: null, checked: 0, busy: false, release: null, hash: null };
const esc = text => String(text ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const txt = source => esc(t(source));
const dateLabel = (iso, time = false) => new Intl.DateTimeFormat(numberLocale(), {timeZone: $('cal-zone').value, dateStyle: 'medium', ...(time ? {timeStyle:'short'} : {})}).format(new Date(iso));
const addDays = (day, count) => new Date(Date.parse(`${day}T12:00:00Z`) + count * 86400000).toISOString().slice(0,10);
function value(v, unit) {
  if (v === null) return '—';
  const number = v.toLocaleString(numberLocale(), {minimumFractionDigits:['thousand_jobs','thousand_claims'].includes(unit)?0:1,maximumFractionDigits:1});
  return `${number}${unit === 'percent' || unit === 'percent_saar' ? '%' : ['thousand_jobs','thousand_claims'].includes(unit) ? 'k' : unit === 'billion_usd' ? ` ${t('tỷ USD')}` : ''}`;
}

function setRange(kind) {
  const today = dayInZone(new Date().toISOString(), $('cal-zone').value);
  let start = today, end = today;
  if (kind === 'week' || kind === 'next') {
    const day = new Date(`${today}T12:00:00Z`).getUTCDay();
    start = addDays(today, -((day + 6) % 7) + (kind === 'next' ? 7 : 0));
    end = addDays(start, 6);
  }
  if (kind === 'month') end = addDays(today, 30);
  if (kind === 'past') start = addDays(today, -30);
  $('cal-start').value = start; $('cal-end').value = end;
  document.querySelectorAll('[data-cal-range]').forEach(b => b.setAttribute('aria-pressed', String(b.dataset.calRange === kind)));
  render();
}
function render() {
  if (!state.data) return;
  for (const id of ['cal-zone','cal-impact']) for (const option of $(id).options) {
    option.dataset.sourceLabel ??= option.textContent;
    option.textContent = t(option.dataset.sourceLabel);
  }
  const { data } = state;
  const start = $('cal-start').value, end = $('cal-end').value, zone = $('cal-zone').value;
  if (!start || !end || end < start) { $('cal-range-error').hidden = false; return; }
  $('cal-range-error').hidden = true;
  const rows = selectEvents(data.events, {start, end, zone, impact:$('cal-impact').value, search:$('cal-search').value});
  if (!rows.some(e => e.id === state.selected)) state.selected = rows[0]?.id ?? null;
  $('cal-count').textContent = `${rows.length} ${t('sự kiện')} · ${zone}`;
  $('cal-empty').hidden = rows.length > 0;
  $('cal-rows').replaceChildren();
  for (const e of rows) {
    const tr = document.createElement('tr');
    tr.classList.toggle('cal-selected', e.id === state.selected);
    const time = new Intl.DateTimeFormat(numberLocale(), {timeZone:zone, hour:'2-digit',minute:'2-digit',hourCycle:'h23'}).format(new Date(e.scheduled_at));
    const elapsed = Date.parse(e.scheduled_at) < Date.now();
    const status = e.actual !== null ? (e.data_status === 'official_release' ? 'Đã có số liệu chính thức' : 'Số liệu kỳ mới nhất')
      : elapsed ? 'Chưa xác minh số liệu' : 'Sắp diễn ra';
    tr.innerHTML = `<td data-label="${txt('Ngày / giờ')}"><time datetime="${esc(e.scheduled_at)}">${esc(dateLabel(e.scheduled_at))}<b>${esc(time)}${e.time_basis ? ' ≈' : ''}</b></time></td>
      <td data-label="${txt('Tiền tệ')}"><span class="badge">USD</span></td>
      <td data-label="${txt('Ảnh hưởng')}"><span class="cal-impact ${e.impact}">${txt(e.impact === 'high' ? 'Cao' : 'Vừa')}</span></td>
      <td class="cal-event"><button class="cal-event-button" data-cal-event="${esc(e.id)}" aria-pressed="${e.id === state.selected}">${txt(e.title)}</button><small>${esc(e.source_title)}</small><a href="${esc(e.source_url)}" target="_blank" rel="noreferrer">${e.provider.toUpperCase()} ↗</a></td>
      <td data-label="${txt('Thực tế')}" class="${e.actual === null ? 'muted' : 'cal-value'}">${esc(value(e.actual,e.unit))}</td><td data-label="${txt('Dự báo')}" class="muted">—</td><td data-label="${txt('Kỳ trước')}" class="${e.previous === null ? 'muted' : 'cal-value'}">${esc(value(e.previous,e.unit))}</td>
      <td data-label="${txt('Trạng thái')}"><span class="small">${txt(status)}</span></td>`;
    tr.querySelector('button').addEventListener('click', () => { state.selected = e.id; render(); });
    $('cal-rows').append(tr);
  }
  const selected = rows.find(e => e.id === state.selected);
  $('cal-assessment').hidden = !selected;
  if (selected) {
    $('cal-selected-title').textContent = t(selected.title);
    const source = `<a href="${esc(selected.data_source_url || selected.source_url)}" target="_blank" rel="noreferrer">${txt('Xem nguồn chính thức')} ↗</a>`;
    $('cal-release-detail').innerHTML = selected.actual !== null
      ? `<div class="cal-result-head"><div><p class="eyebrow">${txt('Kết quả theo kỳ')}</p><strong>${esc(value(selected.actual,selected.unit))}</strong><span class="small muted">${txt('Kỳ trước')}: ${esc(value(selected.previous,selected.unit))}</span></div><div class="small"><p>${txt('Kỳ tham chiếu')}: <b>${esc(selected.reference_period)}</b></p><p>${txt('Dữ liệu tải lúc')}: ${esc(dateLabel(selected.data_vintage_at,true))}</p>${source}</div></div>${selected.details.length ? `<ul>${selected.details.map(d=>`<li>${txt(d.label)}: <b>${esc(value(d.actual,d.unit))}</b> · ${txt('Kỳ trước')}: ${esc(value(d.previous,d.unit))}</li>`).join('')}</ul>` : ''}<p class="small muted">${txt(selected.data_status === 'official_release' ? 'Số liệu từ bản tin công bố chính thức.' : 'Số liệu BLS thuộc kỳ mới nhất, có thể đã được điều chỉnh sau công bố; không phải vintage tại thời điểm sự kiện.')}</p>`
      : `<p class="small muted">${txt(Date.parse(selected.scheduled_at) < Date.now() ? 'Đã qua giờ dự kiến; chưa đối chiếu được số liệu của đúng kỳ công bố.' : 'Chưa đến giờ công bố; số thực tế chưa có.')}</p>${source}`;
    $('cal-scenarios').innerHTML = SCENARIOS[selected.category].map(r => `<tr>${r.map((cell,i) => `<${i===0?'th':'td'}>${txt(cell)}</${i===0?'th':'td'}>`).join('')}</tr>`).join('');
  }
  $('cal-indicators').innerHTML = data.indicators.map(i => {
    const value = v => v === null ? '—' : `${v.toLocaleString(numberLocale(), {minimumFractionDigits: i.unit==='percent'?1:0,maximumFractionDigits:1})}${i.unit==='percent'?'%':'k'}`;
    return `<article class="cal-indicator"><p class="eyebrow">${esc(i.title)}</p><strong>${esc(value(i.value))}</strong><p class="small">${txt('Kỳ tham chiếu')}: ${esc(i.reference_period)}${i.preliminary ? ` · ${txt('Sơ bộ')}` : ''}</p><p class="small muted">${txt('Kỳ trước')}: ${esc(value(i.previous))} (${esc(i.previous_period)})</p><a class="small" href="${esc(i.source_url)}" target="_blank" rel="noreferrer">BLS ↗</a></article>`;
  }).join('');
  const lastSuccess = state.status?.last_success_at ?? data.sources.bls.checked_at;
  const stale = Date.now() - Date.parse(lastSuccess) > 48 * 3600000;
  $('cal-freshness').textContent = `${t('Batch thành công')}: ${dateLabel(lastSuccess, true)} · ${t('Snapshot số liệu')}: ${dateLabel(data.sources.bls_data.checked_at, true)} · ${t(stale ? 'Lịch có thể đã cũ; kiểm tra nguồn chính thức' : 'Nguồn chính thức · cập nhật theo batch')}`;
  $('cal-freshness').classList.toggle('negative', stale);
  $('cal-manifest').href = `/data/calendar/releases/${state.release}/calendar.json`;
}
async function load(force = false) {
  if (state.busy || (!force && Date.now() - state.checked < 15 * 60000)) return;
  state.busy = true; $('cal-refresh').disabled = true;
  try {
    const fetchJSON = async url => { const r = await fetch(url, {cache:'no-cache',signal:AbortSignal.timeout(15000)}); if (!r.ok) throw Error('Lịch kinh tế chưa tải được'); return r.json(); };
    const [pointer, status] = await Promise.all([fetchJSON('/data/calendar/latest.json'), fetchJSON('/data/calendar/status.json')]);
    if (!/^calendar-[a-f0-9]{20}$/.test(pointer.release_id) || pointer.url !== `/data/calendar/releases/${pointer.release_id}/calendar.json` || !/^[a-f0-9]{64}$/.test(pointer.sha256)) throw Error('Dữ liệu lịch không hợp lệ');
    if (state.release === pointer.release_id && state.hash !== pointer.sha256) throw Error('Checksum lịch không khớp');
    if (state.release !== pointer.release_id) {
      const response = await fetch(pointer.url, {signal:AbortSignal.timeout(15000)});
      if (!response.ok) throw Error('Lịch kinh tế chưa tải được');
      const bytes = await response.arrayBuffer();
      const hash = [...new Uint8Array(await crypto.subtle.digest('SHA-256',bytes))].map(v=>v.toString(16).padStart(2,'0')).join('');
      if (hash !== pointer.sha256) throw Error('Checksum lịch không khớp');
      const data = validateCalendar(JSON.parse(new TextDecoder().decode(bytes)));
      if (data.release_id !== pointer.release_id) throw Error('Dữ liệu lịch không hợp lệ');
      state.data = data; state.release = pointer.release_id; state.hash = pointer.sha256;
    }
    state.status = status; state.checked = Date.now(); render();
    $('cal-error').hidden = status.outcome === 'ok';
    $('cal-error-text').textContent = t('Nguồn đang lỗi; giữ bản lịch tốt gần nhất. Kiểm tra đường dẫn chính thức trước sự kiện.');
    $('cal-content').hidden = false;
  } catch (e) {
    $('cal-error').hidden = false; $('cal-error-text').textContent = t(e.message);
  } finally {
    $('cal-loading').hidden = true; $('cal-refresh').disabled = false; state.busy = false;
  }
}
export function openCalendar() { load(); }
export function initCalendar() {
  setRange('week');
  $('cal-mql5').addEventListener('toggle',()=>{if ($('cal-mql5').open && !$('cal-mql5-frame').getAttribute('src')) $('cal-mql5-frame').src='/mql5-calendar.html';});
  document.querySelectorAll('[data-cal-range]').forEach(b => b.addEventListener('click',()=>setRange(b.dataset.calRange)));
  for (const id of ['cal-start','cal-end','cal-zone','cal-impact']) $(id).addEventListener('change',render);
  $('cal-search').addEventListener('input',render);
  $('cal-refresh').addEventListener('click',()=>load(true)); $('cal-retry').addEventListener('click',()=>load(true));
  document.addEventListener('eco-language-changed',render);
  setInterval(()=>{if (!document.hidden && !$('view-calendar').hidden) load();},15*60000);
}
