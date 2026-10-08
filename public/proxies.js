import { PROXIES, validateProxyPointer, validateProxyRelease, exportProxyCSV } from './proxy-model.js?v=proxies-1';
import { numberLocale, translate } from './i18n.js?v=calendar-20261008c';
const $ = id => document.getElementById(id);
const dateLabel = d => new Intl.DateTimeFormat(numberLocale(),{day:'2-digit',month:'2-digit',year:'numeric',timeZone:'UTC'}).format(new Date(`${d}T00:00:00Z`));
const fmt = (v, n=2) => v === null ? '—' : v.toLocaleString(numberLocale(),{maximumFractionDigits:n,minimumFractionDigits:n});
const escape = value => String(value).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const reasonNames = {feature_warmup:'Chưa đủ cửa sổ SMA',missing_input_or_window:'Thiếu dữ liệu trong cửa sổ',nonpositive_log_argument:'Đối số log không dương',normalizer_warmup:'Chưa đủ 365 raw quá khứ',degenerate_normalizer:'Biên chuẩn hóa trùng nhau',raw_unavailable:'Raw chưa khả dụng'};
const state = { history:null, manifest:null, research:null, date:null, followLatest:true, busy:false, chart:null, range:'all', checked:0 };
async function bytes(url, fresh=false) {
  const r = await fetch(url,{cache:fresh?'no-cache':'default',signal:AbortSignal.timeout(20000)});
  if (!r.ok) throw new Error(`Không tải được metric mở rộng (HTTP ${r.status}).`);
  return new Uint8Array(await r.arrayBuffer());
}
async function verified(url, hash) {
  const data = await bytes(url);
  const actual = [...new Uint8Array(await crypto.subtle.digest('SHA-256',data))].map(v=>v.toString(16).padStart(2,'0')).join('');
  if (actual !== hash) throw new Error('Checksum metric mở rộng không khớp.');
  return JSON.parse(new TextDecoder().decode(data));
}
export async function loadProxies() {
  if (state.busy) return;
  state.busy = true; $('proxy-refresh').disabled=true; $('proxy-error').hidden=true;
  try {
    const pointer = JSON.parse(new TextDecoder().decode(await bytes('/data/network-proxies/latest.json',true)));
    validateProxyPointer(pointer);
    const manifest = await verified(pointer.manifest_url,pointer.manifest_sha256);
    if (manifest.release_id !== pointer.release_id) throw new Error('Manifest proxy không khớp pointer.');
    const base = `/data/network-proxies/releases/${pointer.release_id}/`;
    const [history,research] = await Promise.all(['history.json','research.json'].map(n=>verified(base+n,manifest.files[n])));
    validateProxyRelease(history,manifest,research);
    let status=null;
    try { status=JSON.parse(new TextDecoder().decode(await bytes('/data/network-proxies/status.json',true))); } catch { /* Keep verified data usable. */ }
    state.history=history;state.manifest=manifest;state.research=research;state.checked=Date.now();
    if (state.followLatest || !history.rows.some(r=>r.date===state.date)) state.date=history.rows.at(-1).date;
    $('proxy-date').min=history.rows[0].date;$('proxy-date').max=history.rows.at(-1).date;
    $('proxy-loading').hidden=true;$('proxy-content').hidden=false;
    $('proxy-manifest').href=pointer.manifest_url;$('proxy-research-json').href=base+'research.json';
    const coverage=PROXIES.map(m=>`${m.slot}: ${manifest.coverage[m.id].normalized_rows.toLocaleString(numberLocale())} ${translate('ngày có điểm, từ')} ${dateLabel(manifest.coverage[m.id].first_score_date)}`).join(' · ');
    const failure=status?.release_id===pointer.release_id && status.outcome==='failed'?` ${translate('Lần cập nhật gần nhất lỗi; đang giữ bản đã xác minh.')}`:'';
    $('proxy-freshness').textContent=`${translate('Nguồn đến')} ${dateLabel(manifest.last_observation_date)} · ${coverage}.${status?.schedule_vi?` ${translate('Lịch kiểm tra')} ${translate(status.schedule_vi)}.`:''}${failure}`;
    const r=research;
    $('proxy-evaluation').textContent=`Đánh giá exploratory ${dateLabel(r.start)} – ${dateLabel(r.end)}: ${fmt(r.n,0)} ngày, ${fmt(r.positive_labels,0)} nhãn dương. Holdout này đã được dùng cho Core; cần dữ liệu kiểm định mới để xác nhận khả năng dự báo.`;
    $('proxy-results').innerHTML=PROXIES.map(m=>{const c=r.comparisons[`with_${m.id}_vs_core`];return `<tr><td>${m.slot} · ${m.name}</td><td>${fmt(r.statistics[m.id].average_precision,3)}</td><td>${fmt(r.statistics.core.average_precision,3)}</td><td>${fmt(c.ap_delta,4)}</td><td>[${fmt(c.lower_95,4)}; ${fmt(c.upper_95,4)}]</td></tr>`;}).join('');
    render();
  } catch(error) {
    $('proxy-loading').hidden=true;$('proxy-error').hidden=false;
    $('proxy-error-text').textContent=error.message+(state.history?' Đang giữ bản đã xác minh trước đó.':'');
  } finally { state.busy=false;$('proxy-refresh').disabled=false; }
}
function filteredRows() {
  if (state.range==='all') return state.history.rows;
  const start = new Date(Date.parse(state.history.rows.at(-1).date)-(state.range==='1y'?365:1095)*86400000).toISOString().slice(0,10);
  return state.history.rows.filter(r=>r.date>=start);
}
function render() {
  if (!state.history) return;
  const row=state.history.rows.find(r=>r.date===state.date);$('proxy-date').value=state.date;
  $('proxy-cards').innerHTML=PROXIES.map(m=>{
    const v=row.metrics[m.id];const value=v.value===null?'—':m.id==='value_per_transfer'?`$${fmt(v.value,0)} / (lượt/ngày)`:`${fmt(v.value*100,3)}%`;
    const reason=reasonNames[v.raw_reason??v.score_reason]??'';
    return `<article class="proxy-card" style="--proxy-color:${m.color}"><div class="proxy-card-heading"><span class="metric-id">${m.slot} · proxy</span><span class="status-pill ${v.score===null?'missing':'ready'}">${v.score===null?'Chưa đủ':'Nghiên cứu'}</span></div><h2>${m.name}</h2><div class="proxy-score">${v.score===null?'—':fmt(v.score,1)}<small>/ 100</small></div><p class="small">${m.description}</p><p class="small muted">${value} · ${dateLabel(row.date)} UTC${reason?'<br>'+reason:''}${v.source_flags.length?'<br>Cờ nguồn: '+escape(v.source_flags.join(', '))+' · tạm thời':''}</p><p class="small">${m.interpretation}</p><details><summary>Công thức & giới hạn</summary><p><code>${m.formula}</code></p><p class="small">${m.limitation}</p></details></article>`;
  }).join('');
  plot();
}
function plot() {
  if (!state.history || $('view-extended').hidden || $('workspace').hidden) return;
  if (!state.chart) {
    state.chart=window.echarts.init($('proxy-chart'));
    state.chart.on('click',p=>{if(p.data?.[0]) {state.date=p.data[0];state.followLatest=false;render();}});
  }
  const rows=filteredRows();const mobile=innerWidth<=600;
  state.chart.setOption({animation:false,aria:{enabled:true},legend:{data:PROXIES.map(m=>m.slot+' '+translate('proxy')),textStyle:{fontSize:11},top:8},
    grid:{left:mobile?32:45,right:18,top:48,bottom:40},tooltip:{trigger:'axis',confine:true},
    xAxis:{type:'time',splitNumber:mobile?4:8,axisLabel:{fontSize:10,hideOverlap:true}},
    yAxis:{type:'value',min:0,max:100,interval:25,axisLabel:{fontSize:10},splitLine:{lineStyle:{color:'#e7eeeb'}}},
    dataZoom:[{type:'inside',zoomOnMouseWheel:false},{type:'slider',height:14,bottom:4,showDetail:false}],
    series:PROXIES.map(m=>({name:m.slot+' '+translate('proxy'),type:'line',showSymbol:false,connectNulls:false,
      data:rows.map(r=>[r.date,r.metrics[m.id].score]),lineStyle:{color:m.color,width:1.5},itemStyle:{color:m.color}}))},{notMerge:true});
  state.chart.resize();
}
export function resizeProxies() { plot();state.chart?.resize(); }
export function initProxies() {
  document.addEventListener('eco-language-changed',render);
  $('proxy-refresh').addEventListener('click',loadProxies);$('proxy-retry').addEventListener('click',loadProxies);
  $('proxy-date').addEventListener('change',e=>{if(state.history?.rows.some(r=>r.date===e.target.value)){state.date=e.target.value;state.followLatest=false;render();}else e.target.value=state.date??'';});
  $('proxy-latest').addEventListener('click',()=>{if(state.history){state.date=state.history.rows.at(-1).date;state.followLatest=true;render();}});
  document.querySelectorAll('[data-proxy-range]').forEach(b=>b.addEventListener('click',()=>{
    state.range=b.dataset.proxyRange;document.querySelectorAll('[data-proxy-range]').forEach(n=>{n.classList.toggle('active',n===b);n.setAttribute('aria-pressed',String(n===b));});plot();
  }));
  $('proxy-export').addEventListener('click',()=>{
    if (!state.history) return;
    const url=URL.createObjectURL(new Blob([exportProxyCSV(filteredRows(),state.manifest)],{type:'text/csv;charset=utf-8'}));
    const a=document.createElement('a');a.href=url;a.download=`eco-${state.manifest.release_id}-${state.range}.csv`;a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);
  });
  new ResizeObserver(()=>state.chart?.resize()).observe($('proxy-chart'));
  setInterval(()=>{if(!document.hidden)loadProxies();},15*60*1000);
  document.addEventListener('visibilitychange',()=>{if(!document.hidden && Date.now()-state.checked>60000)loadProxies();});
  loadProxies();
}
