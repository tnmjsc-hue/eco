import { DIAGNOSTICS, validateDiagnosticPointer, validateDiagnosticRelease, diagnosticRange, exportDiagnosticCSV } from './diagnostic-model.js?v=diagnostics-1';
import { numberLocale, translate } from './i18n.js?v=calendar-20261008b';
const $ = id => document.getElementById(id);
const dateLabel = d => new Intl.DateTimeFormat(numberLocale(),{day:'2-digit',month:'2-digit',year:'numeric',timeZone:'UTC'}).format(new Date(`${d}T00:00:00Z`));
const fmt = (v,n=3) => v===null?'—':v.toLocaleString(numberLocale(),{minimumFractionDigits:n,maximumFractionDigits:n});
const escape = v => String(v).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const reasons={missing_input:'MVRV thiếu hoặc không dương',invalid_mvrv:'MVRV không hợp lệ',nonpositive_mvrv:'MVRV không dương',parent_day_unavailable:'Nguồn chưa có ngày này',window_warmup:'Chưa đủ 31 ngày quan sát',missing_or_invalid_window:'Thiếu dữ liệu hợp lệ trong cửa sổ 31 ngày',invalid_derived_value:'Phép tính không cho giá trị hữu hạn'};
const state={history:null,manifest:null,manifestHash:null,date:null,followLatest:true,busy:false,checked:0,range:'all',start:null,end:null,metric:DIAGNOSTICS[0].id,chart:null};
async function bytes(url,fresh=false) {
  const r=await fetch(url,{cache:fresh?'no-cache':'default',signal:AbortSignal.timeout(20000)});
  if(!r.ok)throw new Error(`Không tải được chỉ số chẩn đoán (HTTP ${r.status}).`);
  return new Uint8Array(await r.arrayBuffer());
}
const decode = data => JSON.parse(new TextDecoder().decode(data));
async function verified(url,hash) {
  const data=await bytes(url);
  const actual=[...new Uint8Array(await crypto.subtle.digest('SHA-256',data))].map(v=>v.toString(16).padStart(2,'0')).join('');
  if(actual!==hash)throw new Error('Checksum chỉ số chẩn đoán không khớp.');
  return decode(data);
}
export async function loadDiagnostics() {
  if(state.busy)return;
  state.busy=true;$('diag-refresh').disabled=true;$('diag-error').hidden=true;
  try {
    const pointer=decode(await bytes('/data/diagnostics/latest.json',true));validateDiagnosticPointer(pointer);
    if(state.manifest?.release_id===pointer.release_id && state.manifestHash!==pointer.manifest_sha256)throw new Error('Release chẩn đoán đã công bố bị thay đổi.');
    const manifest=await verified(pointer.manifest_url,pointer.manifest_sha256);
    if(manifest.release_id!==pointer.release_id)throw new Error('Manifest chẩn đoán không khớp pointer.');
    const base=`/data/diagnostics/releases/${pointer.release_id}/`;
    const [history,report]=await Promise.all(['history.json','research.json'].map(n=>verified(base+n,manifest.files[n])));
    validateDiagnosticRelease(history,manifest,report);
    let status=null;
    try {status=decode(await bytes('/data/diagnostics/status.json',true));}catch { /* Verified history remains available. */ }
    state.history=history;state.manifest=manifest;state.manifestHash=pointer.manifest_sha256;state.checked=Date.now();
    if(state.followLatest || !history.rows.some(r=>r.date===state.date))state.date=history.rows.at(-1).date;
    state.start??=history.rows[0].date;state.end??=history.rows.at(-1).date;
    if(state.range!=='custom') {const rows=filtered();state.start=rows[0].date;state.end=rows.at(-1).date;}
    for(const id of ['diag-date','diag-start','diag-end']) {$(id).min=history.rows[0].date;$(id).max=history.rows.at(-1).date;}
    $('diag-start').value=state.start;$('diag-end').value=state.end;
    $('diag-loading').hidden=true;$('diag-content').hidden=false;
    $('diag-manifest').href=pointer.manifest_url;$('diag-report').href=base+'research.json';
    $('diag-freshness').textContent=`${translate('Nguồn đến')} ${dateLabel(manifest.last_observation_date)} · ${DIAGNOSTICS.map(d=>d.slot+': '+manifest.coverage[d.id].valid_rows.toLocaleString(numberLocale())+' '+translate('ngày hợp lệ')).join(' · ')}.${status?.schedule_vi?` ${translate(status.schedule_vi)}.`:''}${status?.outcome==='failed'?` ${translate('Lần cập nhật gần nhất lỗi; đang giữ bản đã xác minh.')}`:''}`;
    $('diag-lineage').textContent=`${translate('Phiên bản')} ${manifest.methodology_version} · E2 ${translate('dùng snapshot Core')} ${manifest.parents.core.release_id}; C1/C2 ${translate('dùng snapshot')} ${manifest.parents.proxies.release_id}. ${translate('Thời điểm nguồn sẵn có trong quá khứ chưa được xác định.')}`;
    $('diag-coverage').innerHTML=DIAGNOSTICS.map(d=>{const c=report.coverage[d.id];return `<tr><td>${d.slot} · ${d.name}</td><td>${fmt(c.valid_rows,0)}</td><td>${fmt(c.null_rows,0)}</td><td>${c.first_valid_date?dateLabel(c.first_valid_date):'—'}</td><td>${fmt(c.negative_rows,0)}</td><td>${fmt(c.flagged_rows,0)}</td></tr>`;}).join('');
    render();
  }catch(error) {
    $('diag-loading').hidden=true;$('diag-error').hidden=false;
    $('diag-error-text').textContent=error.message+(state.history?' Đang giữ bản đã xác minh trước đó.':'');
  }finally {state.busy=false;$('diag-refresh').disabled=false;}
}
const filtered = () => diagnosticRange(state.history.rows,state.range,state.start,state.end);
function render() {
  if(!state.history)return;
  const row=state.history.rows.find(r=>r.date===state.date);$('diag-date').value=state.date;
  $('diag-prev').disabled=state.date===state.history.rows[0].date;$('diag-next').disabled=state.date===state.history.rows.at(-1).date;
  $('diag-cards').innerHTML=DIAGNOSTICS.map(d=>{
    const v=row.metrics[d.id],label=v.value===null?'—':fmt(v.value*d.scale,d.unit==='ETH'?0:3)+(d.unit==='ETH'?' ETH':'%');
    return `<article class="proxy-card diagnostic-card" style="--proxy-color:${d.color}"><div class="proxy-card-heading"><span class="metric-id">${d.slot} · chẩn đoán</span><span class="status-pill ${v.value===null?'missing':'ready'}">${v.value===null?'Chưa đủ':'Đã tính'}</span></div><h2>${d.name}</h2><div class="diag-value">${label}</div><p class="small">${d.description}</p><p class="small muted">${dateLabel(row.date)} UTC${v.reason?'<br>'+escape(reasons[v.reason]??v.reason):''}${v.source_flags.length?'<br>Cờ nguồn: '+escape(v.source_flags.join(', '))+' · tạm thời':''}</p><p class="small">${d.interpretation}</p><details><summary>Công thức & giới hạn</summary><p><code>${d.formula}</code></p><p class="small">${d.limitation}</p></details></article>`;
  }).join('');plot();
}
function plot() {
  if(!state.history || $('view-diagnostics').hidden || $('workspace').hidden)return;
  if(!state.chart) {
    state.chart=window.echarts.init($('diag-chart'));
    state.chart.on('click',p=>{if(p.data?.[0])selectDate(p.data[0]);});
  }
  const d=DIAGNOSTICS.find(d=>d.id===state.metric),rows=filtered(),mobile=innerWidth<=600;
  $('diag-range-label').textContent=`${dateLabel(rows[0].date)} – ${dateLabel(rows.at(-1).date)} · ${rows.length.toLocaleString(numberLocale())} ${translate('ngày')} · ${translate('nhấn đường để chọn ngày')}`;
  $('diag-chart').setAttribute('aria-label',`Lịch sử ${d.name}, đơn vị ${d.unit==='ETH'?'ETH':'phần trăm'}, có giá trị âm và ngày thiếu dữ liệu`);
  state.chart.setOption({animation:false,aria:{enabled:true},grid:{left:mobile?56:75,right:20,top:30,bottom:44},
    tooltip:{trigger:'axis',confine:true,valueFormatter:v=>v===null?'—':fmt(v,d.unit==='ETH'?0:3)+(d.unit==='ETH'?' ETH':'%')},
    xAxis:{type:'time',splitNumber:mobile?4:8,axisLabel:{fontSize:10,hideOverlap:true}},
    yAxis:{type:'value',scale:true,name:d.unit==='ETH'?'ETH':'%',axisLabel:{fontSize:10,formatter:v=>d.unit==='ETH'?Intl.NumberFormat(numberLocale(),{notation:'compact'}).format(v):fmt(v,1)},splitLine:{lineStyle:{color:'#e7eeeb'}}},
    dataZoom:[{type:'inside',zoomOnMouseWheel:false},{type:'slider',height:14,bottom:4,showDetail:false}],
    series:[{name:translate(d.name),type:'line',showSymbol:false,connectNulls:false,data:rows.map(r=>[r.date,r.metrics[d.id].value===null?null:r.metrics[d.id].value*d.scale]),
      lineStyle:{color:d.color,width:1.5},itemStyle:{color:d.color}}]},{notMerge:true});state.chart.resize();
}
function selectDate(day,latest=false) {
  if(state.history?.rows.some(r=>r.date===day)){state.date=day;state.followLatest=latest;render();}
  else $('diag-date').value=state.date??'';
}
function rangeUI() {
  document.querySelectorAll('[data-diag-range]').forEach(b=>{b.classList.toggle('active',b.dataset.diagRange===state.range);b.setAttribute('aria-pressed',String(b.dataset.diagRange===state.range));});
}
export function resizeDiagnostics() {plot();state.chart?.resize();}
export function initDiagnostics() {
  document.addEventListener('eco-language-changed',render);
  $('diag-refresh').addEventListener('click',loadDiagnostics);$('diag-retry').addEventListener('click',loadDiagnostics);
  $('diag-date').addEventListener('change',e=>selectDate(e.target.value));
  for(const [id,offset] of [['diag-prev',-1],['diag-next',1]])$(id).addEventListener('click',()=>{if(state.date)selectDate(new Date(Date.parse(state.date)+offset*86400000).toISOString().slice(0,10));});
  $('diag-latest').addEventListener('click',()=>{if(state.history)selectDate(state.history.rows.at(-1).date,true);});
  $('diag-metric').addEventListener('change',e=>{state.metric=e.target.value;plot();});
  document.querySelectorAll('[data-diag-range]').forEach(b=>b.addEventListener('click',()=>{
    state.range=b.dataset.diagRange;
    if(state.history) {const rows=filtered();state.start=rows[0].date;state.end=rows.at(-1).date;$('diag-start').value=state.start;$('diag-end').value=state.end;}
    $('diag-range-error').hidden=true;rangeUI();plot();
  }));
  $('diag-apply').addEventListener('click',()=>{
    if(!state.history)return;
    const start=$('diag-start').value,end=$('diag-end').value;
    try {diagnosticRange(state.history.rows,'custom',start,end);state.start=start;state.end=end;state.range='custom';$('diag-range-error').hidden=true;rangeUI();plot();}
    catch(error){$('diag-range-error').hidden=false;$('diag-range-error').textContent=error.message;}
  });
  $('diag-export').addEventListener('click',()=>{
    if(!state.history)return;
    const rows=filtered(),url=URL.createObjectURL(new Blob([exportDiagnosticCSV(rows,state.manifest)],{type:'text/csv;charset=utf-8'}));
    const a=document.createElement('a');a.href=url;a.download=`eco-${state.manifest.release_id}-${rows[0].date}-${rows.at(-1).date}.csv`;a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);
  });
  new ResizeObserver(()=>state.chart?.resize()).observe($('diag-chart'));
  setInterval(()=>{if(!document.hidden)loadDiagnostics();},15*60*1000);
  document.addEventListener('visibilitychange',()=>{if(!document.hidden && Date.now()-state.checked>60000)loadDiagnostics();});
  loadDiagnostics();
}
