# Báo cáo khả thi nguồn dữ liệu cho 9 vị trí

**Ngày audit:** 2026-10-03. **Bằng chứng:** tài liệu provider chính thức, Coin Metrics Community catalog/live probes. Không mua API và không dùng key trả phí. Quyền công khai/derived/commercial vẫn chưa được xác nhận theo [data-rights.md](data-rights.md).

Register máy đọc được tại [`configs/research/metric-feasibility-v0.1.0.json`](../configs/research/metric-feasibility-v0.1.0.json) chuẩn hóa coverage, quyền, vintage và quyết định cho E1–E9. Bằng chứng live revision `metric-feasibility-v0.1.1` nằm tại [`docs/evidence/d05-live-probe-2026-10-03.json`](evidence/d05-live-probe-2026-10-03.json); raw response và manifest đầy đủ chỉ nằm trong `data/raw/d05/` bị Git ignore.

## Kết quả theo vị trí

| ID | Định nghĩa ECO dự kiến | Nguồn/coverage đã xác minh | Quyền và rủi ro | Kết luận |
|---|---|---|---|---|
| E1 | ETH MA Cycle Stretch | `PriceUSD` Core: Coin Metrics Community, ETH/1d, 2015-08-08..2026-10-01 trong D03 | Cùng quyền Community; thời điểm availability/vintage không có | Core candidate; không tuyên bố Pi Cycle báo đỉnh ETH |
| E2 | ETH NUPL dẫn xuất `1-1/MVRV` | Suy ra từ `CapMVRVCur` ETH/1d; không cần series NUPL độc lập | Derived output vẫn chịu quyền provider; không phải xác nhận độc lập | Diagnostic; không cộng trọng số riêng |
| E3 | RHODL / realized-cap age ratio | Glassnode có RHODL và realized-cap HODL-wave docs; RHODL endpoint mô tả asset `BTC`. Chưa có bằng chứng ETH coverage/plan; chưa có Coin Metrics realized-cap age-band nguồn Community khả dụng | Cần xác minh ETH endpoint, age-band/unit, lịch sử và licence/plan; realized-cap cohorts phải phù hợp account-based ETH | Chưa khả thi xác nhận; không code/điền placeholder |
| E4 | ETH Fee Activity Multiple, không gọi là Puell | Catalog live ghi `FeeTotNtv` 2015-07-30..2026-10-01, `FeeTotUSD` 2015-08-08..2026-10-01, `FeePrioTotNtv` 2021-08-05..2026-10-01 và `FeeBlobTotNtv` 2024-03-13..2026-10-01. Probe timeseries 2021-01-01..03: `FeeTotNtv` 3/3 rows HTTP 200; ba metric còn lại HTTP 403 | FeeTotNtv là native ETH; docs định nghĩa tổng fees gồm fees trả cho miners/validators/stakers/block producers và cả phần bị burn; ETH fee USD gồm execution + blob. L2, EIP-1559, burn/blob và Merge làm ý nghĩa thay đổi. Quyền Community/public vẫn unresolved | Ứng viên R&D duy nhất có sample access hiện tại: thử `ln(SMA30(FeeTotNtv)/SMA365(FeeTotNtv))` sau full audit; không thay vào Core, không gọi Puell, không xem là đã chọn |
| E5 | ETH 2Y MA Stretch | `PriceUSD` Core ETH/1d, D03 từ 2015-08-08 | Warm-up 730 ngày + causal normalizer; cùng quyền/vintage | Core candidate |
| E6 | ETH Log Trend Deviation | `PriceUSD` Core ETH/1d, D03 từ 2015-08-08 | Ngày gốc phải gắn snapshot/version; hệ số dùng quá khứ, cùng quyền/vintage | Core candidate |
| E7 | ETH MVRV Z causal | `CapMrktCurUSD` và `CapMVRVCur` D03 từ 2015-08-08; `CapRealUSD` direct bị HTTP 403, `R=market_cap/MVRV` chỉ là dẫn xuất đại số | Methodology account-based của provider; không trộn source; derived rights chưa rõ | Core candidate với nhãn `derived_realized_cap`, sigma/warm-up theo ADR-001 |
| E8 | ETH dormancy/spending proxy; không gọi Reserve Risk chính xác | Live catalog ghi `SplyAct1yr` ETH/1d 2015-07-30..2026-10-01 nhưng timeseries sample HTTP 403. Glassnode Indicators docs HTTP 200 và có `dormancy_account_based`; Metadata docs HTTP 200 có ETH/asset terms, nhưng chưa có credential/entitlement probe | Account/entity heuristic có thể mutable; ETH staking/contracts và self-transfers ảnh hưởng ý nghĩa; cần coverage/history/rights | Chưa đủ căn cứ chọn proxy; không dùng active supply đổi tên thành Reserve Risk |
| E9 | ETH NVT proxy | Live catalog ghi `TxTfrValAdjUSD` ETH/1d 2015-08-08..2026-10-01; timeseries Community probe 2021-01-01..03 HTTP 403. `TxTfrValDayDst` không có ETH support trong catalog probe (metric UTXO-specific) | Adjusted transfer-value definition/filters, internal transfers, contracts, bridges, MEV và licence cần nghiên cứu; market cap và volume cùng currency/time | Candidate bị quyền truy cập chặn; chưa full audit, chưa code |

## Tài liệu nguồn

- [Coin Metrics API v4](https://docs.coinmetrics.io/api/v4/) — `/catalog-all-v2/asset-metrics` cho asset/metric/frequency/time range; `403` là quyền không đủ, khác `null`/unsupported.
- [Coin Metrics Fees](https://gitbook-docs.coinmetrics.io/network-data/network-data-overview/fees-and-revenue/fees) — FeeTotNtv/USD, thành phần ETH execution/blob fees và burned fees.
- [Coin Metrics Active Supply](https://gitbook-docs.coinmetrics.io/network-data/network-data-overview/supply/active-supply) — định nghĩa trailing active supply cho account-based chains; không tương đương dormancy.
- [Coin Metrics Adjusted Transfer Value](https://gitbook-docs.coinmetrics.io/network-data/network-data-overview/transactions/transfer-value) — TxTfrValAdjUSD định nghĩa transfer value sau điều chỉnh noise/artifacts.
- [Glassnode Indicators](https://docs.glassnode.com/basic-api/endpoints/indicators) — RHODL endpoint chỉ ghi asset BTC; indicator docs yêu cầu API key.
- [Glassnode Supply](https://docs.glassnode.com/basic-api/endpoints/supply) — HODL waves / realized-cap HODL waves và endpoint yêu cầu API key.
- [Glassnode Metadata](https://docs.glassnode.com/basic-api/metadata) — cần tra asset/metric coverage bằng quyền phù hợp trước khi chọn endpoint.
- [Ethereum Merge](https://ethereum.org/roadmap/merge/) — Merge ngày 2022-09-15; không nối doanh thu PoW miner với validator PoS thành một Puell series giữ nguyên nghĩa.

## Quyết định D05

D05 hoàn tất ở mức feasibility và đã có live evidence revision: giữ 4 metric Core như đã khóa; E2 là diagnostic dẫn xuất; E4 `FeeTotNtv` là ứng viên R&D có sample access; E3/E8/E9 chưa có nguồn ETH/plan/right được xác minh đủ để implement. Không tự thu gọn tuyên bố về mục tiêu 9 vị trí. Catalog availability, HTTP 200 hoặc tài liệu endpoint không tự cấp quyền public/derived/commercial và không chứng minh historical vintage. Tiếp tục R&D chỉ sau khi full-history/gap audit, dữ liệu vintage, quyền và công thức của ứng viên cụ thể được chấp thuận.

## Live probe revision 2026-10-03

Script tái lập: `node scripts/audit-d05-feasibility.mjs 2026-10-03`. Lần chạy có 1 catalog HTTP 200 với 7 metric ETH/1d; 7 timeseries sample gồm `FeeTotNtv` HTTP 200 với 3/3 giá trị và `CapRealUSD`, `FeeTotUSD`, `FeeBlobTotNtv`, `FeePrioTotNtv`, `SplyAct1yr`, `TxTfrValAdjUSD` HTTP 403. Ba trang Glassnode liên quan trả HTTP 200 và có từ khóa endpoint mong đợi; đây chỉ là kiểm tra tài liệu, không phải kiểm tra quyền tài khoản. Hash, thời điểm và request metadata được giữ trong manifest local bị ignore dưới `data/raw/d05/`; bản tóm tắt không chứa raw nằm tại [evidence JSON](evidence/d05-live-probe-2026-10-03.json).
