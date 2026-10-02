# Hợp đồng dữ liệu Coin Metrics cho Core

**Trạng thái:** bản audit sơ bộ; chưa khóa adapter production hoặc `methodology_version`.

## Phạm vi request

- Provider: Coin Metrics Community API v4, endpoint `/timeseries/asset-metrics`.
- Asset: `eth`; tần suất: `1d`.
- Trường được probe riêng: `PriceUSD`, `CapMrktCurUSD`, `SplyCur`, `CapMVRVCur`.
- Request không dùng API key. Mỗi request ghi tham số không bí mật, thời điểm gửi, HTTP status, hash SHA-256 và tên file response trong manifest riêng tư.
- Raw response được lưu dưới `data/raw/coinmetrics/`, nằm trong `.gitignore`; không commit response dữ liệu.

## Quy ước thời gian cần tuân thủ

API trả trường `time` dạng ISO 8601 UTC. Probe ban đầu cho thấy thời gian ngày ở `00:00:00Z`, nhưng riêng timestamp này chưa chứng minh giá trị là đầu ngày hay thời điểm đại diện cho kỳ đã đóng. Chưa gán `observation_date` hoặc `period_end_utc` cho sản xuất cho tới khi so với tài liệu metric cụ thể và kiểm tra hành vi endpoint.

Các trường thời gian giữ riêng trong schema:

- `source_timestamp`: chuỗi gốc không đổi từ Coin Metrics.
- `observation_date`: ngày UTC mà phép đo đại diện; ánh xạ cần được xác minh.
- `period_end_utc`: cuối kỳ của phép đo; chưa được xác minh bởi probe timestamp đơn lẻ.
- `source_available_at`: thời điểm nhà cung cấp công bố dữ liệu; metadata hiện có chưa cung cấp timestamp lịch sử cho từng dòng.
- `retrieved_at`: thời điểm máy dự án tải response.
- `computed_at`: thời điểm engine tính kết quả.
- `published_at`: thời điểm release công khai, nếu có.

Không dùng dòng của ngày chưa đóng trong điểm chính thức. Mọi phép tính tại `t` chỉ được phép dùng dữ liệu đã sẵn có tại thời điểm đó. Độ trễ và revision cần đo bằng các snapshot lặp lại; dữ liệu hiện tại không tái dựng được lịch sử `source_available_at`.

## Phân loại probe

- HTTP `200` cùng dữ liệu có giá trị: trường truy cập được trong đúng asset, tần suất và khoảng đã thử.
- HTTP `200` nhưng không có dòng hoặc giá trị: `no_rows` hoặc `rows_without_values`; đây không phải 403.
- HTTP `401`/`403`: quyền truy cập bị từ chối; không diễn giải là metric không tồn tại.
- HTTP `429`, `5xx`, lỗi mạng hoặc payload không theo schema: lỗi truy cập/transport/schema; không diễn giải là thiếu lịch sử.

Probe mẫu không phải full audit. D03 vẫn phải tải toàn lịch sử, xử lý pagination, gaps, duplicates, invalid values, revisions và checksum snapshot; chỉ sau đó mới quyết định khoảng dữ liệu hữu dụng.

## Nguồn

- [Coin Metrics API v4](https://docs.coinmetrics.io/api/v4/)
- [Định nghĩa market capitalization và MVRV](https://docs.coinmetrics.io/network-data/network-data-overview/market/market-capitalization)
