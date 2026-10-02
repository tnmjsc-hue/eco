import { METRICS, REASONS, customScore, displayScore, scoreColor, dateMinus, validateHistory, exportCSV } from './data-model.js?v=dashboard-1';

const $ = id => document.getElementById(id);
const fmt = (number, digits = 2) => number === null ? '—' : number.toLocaleString('vi-VN', { minimumFractionDigits: digits, maximumFractionDigits: digits });
const dateLabel = date => date.split('-').reverse().join('/');
const escape = text => String(text).replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
const state = { rows: [], manifest: null, research: null, range: 'all', mode: 'core', selected: METRICS.map(m => m.id), date: null, view: 'dashboard', busy: false };
let historyChart, researchChart;
const baselineNames = { core: 'Core', normalized_E7_only: 'E7 độc lập', equal_weight_four_components: '4 metric đồng trọng số', normalized_price_group_only: 'Nhóm giá độc lập' };

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
    const pointer = JSON.parse(new TextDecoder().decode(await getBytes('/data/latest.json', true)));
    if (!/^core-[a-f0-9]{20}$/.test(pointer.release_id) || pointer.manifest_url !== `/data/releases/${pointer.release_id}/manifest.json`) throw new Error('Release pointer không hợp lệ.');
    const manifest = await verify(await getBytes(pointer.manifest_url), pointer.manifest_sha256);
    if (manifest.release_id !== pointer.release_id || manifest.methodology_version !== 'core-v0.1.0' || manifest.series_type !== 'reconstructed') throw new Error('Manifest không đúng phiên bản.');
    const base = `/data/releases/${pointer.release_id}/`;
    const [data, research] = await Promise.all(['history.json', 'research.json'].map(async name => verify(await getBytes(base + name), manifest.files[name])));
    validateHistory(data, pointer.release_id);
    const validRows = data.rows.filter(r => r.score !== null);
    if (data.rows.length !== manifest.rows || validRows.length !== manifest.score_rows || validRows.at(-1)?.date !== manifest.last_valid_score_date || validRows.at(-1)?.score !== manifest.last_valid_score) throw new Error('Manifest và lịch sử không khớp.');
    if (research.protocol !== 'core-v0.1.0-protocol-1' || typeof research.success !== 'boolean') throw new Error('Research không đúng protocol.');
    state.rows = data.rows;
    state.manifest = manifest;
    state.research = research;
    if (!state.rows.some(r => r.date === state.date)) state.date = manifest.last_valid_score_date;
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
    requestAnimationFrame(() => { historyChart.resize(); researchChart?.resize(); });
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
function selectDate(date) {
  if (!state.rows.some(r => r.date === date)) { $('selected-date').value = state.date; return; }
  state.date = date;
  renderOverview();
  renderComponents();
}
function render() { if (!state.rows.length) return; renderOverview(); renderComponents(); renderChart(); }
function renderOverview() {
  const index = state.rows.findIndex(r => r.date === state.date);
  const row = state.rows[index];
  const score = state.mode === 'core' ? row.score : customScore(row, state.selected);
  $('score-label').textContent = state.mode === 'core' ? 'ECO Core' : 'Điểm tùy chỉnh · không phải Core';
  $('score-value').textContent = displayScore(score);
  $('score-value').title = score === null ? 'Không có điểm hợp lệ' : fmt(score, 4);
  $('score-value').style.color = scoreColor(score);
  $('heat-marker').hidden = score === null;
  $('heat-marker').style.left = `calc(${score ?? 0}% - 1px)`;
  $('custom-comparison').hidden = state.mode === 'core';
  $('custom-comparison').textContent = `Core cùng ngày: ${displayScore(row.score)} / 100`;
  $('price-value').textContent = row.price_usd === null ? '—' : `$${fmt(row.price_usd)}`;
  const previousPrice = state.rows[index - 1]?.price_usd;
  const change = row.price_usd !== null && previousPrice ? (row.price_usd / previousPrice - 1) * 100 : null;
  $('price-change').textContent = change === null ? 'Không đủ dữ liệu ngày liền trước' : `${change >= 0 ? '+' : ''}${fmt(change)}% so với ngày trước`;
  $('price-change').className = `daily-change ${change === null ? '' : change >= 0 ? 'positive' : 'negative'}`;
  $('coverage-value').textContent = `${row.coverage} / 4`;
  $('coverage-note').textContent = row.coverage === 4 ? 'Đủ thành phần Core' : 'Thiếu thành phần · Core null';
  $('selected-date').value = state.date;
  $('previous-day').disabled = index === 0;
  $('next-day').disabled = index === state.rows.length - 1;
  $('day-reason').textContent = `${dateLabel(row.date)} · ${!row.period_closed_at_retrieval ? 'Ngày chưa đóng lúc tải snapshot.' : !row.source_row_present ? 'Chưa có dữ liệu nguồn.' : row.score === null ? 'Chưa đủ warm-up hoặc dữ liệu.' : 'Ngày quan sát UTC.'}`;
  const last = state.manifest.last_observation_date;
  const today = new Date().toISOString().slice(0, 10);
  const age = Math.max(0, Math.round((Date.parse(today) - Date.parse(last)) / 86400000));
  const missing = state.manifest.missing_dates.length;
  const pending = state.manifest.pending_dates ?? [];
  $('freshness').innerHTML = `<b class="status-dot"></b><span>Nguồn đến ${dateLabel(last)} · cách hiện tại ${age} ngày UTC${missing ? ` · ${missing} ngày đã đóng thiếu dữ liệu` : ''}${pending.length ? ` · ngày chờ ${pending.map(d => escape(dateLabel(d))).join(', ')} (chưa đóng lúc tải)` : ''}. Bản snapshot nghiên cứu, chưa tự cập nhật.</span>`;
}
function renderComponents() {
  const row = state.rows.find(r => r.date === state.date);
  const active = state.mode === 'core' ? METRICS.map(m => m.id) : state.selected;
  const total = METRICS.filter(m => active.includes(m.id)).reduce((sum, m) => sum + m.weight, 0);
  $('component-rows').innerHTML = METRICS.map(m => {
    const value = row.components[m.id];
    const reason = REASONS[row.reasons[m.id]] ?? 'Chưa có dữ liệu';
    const weight = active.includes(m.id) && total ? m.weight / total * 100 : 0;
    return `<tr><td><input type="checkbox" data-metric="${m.id}" aria-label="Chọn ${m.id} ${m.name}" ${active.includes(m.id) ? 'checked' : ''} ${state.mode === 'core' ? 'disabled' : ''}></td><td><span class="metric-id">${m.id}</span><span class="metric-name">${m.name}</span><div class="metric-description">${m.description}</div></td><td><div class="metric-score"><strong style="color:${scoreColor(value)}" title="${value === null ? reason : fmt(value, 4)}">${displayScore(value)}</strong><div class="mini-meter"><span style="width:${value ?? 0}%;background:${scoreColor(value)}"></span></div></div></td><td>${fmt(weight, 1)}%</td><td><span class="status-pill ${value === null ? 'missing' : 'ready'}" title="${value === null ? reason : 'Đã chuẩn hóa causal q05/q95'}">${value === null ? 'Chưa đủ' : 'Khả dụng'}</span></td></tr>`;
  }).join('');
  $('component-rows').querySelectorAll('input').forEach(input => input.addEventListener('change', () => {
    state.selected = input.checked ? [...state.selected, input.dataset.metric] : state.selected.filter(id => id !== input.dataset.metric);
    render();
  }));
  $('selection-note').hidden = state.mode === 'core';
  $('selection-note').textContent = state.selected.length ? `Tùy chỉnh ${state.selected.length}/4 metric. Trọng số gốc được chuẩn hóa trên tập đã chọn; chỉ có điểm khi mọi metric đã chọn đều hợp lệ.` : 'Tập chọn rỗng · không có điểm tùy chỉnh.';
}
function renderChart() {
  const rows = filteredRows();
  const mobile = window.innerWidth <= 600;
  const custom = state.mode === 'custom';
  $('range-label').textContent = `${dateLabel(rows[0].date)} – ${dateLabel(rows.at(-1).date)} · ${rows.length.toLocaleString('vi-VN')} ngày`;
  $('custom-legend').hidden = !custom;
  const series = [{ name: 'Core', type: 'line', data: rows.map(r => [r.date, r.score]), showSymbol: false, connectNulls: false, lineStyle: { width: 1.7, color: '#087f72' }, itemStyle: { color: '#087f72' }, z: 3 }];
  if (custom) series.push({ name: 'Tùy chỉnh', type: 'line', data: rows.map(r => [r.date, customScore(r, state.selected)]), showSymbol: false, connectNulls: false, lineStyle: { width: 1.5, color: '#bb790b', type: 'dashed' }, itemStyle: { color: '#bb790b' }, z: 4 });
  series.push({ name: 'Giá ETH', type: 'line', yAxisIndex: 1, data: rows.map(r => [r.date, r.price_usd]), showSymbol: false, connectNulls: false, lineStyle: { width: 1.2, color: '#455554', opacity: .7 }, itemStyle: { color: '#455554' }, z: 1 });
  historyChart.setOption({ animation: false, aria: { enabled: true }, grid: { left: mobile ? 34 : 42, right: mobile ? 50 : 66, top: 28, bottom: 48 }, textStyle: { fontFamily: 'Segoe UI, Arial, sans-serif' }, tooltip: { trigger: 'axis', confine: true, backgroundColor: '#fff', borderColor: '#dfe6e5', textStyle: { color: '#232b2b' }, formatter: params => {
    const date = params[0]?.value?.[0];
    if (!date) return '';
    return `<div class="ec-tooltip"><strong>${escape(dateLabel(date))} · UTC</strong>${params.map(p => `${escape(p.seriesName)}<span>${p.value[1] === null ? '—' : p.seriesName === 'Giá ETH' ? '$' + fmt(p.value[1]) : fmt(p.value[1], 2)}</span><br>`).join('')}</div>`;
  } }, xAxis: { type: 'time', axisLine: { lineStyle: { color: '#dfe6e5' } }, axisTick: { show: false }, axisLabel: { fontSize: 10, color: '#687575', hideOverlap: true }, splitNumber: mobile ? 4 : 8 }, yAxis: [{ type: 'value', min: 0, max: 100, interval: 25, name: 'Core', nameTextStyle: { color: '#087f72', fontSize: 10, align: 'left' }, axisLabel: { color: '#687575', fontSize: 10 }, splitLine: { lineStyle: { color: '#e7eeeb' } } }, { type: $('log-price').checked ? 'log' : 'value', name: 'USD', nameTextStyle: { color: '#687575', fontSize: 10 }, axisLabel: { color: '#687575', fontSize: 9, formatter: value => value >= 1000 ? `${Math.round(value / 1000)}k` : `${value}` }, splitLine: { show: false } }], dataZoom: [{ type: 'inside', filterMode: 'none', zoomOnMouseWheel: false, moveOnMouseWheel: false }, { type: 'slider', height: 13, bottom: 6, borderColor: 'transparent', backgroundColor: '#edf3f0', fillerColor: '#087f7217', handleStyle: { color: '#7ba79c' }, showDetail: false, brushSelect: false }], series }, { notMerge: true });
}
function renderResearch() {
  const r = state.research;
  $('research-conclusion').textContent = r.success ? 'Protocol đạt tiêu chí incremental ranking utility trên lịch sử reconstructed. Chưa chứng minh hiệu quả realtime.' : 'Chưa chứng minh Core cải thiện so với mọi baseline theo tiêu chí đã khóa. Giữ nguyên công thức; không tối ưu lại để ép kết quả đạt.';
  $('research-summary').innerHTML = [
    ['Khoảng đánh giá', `${escape(dateLabel(r.start))}<br>${escape(dateLabel(r.end))}`], ['Ngày được chấm', fmt(r.n, 0)],
    ['Prevalence nhãn dương', `${fmt(r.prevalence * 100, 1)}%`], ['Core Average Precision', fmt(r.statistics.core.average_precision, 3)],
  ].map(([label, value]) => `<div><div class="label">${label}</div><strong>${value}</strong></div>`).join('');
  $('comparison-rows').innerHTML = Object.entries(r.comparisons).map(([key, c]) => `<tr><td>${baselineNames[key]}</td><td>${c.ap_delta > 0 ? '+' : ''}${fmt(c.ap_delta, 4)}</td><td>[${fmt(c.lower_95, 4)}; ${fmt(c.upper_95, 4)}]</td><td>${c.positive_years}/${c.eligible_years}</td><td><span class="status-pill ${c.pass ? 'ready' : 'missing'}">${c.pass ? 'Đạt' : 'Chưa đạt'}</span></td></tr>`).join('');
  $('secondary-results').innerHTML = `<p>Core ROC-AUC: <strong>${fmt(r.statistics.core.roc_auc, 3)}</strong> · Precision ≥90: <strong>${fmt(r.statistics.core.precision_at_90, 3)}</strong> · Recall ≥90: <strong>${fmt(r.statistics.core.recall_at_90, 3)}</strong> · ${r.statistics.core.predictions_at_90} ngày có điểm ≥90.</p><p>Primary label là future drawdown, không phải nhãn đỉnh chu kỳ. Sensitivity và kết quả từng năm có trong research JSON cùng release.</p>`;
  if (state.view === 'research') plotResearch();
}
function plotResearch() {
  if (!researchChart) researchChart = window.echarts.init($('research-chart'));
  const stats = state.research.statistics;
  const mobile = window.innerWidth <= 600;
  researchChart.setOption({ animation: false, grid: { left: mobile ? 104 : 190, right: 40, top: 14, bottom: 32 }, xAxis: { type: 'value', min: 0, max: 1, axisLabel: { fontSize: 10, color: '#687575' }, splitLine: { lineStyle: { color: '#e7eeeb' } } }, yAxis: { type: 'category', inverse: true, data: Object.keys(stats).map(k => mobile ? ({ core: 'Core', normalized_E7_only: 'E7 độc lập', equal_weight_four_components: 'Đồng trọng số', normalized_price_group_only: 'Nhóm giá' })[k] : baselineNames[k]), axisLabel: { fontSize: 11, color: '#455554' }, axisLine: { show: false }, axisTick: { show: false } }, series: [{ type: 'bar', barWidth: 21, data: Object.values(stats).map((s, i) => ({ value: s.average_precision, itemStyle: { color: ['#087f72', '#8b9895', '#c98668', '#b6a564'][i] } })), label: { show: true, position: 'right', fontSize: 11, color: '#455554', formatter: p => fmt(p.value, 3) } }], markLine: { data: [{ xAxis: state.research.prevalence }] } });
  researchChart.resize();
}
function renderProvenance() {
  const m = state.manifest;
  $('provenance').replaceChildren();
  for (const [label, value] of [ ['Release', m.release_id], ['Snapshot SHA-256', m.snapshot_sha256], ['Protocol SHA-256', m.protocol_sha256], ['Engine SHA-256', m.engine_sha256], ['Tải dữ liệu UTC', m.retrieved_at], ['Tính điểm UTC', m.computed_at], ['Availability lịch sử', 'Không biết; không gọi lịch sử là as-published'], ['Phạm vi', `${m.source_rows} ngày nguồn · ${m.score_rows} ngày có Core · bắt đầu ${m.first_score_date}`] ]) {
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
  if (state.rows.length) requestAnimationFrame(() => { if (name === 'research') plotResearch(); if (name === 'dashboard') historyChart.resize(); });
}
function start() {
  icons();
  document.querySelectorAll('[data-view]').forEach(button => button.addEventListener('click', () => view(button.dataset.view)));
  document.querySelectorAll('[data-range]').forEach(button => button.addEventListener('click', () => {
    state.range = button.dataset.range;
    document.querySelectorAll('[data-range]').forEach(b => { b.classList.toggle('active', b === button); b.setAttribute('aria-pressed', String(b === button)); });
    if (state.rows.length) renderChart();
  }));
  document.querySelectorAll('[data-mode]').forEach(button => button.addEventListener('click', () => {
    state.mode = button.dataset.mode;
    document.querySelectorAll('[data-mode]').forEach(b => { b.classList.toggle('active', b === button); b.setAttribute('aria-pressed', String(b === button)); });
    render();
  }));
  $('selected-date').addEventListener('change', event => selectDate(event.target.value));
  $('previous-day').addEventListener('click', () => selectDate(dateMinus(state.date, 1)));
  $('next-day').addEventListener('click', () => selectDate(dateMinus(state.date, -1)));
  $('latest-day').addEventListener('click', () => selectDate(state.manifest.last_valid_score_date));
  $('log-price').addEventListener('change', renderChart);
  $('refresh').addEventListener('click', load);
  $('retry').addEventListener('click', load);
  $('export').addEventListener('click', () => {
    const csv = exportCSV(filteredRows(), state.selected, state.mode, state.manifest);
    const url = URL.createObjectURL(new Blob([csv], { type: 'text/csv;charset=utf-8' }));
    const link = document.createElement('a'); link.href = url; link.download = `eco-${state.manifest.release_id}-${state.mode}-${state.range}.csv`; link.click();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  });
  new ResizeObserver(() => { historyChart?.resize(); researchChart?.resize(); }).observe(document.querySelector('main'));
  if (['#research', '#methodology'].includes(location.hash)) view(location.hash.slice(1));
  load();
}
if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', start, { once: true }); else start();
