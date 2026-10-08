// The browser verifies published engine output; it never recomputes the regime.
export const MACRO_VERSION='macro-cross-v1.0.1';
export const RULESET_HASH='7a8f1e8fb29a70978588a4ec320ddb0d96437c6a319600592e3cf0622a20f86a';
export const METRICS={cpi_headline_mom_sa:'CPI m/m',pce_core_mom_sa:'PCE core m/m',pce_headline_mom_sa:'PCE headline m/m',ppi_final_demand_mom_sa:'PPI m/m',nfp_change_k_sa:'NFP',unemployment_rate_sa:'Tỷ lệ thất nghiệp',jolts_openings_k_sa:'JOLTS',initial_claims_k_sa:'Trợ cấp thất nghiệp ban đầu',real_gdp_qoq_saar:'GDP thực q/q SAAR',trade_balance_bn_sa:'Cán cân thương mại'};
const directions=['positive','negative','flat','mixed','unknown'];
const labels=['supportive','adverse','mixed','neutral','insufficient_evidence'];
const sha=s=>typeof s==='string'&&/^[a-f0-9]{64}$/.test(s);
const time=s=>typeof s==='string'&&s.endsWith('Z')&&Number.isFinite(Date.parse(s));
const decimal=s=>s===null||typeof s==='string'&&/^-?\d+(?:\.\d+)?$/.test(s);
const fail=()=>{throw Error('Đánh giá macro không hợp lệ');};
export function validateAssessment(a,calendar,pointer,manifest){
  if(a?.schema_version!=='macro-assessment-v1.0.1'||a.ruleset_version!==MACRO_VERSION||a.ruleset_sha256!==RULESET_HASH
    ||!/^macro-[a-f0-9]{20}$/.test(a.assessment_id)||a.assessment_id!==pointer.assessment_id||a.assessment_id!==manifest.assessment_id
    ||!/^macro-state-[a-f0-9]{20}$/.test(a.state_id)||a.state_id!==manifest.state_id||!time(a.as_of)||!time(a.generated_at)
    ||a.calendar_release_id!==calendar.release_id||a.calendar_sha256!==manifest.calendar.sha256||a.calendar_release_id!==pointer.calendar_release_id
    ||manifest.assessment_sha256!==pointer.sha256||manifest.ruleset_sha256!==RULESET_HASH||!sha(a.observation_bundle_sha256)
    ||a.history_mode!=='latest_vintage_context'||a.comparison_basis!=='previous_period'||a.surprise?.status!=='unavailable'||a.market_confirmation?.status!=='not_measured'
    ||!['fresh','stale','unknown'].includes(a.pipeline_state)||!['coherent','partial','conflicted','insufficient','stale'].includes(a.evidence_grade)
    ||!Array.isArray(a.signals)||a.signals.length!==10||new Set(a.signals.map(s=>s.metric_id)).size!==10||!Array.isArray(a.excluded_inputs)||!Array.isArray(a.triggered_rules)||!Array.isArray(a.warnings))fail();
  for(const s of a.signals){
    if(!METRICS[s.metric_id]||!directions.includes(s.direction)||!['actual','previous','delta','signed_delta','epsilon'].every(k=>decimal(s[k]))
      ||!Array.isArray(s.quality_flags)||(s.observation_id!==null&&!/^obs-[a-f0-9]{20}$/.test(s.observation_id)))fail();
    if(s.source_url!==null){const u=new URL(s.source_url);if(u.protocol!=='https:'||!['api.bls.gov','data.bls.gov','www.bea.gov','oui.doleta.gov'].includes(u.hostname)||!sha(s.source_sha256))fail();}
  }
  for(const key of ['inflation','labor','growth','activity']){const x=a.axes?.[key];if(!x||!directions.includes(x.direction)||!Number.isInteger(x.available_slots)||!Number.isInteger(x.expected_slots)||x.available_slots<0||x.available_slots>x.expected_slots||!Array.isArray(x.input_observation_ids))fail();}
  for(const key of ['usd','gold','crypto_risk_assets']){const x=a.assets?.[key];if(!x||!labels.includes(x.conclusion)||x.conditional!==true||!Array.isArray(x.mechanism_codes)||!Array.isArray(x.unobserved_conditions))fail();}
  const batch=a.latest_event_batch;
  if(batch&&(!time(batch.scheduled_at)||!time(batch.usable_at_max)||!Array.isArray(batch.event_ids)||!batch.event_ids.length||batch.event_ids.some(id=>!calendar.events.some(e=>e.id===id&&e.actual!==null))||!['divergent','mixed_peers','aligned','small_change','not_assessable'].includes(batch.event_context_relation)))fail();
  return a;
}
export async function hashBytes(bytes){return [...new Uint8Array(await crypto.subtle.digest('SHA-256',bytes))].map(x=>x.toString(16).padStart(2,'0')).join('');}
export function canonical(value){
  if(Array.isArray(value))return value.map(canonical);
  if(value&&typeof value==='object')return Object.fromEntries(Object.keys(value).sort().map(k=>[k,canonical(value[k])]));
  return value;
}
export async function verifiedAsset(record,fetcher=fetch){
  if(!record||!sha(record.sha256)||!/^\/data\/(?:calendar\/releases\/calendar-[a-f0-9]{20}\/calendar|macro-assessment\/(?:inputs\/[a-f0-9]{64}|releases\/macro-[a-f0-9]{20}\/(?:assessment|manifest)))\.json$/.test(record.url))fail();
  const response=await fetcher(record.url,{cache:'no-cache',signal:AbortSignal.timeout(15000)});
  if(!response.ok)throw Error('Chưa tải được đánh giá macro');
  const bytes=await response.arrayBuffer();if(await hashBytes(bytes)!==record.sha256)throw Error('Checksum macro không khớp');
  return JSON.parse(new TextDecoder().decode(bytes));
}
export async function loadAssessment(fetcher=fetch){
  const json=async url=>{const r=await fetcher(url,{cache:'no-cache',signal:AbortSignal.timeout(15000)});if(!r.ok)throw Error('Chưa tải được đánh giá macro');return r.json();};
  const [pointer,status]=await Promise.all([json('/data/macro-assessment/latest.json'),json('/data/macro-assessment/status.json')]);
  if(pointer.ruleset_version!==MACRO_VERSION||pointer.url!==`/data/macro-assessment/releases/${pointer.assessment_id}/assessment.json`||pointer.manifest?.url!==`/data/macro-assessment/releases/${pointer.assessment_id}/manifest.json`)fail();
  const [assessment,manifest]=await Promise.all([verifiedAsset(pointer,fetcher),verifiedAsset(pointer.manifest,fetcher)]);
  const [calendar,bundle,proof,ruleset]=await Promise.all(['calendar','observations','batch_status','ruleset'].map(k=>verifiedAsset(manifest[k],fetcher)));
  if(await hashBytes(new TextEncoder().encode(JSON.stringify(canonical(ruleset))))!==RULESET_HASH||bundle.calendar_release_id!==calendar.release_id||bundle.calendar_sha256!==manifest.calendar.sha256||proof.id!==assessment.batch_status_id||proof.sha256!==assessment.batch_status_sha256)fail();
  // Bundle is already canonical in the publisher, including sorted arrays.
  if(await hashBytes(new TextEncoder().encode(JSON.stringify(canonical(bundle))))!==assessment.observation_bundle_sha256||await hashBytes(new TextEncoder().encode(JSON.stringify(canonical(proof.data))))!==proof.sha256)fail();
  validateAssessment(assessment,calendar,pointer,manifest);
  if(status.outcome!=='error'){
    const currentProof=await verifiedAsset(status.batch_status,fetcher);
    if(currentProof.sha256!==await hashBytes(new TextEncoder().encode(JSON.stringify(canonical(currentProof.data))))||currentProof.data.known_at!==status.checked_at||currentProof.data.last_successful_source_check_at!==status.last_successful_source_check_at)fail();
  }
  return {assessment,calendar,pointer,manifest,status};
}
