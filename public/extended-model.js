import { METRICS, dateMinus } from './data-model.js?v=dashboard-1';
import { PROXIES } from './proxy-model.js?v=proxies-1';
export const EXTENDED_VERSION = 'extended-v0.1.0';
export const EXTENDED_PROTOCOL_HASH = '719b9873e7e96546f829df915051d993dafbb960e53878495c1bce249c948bcb';
export const EXTENDED_METRICS = [
  ...METRICS.map(m=>({...m,weight:m.weight*.75,slot:m.id})),
  ...PROXIES.map(m=>({...m,weight:1/12,description:m.description})),
];
export function extendedScore(row, selected=EXTENDED_METRICS.map(m=>m.id)) {
  const metrics = EXTENDED_METRICS.filter(m=>selected.includes(m.id));
  if (!metrics.length || metrics.length !== selected.length || new Set(selected).size !== selected.length
      || metrics.some(m=>row.components[m.id] === null || !Number.isFinite(row.components[m.id]))) return null;
  if (metrics.length === 1) return row.components[metrics[0].id];
  return metrics.reduce((s,m)=>s+row.components[m.id]*m.weight,0)/metrics.reduce((s,m)=>s+m.weight,0);
}
export function validateExtendedPointer(p) {
  if (!/^extended-[a-f0-9]{20}$/.test(p?.release_id) || p.methodology_version !== EXTENDED_VERSION
      || p.manifest_url !== `/data/extended/releases/${p.release_id}/manifest.json`
      || !/^[a-f0-9]{64}$/.test(p.manifest_sha256)) throw new Error('Pointer ECO 7 không hợp lệ.');
}
export function validateExtended(history, manifest, research) {
  const ids = EXTENDED_METRICS.map(m=>m.id).sort().join();
  if (manifest.methodology_version !== EXTENDED_VERSION || manifest.protocol_sha256 !== EXTENDED_PROTOCOL_HASH
      || manifest.protocol !== `${EXTENDED_VERSION}-protocol-1` || manifest.asset !== 'eth'
      || manifest.series_type !== 'reconstructed' || manifest.research_only !== true || manifest.required_coverage !== 7
      || manifest.attribution?.licence !== 'CC BY-NC 4.0' || manifest.source_available_at !== null
      || history.release_id !== manifest.release_id || history.methodology_version !== EXTENDED_VERSION
      || history.asset !== 'eth' || history.series_type !== 'reconstructed' || history.schema_version !== '1.0.0'
      || !Array.isArray(history.rows) || !history.rows.length || history.rows.length !== manifest.rows
      || research.methodology_version !== EXTENDED_VERSION || research.protocol !== manifest.protocol
      || research.status !== 'exploratory_reconstructed_only' || research.bootstrap?.replicates !== 10000
      || research.bootstrap.block_calendar_days !== 90 || research.bootstrap.seed !== 20261003
      || research.decision !== 'publish_experimental_preview_no_predictive_validation_claim') throw new Error('Hợp đồng ECO 7 không hợp lệ.');
  for (const parent of ['core','proxies']) {
    const p = manifest.parents?.[parent], prefix = parent === 'core' ? 'core' : 'proxy';
    const path = parent === 'core' ? '/data/releases/' : '/data/network-proxies/releases/';
    if (!new RegExp(`^${prefix}-[a-f0-9]{20}$`).test(p?.release_id)
        || p.manifest_url !== path+p.release_id+'/manifest.json' || !/^[a-f0-9]{64}$/.test(p.manifest_sha256)
        || !/^[a-f0-9]{64}$/.test(p.history_sha256)) throw new Error('Release cha ECO 7 không hợp lệ.');
  }
  for (const weights of [history.weights,manifest.weights]) {
    if (Object.keys(weights ?? {}).sort().join() !== ids || EXTENDED_METRICS.some(m=>Math.abs(weights[m.id]-m.weight)>1e-15)) throw new Error('Trọng số ECO 7 đã đổi.');
  }
  let previous = null;
  for (const r of history.rows) {
    if (!/^\d{4}-\d{2}-\d{2}$/.test(r.date) || dateMinus(r.date,0) !== r.date || (previous && dateMinus(r.date,1) !== previous)
        || Object.keys(r.components ?? {}).sort().join() !== ids || Object.keys(r.reasons ?? {}).sort().join() !== ids
        || Object.keys(r.source_flags ?? {}).sort().join() !== ids) throw new Error('Calendar hoặc thành phần ECO 7 không khớp.');
    const values = Object.values(r.components), score = extendedScore(r);
    const core = METRICS.some(m=>r.components[m.id]===null) ? null : METRICS.reduce((s,m)=>s+r.components[m.id]*m.weight,0);
    if (values.some(v=>v !== null && (typeof v !== 'number' || !Number.isFinite(v) || v<0 || v>100))
        || values.filter(v=>v!==null).length !== r.coverage
        || (score === null ? r.score !== null : !Number.isFinite(r.score) || Math.abs(score-r.score)>1e-8)
        || (core === null ? r.core_score !== null : !Number.isFinite(r.core_score) || Math.abs(core-r.core_score)>1e-8)
        || (r.price_usd !== null && (!Number.isFinite(r.price_usd) || r.price_usd<=0))
        || r.period_closed_at_retrieval !== true || typeof r.source_row_present !== 'boolean' || typeof r.proxy_row_present !== 'boolean'
        || EXTENDED_METRICS.some(m=>!Array.isArray(r.source_flags[m.id]) || r.source_flags[m.id].some(f=>typeof f !== 'string' || f.length>80)
          || (r.components[m.id]===null ? typeof r.reasons[m.id] !== 'string' : r.reasons[m.id] !== null))) throw new Error('Điểm, lý do hoặc coverage ECO 7 không hợp lệ.');
    previous = r.date;
  }
  const valid = history.rows.filter(r=>r.score!==null);
  if (valid.length!==manifest.score_rows || valid[0]?.date!==manifest.first_score_date || valid.at(-1)?.date!==manifest.last_valid_score_date
      || valid.at(-1)?.score!==manifest.last_valid_score || history.rows[0].date!==manifest.first_observation_date
      || history.rows.at(-1).date!==manifest.last_observation_date) throw new Error('Phạm vi ECO 7 không khớp manifest.');
}
export function exportExtendedCSV(rows, selected, mode, manifest) {
  const quote = v=>`"${String(v??'').replaceAll('"','""')}"`;
  const ids = EXTENDED_METRICS.map(m=>m.id);
  const columns = ['date_utc','price_usd','extended_score','core_score','custom_score',...ids,'coverage',...ids.map(id=>id+'_reason'),...ids.map(id=>id+'_source_flags'),'methodology_version','release_id','core_parent_release','proxy_parent_release','series_type','mode','selected_components','source','license','license_url','modifications'];
  const lines = rows.map(r=>[r.date,r.price_usd,r.score,r.core_score,mode==='custom'?extendedScore(r,selected):null,...ids.map(id=>r.components[id]),r.coverage,...ids.map(id=>r.reasons[id]),...ids.map(id=>r.source_flags[id].join('|')),manifest.methodology_version,manifest.release_id,manifest.parents.core.release_id,manifest.parents.proxies.release_id,'reconstructed',mode,mode==='custom'?selected.join('|'):mode==='core'?'E1|E5|E6|E7':ids.join('|'),'Coin Metrics Community Data','CC BY-NC 4.0',manifest.license_url,'ECO normalized and aggregated; no endorsement; no warranties'].map(quote).join(','));
  return '\uFEFF'+[columns.join(','),...lines].join('\r\n');
}
