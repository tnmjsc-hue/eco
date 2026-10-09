import {hashBytes,canonical,verifiedAsset} from './macro-model.js?v=prob-20261009a';
export const VERSION='macro-probability-v1.0.0';
export const PROTOCOL_SHA='3ae63a0eb85f431bcdd8a8f9a0cdb770dbb5233bc1868831fd5b7cdda3e47101';
const pattern=/^\/data\/macro-probability\/(?:records\/case-[a-f0-9]{20}|outcomes\/result-[a-f0-9]{20}|releases\/prob-[a-f0-9]{20}\/(?:report|manifest|inputs|protocol))\.json$/;
const fail=()=>{throw Error('Mô hình xác suất không hợp lệ');};
const time=x=>typeof x==='string'&&/(Z|\+00:00)$/.test(x)&&Number.isFinite(Date.parse(x));
const count=x=>Number.isSafeInteger(x)&&x>=0;
const decimal=x=>typeof x==='string'&&/^-?\d+(?:\.\d+)?$/.test(x)&&Number.isFinite(Number(x));
const day=x=>typeof x==='string'&&/^\d{4}-\d{2}-\d{2}$/.test(x)&&Number.isFinite(Date.parse(x))&&new Date(x).toISOString().slice(0,10)===x;
const encode=x=>new TextEncoder().encode(JSON.stringify(canonical(x))+'\n');
export async function probabilityAsset(record,fetcher=fetch){
  if(!record||!pattern.test(record.url)||!/^([a-f0-9]{64})$/.test(record.sha256))fail();
  const r=await fetcher(record.url,{cache:'no-cache',signal:AbortSignal.timeout(15000)});
  if(!r.ok)throw Error('Chưa tải được mô hình xác suất');
  const bytes=await r.arrayBuffer();if(await hashBytes(bytes)!==record.sha256)throw Error('Checksum mô hình xác suất không khớp');
  return JSON.parse(new TextDecoder().decode(bytes));
}
export function validateProbability(d,inputs,protocol,status){
  const e=d.evaluation,c=d.latest_case;
  if(d.schema_version!==VERSION||protocol.version!==VERSION||d.asset!=='eth'||d.target!=='seven_day_price_direction'||d.horizon_days!==7||d.flat_band_percent!=='1'||d.scope!=='noncommercial_prospective_research'||d.consensus!=='not_market_consensus'||!time(d.generated_at)
    ||!['collecting','awaiting_calibration','awaiting_test','validation_failed','validated_holdout'].includes(e?.state)||!Array.isArray(e.failures)
    ||!count(d.cases_count)||!count(d.resolved_count)||d.resolved_count>d.cases_count||d.cases_count!==inputs.cases.length||d.resolved_count!==inputs.outcomes.length
    ||!['train_n','calibration_n','test_n'].every(k=>count(e[k]))||e.train_n>90||e.calibration_n>45||e.test_n>45
    ||!['published','unchanged','error'].includes(status.outcome)||!time(status.checked_at)||Date.parse(status.checked_at)<Date.parse(d.generated_at)
    ||!time(d.current_context?.as_of)||Date.parse(d.current_context.as_of)>Date.parse(d.generated_at)||typeof d.current_context.eligible!=='boolean'
    ||JSON.stringify(canonical(d.current_context.parents))!==JSON.stringify(canonical(inputs.macro_parents)))fail();
  if(status.outcome!=='error'&&status.release_id!==d.release_id)fail();
  if(e.state==='validated_holdout'){
    if(e.train_n!==90||e.calibration_n!==45||e.test_n!==45||e.failures.length||e.regime_counts.train<30||e.regime_counts.calibration<15||e.regime_counts.test<15
      ||!e.test||!e.baseline||!e.regime_test||!e.regime_baseline||!e.brier_delta_ci95||Number(e.brier_delta_ci95[1])>=0)fail();
    for(const [a,b] of [[e.test,e.baseline],[e.regime_test,e.regime_baseline]]){
      if(!decimal(a.brier)||!decimal(a.log_loss)||Number(b.brier)-Number(a.brier)<0.01||Number(a.log_loss)>Number(b.log_loss)||!['down','flat','up'].every(k=>decimal(a.class_ece[k])&&Number(a.class_ece[k])<=0.15))fail();
    }
  }
  const vector=(p,state)=>{
    if(state!=='validated_holdout'){if(p!==null)fail();return;}
    if(!p||Object.keys(p).sort().join(',')!=='down,flat,up'||Object.values(p).some(v=>!decimal(v)||Number(v)<=0||Number(v)>=1)||Math.abs(Object.values(p).reduce((s,v)=>s+Number(v),0)-1)>1e-12)fail();
  };
  vector(e.probabilities,e.state);
  if(c){
    if(c.version!==VERSION||!/^case-[a-f0-9]{20}$/.test(c.case_id)||!time(c.issued_at)||Date.parse(c.issued_at)>Date.parse(d.generated_at)||!day(c.base_date)||!day(c.end_date)
      ||Date.parse(c.base_date)-Date.parse(c.issued_at.slice(0,10))!==86400000||Date.parse(c.end_date)-Date.parse(c.base_date)!==7*86400000||!protocol.regimes.includes(c.regime_id))fail();
    vector(c.probabilities,c.model_state);
  }else if(d.cases_count!==0)fail();
  return d;
}
export async function loadProbability(fetcher=fetch){
  const fetchJson=async url=>{const r=await fetcher(url,{cache:'no-cache',signal:AbortSignal.timeout(15000)});if(!r.ok)throw Error('Chưa tải được mô hình xác suất');return r.json();};
  const [pointer,status]=await Promise.all(['/data/macro-probability/latest.json','/data/macro-probability/status.json'].map(fetchJson));
  if(pointer.schema_version!==VERSION||pointer.url!==`/data/macro-probability/releases/${pointer.release_id}/report.json`)fail();
  const [data,manifest]=await Promise.all([probabilityAsset(pointer,fetcher),probabilityAsset(pointer.manifest,fetcher)]);
  if(data.release_id!==pointer.release_id||manifest.release_id!==pointer.release_id||manifest.report.sha256!==pointer.sha256||manifest.protocol_sha256!==PROTOCOL_SHA)fail();
  const [inputs,protocol]=await Promise.all([probabilityAsset(manifest.inputs,fetcher),probabilityAsset(manifest.protocol,fetcher)]);
  if(await hashBytes(encode(protocol))!==PROTOCOL_SHA)fail();
  const stateReport={...data};for(const k of ['schema_version','release_id','generated_at'])delete stateReport[k];
  if(await hashBytes(encode({inputs,report:stateReport,protocol_sha256:PROTOCOL_SHA}))!==manifest.state_sha256)fail();
  if(`prob-${(await hashBytes(encode({state_sha256:manifest.state_sha256,previous_release_id:manifest.previous_release_id}))).slice(0,20)}`!==data.release_id)fail();
  validateProbability(data,inputs,protocol,status);
  const parent=inputs.macro_parents;
  const [assessment,macroManifest,calendar,...rest]=await Promise.all(['assessment','manifest','calendar','observations','ruleset','batch_status'].map(k=>verifiedAsset(parent[k],fetcher)));
  if(assessment.assessment_id!==data.current_context.assessment_id||assessment.regime_id!==data.current_context.regime_id||assessment.as_of!==data.current_context.as_of||assessment.calendar_release_id!==calendar.release_id||macroManifest.assessment_sha256!==parent.assessment.sha256||macroManifest.calendar.sha256!==parent.calendar.sha256)fail();
  const proof=rest[2].data;
  if(!time(proof.known_at)||Date.parse(proof.known_at)>Date.parse(data.generated_at)||proof.last_successful_source_check_at!==null&&(!time(proof.last_successful_source_check_at)||Date.parse(proof.last_successful_source_check_at)>Date.parse(proof.known_at)))fail();
  const currentMacro=await fetchJson('/data/macro-assessment/latest.json');
  if(data.latest_case){
    const c=data.latest_case,ref=inputs.cases.find(x=>x.url===`/data/macro-probability/records/${c.case_id}.json`);
    if(!ref||await hashBytes(encode(c))!==ref.sha256)fail();
    const identity={...c};delete identity.case_id;
    if(c.case_id!==`case-${(await hashBytes(encode(identity))).slice(0,20)}`)fail();
  }
  const eth=inputs.eth_parent;
  const readEth=async r=>{
    if(!/^\/data\/core-v2\/releases\/core10-[a-f0-9]{20}\/(?:manifest|history)\.json$/.test(r.url))fail();
    const res=await fetcher(r.url,{cache:'no-cache',signal:AbortSignal.timeout(15000)});if(!res.ok)fail();
    const bytes=await res.arrayBuffer();if(await hashBytes(bytes)!==r.sha256)throw Error('Checksum mô hình xác suất không khớp');return JSON.parse(new TextDecoder().decode(bytes));
  };
  const [ethManifest,history]=await Promise.all([readEth(eth.manifest),readEth(eth.history)]);
  if(history.asset!=='eth'||ethManifest.asset!=='eth'||ethManifest.methodology_version!=='core-v0.2.0'||history.release_id!==ethManifest.release_id||ethManifest.files['history.json']!==eth.history.sha256||Date.parse(ethManifest.computed_at)>Date.parse(data.generated_at))fail();
  return {data,pointer,status,manifest,proof,currentMacro};
}
