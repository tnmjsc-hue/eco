import { REASONS, displayScore, scoreColor, dateMinus } from './data-model.js?v=dashboard-1';
import { initProxies, resizeProxies } from './proxies.js?v=calendar-20261008c';
import { initDiagnostics, resizeDiagnostics } from './diagnostics.js?v=calendar-20261008c';
import { CORE_METRICS, CORE_VERSION, coreScore, validateCorePointer, validateCore, validateCoreParents, exportCoreCSV } from './core-model.js?v=core-ten-only-1';
import { initLanguage, numberLocale, relativeDaysAgo, translate } from './i18n.js?v=calendar-20261008c';
import { initCalendar, openCalendar } from './calendar.js?v=calendar-20261008c';

const $ = id => document.getElementById(id);
const fmt = (number, digits = 2) => number === null ? '—' : number.toLocaleString(numberLocale(), { minimumFractionDigits: digits, maximumFractionDigits: digits });
const dateLabel = date => new Intl.DateTimeFormat(numberLocale(), { day: '2-digit', month: '2-digit', year: 'numeric', timeZone: 'UTC' }).format(new Date(`${date}T00:00:00Z`));
const escape = text => String(text).replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
const state = { rows: [], manifest: null, research: null, status: null, pointerHash: null, followLatest: true, lastChecked: 0, range: 'all', mode: 'ten', selected: CORE_METRICS.map(m => m.id), date: null, view: 'dashboard', busy: false };
let historyChart;
const baselineNames = { core: 'Core 4', extended: 'ECO 7', normalized_E7_only: 'E7 riêng', equal_weight_four_components: '4 metric đồng trọng số', normalized_price_group_only: 'Nhóm giá riêng' };

async function getBytes(url, fresh = false) {
  const response = await fetch(url, { cache: fresh ? 'no-cache' : 'default', signal: AbortSignal.timeout(20000) });
  if (!response.ok) throw new Error(`Không tải được dữ liệu (HTTP ${response.status}).`);
  return new Uint8Array(await response.arrayBuffer());
}
async function verify(bytes, expected) {
  const hash = [...new Uint8Array(await crypto.subtle.digest('SHA-256', bytes))].map(v => v.toString(16).padStart(2, '0')).join('');
  if (hash !== expected) throw new Error('Checksum không khớp. Bản dữ liệu chưa được hiển thị.');
  return JSON.parse(new TextDecoder().decode(bytes));
}
async function load() {
  if (state.busy) return;
  state.busy = true;
  $('refresh').disabled = true;
  $('retry').disabled = true;
  $('error').hidden = true;
  try {
    if (!window.echarts || !window.lucide) throw new Error('Thư viện giao diện chưa tải được. Vui lòng tải lại trang.');
    let status = null;
    try { status = JSON.parse(new TextDecoder().decode(await getBytes('/data/core-v2/status.json', true))); } catch { /* Data remains usable when operational status is unavailable. */ }
    const pointer = JSON.parse(new TextDecoder().decode(await getBytes('/data/core-v2/latest.json', true)));
    validateCorePointer(pointer);
    if (state.manifest?.release_id === pointer.release_id && state.pointerHash !== pointer.manifest_sha256) throw new Error('Release bất biến đã đổi checksum.');
    state.lastChecked = Date.now();
    if (state.manifest?.release_id === pointer.release_id && state.pointerHash === pointer.manifest_sha256) {
      state.status = status?.release_id === pointer.release_id ? status : null;
      renderOverview();
      return;
    }
    const manifest = await verify(await getBytes(pointer.manifest_url), pointer.manifest_sha256);
    if (manifest.release_id !== pointer.release_id) throw new Error('Manifest không đúng release.');
    const base = `/data/core-v2/releases/${pointer.release_id}/`;
    const [data, research] = await Promise.all(['history.json', 'research.json'].map(async name => verify(await getBytes(base + name), manifest.files[name])));
    validateCore(data, manifest, research);
    const parents = Object.fromEntries(await Promise.all(Object.entries(manifest.parents).map(async ([kind,ref])=>[kind,await verify(await getBytes(ref.manifest_url),ref.manifest_sha256)])));
    validateCoreParents(manifest, parents);
    state.rows = data.rows;
    state.manifest = manifest;
    state.pointerHash = pointer.manifest_sha256;
    state.research = research;
    state.status = status?.release_id === pointer.release_id ? status : null;
    if (state.followLatest || !state.rows.some(r => r.date === state.date)) state.date = manifest.last_valid_score_date;
    $('selected-date').min = state.rows[0].date;
    $('selected-date').max = state.rows.at(-1).date;
    $('manifest-link').href = pointer.manifest_url;
    $('loading').hidden = true;
    $('workspace').hidden = false;
    if (!historyChart) {
      historyChart = window.echarts.init($('history-chart'), null, { renderer: 'canvas' });
      historyChart.on('click', params => {
        if (params.data?.[0]) selectDate(params.data[0]);
      });
    }
    render();
    renderResearch();
    renderProvenance();
    icons();
    requestAnimationFrame(() => { historyChart.resize(); resizeProxies(); resizeDiagnostics(); });
  } catch (error) {
    $('loading').hidden = true;
    $('error').hidden = false;
    $('error-text').textContent = `${error.message}${state.rows.length ? ' Đang giữ bản dữ liệu đã xác minh trước đó.' : ''}`;
  } finally {
    state.busy = false;
    $('refresh').disabled = false;
    $('retry').disabled = false;
  }
}
function icons() { window.lucide?.createIcons(); }
function filteredRows() {
  const start = state.range === 'all' ? state.rows[0].date : dateMinus(state.rows.at(-1).date, state.range === '1y' ? 365 : 1095);
  return state.rows.filter(r => r.date >= start);
}
function selectDate(date, followLatest = false) {
  if (!state.rows.some(r => r.date === date)) { $('selected-date').value = state.date; return; }
  state.date = date;
  state.followLatest = followLatest;
  renderOverview();
  renderComponents();
}
function render() { if (!state.rows.length) return; renderOverview(); renderComponents(); renderChart(); }
function renderOverview() {
  const index = state.rows.findIndex(r => r.date === state.date);
  const row = state.rows[index];
  if (!row) return;
  const score = state.mode === 'custom' ? coreScore(row, state.selected) : row.score;
  $('score-label').textContent = state.mode === 'custom' ? 'Điểm tùy chỉnh · Experimental' : 'ECO Core · 10 Experimental';
  $('score-version').textContent = CORE_VERSION;
  $('score-value').textContent = displayScore(score);
  $('score-value').title = score === null ? 'Không có điểm hợp lệ' : fmt(score, 4);
  $('score-value').style.color = scoreColor(score);
  $('heat-marker').hidden = score === null;
  $('heat-marker').style.left = `calc(${score ?? 0}% - 1px)`;
  $('price-value').textContent = row.price_usd === null ? '—' : `$${fmt(row.price_usd)}`;
  const previousPrice = state.rows[index - 1]?.price_usd;
  const change = row.price_usd !== null && previousPrice ? (row.price_usd / previousPrice - 1) * 100 : null;
  $('price-change').textContent = change === null ? 'Không đủ dữ liệu ngày liền trước' : `${change >= 0 ? '+' : ''}${fmt(change)}% so với ngày trước`;
  $('price-change').className = `daily-change ${change === null ? '' : change >= 0 ? 'positive' : 'negative'}`;
  const selected = state.mode === 'custom' ? state.selected : activeMetrics().map(m=>m.id);
  const available = selected.filter(id=>row.components[id] !== null).length;
  $('coverage-value').textContent = `${available} / ${selected.length}`;
  $('coverage-note').textContent = score !== null ? 'Đủ thành phần đã chọn' : 'Thiếu thành phần / tập chọn rỗng';
  $('selected-date').value = state.date;
  $('previous-day').disabled = index === 0;
  $('next-day').disabled = index === state.rows.length - 1;
  $('day-reason').textContent = `${dateLabel(row.date)} · ${!row.period_closed_at_retrieval ? 'Ngày chưa đóng lúc tải snapshot.' : !row.source_row_present ? 'Chưa có dữ liệu nguồn.' : row.score === null ? 'Chưa đủ warm-up hoặc dữ liệu.' : 'Ngày quan sát UTC.'}`;
  const last = state.manifest.last_observation_date;
  const today = new Date().toISOString().slice(0, 10);
  const age = Math.max(0, Math.round((Date.parse(today) - Date.parse(last)) / 86400000));
  const missing = state.manifest.missing_dates.length;
  const pending = state.manifest.pending_dates ?? [];
  const update = state.status;
  const labels = { published: 'Đã phát hành ngày mới', revised: 'Đã phát hành revision', unchanged: 'Dữ liệu không đổi', source_pending: 'Đang chờ dữ liệu nguồn', failed: 'Cập nhật lỗi · giữ bản hợp lệ' };
  const timeLabel = value => new Date(value).toLocaleString(numberLocale(), { timeZone: 'Asia/Ho_Chi_Minh', hour12: false });
  const schedule = update ? `${translate('Ghép sau batch Core 10:17/14:17 và proxy 10:47/14:47 (giờ Việt Nam).')} ${escape(translate(labels[update.outcome] ?? 'Chờ lần chạy đầu'))}${update.last_attempt_at ? ` · ${translate('lần kiểm tra')} ${escape(timeLabel(update.last_attempt_at))}` : ''}.` : translate('Chưa xác minh trạng thái lịch cập nhật.');
  const scoreLag = (Date.now() - Date.parse(state.manifest.last_valid_score_date + 'T00:00:00Z') - 86400000) / 3600000;
  const jobLag = update?.last_attempt_at ? (Date.now() - Date.parse(update.last_attempt_at)) / 3600000 : 0;
  const warning = scoreLag > 48 || jobLag > 26 ? ` ${translate('Dữ liệu chậm; điểm gần nhất vẫn có ngày quan sát gốc.')}` : '';
  const revision = state.manifest.revision?.changed_dates?.length ? ` ${translate('Revision nguồn:')} ${state.manifest.revision.changed_dates.length} ${translate('ngày lịch sử; release cũ được giữ nguyên.')}` : '';
  $('freshness').innerHTML = `<b class="status-dot"></b><span>${translate('Nguồn đến')} ${dateLabel(last)} · ${relativeDaysAgo(age)}${missing ? ` · ${missing} ${translate('ngày đã đóng thiếu dữ liệu')}` : ''}${pending.length ? ` · ${translate('ngày chờ')} ${pending.map(d => escape(dateLabel(d))).join(', ')} (${translate('chưa đóng lúc tải')})` : ''}. ${schedule}${warning}${revision}</span>`;
}
function activeMetrics() { return CORE_METRICS; }
function renderComponents() {
  const row = state.rows.find(r => r.date === state.date);
  const active = state.mode === 'custom' ? state.selected : activeMetrics().map(m=>m.id);
  const activeWeights = Object.fromEntries(activeMetrics().map(m=>[m.id,m.weight]));
  const total = active.reduce((sum,id)=>sum+(activeWeights[id]??0),0);
  $('component-rows').innerHTML = CORE_METRICS.map(m => {
    const value = row.components[m.id];
    const input = row.new_features[m.id];
    const original = input && input.input_value!==null ? `${fmt(input.input_unit==='ratio'?input.input_value*100:input.input_value,input.input_unit==='ETH'?2:4)} ${input.input_unit==='ETH'?'ETH':'%'}` : null;
    const reason = REASONS[row.reasons[m.id]] ?? ({parent_date_unavailable:'Chờ proxy cùng ngày',window_unavailable:'Thiếu dữ liệu cửa sổ',nonpositive_log_argument:'Đối số log không dương'}[row.reasons[m.id]]) ?? row.reasons[m.id] ?? 'Chưa có dữ liệu';
    const weight = active.includes(m.id) && total ? activeWeights[m.id] / total * 100 : 0;
    const flash = row.source_flags[m.id].includes('flash');
    const metricType = m.kind === 'proxy' ? ` · ${translate('proxy')}` : m.kind === 'derived' ? ` · ${translate('dẫn xuất')}` : '';
    const availability = value === null ? translate('Chưa đủ') : flash ? translate('Tạm thời · flash') : translate('Khả dụng');
    const statusTitle = value === null ? translate(reason) : flash ? translate('Nhãn sàn và số liệu tạm thời; có thể sửa hồi cứu') : translate('Đã chuẩn hóa causal q05/q95');
    return `<tr><td><input type="checkbox" data-metric="${m.id}" aria-label="${escape(translate(`Chọn ${m.slot} ${m.name}`))}" ${active.includes(m.id) ? 'checked' : ''} ${state.mode !== 'custom' ? 'disabled' : ''}></td><td><span class="metric-id">${m.slot}${metricType}</span><span class="metric-name">${translate(m.name)}</span><div class="metric-description">${translate(m.description)}${m.limitation ? `<br><span title="${escape(translate(m.limitation))}">${escape(translate(m.interpretation))}</span>` : ''}${original ? `<br>${translate('Giá trị gốc:')} ${escape(original)}` : ''}</div></td><td><div class="metric-score"><strong style="color:${scoreColor(value)}" title="${value === null ? escape(translate(reason)) : fmt(value, 4)}">${displayScore(value)}</strong><div class="mini-meter"><span style="width:${value ?? 0}%;background:${scoreColor(value)}"></span></div></div></td><td>${fmt(weight, 3)}%</td><td><span class="status-pill ${value === null || flash ? 'missing' : 'ready'}" title="${escape(statusTitle)}">${availability}</span></td></tr>`;
  }).join('');
  $('component-rows').querySelectorAll('input').forEach(input => input.addEventListener('change', () => {
    state.selected = input.checked ? [...state.selected, input.dataset.metric] : state.selected.filter(id => id !== input.dataset.metric);
    render();
  }));
  $('selection-note').hidden = state.mode !== 'custom';
  $('selection-note').textContent = state.selected.length ? `Tùy chỉnh ${state.selected.length}/10 metric. Trọng số Core 10 được chuẩn hóa trên tập đã chọn; chỉ có điểm khi mọi metric đã chọn đều hợp lệ.` : 'Tập chọn rỗng · không có điểm tùy chỉnh.';
}
function renderChart() {
  const rows = filteredRows();
  const mobile = window.innerWidth <= 600;
  const custom = state.mode === 'custom';
  $('range-label').textContent = `${dateLabel(rows[0].date)} – ${dateLabel(rows.at(-1).date)} · ${rows.length.toLocaleString(numberLocale())} ${translate('ngày')}`;
  $('core-legend').hidden = custom;
  $('custom-legend').hidden = !custom;
  $('chart-title').textContent = custom ? `${translate('Tùy chỉnh')} & ${translate('Giá ETH')}` : translate('Core 10 & giá ETH');
  $('history-chart').setAttribute('aria-label', custom ? `${translate('Biểu đồ lịch sử điểm')} ${translate('Tùy chỉnh')} ${translate('và')} ${translate('Giá ETH')}` : translate('Biểu đồ lịch sử điểm Core 10 và giá ETH'));
  const color = custom ? '#bb790b' : '#087f72';
  const scoreName = custom ? translate('Tùy chỉnh') : 'Core 10';
  const priceName = translate('Giá ETH');
  const series = [{ name: scoreName, type: 'line', data: rows.map(r => [r.date, custom ? coreScore(r, state.selected) : r.score]), showSymbol: false, connectNulls: false, lineStyle: { width: 1.9, color, type: custom ? 'dashed' : 'solid' }, itemStyle: { color }, z: 3 }];
  series.push({ name: priceName, type: 'line', yAxisIndex: 1, data: rows.map(r => [r.date, r.price_usd]), showSymbol: false, connectNulls: false, lineStyle: { width: 1.2, color: '#455554', opacity: .7 }, itemStyle: { color: '#455554' }, z: 1 });
  historyChart.setOption({ animation: false, aria: { enabled: true }, grid: { left: mobile ? 34 : 42, right: mobile ? 50 : 66, top: 28, bottom: 48 }, textStyle: { fontFamily: 'Segoe UI, Arial, sans-serif' }, tooltip: { trigger: 'axis', confine: true, backgroundColor: '#fff', borderColor: '#dfe6e5', textStyle: { color: '#232b2b' }, formatter: params => {
    const date = params[0]?.value?.[0];
    if (!date) return '';
    return `<div class="ec-tooltip"><strong>${escape(dateLabel(date))} · UTC</strong>${params.map(p => `${escape(p.seriesName)}<span>${p.value[1] === null ? '—' : p.seriesName === priceName ? '$' + fmt(p.value[1]) : fmt(p.value[1], 2)}</span><br>`).join('')}</div>`;
  } }, xAxis: { type: 'time', axisLine: { lineStyle: { color: '#dfe6e5' } }, axisTick: { show: false }, axisLabel: { fontSize: 10, color: '#687575', hideOverlap: true }, splitNumber: mobile ? 4 : 8 }, yAxis: [{ type: 'value', min: 0, max: 100, interval: 25, name: translate('Điểm'), nameTextStyle: { color: '#087f72', fontSize: 10, align: 'left' }, axisLabel: { color: '#687575', fontSize: 10 }, splitLine: { lineStyle: { color: '#e7eeeb' } } }, { type: $('log-price').checked ? 'log' : 'value', name: 'USD', nameTextStyle: { color: '#687575', fontSize: 10 }, axisLabel: { color: '#687575', fontSize: 9, formatter: value => value >= 1000 ? `${Math.round(value / 1000)}k` : `${value}` }, splitLine: { show: false } }], dataZoom: [{ type: 'inside', filterMode: 'none', zoomOnMouseWheel: false, moveOnMouseWheel: false }, { type: 'slider', height: 13, bottom: 6, borderColor: 'transparent', backgroundColor: '#edf3f0', fillerColor: '#087f7217', handleStyle: { color: '#7ba79c' }, showDetail: false, brushSelect: false }], series }, { notMerge: true });
}
function renderResearch() {
  const r = state.research;
  $('research-conclusion').textContent = `Chưa chứng minh Core 10 cải thiện dự báo.${r.comparisons.core.upper_95 < 0 ? ' AP thăm dò thấp hơn Core 4 trong khoảng tin cậy này;' : ''} Holdout đã dùng lại. Giữ nguyên công thức và nhãn Experimental.`;
  $('research-summary').innerHTML = [
    ['Khoảng đánh giá', `${escape(dateLabel(r.start))}<br>${escape(dateLabel(r.end))}`], ['Ngày được chấm', fmt(r.n, 0)],
    ['Prevalence nhãn dương', `${fmt(r.prevalence * 100, 1)}%`], ['Core 10 Average Precision', fmt(r.statistics.core_ten.average_precision, 3)],
  ].map(([label, value]) => `<div><div class="label">${label}</div><strong>${value}</strong></div>`).join('');
  $('extended-results').innerHTML = Object.entries(r.statistics).map(([n,v])=>`<tr><td>${n==='core_ten'?'Core 10':baselineNames[n]??n}</td><td>${fmt(v.average_precision,4)}</td><td>${n==='core_ten'?'—':fmt(r.comparisons[n].ap_delta,4)}</td><td>${n==='core_ten'?'—':`[${fmt(r.comparisons[n].lower_95,4)}; ${fmt(r.comparisons[n].upper_95,4)}]`}</td></tr>`).join('');
  $('extended-research-link').href = `/data/core-v2/releases/${state.manifest.release_id}/research.json`;
}
function renderProvenance() {
  const m = state.manifest;
  $('provenance').replaceChildren();
  for (const [label, value] of [ ['Release Core 10', m.release_id], ['Core 4 cha', m.parents.core.release_id], ['Proxy cha', m.parents.proxies.release_id], ['ECO 7 cha',m.parents.extended.release_id], ['Diagnostics cha',m.parents.diagnostics.release_id], ['Protocol SHA-256', m.protocol_sha256], ['Engine SHA-256', m.engine_sha256], ['Tính điểm UTC', m.computed_at], ['Revision', m.revision ? `${m.revision.reason} · trước đó ${m.revision.previous_release_id??'không có'}` : 'Release nghiên cứu ban đầu'], ['Availability lịch sử', 'Không biết; không gọi lịch sử là as-published'], ['Phạm vi', `${m.rows} ngày lịch · ${m.score_rows} ngày có Core 10 · bắt đầu ${m.first_score_date}`] ]) {
    const dt = document.createElement('dt'); dt.textContent = label;
    const dd = document.createElement('dd'); dd.textContent = value;
    $('provenance').append(dt, dd);
  }
}
function view(name) {
  state.view = name;
  document.querySelectorAll('.view').forEach(node => { node.hidden = node.id !== `view-${name}`; });
  document.querySelectorAll('[data-view]').forEach(node => { node.classList.toggle('active', node.dataset.view === name); if (node.dataset.view === name) node.setAttribute('aria-current', 'page'); else node.removeAttribute('aria-current'); });
  history.replaceState(null, '', name === 'dashboard' ? location.pathname : `#${name}`);
  if (name === 'calendar') { $('workspace').hidden = false; $('loading').hidden = true; openCalendar(); }
  if (state.rows.length) requestAnimationFrame(() => { if (name === 'dashboard') historyChart.resize(); if (name === 'extended') resizeProxies(); if (name === 'diagnostics') resizeDiagnostics(); });
}
function start() {
  icons();
  initProxies();
  initDiagnostics();
  initCalendar();
  document.querySelectorAll('[data-view]').forEach(button => button.addEventListener('click', () => view(button.dataset.view)));
  document.querySelectorAll('[data-range]').forEach(button => button.addEventListener('click', () => {
    state.range = button.dataset.range;
    document.querySelectorAll('[data-range]').forEach(b => { b.classList.toggle('active', b === button); b.setAttribute('aria-pressed', String(b === button)); });
    if (state.rows.length) renderChart();
  }));
  document.querySelectorAll('[data-mode]').forEach(button => button.addEventListener('click', () => {
    state.mode = button.dataset.mode;
    document.querySelectorAll('[data-mode]').forEach(b => { b.classList.toggle('active', b === button); b.setAttribute('aria-pressed', String(b === button)); });
    if (state.rows.length) render();
  }));
  $('selected-date').addEventListener('change', event => selectDate(event.target.value));
  $('previous-day').addEventListener('click', () => selectDate(dateMinus(state.date, 1)));
  $('next-day').addEventListener('click', () => selectDate(dateMinus(state.date, -1)));
  $('latest-day').addEventListener('click', () => { if (state.rows.length) selectDate(state.manifest.last_valid_score_date, true); });
  $('log-price').addEventListener('change', renderChart);
  $('refresh').addEventListener('click', load);
  $('retry').addEventListener('click', load);
  $('export').addEventListener('click', () => {
    if (!state.rows.length) return;
    const csv = exportCoreCSV(filteredRows(), state.selected, state.mode, state.manifest);
    const url = URL.createObjectURL(new Blob([csv], { type: 'text/csv;charset=utf-8' }));
    const link = document.createElement('a'); link.href = url; link.download = `eco-${state.manifest.release_id}-${state.mode}-${state.range}.csv`; link.click();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  });
  new ResizeObserver(() => { historyChart?.resize(); }).observe(document.querySelector('main'));
  if (['#research', '#methodology', '#extended', '#diagnostics', '#calendar'].includes(location.hash)) view(location.hash.slice(1));
  setInterval(() => { if (!document.hidden) load(); }, 15 * 60 * 1000);
  document.addEventListener('visibilitychange', () => { if (!document.hidden && Date.now() - state.lastChecked > 60000) load(); });
  initLanguage();
  document.addEventListener('eco-language-changed', () => { if (!state.rows.length) return; render(); renderResearch(); renderProvenance(); requestAnimationFrame(() => historyChart?.resize()); });
  load();
}
if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', start, { once: true }); else start();
