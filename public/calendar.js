import { translate as t, numberLocale } from './i18n.js?v=calendar-vn-days-1';
import { VIETNAM_TIME_ZONE, validateCalendar } from './calendar-model.js?v=calendar-vn-days-1';
import { initForexCalendar, refreshForexCalendar } from './forex-factory.js?v=calendar-vn-days-1';
import {refreshMacro,renderMacro} from './macro.js?v=calendar-vn-days-1';
import {refreshMarket,renderMarket} from './macro-market.js?v=calendar-vn-days-1';
import {refreshProbability,renderProbability} from './macro-probability.js?v=calendar-vn-days-1';

const $ = id => document.getElementById(id);
const state = { data: null, status: null, checked: 0, busy: false, release: null, hash: null };
const esc = text => String(text ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const txt = source => esc(t(source));
const dateLabel = iso => new Intl.DateTimeFormat(numberLocale(), {timeZone: VIETNAM_TIME_ZONE, dateStyle: 'medium',timeStyle:'short'}).format(new Date(iso));

function render() {
  renderMacro();
  renderMarket();
  renderProbability();
  if (!state.data) return;
  const { data } = state;
  $('cal-indicators').innerHTML = data.indicators.map(i => {
    const value = v => v === null ? '—' : `${v.toLocaleString(numberLocale(), {minimumFractionDigits: i.unit==='percent'?1:0,maximumFractionDigits:1})}${i.unit==='percent'?'%':'k'}`;
    return `<article class="cal-indicator"><p class="eyebrow">${esc(i.title)}</p><strong>${esc(value(i.value))}</strong><p class="small">${txt('Kỳ tham chiếu')}: ${esc(i.reference_period)}${i.preliminary ? ` · ${txt('Sơ bộ')}` : ''}</p><p class="small muted">${txt('Kỳ trước')}: ${esc(value(i.previous))} (${esc(i.previous_period)})</p><a class="small" href="${esc(i.source_url)}" target="_blank" rel="noreferrer">BLS ↗</a></article>`;
  }).join('');
  const lastSuccess = state.status?.last_success_at ?? data.sources.bls.checked_at;
  const stale = Date.now() - Date.parse(lastSuccess) > 48 * 3600000;
  $('cal-freshness').textContent = `${t('Batch thành công')}: ${dateLabel(lastSuccess)} · ${t('Snapshot số liệu')}: ${dateLabel(data.sources.bls_data.checked_at)} · ${t(stale ? 'Lịch có thể đã cũ; kiểm tra nguồn chính thức' : 'Nguồn chính thức · cập nhật theo batch')}`;
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
    $('cal-loading').hidden = true;
    await Promise.all([refreshMacro(state.release),refreshMarket(),refreshProbability(state.release)]);
    $('cal-refresh').disabled = false; state.busy = false;
  }
}
export function openCalendar() {
  refreshForexCalendar();
  load();
}

export function initCalendar() {
  initForexCalendar();
  $('cal-refresh').addEventListener('click',() => {
    refreshForexCalendar(true);
    load(true);
  });
  $('cal-retry').addEventListener('click',() => load(true));
  document.addEventListener('eco-language-changed',render);
  setInterval(() => { if (!document.hidden && !$('view-calendar').hidden) load(); },15*60000);
}
