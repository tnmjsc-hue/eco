export const PROXY_VERSION = 'network-proxies-v0.1.0';
export const PROXIES = [
  { id: 'exchange_share', slot: 'E3', name: 'Tỷ trọng ETH trên sàn', color: '#7b62a3', formula: 'ln(SMA30(SplyExNtv / SplyCur))',
    description: 'Tỷ trọng native ETH ở ví sàn được nhận diện, trung bình 30 ngày.',
    interpretation: 'Điểm cao: tỷ trọng ETH trên sàn cao hơn lịch sử gần.',
    limitation: 'Địa chỉ sàn có thể thiếu và được sửa hồi cứu. Dữ liệu flash là tạm thời; metric không đo tuổi ETH hay RHODL.' },
  { id: 'address_activity', slot: 'E8', name: 'Cường độ địa chỉ hoạt động', color: '#b07831', formula: 'ln(SMA30(AdrActCnt) / AdrBalCnt)',
    description: 'Địa chỉ hoạt động trung bình 30 ngày so với số địa chỉ có số dư ETH.',
    interpretation: 'Điểm cao: cường độ hoạt động địa chỉ cao hơn lịch sử gần.',
    limitation: 'Địa chỉ không bằng người dùng; active và funded là hai tập khác nhau. Có thể gồm gửi 0, tự gửi và giao dịch thất bại. Không đo Dormancy.' },
  { id: 'value_per_transfer', slot: 'E9', name: 'Vốn hóa / lượt chuyển ETH', color: '#237f9d', formula: 'ln(CapMrktCurUSD / SMA90(TxTfrCnt))',
    description: 'Vốn hóa ETH chia số lượt chuyển native ETH trung bình ngày trong 90 ngày.',
    interpretation: 'Điểm cao: vốn hóa trên lượt chuyển cao hơn lịch sử gần.',
    limitation: 'Gồm internal transfers, chưa điều chỉnh theo chủ sở hữu; số lượt không phải giá trị chuyển USD. Không tương đương NVT/CVDD và không bao quát ERC-20/L2.' },
];
const datePattern = /^\d{4}-\d{2}-\d{2}$/;
const hashPattern = /^[a-f0-9]{64}$/;
const numeric = v => typeof v === 'number' && Number.isFinite(v);
export function validateProxyPointer(pointer) {
  if (!/^proxy-[a-f0-9]{20}$/.test(pointer?.release_id) || pointer.methodology_version !== PROXY_VERSION
      || pointer.manifest_url !== `/data/network-proxies/releases/${pointer.release_id}/manifest.json`
      || !hashPattern.test(pointer.manifest_sha256)) throw new Error('Pointer metric mở rộng không hợp lệ.');
}
export function validateProxyRelease(history, manifest, research) {
  if (manifest.methodology_version !== PROXY_VERSION || manifest.protocol !== `${PROXY_VERSION}-protocol-1`
      || manifest.protocol_sha256 !== '4f3b9ebdf2ce0c69704174c47cd5183731942b1051321e33596d80d39f71af2c'
      || manifest.source_evidence_sha256 !== '5d35aa2fa85e6a8ef7d6e538d8f7fc8ac456f366b3efedac54cd01b07200e72d'
      || manifest.research_only !== true || manifest.core_promotion !== false || manifest.series_type !== 'reconstructed'
      || manifest.asset !== 'eth' || manifest.attribution?.licence !== 'CC BY-NC 4.0'
      || !manifest.private_backup?.all_objects_readback_verified || manifest.bootstrap_replicates !== 10000
      || history.release_id !== manifest.release_id || history.methodology_version !== PROXY_VERSION
      || history.asset !== 'eth' || history.series_type !== 'reconstructed' || history.composite_score !== null
      || !Array.isArray(history.rows) || !history.rows.length || history.rows.length !== manifest.rows) {
    throw new Error('Hợp đồng metric mở rộng không hợp lệ.');
  }
  let previous = null;
  for (const row of history.rows) {
    if (!datePattern.test(row.date) || new Date(row.date+'T00:00:00Z').toISOString().slice(0,10) !== row.date
        || (previous && Date.parse(row.date)-Date.parse(previous) !== 86400000)
        || Object.keys(row.metrics ?? {}).sort().join() !== PROXIES.map(m=>m.id).sort().join()) throw new Error('Lịch sử mở rộng thiếu ngày hoặc sai metric.');
    for (const metric of PROXIES) {
      const value = row.metrics[metric.id];
      if ((value.score !== null && (!numeric(value.score) || value.score < 0 || value.score > 100))
          || (value.raw !== null && !numeric(value.raw))
          || (value.value !== null && (!numeric(value.value) || value.value <= 0))
          || ((value.value === null) !== (value.raw === null))
          || (value.raw !== null && Math.abs(Math.log(value.value)-value.raw) > 1e-10)
          || (value.score !== null && (value.raw === null || value.score_reason !== null))
          || !Array.isArray(value.source_flags) || value.source_flags.some(f=>typeof f !== 'string' || f.length > 80)) throw new Error('Giá trị metric mở rộng không hợp lệ.');
    }
    previous = row.date;
  }
  if (history.rows[0].date !== '2015-07-30' || history.rows.at(-1).date !== manifest.last_observation_date
      || manifest.first_observation_date !== history.rows[0].date) throw new Error('Phạm vi metric mở rộng không khớp.');
  for (const metric of PROXIES) {
    for (const defs of [manifest.metric_definitions, history.metric_definitions]) {
      if (defs?.[metric.id]?.formula !== metric.formula || defs[metric.id].equivalent_to_original !== false
          || defs[metric.id].slot !== metric.slot || Object.keys(defs).length !== 3) throw new Error('Công thức proxy đã thay đổi dưới cùng version.');
    }
    const valid = history.rows.filter(r=>r.metrics[metric.id].score !== null);
    const raw = history.rows.filter(r=>r.metrics[metric.id].raw !== null);
    const c = manifest.coverage[metric.id];
    if (c.normalized_rows !== valid.length || c.raw_rows !== raw.length || c.calendar_rows !== history.rows.length
        || c.first_score_date !== (valid[0]?.date ?? null) || c.last_score_date !== (valid.at(-1)?.date ?? null)) throw new Error('Coverage metric không khớp.');
  }
  if (research.methodology_version !== PROXY_VERSION || research.protocol !== manifest.protocol
      || research.status !== 'exploratory_reconstructed_only' || research.bootstrap?.replicates !== 10000
      || research.bootstrap.block_calendar_days !== 90 || research.bootstrap.seed !== 20261003
      || research.decision !== 'publish_research_metrics_only_no_core_promotion') throw new Error('Báo cáo mở rộng sai protocol.');
}
export function exportProxyCSV(rows, manifest) {
  const ids = PROXIES.map(m=>m.id);
  const header = ['observation_date', ...ids.flatMap(id=>[id+'_value',id+'_raw',id+'_score',id+'_reason',id+'_source_flags'])];
  const csv = rows.map(row=>[row.date,...ids.flatMap(id=>{ const m=row.metrics[id]; return [m.value??'',m.raw??'',m.score??'',m.raw_reason??m.score_reason??'',m.source_flags.join('|')]; })].join(','));
  return [`# Coin Metrics Community Data; CC BY-NC 4.0; noncommercial; transformed data; no warranty`,
    `# ${manifest.release_id}; ${PROXY_VERSION}; reconstructed; research proxies; not a probability`,header.join(','),...csv].join('\n')+'\n';
}
