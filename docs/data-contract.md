# Hợp đồng dữ liệu Coin Metrics cho Core

**Trạng thái:** D02 đã chốt cách diễn giải cho audit; chưa khóa adapter production hoặc `methodology_version`.

## Phạm vi request

- Provider: Coin Metrics Community API v4, endpoint `/timeseries/asset-metrics`.
- Asset: `eth`; tần suất: `1d`.
- Trường được probe riêng: `PriceUSD`, `CapMrktCurUSD`, `SplyCur`, `CapMVRVCur`.
- Request không dùng API key. Mỗi request ghi tham số không bí mật, thời điểm gửi, HTTP status, hash SHA-256 và tên file response trong manifest riêng tư.
- Raw response được lưu dưới `data/raw/coinmetrics/`, nằm trong `.gitignore`; không commit response dữ liệu.

## Quy ước thời gian cần tuân thủ

API trả trường `time` dạng ISO 8601 UTC; daily rows dùng nhãn `00:00:00Z` của ngày UTC. Tài liệu Coin Metrics mô tả `PriceUSD` là giá cuối ngày UTC; `SplyCur` là supply ở thời điểm tính toán trong ngày; `CapMrktCurUSD` dùng `SplyCur × PriceUSD` với giá đóng cửa ngày; `CapMVRVCur` là tỷ lệ vốn hóa thị trường/vốn hóa realized ở tần suất ngày. Canonical audit giữ nguyên nhãn nguồn, coi ngày UTC trong nhãn là `observation_date`, và dùng nửa đêm đầu ngày kế tiếp làm `period_end_utc` theo quy ước biên cuối kỳ mở.

Quy ước này mô tả kỳ đo, **không** chứng minh dữ liệu đã sẵn có đúng tại `period_end_utc`. Không dùng ngày đang mở trong tính điểm. Độ trễ công bố lịch sử và revision theo vintage chưa được API mẫu cung cấp; không thể dựng lại `source_available_at` hay `as_published` từ snapshot hiện tại.

Các trường thời gian giữ riêng trong schema:

- `source_timestamp`: chuỗi gốc không đổi từ Coin Metrics.
- `observation_date`: phần ngày UTC của `time` gốc.
- `period_end_utc`: biên mở đầu ngày kế tiếp (`time` date + 1 ngày), quy ước cuối kỳ daily UTC; không phải timestamp nguồn riêng.
- `source_available_at`: thời điểm nhà cung cấp công bố dữ liệu; metadata hiện có chưa cung cấp timestamp lịch sử cho từng dòng.
- `retrieved_at`: thời điểm máy dự án tải response.
- `computed_at`: thời điểm engine tính kết quả.
- `published_at`: thời điểm release công khai, nếu có.

Không dùng dòng của ngày chưa đóng trong điểm chính thức. Mọi phép tính tại `t` chỉ được phép dùng dữ liệu đã sẵn có tại thời điểm đó. Độ trễ hiện tại có thể đo bằng snapshot lặp lại; một snapshot không tái dựng được lịch sử `source_available_at` hoặc vintage đã công bố.

## Phân loại probe

- HTTP `200` cùng dữ liệu có giá trị: trường truy cập được trong đúng asset, tần suất và khoảng đã thử.
- HTTP `200` nhưng không có dòng hoặc giá trị: `no_rows` hoặc `rows_without_values`; đây không phải 403.
- HTTP `401`/`403`: quyền truy cập bị từ chối; không diễn giải là metric không tồn tại.
- HTTP `429`, `5xx`, lỗi mạng hoặc payload không theo schema: lỗi truy cập/transport/schema; không diễn giải là thiếu lịch sử.

Probe mẫu không phải full audit. D03 tải toàn lịch sử, giữ từng trang raw riêng tư và canonical JSONL có SHA-256, kiểm kê gaps, duplicates, invalid values và revision-status nếu API trả trường đó. Không có status field không được diễn giải là không có revision. Khoảng dữ liệu hữu dụng dựa vào report; không nội suy hoặc điền giá trị thiếu.

## Nguồn

- [Coin Metrics API v4](https://docs.coinmetrics.io/api/v4/)
- [PriceUSD: giá cuối ngày UTC](https://gitbook-docs.coinmetrics.io/network-data/network-data-overview/market/price)
- [Current Supply](https://gitbook-docs.coinmetrics.io/network-data/network-data-overview/supply/current-supply)
- [Market capitalization và MVRV](https://gitbook-docs.coinmetrics.io/network-data/network-data-overview/market/market-capitalization)
