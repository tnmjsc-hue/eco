# ADR-005 — Ba metric thay thế bằng dữ liệu ETH truy cập được

- Ngày: 2026-10-03. Quyết định: Accepted cho preview nghiên cứu phi thương mại.
- Version mới: `network-proxies-v0.1.0`; protocol khóa trước khi backfill và đánh giá toàn bộ lịch sử.

Người dùng yêu cầu chủ động tìm nguồn khác hoặc mô phỏng theo mô tả/dữ liệu đã lưu và hoàn thành thêm ít nhất ba metric. Probe Community thật trả HTTP 200 cho sáu trường ETH cần thiết. Adjusted transfer value, age bands và dormancy vẫn không truy cập được; catalog Pro không cấp quyền tải. Chọn ba phép dẫn xuất từ dữ liệu on-chain thật, công thức mới và ID riêng.

| Vai trò | ID mới | Công thức raw | Diễn giải điểm cao |
|---|---|---|---|
| E3 · hành vi nắm giữ | `exchange_share` | `ln(SMA30(SplyExNtv / SplyCur))` | Tỷ trọng native ETH tại địa chỉ sàn được nhận diện cao hơn lịch sử gần |
| E8 · hoạt động chi tiêu | `address_activity` | `ln(SMA30(AdrActCnt) / AdrBalCnt)` | Hoạt động địa chỉ trung bình cao hơn so với số địa chỉ có số dư |
| E9 · định giá mạng | `value_per_transfer` | `ln(CapMrktCurUSD / SMA90(TxTfrCnt))` | Vốn hóa cao hơn trên mỗi lượt chuyển ETH trung bình ngày |

Đây là **thay thế vai trò nghiên cứu**, không tái tạo RHODL, Dormancy/Reserve Risk hay NVT theo giá trị chuyển. Không gọi chúng là ba metric độc lập đã chứng minh dự báo. Điểm 0–100 chỉ định vị đại lượng trong lịch sử gần; không mặc định cả ba có cùng ý nghĩa nóng/lạnh. Không thêm trọng số vào Core. Lịch sử và pointer Core giữ nguyên; ba metric có manifest/pointer riêng, CSV và kết quả đánh giá riêng.

Normalizer kế thừa thuật toán nhân quả đã kiểm: q05/q95 tuyến tính trên 1.460 ngày **trước t**, tối thiểu 365 raw hợp lệ. SMA dùng ngày lịch liên tiếp gồm t. Null/gap không nội suy; đầu vào zero thật được giữ, đối số log không dương tạo null kèm lý do. Ngày quan sát UTC, ngày đóng và thời điểm tải riêng; không biết historical availability nên chỉ gọi `reconstructed`.

Exchange supply là tổng ví nóng/lạnh của các sàn provider nhận diện, có thể thiếu địa chỉ và bị sửa hồi cứu. API hiện có cờ `flash` cho lịch sử này: lưu cờ từ raw, nêu provisional trong manifest/UI, không coi là dữ liệu as-published. `AdrActCnt` có thể gồm giao dịch thất bại, gửi 0 hoặc tự gửi; không bằng số người dùng. Mẫu số funded addresses không cùng tập với active addresses, tỷ số không phải xác suất tham gia và không đo tuổi ETH. `TxTfrCnt` tính chuyển native ETH giá trị dương giữa địa chỉ khác nhau, gồm internal transfers, loại failed/self-send; không entity-adjusted, không đo USD chuyển và không đại diện ERC-20/L2.

Đánh giá khóa hướng cao theo raw, baseline Core/E7/nhóm giá và phép thăm dò `0.75*Core + 0.25*proxy`, bootstrap ghép cặp 90 ngày/10.000 lần/seed 20261003, tương quan và các giai đoạn London/Merge/Dencun. Holdout Core đã được xem nên kết quả chỉ exploratory; không đảo chiều hoặc tối ưu công thức theo kết quả. Công bố metric/báo cáo nghiên cứu được phép dù chưa chứng minh utility; đưa vào composite chính thức cần ADR/version và kiểm định mới.

Quyền: Community inputs theo [Coin Metrics Community](https://gitbook-docs.coinmetrics.io/packages/coin-metrics-community-data) và [CC BY-NC 4.0](https://creativecommons.org/licenses/by-nc/4.0/), áp dụng xác nhận phi thương mại tại ADR-002. Ghi nguồn, giấy phép, các phép biến đổi và không bảo đảm trong UI/CSV/manifest. Raw giữ private, backup R2/readback hash trước publication. Không tải hoặc cấp phép thay cho trường Pro, không mua API. Snapshot nguồn, code/config và license evidence được hash; release cũ bất biến, revision có lý do khi dữ liệu lịch sử thay đổi.

Lựa chọn khác: tiếp tục chờ credential Pro không đáp ứng yêu cầu hoàn thành phiên này; tự dựng archive node/cohort ETH cần dữ liệu transaction-level và kiểm account/staking, không thể suy từ aggregate. E2 là dẫn xuất đại số của MVRV và E4 đã có kết quả R&D nên không dùng chúng để đếm ba metric mới. Báo cáo thực nghiệm và bằng chứng thực thi sẽ ghi trong `NETWORK_PROXIES.md` và HANDOFF.

Nguồn định nghĩa: [Exchange supply](https://gitbook-docs.coinmetrics.io/network-data/network-data-overview/exchange/exchange-supply), [Active addresses](https://gitbook-docs.coinmetrics.io/network-data/network-data-overview/addresses/active-addresses), [Addresses with balance](https://gitbook-docs.coinmetrics.io/network-data/network-data-overview/supply/addresses-with-balance), [Transfers](https://gitbook-docs.coinmetrics.io/network-data/network-data-overview/transactions/transfers).
