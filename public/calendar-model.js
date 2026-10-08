export const CALENDAR_VERSION = 'us-macro-calendar-v1.0.0';
export const SCENARIOS = {
  inflation: [
    ['Lạm phát cao hơn kỳ vọng', 'Có thể được hỗ trợ', 'Có thể chịu áp lực', 'Có thể chịu áp lực', 'Nếu thị trường nâng kỳ vọng lãi suất và lợi suất thực. Vàng cũng có thể tăng khi nhu cầu phòng hộ lạm phát chiếm ưu thế.'],
    ['Lạm phát thấp hơn kỳ vọng', 'Có thể chịu áp lực', 'Có thể được hỗ trợ', 'Có thể được hỗ trợ', 'Nếu lợi suất giảm và kỳ vọng nới lỏng tăng; phản ứng còn phụ thuộc tăng trưởng và vị thế trước tin.'],
  ],
  labor: [
    ['Lao động mạnh hơn kỳ vọng', 'Có thể được hỗ trợ', 'Có thể chịu áp lực', 'Hai chiều', 'Việc làm mạnh có thể giữ lãi suất cao, nhưng cũng hỗ trợ khẩu vị rủi ro. Đọc cùng thất nghiệp, tiền lương và revision.'],
    ['Lao động yếu hơn kỳ vọng', 'Hai chiều', 'Có thể được hỗ trợ', 'Hai chiều', 'Kỳ vọng hạ lãi suất có thể hỗ trợ tài sản rủi ro; lo ngại suy thoái có thể kéo crypto giảm và thúc đẩy nhu cầu USD.'],
  ],
  growth: [
    ['Tăng trưởng mạnh hơn kỳ vọng', 'Có thể được hỗ trợ', 'Có thể chịu áp lực', 'Hai chiều', 'Tăng trưởng tốt hỗ trợ khẩu vị rủi ro, nhưng lợi suất tăng có thể gây áp lực. Kiểm tra cấu phần và revision.'],
    ['Tăng trưởng yếu hơn kỳ vọng', 'Hai chiều', 'Có thể được hỗ trợ', 'Hai chiều', 'Phản ứng phụ thuộc mức độ lo suy thoái so với kỳ vọng hạ lãi suất; vàng cũng có thể bị bán để lấy thanh khoản.'],
  ],
  policy: [
    ['Fed cứng rắn hơn kỳ vọng', 'Có thể được hỗ trợ', 'Có thể chịu áp lực', 'Có thể chịu áp lực', 'Đánh giá mức lãi suất, thông điệp, dự báo và họp báo cùng nhau; quyết định đã được định giá có thể tạo phản ứng ngược.'],
    ['Fed mềm mỏng hơn kỳ vọng', 'Có thể chịu áp lực', 'Có thể được hỗ trợ', 'Có thể được hỗ trợ', 'Thanh khoản kỳ vọng cải thiện có thể hỗ trợ crypto; cắt lãi suất vì khủng hoảng vẫn có thể đi cùng bán tháo.'],
  ],
};

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
  if (data.schema_version !== '1.0.0' || data.calendar_version !== CALENDAR_VERSION || data.scope !== 'US_major_macro'
    || !Array.isArray(data.events) || data.events.length < 15 || !Array.isArray(data.indicators) || data.indicators.length !== 5
    || !data.private_backup?.verified || !Number.isFinite(Date.parse(data.generated_at))) throw Error('Dữ liệu lịch không hợp lệ');
  const sources = {bls:'https://www.bls.gov/schedule/news_release/bls.ics',bea:'https://www.bea.gov/news/schedule/ics/online-calendar-subscription.ics',fed:'https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm',bls_data:'https://api.bls.gov/publicAPI/v2/timeseries/data/'};
  for (const [key,url] of Object.entries(sources)) {
    const source = data.sources?.[key];
    if (source?.source_url !== url || !/^[a-f0-9]{64}$/.test(source.sha256)
      || !Number.isFinite(Date.parse(source.retrieved_at)) || !Number.isFinite(Date.parse(source.checked_at))) throw Error('Dữ liệu lịch không hợp lệ');
  }
  if (!Array.isArray(data.private_backup.objects) || data.private_backup.objects.length !== 6
    || !data.private_backup.objects.every(o=>o.readback_verified === true && /^[a-f0-9]{64}$/.test(o.sha256))) throw Error('Dữ liệu lịch không hợp lệ');
  const ids = new Set();
  for (const e of data.events) {
    const host = new URL(e.source_url).hostname;
    if (typeof e.id !== 'string' || typeof e.title !== 'string' || typeof e.source_title !== 'string' || ids.has(e.id) || !['bls','bea','fed'].includes(e.provider) || e.currency !== 'USD'
      || !['high','medium'].includes(e.impact) || !SCENARIOS[e.category] || !Number.isFinite(Date.parse(e.scheduled_at))
      || !['www.bls.gov','www.bea.gov','www.federalreserve.gov'].includes(host)
      || !e.source_url.startsWith('https://') || e.actual !== null || e.forecast !== null || e.previous !== null) throw Error('Sự kiện lịch không hợp lệ');
    ids.add(e.id);
  }
  for (const i of data.indicators) {
    if (typeof i.title !== 'string' || !/^\d{4}-(0[1-9]|1[0-2])$/.test(i.reference_period) || !['percent','thousand_jobs'].includes(i.unit)
      || (i.value !== null && !Number.isFinite(i.value)) || (i.previous !== null && !Number.isFinite(i.previous))
      || new URL(i.source_url).hostname !== 'data.bls.gov' || !i.source_url.startsWith('https://')) throw Error('Số liệu BLS không hợp lệ');
  }
  return data;
}
