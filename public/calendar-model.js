export const CALENDAR_VERSION = 'us-macro-calendar-v1.1.0';
const CATEGORIES=['inflation','labor','growth','policy'];

export function dayInZone(iso, zone = 'Asia/Ho_Chi_Minh') {
  const parts = new Intl.DateTimeFormat('en-CA', { timeZone: zone, year: 'numeric', month: '2-digit', day: '2-digit' }).formatToParts(new Date(iso));
  const get = key => parts.find(p => p.type === key).value;
  return `${get('year')}-${get('month')}-${get('day')}`;
}
export function selectEvents(events, { start, end, zone, impact = 'all', search = '' }) {
  return events.filter(e => {
    const day = dayInZone(e.scheduled_at, zone);
    return day >= start && day <= end && (impact === 'all' || e.impact === impact)
      && `${e.title} ${e.source_title} ${e.provider}`.toLowerCase().includes(search.trim().toLowerCase());
  });
}
export function validateCalendar(data) {
  if (data.schema_version !== '1.1.0' || data.calendar_version !== CALENDAR_VERSION || data.scope !== 'US_major_macro'
    || !Array.isArray(data.events) || data.events.length < 15 || !Array.isArray(data.indicators) || data.indicators.length !== 5
    || !data.private_backup?.verified || !Number.isFinite(Date.parse(data.generated_at))) throw Error('Dữ liệu lịch không hợp lệ');
  const sources = {bls:'https://www.bls.gov/schedule/news_release/bls.ics',bea:'https://www.bea.gov/news/schedule/ics/online-calendar-subscription.ics',fed:'https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm',bls_data:'https://api.bls.gov/publicAPI/v2/timeseries/data/',bea_schedule:'https://www.bea.gov/news/schedule/full',fed_calendar:'https://www.federalreserve.gov/newsevents/calendar.htm',dol_schedule:'https://oui.doleta.gov/unemploy/claims_arch.asp'};
  for (const [key,url] of Object.entries(sources)) {
    const source = data.sources?.[key];
    if (source?.source_url !== url || !/^[a-f0-9]{64}$/.test(source.sha256)
      || !Number.isFinite(Date.parse(source.retrieved_at)) || !Number.isFinite(Date.parse(source.checked_at))) throw Error('Dữ liệu lịch không hợp lệ');
  }
  for (const [key,source] of Object.entries(data.sources)) {
    if (key in sources) continue;
    const fedMonth = /^fed_month_\d{6}$/.test(key) && /^https:\/\/www\.federalreserve\.gov\/newsevents\/\d{4}-[a-z]+\.htm$/.test(source.source_url);
    const beaReport = /^bea_report_bea_[a-zA-Z0-9_]+$/.test(key) && /^https:\/\/www\.bea\.gov\/news\/\d{4}\/[a-zA-Z0-9/_-]+$/.test(source.source_url);
    const dolReport = /^dol_report_\d{8}$/.test(key) && /^https:\/\/oui\.doleta\.gov\/press\/\d{4}\/\d{6}\.pdf$/.test(source.source_url);
    if ((!fedMonth && !beaReport && !dolReport) || !/^[a-f0-9]{64}$/.test(source.sha256)
      || !Number.isFinite(Date.parse(source.retrieved_at)) || !Number.isFinite(Date.parse(source.checked_at))) throw Error('Nguồn lịch không hợp lệ');
  }
  if (!Array.isArray(data.private_backup.objects) || data.private_backup.objects.length !== Object.keys(data.sources).length + 2
    || !data.private_backup.objects.every(o=>o.readback_verified === true && /^[a-f0-9]{64}$/.test(o.sha256))) throw Error('Dữ liệu lịch không hợp lệ');
  const ids = new Set();
  for (const e of data.events) {
    const host = new URL(e.source_url).hostname;
    if (typeof e.id !== 'string' || typeof e.title !== 'string' || typeof e.source_title !== 'string' || ids.has(e.id) || !['bls','bea','fed','dol'].includes(e.provider) || e.currency !== 'USD'
      || !['high','medium'].includes(e.impact) || !CATEGORIES.includes(e.category) || !Number.isFinite(Date.parse(e.scheduled_at))
      || !['www.bls.gov','www.bea.gov','www.federalreserve.gov','oui.doleta.gov'].includes(host)
      || !e.source_url.startsWith('https://') || e.forecast !== null
      || !['scheduled','current_vintage_period_match','official_release'].includes(e.data_status)
      || (e.actual !== null && !Number.isFinite(e.actual)) || (e.previous !== null && !Number.isFinite(e.previous))
      || (e.unit !== null && !['percent','percent_saar','thousand_jobs','thousand_claims','billion_usd'].includes(e.unit))
      || (e.reference_period !== null && !/^\d{4}-(0[1-9]|1[0-2]|Q[1-4])$|^\d{4}-\d{2}-\d{2}$/.test(e.reference_period))
      || !Array.isArray(e.details) || e.details.some(d=>typeof d.label!=='string'||!Number.isFinite(d.actual)||(d.previous!==null&&!Number.isFinite(d.previous))||!['percent','percent_saar','thousand_jobs','thousand_claims','billion_usd'].includes(d.unit))
      || (e.data_status === 'scheduled' && (e.actual !== null || e.previous !== null || e.data_source_url !== null || e.data_vintage_at !== null))
      || (e.data_status !== 'scheduled' && (!Number.isFinite(e.actual) || !e.reference_period || !e.unit
        || !Number.isFinite(Date.parse(e.data_vintage_at)) || !e.data_source_url?.startsWith('https://')
        || !['data.bls.gov','www.bea.gov','oui.doleta.gov'].includes(new URL(e.data_source_url).hostname)))) throw Error('Sự kiện lịch không hợp lệ');
    ids.add(e.id);
  }
  for (const i of data.indicators) {
    if (typeof i.title !== 'string' || !/^\d{4}-(0[1-9]|1[0-2])$/.test(i.reference_period) || !['percent','thousand_jobs'].includes(i.unit)
      || (i.value !== null && !Number.isFinite(i.value)) || (i.previous !== null && !Number.isFinite(i.previous))
      || new URL(i.source_url).hostname !== 'data.bls.gov' || !i.source_url.startsWith('https://')) throw Error('Số liệu BLS không hợp lệ');
  }
  return data;
}
