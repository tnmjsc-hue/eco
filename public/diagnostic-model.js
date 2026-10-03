export const DIAGNOSTIC_VERSION = 'diagnostics-v0.1.0';
export const DIAGNOSTIC_PROTOCOL_HASH = 'fb7f5b80ca84ffc4babb8b5ffe823574500f13fed31fc03a3a25922da76afc4a';
export const DIAGNOSTICS = [
  {id:'nupl_diagnostic',slot:'E2',unit:'ratio',scale:100,color:'#7b62a3',name:'NUPL dẫn xuất',formula:'1 - 1 / CapMVRVCur(t)',
    description:'Lãi/lỗ chưa thực hiện theo vốn hóa thị trường và vốn hóa thực hiện.',
    interpretation:'Giá trị âm biểu thị vốn hóa thị trường thấp hơn vốn hóa thực hiện.',
    limitation:'Phụ thuộc đại số với MVRV của Core. Không phải tỷ lệ ví đang có lãi; không thêm một phiếu xác nhận độc lập.'},
  {id:'supply_change_30d',slot:'C1',unit:'percent',scale:1,color:'#087f72',name:'Thay đổi nguồn cung · 30 ngày',formula:'100 * (SplyCur(t) / SplyCur(t-30) - 1)',
    description:'Phần trăm thay đổi nguồn cung ETH trên sổ cái trong 30 ngày.',
    interpretation:'Giá trị âm là nguồn cung giảm ròng; dương là tăng ròng trong khoảng này.',
    limitation:'SplyCur là nguồn cung hiện tại trên sổ cái, khác nguồn cung lưu hành hoặc free float. Thay đổi ròng không tách riêng phát hành và đốt phí.'},
  {id:'exchange_balance_change_30d',slot:'C2',unit:'ETH',scale:1,color:'#526e91',name:'Thay đổi số dư sàn · 30 ngày',formula:'SplyExNtv(t) - SplyExNtv(t-30)',
    description:'Lượng ETH thay đổi trong các địa chỉ sàn được Coin Metrics nhận diện.',
    interpretation:'Giá trị âm là số dư giảm ròng; dương là tăng ròng. Đơn vị ETH.',
    limitation:'Không phải tổng nạp/rút hoặc toàn bộ số dư mọi sàn. Nhãn ví có thể thiếu hoặc sửa hồi cứu; cờ flash biểu thị dữ liệu nguồn tạm thời.'}
];
const hash = value => typeof value==='string' && /^[a-f0-9]{64}$/.test(value);
const fail = () => { throw new Error('Hợp đồng chỉ số chẩn đoán không hợp lệ.'); };
const same = (a,b) => JSON.stringify(a)===JSON.stringify(b);
const dateValid = day => typeof day==='string' && /^\d{4}-\d{2}-\d{2}$/.test(day) && Number.isFinite(Date.parse(day)) && new Date(day).toISOString().slice(0,10)===day;
export function validateDiagnosticPointer(p) {
  if (p.methodology_version!==DIAGNOSTIC_VERSION || !/^diagnostic-[a-f0-9]{20}$/.test(p.release_id??'')
      || p.manifest_url!==`/data/diagnostics/releases/${p.release_id}/manifest.json` || !hash(p.manifest_sha256)) fail();
}
function summary(rows,id) {
  const valid=rows.filter(r=>r.metrics[id].value!==null), values=valid.map(r=>r.metrics[id].value);
  return {valid_rows:valid.length,null_rows:rows.length-valid.length,first_valid_date:valid[0]?.date??null,last_valid_date:valid.at(-1)?.date??null,
    last_value:values.at(-1)??null,minimum:values.length?Math.min(...values):null,maximum:values.length?Math.max(...values):null,
    negative_rows:values.filter(v=>v<0).length,zero_rows:values.filter(v=>v===0).length,flagged_rows:rows.filter(r=>r.metrics[id].source_flags.length).length};
}
export function validateDiagnosticRelease(h,m,r) {
  if (m.methodology_version!==DIAGNOSTIC_VERSION || h.methodology_version!==DIAGNOSTIC_VERSION || h.release_id!==m.release_id
      || !/^diagnostic-[a-f0-9]{20}$/.test(m.release_id??'') || m.protocol_sha256!==DIAGNOSTIC_PROTOCOL_HASH || !hash(m.engine_sha256)
      || m.protocol!==`${DIAGNOSTIC_VERSION}-protocol-1` || h.asset!=='eth' || m.asset!=='eth' || h.frequency!=='1d'
      || h.series_type!=='reconstructed' || m.series_type!=='reconstructed' || m.source_available_at!==null
      || h.composite_score!==null || m.role!=='raw_diagnostics_only' || m.normalizer!==null || m.composite_score!==null || m.core_promotion!==false
      || r.methodology_version!==DIAGNOSTIC_VERSION || r.protocol!==m.protocol || r.status!=='descriptive_raw_diagnostics'
      || r.forecast_evaluation!=='not_applicable_raw_context_only' || r.predictive_utility_claim!==false
      || m.attribution?.source!=='Coin Metrics Community Data' || m.attribution.licence!=='CC BY-NC 4.0'
      || m.attribution.licence_url!=='https://creativecommons.org/licenses/by-nc/4.0/' || m.attribution.scope!=='noncommercial_research_preview'
      || !same(Object.keys(m.files??{}).sort(),['history.json','research.json']) || !Object.values(m.files).every(hash)
      || !Array.isArray(h.rows) || !h.rows.length || m.rows!==h.rows.length) fail();
  if (!same(Object.keys(h.metric_definitions??{}),DIAGNOSTICS.map(d=>d.id))) fail();
  for (const d of DIAGNOSTICS) {
    const definition=h.metric_definitions[d.id];
    if (definition.slot!==d.slot || definition.formula!==d.formula || definition.unit!==d.unit || definition.display_scale!==d.scale
        || definition.independent_vote!==false || definition.input_parent!==(d.slot==='E2'?'core':'proxies')
        || definition.window_days!==(d.slot==='E2'?1:31)) fail();
  }
  if (!same(Object.keys(m.parents??{}).sort(),['core','proxies']) || !same(Object.keys(m.private_inputs_verified??{}).sort(),['core','proxies'])) fail();
  for (const [kind,prefix,version,pattern] of [['core','','core-v0.1.0',/^core-[a-f0-9]{20}$/],['proxies','network-proxies/','network-proxies-v0.1.0',/^proxy-[a-f0-9]{20}$/]]) {
    const p=m.parents[kind], proof=m.private_inputs_verified[kind];
    if (!pattern.test(p.release_id??'') || p.methodology_version!==version || !hash(p.manifest_sha256) || !hash(p.history_sha256)
        || p.manifest_url!==`/data/${prefix}releases/${p.release_id}/manifest.json` || !dateValid(p.last_observation_date)
        || !hash(proof.canonical_sha256) || !hash(proof.source_manifest_sha256) || !hash(proof.receipt_sha256)
        || proof.objects_readback_verified!==true || !Number.isInteger(proof.file_count) || proof.file_count<3) fail();
  }
  let previous=null;
  for (const row of h.rows) {
    if (!dateValid(row.date) || (previous && Date.parse(row.date)-Date.parse(previous)!==86400000)
        || !same(Object.keys(row.metrics??{}),DIAGNOSTICS.map(d=>d.id))
        || !same(Object.keys(row.source_rows_present??{}).sort(),['core','proxies']) || !Object.values(row.source_rows_present).every(v=>typeof v==='boolean')) fail();
    previous=row.date;
    for (const d of DIAGNOSTICS) {
      const v=row.metrics[d.id];
      if (!same(Object.keys(v).sort(),['reason','source_flags','unit','value']) || v.unit!==d.unit
          || (v.value===null ? typeof v.reason!=='string' || !v.reason : typeof v.value!=='number' || !Number.isFinite(v.value) || v.reason!==null)
          || (d.slot==='E2' && v.value!==null && v.value>=1) || !Array.isArray(v.source_flags)
          || !v.source_flags.every(f=>typeof f==='string' && f.length) || !same(v.source_flags,[...new Set(v.source_flags)].sort())) fail();
    }
  }
  if (m.first_date!==h.rows[0].date || m.last_observation_date!==h.rows.at(-1).date || !same(m.limitations,r.limitations)) fail();
  for (const d of DIAGNOSTICS) {
    if (!same(summary(h.rows,d.id),r.coverage?.[d.id]) || !same(m.coverage?.[d.id],r.coverage[d.id])) fail();
  }
  const regimes=[['pre_london',null,'2021-08-05'],['london_pre_merge','2021-08-05','2022-09-15'],['merge_pre_dencun','2022-09-15','2024-03-13'],['post_dencun','2024-03-13',null]];
  for (const [name,start,end] of regimes) {
    const rows=h.rows.filter(v=>(!start || v.date>=start) && (!end || v.date<end));
    if (r.regimes?.[name]?.rows!==rows.length || DIAGNOSTICS.some(d=>!same(summary(rows,d.id),r.regimes[name].metrics[d.id]))) fail();
  }
}
export function diagnosticRange(rows,range,start,end) {
  if (range==='all') return rows;
  if (range==='custom') {
    if (!dateValid(start) || !dateValid(end) || start>end || start<rows[0].date || end>rows.at(-1).date) throw new Error('Khoảng ngày phải nằm trong lịch sử và ngày bắt đầu không sau ngày kết thúc.');
  } else if (['1y','3y'].includes(range)) {
    end=rows.at(-1).date; start=new Date(Date.parse(end)-(range==='1y'?365:1095)*86400000).toISOString().slice(0,10);
  } else throw new Error('Khoảng lịch sử không hợp lệ.');
  return rows.filter(r=>r.date>=start && r.date<=end);
}
const cell = v => '"'+String(v??'').replace(/"/g,'""')+'"';
export function exportDiagnosticCSV(rows,manifest) {
  const headers=['observation_date',...DIAGNOSTICS.flatMap(d=>[d.id,d.id+'_unit',d.id+'_reason',d.id+'_source_flags']),
    'methodology_version','release_id','series_type','core_release_id','proxies_release_id','core_canonical_sha256','proxies_canonical_sha256'];
  return ['# Coin Metrics Community Data | CC BY-NC 4.0 | https://creativecommons.org/licenses/by-nc/4.0/',
    '# Reconstructed raw diagnostics; derived NUPL and signed 30-day changes; no composite score or probability.',headers.join(','),
    ...rows.map(r=>[r.date,...DIAGNOSTICS.flatMap(d=>{const v=r.metrics[d.id];return [v.value,v.unit,v.reason,v.source_flags.join('|')];}),
      manifest.methodology_version,manifest.release_id,'reconstructed',manifest.parents.core.release_id,manifest.parents.proxies.release_id,
      manifest.private_inputs_verified.core.canonical_sha256,manifest.private_inputs_verified.proxies.canonical_sha256].map(cell).join(','))].join('\n')+'\n';
}
