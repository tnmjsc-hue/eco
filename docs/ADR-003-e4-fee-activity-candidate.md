# ADR-003 — Ứng viên E4 Fee Activity cho ETH

- Ngày khóa: 2026-10-03.
- Trạng thái: candidate research only; chưa phải component Core và chưa phải metric phát hành.
- Config: [`configs/research/e4-fee-candidate-v0.1.0.json`](../configs/research/e4-fee-candidate-v0.1.0.json).

## Quyết định

Nghiên cứu E4 bằng `FeeTotNtv` native ETH của Coin Metrics Community, daily UTC. Raw feature khóa trước khi đánh giá là:

`x_t = ln(SMA30(FeeTotNtv)_t / SMA365(FeeTotNtv)_t)`.

Hai SMA dùng ngày lịch UTC, bao gồm ngày `t`, và chỉ hợp lệ khi đủ cửa sổ không có ngày thiếu. Giá trị FeeTotNtv bằng 0 được giữ trong raw; nếu một trong hai trung bình cửa sổ không dương thì feature là `null` với reason, không thay bằng epsilon hoặc số 0. Normalizer dùng causal q05/q95 trên 1.460 ngày lịch trước `t`, tối thiểu 365 raw observations, clip 0–100. Điểm chỉ là mức hoạt động phí tương đối theo lịch sử, không phải xác suất.

Coin Metrics định nghĩa FeeTotNtv là tổng phí native; trên Ethereum gồm execution và blob fees, được cấu thành từ base fee, priority fee và blob fee, đồng thời vẫn tính phí bị burn. Vì ý nghĩa thay đổi qua EIP-1559, Merge và Dencun, báo cáo phải phân đoạn bốn regime đã khóa trong config. E4 không được gọi là Puell Multiple.

## Giới hạn và đánh giá

Snapshot E4-01 đã audit đủ coverage/quality nhưng không cung cấp `source_available_at` hoặc vintage revision lịch sử. Vì vậy engine candidate chỉ tạo reconstructed feature. Đánh giá trên holdout Core đã xem chỉ có tính mô tả; không được tuyên bố incremental utility. Cần holdout mới hoặc dữ liệu prospective trước khi đặt success rule cho E4.

Raw snapshot/manifest/hash giữ private. Quyền preview phi thương mại của Community không tự cấp quyền public riêng cho candidate trước khi có quyết định phương pháp; không mua API và không đăng ký nguồn trả phí trong ADR này.

## Ảnh hưởng lịch sử

Không thay `core-v0.1.0`, không đổi weights hoặc điểm đã công bố. E4 có methodology version riêng; nếu provider, đơn vị, cửa sổ, thành phần phí hoặc normalizer đổi thì tạo version mới và audit mới.
