import { METRICS, REASONS, displayScore, scoreColor, dateMinus } from './data-model.js?v=dashboard-1';
import { initProxies, resizeProxies } from './proxies.js?v=proxies-1';
import { initDiagnostics, resizeDiagnostics } from './diagnostics.js?v=diagnostics-1';
import { EXTENDED_METRICS } from './extended-model.js?v=extended-1';
import { CORE_METRICS, CORE_VERSION, coreScore, validateCorePointer, validateCore, validateCoreParents, exportCoreCSV } from './core-model.js?v=core-ten-1';

const $ = id => document.getElementById(id);
const fmt = (number, digits = 2) => number === null ? '—' : number.toLocaleString('vi-VN', { minimumFractionDigits: digits, maximumFractionDigits: digits });
const dateLabel = date => date.split('-').reverse().join('/');
const escape = text => String(text).replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
const state = { rows: [], manifest: null, coreManifest: null, extendedManifest: null, research: null, extendedResearch: null, status: null, pointerHash: null, followLatest: true, lastChecked: 0, range: 'all', mode: 'ten', selected: CORE_METRICS.map(m => m.id), date: null, view: 'dashboard', busy: false };
let historyChart, researchChart;
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
    const [data, extendedResearch] = await Promise.all(['history.json', 'research.json'].map(async name => verify(await getBytes(base + name), manifest.files[name])));
    validateCore(data, manifest, extendedResearch);
    const parents = Object.fromEntries(await Promise.all(Object.entries(manifest.parents).map(async ([kind,ref])=>[kind,await verify(await getBytes(ref.manifest_url),ref.manifest_sha256)])));
    validateCoreParents(manifest, parents);
    const coreParent = manifest.parents.core;
    const coreManifest = parents.core;
    if (coreManifest.release_id !== coreParent.release_id || coreManifest.methodology_version !== 'core-v0.1.0'
        || coreManifest.files['history.json'] !== coreParent.history_sha256) throw new Error('Core cha không khớp.');
    const research = await verify(await getBytes(`/data/releases/${coreParent.release_id}/research.json`), coreManifest.files['research.json']);
    if (research.protocol !== 'core-v0.1.0-protocol-1' || typeof research.success !== 'boolean') throw new Error('Research không đúng protocol.');
    state.rows = data.rows;
    state.manifest = manifest;
    state.coreManifest = coreManifest;
    state.extendedManifest = parents.extended;
    state.pointerHash = pointer.manifest_sha256;
    state.research = research;
    state.extendedResearch = extendedResearch;
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
    requestAnimationFrame(() => { historyChart.resize(); researchChart?.resize(); resizeProxies(); resizeDiagnostics(); });
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
  const score = state.mode === 'core' ? row.core_score : state.mode === 'extended' ? row.extended_score : state.mode === 'ten' ? row.score : coreScore(row, state.selected);
  $('score-label').textContent = state.mode === 'core' ? 'ECO Core · 4' : state.mode === 'extended' ? 'ECO 7 · Experimental' : state.mode === 'ten' ? 'ECO Core · 10 Experimental' : 'Điểm tùy chỉnh · Experimental';
  $('score-version').textContent = state.mode === 'core' ? 'core-v0.1.0' : state.mode === 'extended' ? 'extended-v0.1.0' : CORE_VERSION;
  $('score-value').textContent = displayScore(score);
  $('score-value').title = score === null ? 'Không có điểm hợp lệ' : fmt(score, 4);
  $('score-value').style.color = scoreColor(score);
  $('heat-marker').hidden = score === null;
  $('heat-marker').style.left = `calc(${score ?? 0}% - 1px)`;
  $('custom-comparison').hidden = false;
  $('custom-comparison').textContent = `Cùng ngày · Core 10: ${displayScore(row.score)} · ECO 7: ${displayScore(row.extended_score)} · Core 4: ${displayScore(row.core_score)}`;
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
  const timeLabel = value => new Date(value).toLocaleString('vi-VN', { timeZone: 'Asia/Ho_Chi_Minh', hour12: false });
  const schedule = update ? `Ghép sau batch Core 10:17/14:17 và proxy 10:47/14:47 (giờ Việt Nam). ${escape(labels[update.outcome] ?? 'Chờ lần chạy đầu')}${update.last_attempt_at ? ` · lần kiểm tra ${escape(timeLabel(update.last_attempt_at))}` : ''}.` : 'Chưa xác minh trạng thái lịch cập nhật.';
  const scoreLag = (Date.now() - Date.parse(state.manifest.last_valid_score_date + 'T00:00:00Z') - 86400000) / 3600000;
  const jobLag = update?.last_attempt_at ? (Date.now() - Date.parse(update.last_attempt_at)) / 3600000 : 0;
  const warning = scoreLag > 48 || jobLag > 26 ? ' Dữ liệu chậm; điểm gần nhất vẫn có ngày quan sát gốc.' : '';
  const revision = state.manifest.revision?.changed_dates?.length ? ` Revision nguồn: ${state.manifest.revision.changed_dates.length} ngày lịch sử; release cũ được giữ nguyên.` : '';
  $('freshness').innerHTML = `<b class="status-dot"></b><span>Nguồn đến ${dateLabel(last)} · cách hiện tại ${age} ngày UTC${missing ? ` · ${missing} ngày đã đóng thiếu dữ liệu` : ''}${pending.length ? ` · ngày chờ ${pending.map(d => escape(dateLabel(d))).join(', ')} (chưa đóng lúc tải)` : ''}. ${schedule}${warning}${revision}</span>`;
}
function activeMetrics() { return state.mode === 'core' ? METRICS : state.mode === 'extended' ? EXTENDED_METRICS : CORE_METRICS; }
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
    return `<tr><td><input type="checkbox" data-metric="${m.id}" aria-label="Chọn ${m.slot} ${m.name}" ${active.includes(m.id) ? 'checked' : ''} ${state.mode !== 'custom' ? 'disabled' : ''}></td><td><span class="metric-id">${m.slot}${m.kind==='proxy'?' · proxy':m.kind==='derived'?' · dẫn xuất':''}</span><span class="metric-name">${m.name}</span><div class="metric-description">${m.description}${m.limitation?`<br><span title="${escape(m.limitation)}">${escape(m.interpretation)}</span>`:''}${original?`<br>Giá trị gốc: ${escape(original)}`:''}</div></td><td><div class="metric-score"><strong style="color:${scoreColor(value)}" title="${value === null ? escape(reason) : fmt(value, 4)}">${displayScore(value)}</strong><div class="mini-meter"><span style="width:${value ?? 0}%;background:${scoreColor(value)}"></span></div></div></td><td>${fmt(weight, 3)}%</td><td><span class="status-pill ${value === null || flash ? 'missing' : 'ready'}" title="${value === null ? escape(reason) : flash ? 'Nhãn sàn và số liệu tạm thời; có thể sửa hồi cứu' : 'Đã chuẩn hóa causal q05/q95'}">${value === null ? 'Chưa đủ' : flash ? 'Tạm thời · flash' : 'Khả dụng'}</span></td></tr>`;
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
  $('range-label').textContent = `${dateLabel(rows[0].date)} – ${dateLabel(rows.at(-1).date)} · ${rows.length.toLocaleString('vi-VN')} ngày`;
  $('custom-legend').hidden = !custom;
  const series = [{ name: 'Core 10', type: 'line', data: rows.map(r => [r.date, r.score]), showSymbol: false, connectNulls: false, lineStyle: { width: state.mode === 'ten'?1.9:1.2, color: '#087f72' }, itemStyle: { color: '#087f72' }, z: 3 },
    { name:'ECO 7',type:'line',data:rows.map(r=>[r.date,r.extended_score]),showSymbol:false,connectNulls:false,lineStyle:{width:state.mode==='extended'?1.9:1.1,color:'#a87b48',type:'dotted'},itemStyle:{color:'#a87b48'},z:2 },
    { name: 'Core 4', type: 'line', data: rows.map(r=>[r.date,r.core_score]),showSymbol:false,connectNulls:false,lineStyle:{width:state.mode==='core'?1.9:1.2,color:'#7b62a3',type:'dashed'},itemStyle:{color:'#7b62a3'},z:2 }];
  if (custom) series.push({ name: 'Tùy chỉnh', type: 'line', data: rows.map(r => [r.date, coreScore(r, state.selected)]), showSymbol: false, connectNulls: false, lineStyle: { width: 1.5, color: '#bb790b', type: 'dashed' }, itemStyle: { color: '#bb790b' }, z: 4 });
  series.push({ name: 'Giá ETH', type: 'line', yAxisIndex: 1, data: rows.map(r => [r.date, r.price_usd]), showSymbol: false, connectNulls: false, lineStyle: { width: 1.2, color: '#455554', opacity: .7 }, itemStyle: { color: '#455554' }, z: 1 });
  historyChart.setOption({ animation: false, aria: { enabled: true }, grid: { left: mobile ? 34 : 42, right: mobile ? 50 : 66, top: 28, bottom: 48 }, textStyle: { fontFamily: 'Segoe UI, Arial, sans-serif' }, tooltip: { trigger: 'axis', confine: true, backgroundColor: '#fff', borderColor: '#dfe6e5', textStyle: { color: '#232b2b' }, formatter: params => {
    const date = params[0]?.value?.[0];
    if (!date) return '';
    return `<div class="ec-tooltip"><strong>${escape(dateLabel(date))} · UTC</strong>${params.map(p => `${escape(p.seriesName)}<span>${p.value[1] === null ? '—' : p.seriesName === 'Giá ETH' ? '$' + fmt(p.value[1]) : fmt(p.value[1], 2)}</span><br>`).join('')}</div>`;
  } }, xAxis: { type: 'time', axisLine: { lineStyle: { color: '#dfe6e5' } }, axisTick: { show: false }, axisLabel: { fontSize: 10, color: '#687575', hideOverlap: true }, splitNumber: mobile ? 4 : 8 }, yAxis: [{ type: 'value', min: 0, max: 100, interval: 25, name: 'Điểm', nameTextStyle: { color: '#087f72', fontSize: 10, align: 'left' }, axisLabel: { color: '#687575', fontSize: 10 }, splitLine: { lineStyle: { color: '#e7eeeb' } } }, { type: $('log-price').checked ? 'log' : 'value', name: 'USD', nameTextStyle: { color: '#687575', fontSize: 10 }, axisLabel: { color: '#687575', fontSize: 9, formatter: value => value >= 1000 ? `${Math.round(value / 1000)}k` : `${value}` }, splitLine: { show: false } }], dataZoom: [{ type: 'inside', filterMode: 'none', zoomOnMouseWheel: false, moveOnMouseWheel: false }, { type: 'slider', height: 13, bottom: 6, borderColor: 'transparent', backgroundColor: '#edf3f0', fillerColor: '#087f7217', handleStyle: { color: '#7ba79c' }, showDetail: false, brushSelect: false }], series }, { notMerge: true });
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
  for (const [label, value] of [ ['Release Core 10', m.release_id], ['Core 4 cha', m.parents.core.release_id], ['Proxy cha', m.parents.proxies.release_id], ['ECO 7 cha',m.parents.extended.release_id], ['Diagnostics cha',m.parents.diagnostics.release_id], ['Protocol SHA-256', m.protocol_sha256], ['Engine SHA-256', m.engine_sha256], ['Tính điểm UTC', m.computed_at], ['Revision', m.revision ? `${m.revision.reason} · trước đó ${m.revision.previous_release_id??'không có'}` : 'Release nghiên cứu ban đầu'], ['Availability lịch sử', 'Không biết; không gọi lịch sử là as-published'], ['Phạm vi', `${m.rows} ngày lịch · ${m.score_rows} ngày có Core 10 · bắt đầu ${m.first_score_date}`] ]) {
    const dt = document.createElement('dt'); dt.textContent = label;
    const dd = document.createElement('dd'); dd.textContent = value;
    $('provenance').append(dt, dd);
  }
  const r = state.extendedResearch;
  $('core-ten-performance').textContent = `AP thăm dò: Core 10 ${fmt(r.statistics.core_ten.average_precision,3)} / Core 4 ${fmt(r.statistics.core.average_precision,3)}. Xem Kiểm định.`;
  $('extended-evaluation').textContent = `${r.n.toLocaleString('vi-VN')} ngày đánh giá ${dateLabel(r.start)}–${dateLabel(r.end)}, ${r.positive_labels} nhãn dương. AP Core 10 ${fmt(r.statistics.core_ten.average_precision,4)}, Core 4 ${fmt(r.statistics.core.average_precision,4)}; Δ AP ${fmt(r.comparisons.core.ap_delta,4)}. Holdout đã dùng lại; kết quả thăm dò, ${r.comparisons.core.upper_95<0?'thấp hơn Core 4 trong khoảng tin cậy này':'chưa chứng minh cải thiện dự báo'}.`;
  $('extended-results').innerHTML = Object.entries(r.statistics).map(([n,v])=>`<tr><td>${n==='core_ten'?'Core 10':baselineNames[n]??n}</td><td>${fmt(v.average_precision,4)}</td><td>${n==='core_ten'?'—':fmt(r.comparisons[n].ap_delta,4)}</td><td>${n==='core_ten'?'—':`[${fmt(r.comparisons[n].lower_95,4)}; ${fmt(r.comparisons[n].upper_95,4)}]`}</td></tr>`).join('');
  $('extended-research-link').href = `/data/core-v2/releases/${m.release_id}/research.json`;
}
function view(name) {
  state.view = name;
  document.querySelectorAll('.view').forEach(node => { node.hidden = node.id !== `view-${name}`; });
  document.querySelectorAll('[data-view]').forEach(node => { node.classList.toggle('active', node.dataset.view === name); if (node.dataset.view === name) node.setAttribute('aria-current', 'page'); else node.removeAttribute('aria-current'); });
  history.replaceState(null, '', name === 'dashboard' ? location.pathname : `#${name}`);
  if (state.rows.length) requestAnimationFrame(() => { if (name === 'research') plotResearch(); if (name === 'dashboard') historyChart.resize(); if (name === 'extended') resizeProxies(); if (name === 'diagnostics') resizeDiagnostics(); });
}
function start() {
  icons();
  initProxies();
  initDiagnostics();
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
  $('latest-day').addEventListener('click', () => { if (state.rows.length) selectDate(state.mode==='core'?state.coreManifest.last_valid_score_date:state.mode==='extended'?state.extendedManifest.last_valid_score_date:state.manifest.last_valid_score_date, true); });
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
  new ResizeObserver(() => { historyChart?.resize(); researchChart?.resize(); }).observe(document.querySelector('main'));
  if (['#research', '#methodology', '#extended', '#diagnostics'].includes(location.hash)) view(location.hash.slice(1));
  setInterval(() => { if (!document.hidden) load(); }, 15 * 60 * 1000);
  document.addEventListener('visibilitychange', () => { if (!document.hidden && Date.now() - state.lastChecked > 60000) load(); });
  load();
}
if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', start, { once: true }); else start();
