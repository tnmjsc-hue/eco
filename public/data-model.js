export const METRICS = [
  { id: 'E1', name: 'MA Cycle', description: 'SMA 111 / (2 × SMA 350)', weight: 1 / 6 },
  { id: 'E5', name: 'MA 2 năm', description: 'Giá / SMA 730 ngày', weight: 1 / 6 },
  { id: 'E6', name: 'Log Trend', description: 'Độ lệch xu hướng log nhân quả', weight: 1 / 6 },
  { id: 'E7', name: 'MVRV Z', description: 'Định giá / độ phân tán vốn hóa', weight: 1 / 2 },
];
export const REASONS = { raw_unavailable: 'Thiếu input / warm-up raw', normalizer_warmup: 'Warm-up normalizer', degenerate_normalizer: 'Biên chuẩn hóa suy biến' };
export function customScore(row, selected) {
  const metrics = METRICS.filter(m => selected.includes(m.id));
  if (!metrics.length || metrics.length !== selected.length || metrics.some(m => row.components[m.id] === null)) return null;
  return metrics.reduce((sum, m) => sum + row.components[m.id] * m.weight, 0) / metrics.reduce((sum, m) => sum + m.weight, 0);
}
export function displayScore(value) { return value === null ? '—' : String(Math.floor(value + .5)); }
export function scoreColor(value) {
  if (value === null) return '#687575';
  return ['#28836d', '#609c49', '#b59021', '#cd7c3a', '#c85b53'][Math.min(4, Math.floor(value / 20))];
}
export function dateMinus(value, days) { const date = new Date(`${value}T00:00:00Z`); date.setUTCDate(date.getUTCDate() - days); return date.toISOString().slice(0, 10); }
export function validateHistory(data, releaseId) {
  if (data.release_id !== releaseId || data.methodology_version !== 'core-v0.1.0' || data.series_type !== 'reconstructed' || data.asset !== 'eth' || data.schema_version !== '1.0.0' || !Array.isArray(data.rows) || !data.rows.length) throw new Error('Hợp đồng dữ liệu không khớp.');
  let previous = null;
  for (const row of data.rows) {
    if (!/^\d{4}-\d{2}-\d{2}$/.test(row.date) || dateMinus(row.date, 0) !== row.date || (previous && dateMinus(row.date, 1) !== previous)) throw new Error('Chuỗi ngày UTC không liên tục.');
    previous = row.date;
    if (typeof row.period_closed_at_retrieval !== 'boolean' || (!row.period_closed_at_retrieval && (row.score !== null || row.price_usd !== null))) throw new Error('Ngày chưa đóng không được có giá hoặc điểm.');
    if (row.price_usd !== null && (!Number.isFinite(row.price_usd) || row.price_usd <= 0)) throw new Error('Giá không hợp lệ.');
    const values = METRICS.map(m => row.components?.[m.id]);
    if (values.some(v => v !== null && (!Number.isFinite(v) || v < 0 || v > 100))) throw new Error('Thành phần không hợp lệ.');
    const coverage = values.filter(v => v !== null).length;
    const expected = customScore(row, METRICS.map(m => m.id));
    if (coverage !== row.coverage || (expected === null ? row.score !== null : !Number.isFinite(row.score) || Math.abs(row.score - expected) > 1e-8)) throw new Error('Điểm / coverage không khớp.');
  }
  return data;
}
export function exportCSV(rows, selected, mode, manifest) {
  const quote = value => `"${String(value ?? '').replaceAll('"', '""')}"`;
  const headers = ['date_utc', 'price_usd', 'core_score', 'custom_score', 'E1', 'E5', 'E6', 'E7', 'coverage', 'methodology_version', 'release_id', 'series_type', 'selected_components', 'source', 'license', 'license_url', 'modifications'];
  const number = n => n === null ? '' : n.toFixed(4);
  const lines = rows.map(r => [r.date, number(r.price_usd), number(r.score), mode === 'custom' ? number(customScore(r, selected)) : '', ...METRICS.map(m => number(r.components[m.id])), r.coverage, manifest.methodology_version, manifest.release_id, 'reconstructed', mode === 'custom' ? selected.join('|') : 'E1|E5|E6|E7', 'Coin Metrics Community Data', 'CC BY-NC 4.0', manifest.license_url, 'ECO normalized and aggregated; no endorsement; no warranties'].map(quote).join(','));
  return '\uFEFF' + [headers.join(','), ...lines].join('\r\n');
}
