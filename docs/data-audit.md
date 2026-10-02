# Báo cáo probe khả năng truy cập Coin Metrics

**Lần chạy:** 2026-10-02 17:51 UTC (ngày nghiệp vụ 2026-10-03, Asia/Saigon). **Loại bằng chứng:** probe mẫu, không phải full audit.

## Phạm vi

Coin Metrics Community API v4 `/timeseries/asset-metrics`, `assets=eth`, `frequency=1d`, không API key. Bốn metric được gọi tách biệt tại ba khoảng: 2015-08-01..12, 2018-01-01..03, và 2026-09-30..10-02. Script: [`scripts/audit-coinmetrics.mjs`](../scripts/audit-coinmetrics.mjs).

| Metric | 2015: dòng có giá trị, đầu..cuối | 2018: dòng có giá trị | Gần nhất: dòng có giá trị, đầu..cuối | Kết quả |
|---|---:|---:|---:|---|
| `PriceUSD` | 5, 2015-08-08..12 | 3 | 2, 2026-09-30..10-01 | HTTP 200; có dữ liệu ở cả ba khoảng |
| `CapMrktCurUSD` | 5, 2015-08-08..12 | 3 | 2, 2026-09-30..10-01 | HTTP 200; có dữ liệu ở cả ba khoảng |
| `SplyCur` | 12, 2015-08-01..12 | 3 | 2, 2026-09-30..10-01 | HTTP 200; có dữ liệu ở cả ba khoảng |
| `CapMVRVCur` | 5, 2015-08-08..12 | 3 | 2, 2026-09-30..10-01 | HTTP 200; có dữ liệu ở cả ba khoảng |

Tổng cộng 12/12 request trả HTTP 200 và payload có giá trị. Khác biệt ngày bắt đầu giữa `SplyCur` và ba trường còn lại đã được giữ nguyên, không nội suy hoặc coi là ngày lỗi. Lần tải gần nhất hoàn tất lúc 2026-10-02 17:51 UTC; API mới nhất trả record mang nhãn `2026-10-01`. Đây chỉ là quan sát hai lần chạy ngắn; chưa đủ để ước lượng SLA/lag.

## Bằng chứng riêng tư

Manifest, request URL không bí mật, thời gian request/completion, response headers được chọn, HTTP status, số dòng, timestamp đầu/cuối, kích thước, tên raw file và SHA-256 được lưu tại:

`data/raw/coinmetrics/coinmetrics-2026-10-03-2026-10-02T175134924Z/manifest.json`

Mỗi body response nằm cạnh manifest. Thư mục `data/raw/` bị Git ignore theo `.gitignore`; raw data không được commit hoặc công khai. Chạy lại bằng `node scripts/audit-coinmetrics.mjs 2026-10-03`. Hai lượt trong cùng phiên trả cùng SHA-256 cho cả 12 body; điều đó không chứng minh lịch sử không bị revision.

## Kết luận và giới hạn

- Capability đã xác nhận cho bốn metric, đúng asset `eth` và tần suất `1d`, trong các khoảng đã probe.
- Không có 403 trong lần chạy này. Kết quả 403 lịch sử của `CapRealUSD`/`FeeTotUSD` trong [RESEARCH.md](RESEARCH.md) là probe khác; không suy rộng sang 4 metric Core.
- HTTP 200 ở mẫu không chứng minh full coverage, continuity, không có duplicate/revision, quyền tái phân phối, hay khả năng tái lập release.
- API `time` trả timestamp `00:00:00Z`. Tài liệu metric daily UTC được dùng để gán phần ngày làm `observation_date`, và nửa đêm ngày sau làm biên cuối kỳ mở; `source_available_at` và lịch sử revision không được cung cấp.
- Không có điểm ECO, backtest, hoặc `methodology_version` được tính từ dữ liệu probe.

## D03 — full-history snapshot

Chạy `node scripts/backfill-coinmetrics.mjs 2015-08-01 2026-10-03` với Coin Metrics Community API v4, không API key. Request range gồm ngày 2015-08-01..2026-10-02; endpoint trả 5 trang, tổng 4.080 dòng và 4.080 ngày riêng biệt, từ 2015-08-01 đến 2026-10-01. Ngày 2026-10-02 không có dòng trong response và được ghi là một ngày thiếu, không được lấp hoặc loại khỏi báo cáo.

| Metric | Giá trị hợp lệ đầu | Giá trị hợp lệ cuối | Null | Thiếu field | Không hợp lệ | Zero / âm |
|---|---|---|---:|---:|---:|---:|
| `PriceUSD` | 2015-08-08 | 2026-10-01 | 7 | 0 | 0 | 0 / 0 |
| `CapMrktCurUSD` | 2015-08-08 | 2026-10-01 | 7 | 0 | 0 | 0 / 0 |
| `SplyCur` | 2015-08-01 | 2026-10-01 | 0 | 0 | 0 | 0 / 0 |
| `CapMVRVCur` | 2015-08-08 | 2026-10-01 | 7 | 0 | 0 | 0 / 0 |

Số dòng trùng: 0. Timestamp không hợp lệ: 0. Sai asset: 0. Thiếu field: 0 cho cả bốn metric. API response không có trường revision-status cho metric, nên **không** suy ra rằng không có revision. SHA-256 canonical snapshot: `aa78757fcaee33ef23ecf3ebd92791a685df2617f2b3874f5f5183d16babdd03`. Hash từng trang, canonical rows, request metadata và manifest giữ riêng tư tại `data/raw/coinmetrics/coinmetrics-backfill-2026-10-03-2026-10-02T182337734Z/`; chuỗi dữ liệu thô không được commit hoặc công khai.

D03 hoàn tất với tư cách audit toàn lịch sử, không có nghĩa dữ liệu không còn gap hoặc đã sẵn sàng production. Dòng mới nhất chậm hơn một ngày so với ngày kết thúc yêu cầu; một lần lấy dữ liệu không xác lập SLA của provider. Availability/vintage lịch sử và quyền hiển thị công khai, tái phân phối, điểm dẫn xuất hay sử dụng thương mại vẫn chưa được giải quyết. `score_available=false` và `data_release_available=false`.
