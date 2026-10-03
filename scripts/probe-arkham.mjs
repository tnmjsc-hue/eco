// Read-only, unauthenticated capability probe. It never consumes API credits or accepts terms.
import { mkdir, writeFile } from 'node:fs/promises';
import { createHash } from 'node:crypto';
import { resolve } from 'node:path';
const date = process.argv[2] || new Date(Date.now()-86400000).toISOString().slice(0,10);
if (!/^\d{4}-\d{2}-\d{2}$/.test(date) || new Date(date+'T00:00:00Z').toISOString().slice(0,10)!==date) throw new Error('Expected an observation date in UTC.');
const folder = resolve('data/raw/arkham',new Date().toISOString().replaceAll(':','').replaceAll('.',''));
await mkdir(folder,{recursive:true});
const specs = [
  {id:'holders',path:'/token/holders/ethereum',query:{groupByEntity:'true',limit:'5',offset:'0'}},
  {id:'cex_transfers',path:'/transfers/histogram',query:{base:'binance',chains:'ethereum',tokens:'ethereum',granularity:'1d',timeGte:date+'T00:00:00Z',timeLte:date+'T23:59:59Z'}},
];
const probes = [];
for (const spec of specs) {
  const url = new URL(spec.path,'https://api.arkm.com');
  url.search = new URLSearchParams(spec.query).toString();
  const started = new Date().toISOString();
  try {
    const r = await fetch(url,{headers:{Accept:'application/json'},signal:AbortSignal.timeout(20000),redirect:'error'});
    const body = Buffer.from(await r.arrayBuffer());
    await writeFile(resolve(folder,spec.id+'.response'),body,{flag:'wx'});
    probes.push({id:spec.id,request_url:url.href,auth:'none',status:r.status,content_type:r.headers.get('content-type'),
      response_sha256:createHash('sha256').update(body).digest('hex'),bytes:body.length,
      access:r.ok?'anonymous_sample_received_not_licensed_for_publication':r.status===401?'authentication_required':r.status===403?'forbidden':'http_error',
      started_at:started,completed_at:new Date().toISOString(),full_history_verified:false,coverage:null});
  } catch {
    probes.push({id:spec.id,auth:'none',access:'network_or_redirect_error',started_at:started,completed_at:new Date().toISOString(),coverage:null});
  }
}
const report = {provider:'arkham',asset:'eth',scope:'unauthenticated_read_only_probe',observed_at:new Date().toISOString(),
  credential_present:Boolean(process.env.ARKHAM_API_KEY),credential_used:false,account_created:false,terms_accepted:false,
  paid_requests:false,public_data_rights_verified:false,source_available_at:null,probes};
await writeFile(resolve(folder,'manifest.json'),JSON.stringify(report,null,2)+'\n',{flag:'wx'});
// Metadata only: error bodies may contain IP addresses and never go to public artifacts or logs.
console.log(JSON.stringify(report,null,2));
