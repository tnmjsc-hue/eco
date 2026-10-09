import {hashBytes,canonical} from './macro-model.js?v=market-20261009a';
export const VERSION='macro-market-v1.0.0';
export const PROTOCOL_SHA='2f1920b845406637f13087778d6999af6065a70c3f6ce9a18b8a5c061e008a4d';
export const SPEC={treasury_2y:['fed','RIFLGFCY02_N.B','percent','bps',7],treasury_10y:['fed','RIFLGFCY10_N.B','percent','bps',7],real_yield_10y:['treasury','TC_10YEAR','percent','bps',7],usd_broad:['fed','JRXWTFB_N.B','index','percent',14],eth_usd:['coinmetrics','PriceUSD','USD','percent',4],gold_usd:[null,null,'USD','percent',null]};
const fail=()=>{throw Error('Số đo thị trường không hợp lệ');};
const sha=x=>typeof x==='string'&&/^[a-f0-9]{64}$/.test(x);
const utc=x=>typeof x==='string'&&/(Z|\+00:00)$/.test(x)&&Number.isFinite(Date.parse(x));
const day=x=>typeof x==='string'&&/^\d{4}-\d{2}-\d{2}$/.test(x)&&Number.isFinite(Date.parse(x))&&new Date(x).toISOString().slice(0,10)===x;
const decimal=x=>typeof x==='string'&&/^-?\d+(?:\.\d+)?$/.test(x)&&Number.isFinite(Number(x));
const encode=x=>new TextEncoder().encode(JSON.stringify(canonical(x))+'\n');
export async function marketAsset(record,fetcher=fetch){
  if(!record||!sha(record.sha256)||!/^\/data\/(?:macro-market\/releases\/market-[a-f0-9]{20}\/(?:market|manifest|inputs|protocol)|core-v2\/releases\/core10-[a-f0-9]{20}\/(?:manifest|history))\.json$/.test(record.url))fail();
  const r=await fetcher(record.url,{cache:'no-cache',signal:AbortSignal.timeout(15000)});
  if(!r.ok)throw Error('Chưa tải được số đo thị trường');
  const bytes=await r.arrayBuffer();if(await hashBytes(bytes)!==record.sha256)throw Error('Checksum thị trường không khớp');
  return JSON.parse(new TextDecoder().decode(bytes));
}
export function validateMarket(data,inputs,protocol,status){
  if(data.schema_version!==VERSION||data.comparison_basis!=='daily_change'||!utc(data.generated_at)
    ||data.consensus?.status!=='unavailable'||data.consensus.reason!=='no_approved_pre_release_consensus'
    ||data.event_reaction?.status!=='not_measured'||data.event_reaction.reason!=='no_verified_intraday_window'
    ||protocol.version!==VERSION||protocol.maximum_pair_gap_days!==7||protocol.comparison_basis!=='daily_change'
    ||protocol.event_reaction!=='not_measured'||protocol.consensus!=='unavailable'||inputs.protocol_version!==VERSION
    ||JSON.stringify(canonical(data.metrics))!==JSON.stringify(canonical(inputs.metrics))||!Array.isArray(data.metrics)
    ||data.metrics.length!==6||new Set(data.metrics.map(m=>m.metric_id)).size!==6
    ||!['published','unchanged','error'].includes(status.outcome)||!utc(status.checked_at)
    ||(status.outcome!=='error'&&status.release_id!==data.release_id)||Date.parse(status.checked_at)<Date.parse(data.generated_at))fail();
  for(const m of data.metrics){
    const spec=SPEC[m.metric_id],p=protocol.metrics?.[m.metric_id];
    if(!spec||!p||JSON.stringify([m.provider,m.series_id,m.unit,m.change_unit,m.max_age_days])!==JSON.stringify(spec)
      ||JSON.stringify([p.provider,p.series_id,p.unit,p.change_unit,p.max_age_days])!==JSON.stringify(spec)
      ||!['measured','stale','unavailable'].includes(m.status)||!['latest','previous','change'].every(k=>m[k]===null||decimal(m[k]))
      ||!['latest_date','previous_date'].every(k=>m[k]===null||day(m[k])))fail();
    if(m.metric_id==='gold_usd'){
      if(m.status!=='unavailable'||m.reason!=='no_approved_gold_source'||m.source!==null||['latest','previous','change','latest_date','previous_date'].some(k=>m[k]!==null))fail();
      continue;
    }
    const s=m.source;if(!s||s.provider!==m.provider||!sha(s.sha256)||!utc(s.usable_at)||Date.parse(s.usable_at)>Date.parse(data.generated_at))fail();
    if(m.provider==='coinmetrics'){
      if(s.retrieved_at!==null||s.knowledge_basis!=='verified_parent_computed_at')fail();
    }else if(!utc(s.retrieved_at)||s.usable_at!==s.retrieved_at||s.knowledge_basis!=='source_retrieved_at')fail();
    const u=new URL(s.url);if(u.protocol!=='https:'||u.username||u.password)fail();
    if(m.provider==='fed'&&(u.origin!=='https://www.federalreserve.gov'||u.pathname!=='/datadownload/Output.aspx'||u.searchParams.get('rel')!==(m.metric_id==='usd_broad'?'H10':'H15')||u.searchParams.get('series')!==(m.metric_id==='usd_broad'?'122e3bcb627e8e53f1bf72a1a09cfb81':'bf17364827e38702b42a58cf8eaa3f78')||s.licence!=='US_government_public_domain'))fail();
    if(m.provider==='treasury'&&(u.origin!=='https://home.treasury.gov'||u.pathname!=='/resource-center/data-chart-center/interest-rates/pages/xml'||u.searchParams.get('data')!=='daily_treasury_real_yield_curve'||s.licence!=='US_government_public_domain'))fail();
    if(m.provider==='coinmetrics'&&(s.url!=='https://gitbook-docs.coinmetrics.io/packages/coin-metrics-community-data'||s.licence!=='CC BY-NC 4.0'))fail();
    if(m.latest_date&&m.latest_date>=data.generated_at.slice(0,10))fail();
    if(m.status==='unavailable'){
      if(!['missing_pair','missing_latest_value','pair_gap','invalid_price_or_index'].includes(m.reason)||m.change!==null)fail();
      continue;
    }
    if(['latest','previous','change','latest_date','previous_date'].some(k=>m[k]===null)||m.previous_date>=m.latest_date)fail();
    const gap=(Date.parse(m.latest_date)-Date.parse(m.previous_date))/86400000;
    const age=(Date.parse(data.generated_at.slice(0,10))-Date.parse(m.latest_date))/86400000;
    if(gap>7||(m.status==='stale')!==(age>m.max_age_days)||m.reason!==(m.status==='stale'?'observation_expired':null))fail();
    const latest=Number(m.latest),previous=Number(m.previous);
    if(m.change_unit==='percent'&&(latest<=0||previous<=0))fail();
    const change=m.change_unit==='bps'?(latest-previous)*100:(latest/previous-1)*100;
    if(Math.abs(change-Number(m.change))>1e-9)fail();
  }
  return data;
}
export async function loadMarket(fetcher=fetch){
  const json=async url=>{const r=await fetcher(url,{cache:'no-cache',signal:AbortSignal.timeout(15000)});if(!r.ok)throw Error('Chưa tải được số đo thị trường');return r.json();};
  const [pointer,status]=await Promise.all([json('/data/macro-market/latest.json'),json('/data/macro-market/status.json')]);
  if(pointer.schema_version!==VERSION||!/^market-[a-f0-9]{20}$/.test(pointer.release_id)||pointer.url!==`/data/macro-market/releases/${pointer.release_id}/market.json`||pointer.manifest?.url!==`/data/macro-market/releases/${pointer.release_id}/manifest.json`)fail();
  const [data,manifest]=await Promise.all([marketAsset(pointer,fetcher),marketAsset(pointer.manifest,fetcher)]);
  if(data.release_id!==pointer.release_id||manifest.release_id!==pointer.release_id||manifest.schema_version!==VERSION)fail();
  for(const key of ['inputs','protocol'])if(manifest[key]?.url!==`/data/macro-market/releases/${pointer.release_id}/${key}.json`)fail();
  if(manifest.protocol.sha256!==PROTOCOL_SHA)fail();
  const [inputs,protocol]=await Promise.all([marketAsset(manifest.inputs,fetcher),marketAsset(manifest.protocol,fetcher)]);
  if(JSON.stringify(canonical(inputs.eth_parent))!==JSON.stringify(canonical(manifest.eth_parent)))fail();
  const [parent,history]=await Promise.all(['manifest','history'].map(k=>marketAsset(manifest.eth_parent[k],fetcher)));
  if(parent.asset!=='eth'||history.asset!=='eth'||parent.attribution?.licence!=='CC BY-NC 4.0'||parent.release_id!==history.release_id||parent.files?.['history.json']!==manifest.eth_parent.history.sha256
    ||manifest.eth_parent.history.url!==`/data/core-v2/releases/${parent.release_id}/history.json`||manifest.eth_parent.manifest.url!==`/data/core-v2/releases/${parent.release_id}/manifest.json`)fail();
  const eth=data.metrics?.find(m=>m.metric_id==='eth_usd');if(eth?.source.sha256!==manifest.eth_parent.history.sha256||eth.source.usable_at!==parent.computed_at)fail();
  for(const [dateField,valueField] of [['latest_date','latest'],['previous_date','previous']]){
    const row=history.rows?.find(r=>r.date===eth[dateField]);if(eth[dateField]&&(row?.period_closed_at_retrieval!==true||Number(row.price_usd)!==Number(eth[valueField])))fail();
  }
  const identity={input_sha256:manifest.inputs.sha256,protocol_sha256:manifest.protocol.sha256};
  if(manifest.previous_release_id!==null){if(!/^market-[a-f0-9]{20}$/.test(manifest.previous_release_id))fail();identity.previous_release_id=manifest.previous_release_id;}
  const digest=await hashBytes(encode(identity));
  if(pointer.release_id!==`market-${digest.slice(0,20)}`||manifest.private_backup?.verified!==true||!Array.isArray(manifest.private_backup.objects)||manifest.private_backup.objects.length<5||manifest.private_backup.objects.some(o=>o.readback_verified!==true||!sha(o.sha256)))fail();
  validateMarket(data,inputs,protocol,status);
  return {data,manifest,pointer,status};
}
