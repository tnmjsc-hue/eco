import {loadMarket} from './macro-market-model.js?v=prob-20261009a';
import {translate as t,numberLocale} from './i18n.js?v=prob-20261009a';
const $=id=>document.getElementById(id);
const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const text=s=>esc(t(s));
const NAMES={treasury_2y:'Lợi suất Mỹ 2 năm',treasury_10y:'Lợi suất Mỹ 10 năm',real_yield_10y:'Lợi suất thực Mỹ 10 năm',usd_broad:'USD broad · Fed H.10',eth_usd:'ETH / USD',gold_usd:'Vàng / USD'};
const REASONS={missing_pair:'Chưa đủ hai ngày quan sát',missing_latest_value:'Nguồn thiếu giá trị ngày mới nhất',pair_gap:'Hai ngày quan sát cách nhau quá xa',invalid_price_or_index:'Giá hoặc chỉ số không hợp lệ',no_approved_gold_source:'Chưa có nguồn vàng được phép hiển thị',observation_expired:'Ngày quan sát đã cũ'};
let good=null,busy=false,warning=null;
const day=iso=>iso?new Intl.DateTimeFormat(numberLocale(),{timeZone:'UTC',dateStyle:'medium'}).format(new Date(iso)):'—';
const timestamp=iso=>new Intl.DateTimeFormat(numberLocale(),{timeZone:$('cal-zone').value,dateStyle:'medium',timeStyle:'short'}).format(new Date(iso));
const num=value=>value===null?'—':Number(value).toLocaleString(numberLocale(),{maximumFractionDigits:4});
export function renderMarket(){
  if(!good){$('market-error').hidden=false;$('market-error').textContent=t(warning||'Đang xác minh số đo thị trường…');return;}
  const {data:d,status,pointer}=good;
  const age=Date.now()-Date.parse(status.checked_at);
  const outdated=!!warning||status.outcome==='error'||age<0||age>48*3600000;
  $('market-error').hidden=!outdated;$('market-error').textContent=t(warning||'Giữ số đo tại ngày gốc; lần kiểm tra nguồn mới nhất chưa thành công hoặc đã quá hạn.');
  $('market-content').hidden=false;$('market-content').dataset.releaseId=d.release_id;
  $('market-date').textContent=`${t('Snapshot thị trường')}: ${timestamp(d.generated_at)} · ${t('Kiểm tra nguồn')}: ${timestamp(status.checked_at)}`;
  $('market-rows').innerHTML=d.metrics.map(m=>{
    const currentAge=(Date.parse(new Date().toISOString().slice(0,10))-Date.parse(m.latest_date))/86400000;
    const stale=m.status==='stale'||m.status==='measured'&&currentAge>m.max_age_days;
    const label=outdated?'Bản giữ tại ngày gốc':stale?'Ngày quan sát đã cũ':m.status==='measured'?'Đã đo theo ngày':'Chưa có số đo';
    const suffix=m.unit==='percent'?'%':m.unit==='USD'?' USD':m.unit==='index'?` ${t('điểm chỉ số')}`:'';
    const change=m.change===null?'—':`${Number(m.change)>0?'+':''}${num(m.change)} ${m.change_unit==='bps'?'bps':'%'}`;
    return `<tr><th>${text(NAMES[m.metric_id])}<small>${text(label)}</small>${m.source?`<a class="small" href="${esc(m.source.url)}" target="_blank" rel="noreferrer">${text('Nguồn số đo')} ↗</a>`:''}</th><td>${esc(num(m.latest))}${m.latest!==null?esc(suffix):''}<small>${esc(day(m.latest_date))} · ${text('ngày quan sát')}</small></td><td>${esc(change)}<small>${m.previous_date?`${esc(day(m.previous_date))} → ${esc(day(m.latest_date))}`:text(REASONS[m.reason]||'Chưa đủ hai ngày quan sát')}</small>${m.previous!==null?`<small>${text('Kỳ trước')}: ${esc(num(m.previous))}${esc(suffix)}</small>`:''}${m.reason&&m.previous_date?`<small>${text(REASONS[m.reason])}</small>`:''}</td></tr>`;
  }).join('');
  $('market-download').href=pointer.url;$('market-manifest').href=pointer.manifest.url;
}
export async function refreshMarket(){
  if(busy)return;busy=true;
  try{good=await loadMarket();warning=null;}catch(e){warning=e.message;}
  finally{busy=false;renderMarket();}
}
