import { METRICS, dateMinus } from './data-model.js?v=dashboard-1';
import { EXTENDED_METRICS, extendedScore } from './extended-model.js?v=extended-1';
export const CORE_VERSION = 'core-v0.2.0';
export const CORE_PROTOCOL_HASH = '43fc1f29c02868f4d1f5b02ed0f121fc15d9e79e5f886dbaf2061e8b8837d404';
const weights = { E1:.125, E5:.125, E6:.125, E7:.1875, exchange_share:.03125, address_activity:.0625, value_per_transfer:.0625, E2:.1875, supply_scarcity:.0625, exchange_balance_pressure:.03125 };
export const NEW_FEATURES = {
  E2: { input:'nupl_diagnostic', unit:'ratio', sign:1, hypothesis:'larger_unrealized_profit_higher_valuation_heat' },
  supply_scarcity: { input:'supply_change_30d', unit:'percent', sign:-1, hypothesis:'lower_net_supply_growth_higher_relative_scarcity_heat_not_price_forecast' },
  exchange_balance_pressure: { input:'exchange_balance_change_30d', unit:'ETH', sign:1, hypothesis:'larger_exchange_balance_increase_higher_potential_selling_availability_not_gross_inflow' },
};
export const CORE_GROUPS = { price:{weight:.375,members:['E1','E5','E6']}, valuation:{weight:.375,members:['E7','E2'],dependence:'shared_MVRV_family_not_independent_votes'}, network:{weight:.25,families:{exchange:{weight:.0625,members:['exchange_share','exchange_balance_pressure']},supply:{weight:.0625,members:['supply_scarcity']},addresses:{weight:.0625,members:['address_activity']},transfers:{weight:.0625,members:['value_per_transfer']}}} };
export const CORE_NORMALIZER = { method:'past_only_linear_q05_q95_clip_0_100',window_calendar_days:1460,minimum_valid_observations:365,exclude_current:true,epsilon:1e-12,input_calendar:'full_pinned_diagnostics_calendar' };
export const CORE_METRICS = [
  ...EXTENDED_METRICS.map(m=>({...m,weight:weights[m.id],kind:m.formula?'proxy':'core'})),
  { id:'E2',slot:'E2',name:'NUPL',weight:weights.E2,kind:'derived',description:'Lợi nhuận chưa thực hiện · 1 − 1/MVRV',interpretation:'Chia nhóm định giá với E7',limitation:'Cùng họ MVRV, không phải nguồn xác nhận độc lập' },
  { id:'supply_scarcity',slot:'C1',name:'Khan hiếm nguồn cung',weight:weights.supply_scarcity,kind:'derived',description:'Âm của % thay đổi nguồn cung 30 ngày',interpretation:'Tăng cung ròng thấp → điểm cao',limitation:'Chiều tính là giả thuyết nghiên cứu; chịu thay đổi cơ chế phát hành và burn' },
  { id:'exchange_balance_pressure',slot:'C2',name:'Biến động số dư sàn',weight:weights.exchange_balance_pressure,kind:'derived',description:'Số dư ETH trên sàn t − t−30',interpretation:'Tăng số dư sàn → điểm cao',limitation:'Không phải tổng nạp/rút; nhãn địa chỉ có thể thiếu và sửa hồi cứu' },
];
const ids = CORE_METRICS.map(m=>m.id), newIds = Object.keys(NEW_FEATURES);
const same = (a,b) => JSON.stringify(canonical(a)) === JSON.stringify(canonical(b));
function canonical(v) { return Array.isArray(v)?v.map(canonical):v && typeof v==='object'?Object.fromEntries(Object.keys(v).sort().map(k=>[k,canonical(v[k])])):v; }
const keys = (v,expected) => v && typeof v==='object' && !Array.isArray(v) && Object.keys(v).sort().join()===expected.toSorted().join();
const finite = v => typeof v==='number' && Number.isFinite(v);
const scoreEqual = (a,b) => a===null?b===null:finite(b) && Math.abs(a-b)<=1e-8;
export function coreScore(row, selected=ids) {
  if (!selected.length || new Set(selected).size!==selected.length || selected.some(id=>!ids.includes(id))) return null;
  const chosen=CORE_METRICS.filter(m=>selected.includes(m.id));
  if (chosen.some(m=>!finite(row.components[m.id]) || row.components[m.id]<0 || row.components[m.id]>100)) return null;
  if (chosen.length===1) return row.components[chosen[0].id];
  return chosen.reduce((s,m)=>s+row.components[m.id]*m.weight,0)/chosen.reduce((s,m)=>s+m.weight,0);
}
export function validateCorePointer(p) {
  if (!/^core10-[a-f0-9]{20}$/.test(p?.release_id) || p.methodology_version!==CORE_VERSION
      || p.manifest_url!==`/data/core-v2/releases/${p.release_id}/manifest.json` || !/^[a-f0-9]{64}$/.test(p.manifest_sha256)) throw new Error('Pointer Core 10 không hợp lệ.');
}
const parentSpecs = {
  core:['core','/data/','core-v0.1.0','da76f0d4357f54fc319d49e57323e95f3bd33338a2b5774a5cda54e228ce7d09'],
  proxies:['proxy','/data/network-proxies/','network-proxies-v0.1.0','4f3b9ebdf2ce0c69704174c47cd5183731942b1051321e33596d80d39f71af2c'],
  extended:['extended','/data/extended/','extended-v0.1.0','719b9873e7e96546f829df915051d993dafbb960e53878495c1bce249c948bcb'],
  diagnostics:['diagnostic','/data/diagnostics/','diagnostics-v0.1.0','fb7f5b80ca84ffc4babb8b5ffe823574500f13fed31fc03a3a25922da76afc4a'],
};
export function validateCoreParents(manifest, parents) {
  if (!keys(manifest.parents,Object.keys(parentSpecs))) throw new Error('Thiếu release cha Core 10.');
  for (const [kind,[prefix,path,version,protocolHash]] of Object.entries(parentSpecs)) {
    const ref=manifest.parents[kind], m=parents[kind];
    if (!new RegExp(`^${prefix}-[a-f0-9]{20}$`).test(ref?.release_id) || ref.manifest_url!==`${path}releases/${ref.release_id}/manifest.json`
        || ref.methodology_version!==version || !/^[a-f0-9]{64}$/.test(ref.manifest_sha256) || !/^[a-f0-9]{64}$/.test(ref.history_sha256)
        || m.release_id!==ref.release_id || m.methodology_version!==version || m.protocol_sha256!==protocolHash
        || m.files['history.json']!==ref.history_sha256 || m.last_observation_date!==ref.last_observation_date) throw new Error('Nguồn cha Core 10 không khớp.');
  }
  const lineage={core:manifest.parents.core,proxies:manifest.parents.proxies};
  if (!same(parents.extended.parents,lineage) || !same(parents.diagnostics.parents,lineage)
      || parents.diagnostics.role!=='raw_diagnostics_only' || parents.diagnostics.normalizer!==null || parents.diagnostics.core_promotion!==false
      || parents.diagnostics.composite_score!==null || !same(manifest.private_inputs_verified,parents.diagnostics.private_inputs_verified)) throw new Error('Lineage Core 10 chưa đồng bộ.');
  for (const kind of ['core','proxies']) {
    const proof=manifest.private_inputs_verified[kind];
    if (proof.canonical_sha256!==parents[kind].snapshot_sha256 || proof.objects_readback_verified!==true
        || proof.file_count!==(kind==='core'?7:8)) throw new Error('Snapshot/readback Core 10 không khớp.');
  }
}
export function validateCore(history, manifest, research) {
  if (manifest.methodology_version!==CORE_VERSION || manifest.protocol_sha256!==CORE_PROTOCOL_HASH || manifest.protocol!==`${CORE_VERSION}-protocol-1`
      || manifest.asset!=='eth' || manifest.series_type!=='reconstructed' || manifest.research_only!==true || manifest.required_coverage!==10
      || manifest.attribution?.licence!=='CC BY-NC 4.0' || manifest.attribution?.scope!=='noncommercial_research_preview' || manifest.source_available_at!==null
      || !same(manifest.groups,CORE_GROUPS) || !same(manifest.new_features,NEW_FEATURES) || !same(manifest.normalizer,CORE_NORMALIZER)
      || !same(manifest.weights,weights) || !same(history.weights,weights) || history.schema_version!=='1.0.0'
      || history.release_id!==manifest.release_id || history.methodology_version!==CORE_VERSION || history.asset!=='eth' || history.series_type!=='reconstructed'
      || !Array.isArray(history.rows) || !history.rows.length || history.rows.length!==manifest.rows
      || research.methodology_version!==CORE_VERSION || research.protocol!==manifest.protocol || research.status!=='exploratory_reconstructed_only'
      || research.bootstrap?.replicates!==10000 || research.bootstrap.block_calendar_days!==90 || research.bootstrap.seed!==20261003
      || research.decision!=='publish_experimental_preview_no_predictive_validation_claim'
      || !keys(research.statistics,['core_ten','core','extended','normalized_E7_only','normalized_price_group_only'])
      || !research.limitations?.includes('reused_holdout_is_exploratory')) throw new Error('Hợp đồng Core 10 không hợp lệ.');
  let previous=null;
  for (const r of history.rows) {
    if (!/^\d{4}-\d{2}-\d{2}$/.test(r.date) || dateMinus(r.date,0)!==r.date || previous && dateMinus(r.date,1)!==previous
        || !keys(r.components,ids) || !keys(r.reasons,ids) || !keys(r.source_flags,ids) || !keys(r.new_features,newIds)) throw new Error('Calendar/thành phần Core 10 không hợp lệ.');
    const values=Object.values(r.components), expected=coreScore(r);
    const legacy=METRICS.some(m=>r.components[m.id]===null)?null:METRICS.reduce((s,m)=>s+r.components[m.id]*m.weight,0);
    if (values.some(v=>v!==null && (!finite(v) || v<0 || v>100)) || values.filter(v=>v!==null).length!==r.coverage
        || typeof r.period_closed_at_retrieval!=='boolean' || !scoreEqual(r.period_closed_at_retrieval?expected:null,r.score)
        || !scoreEqual(legacy,r.core_score) || !scoreEqual(extendedScore(r),r.extended_score)
        || (r.price_usd!==null && (!finite(r.price_usd) || r.price_usd<=0)) || (!r.period_closed_at_retrieval && r.price_usd!==null)
        || typeof r.source_row_present!=='boolean' || typeof r.proxy_row_present!=='boolean'
        || ids.some(id=>!Array.isArray(r.source_flags[id]) || r.source_flags[id].some(f=>typeof f!=='string' || !f || f.length>80)
          || (r.components[id]===null?typeof r.reasons[id]!=='string':r.reasons[id]!==null))) throw new Error('Điểm/coverage Core 10 không hợp lệ.');
    for (const id of newIds) {
      const f=r.new_features[id],spec=NEW_FEATURES[id];
      if (!keys(f,['raw','score','reason','history_count','lower','upper','input_value','input_unit','source_flags']) || f.input_unit!==spec.unit
          || (f.input_value!==null && (!finite(f.input_value) || id==='E2' && f.input_value>=1))
          || f.raw!==(f.input_value===null?null:spec.sign*f.input_value) || f.score!==r.components[id] || f.reason!==r.reasons[id]
          || !same(f.source_flags,r.source_flags[id]) || !Number.isInteger(f.history_count) || f.history_count<0 || f.history_count>1460
          || (f.history_count<365 ? f.lower!==null || f.upper!==null : !finite(f.lower) || !finite(f.upper) || f.lower>f.upper)) throw new Error('Feature chuẩn hóa Core 10 không hợp lệ.');
      const expectedFeature=f.raw===null || f.history_count<365 || f.upper-f.lower<=1e-12?null:Math.max(0,Math.min(100,100*(f.raw-f.lower)/(f.upper-f.lower)));
      if (!scoreEqual(expectedFeature,f.score) || (f.raw!==null && f.history_count<365 && f.reason!=='normalizer_warmup')
          || (f.raw!==null && f.history_count>=365 && f.upper-f.lower<=1e-12 && f.reason!=='degenerate_normalizer')) throw new Error('Điểm chuẩn hóa Core 10 không khớp.');
    }
    previous=r.date;
  }
  const valid=history.rows.filter(r=>r.score!==null);
  if (valid.length!==manifest.score_rows || valid[0]?.date!==manifest.first_score_date || valid.at(-1)?.date!==manifest.last_valid_score_date
      || valid.at(-1)?.score!==manifest.last_valid_score || history.rows[0].date!==manifest.first_observation_date || history.rows.at(-1).date!==manifest.last_observation_date) throw new Error('Phạm vi Core 10 không khớp.');
}
export function exportCoreCSV(rows, selected, mode, manifest) {
  const quote=v=>`"${String(v??'').replaceAll('"','""')}"`;
  const chosen=mode==='custom'?selected:ids;
  const columns=['date_utc','price_usd','core_ten_score','custom_score',...ids,'coverage',...ids.map(id=>id+'_reason'),...ids.map(id=>id+'_source_flags'),...newIds.flatMap(id=>[id+'_input_value',id+'_input_unit',id+'_oriented_raw']),'methodology_version','release_id','core_parent_release','proxy_parent_release','extended_parent_release','diagnostic_parent_release','series_type','mode','selected_components','source','license','license_url','modifications'];
  const lines=rows.map(r=>[r.date,r.price_usd,r.score,mode==='custom'?coreScore(r,selected):null,...ids.map(id=>r.components[id]),r.coverage,...ids.map(id=>r.reasons[id]),...ids.map(id=>r.source_flags[id].join('|')),...newIds.flatMap(id=>[r.new_features[id].input_value,r.new_features[id].input_unit,r.new_features[id].raw]),manifest.methodology_version,manifest.release_id,...['core','proxies','extended','diagnostics'].map(k=>manifest.parents[k].release_id),'reconstructed',mode,chosen.join('|'),'Coin Metrics Community Data','CC BY-NC 4.0',manifest.license_url,'Core 10 normalized and aggregated; signed inputs retained; no endorsement; no warranties'].map(quote).join(','));
  return '\uFEFF'+[columns.join(','),...lines].join('\r\n');
}
