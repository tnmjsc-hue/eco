# E4 — Audit dữ liệu FeeTotNtv

**Trạng thái:** E4-01 hoàn tất ở mức full-history data audit; E4 chưa được chọn làm metric và chưa được tính vào Core.

Ngày 2026-10-03, adapter ETH/1d của Coin Metrics Community tải `FeeTotNtv` không cần API key từ 2015-07-30 đến 2026-10-02. Snapshot có 4.083 ngày, 5 trang API, không có ngày thiếu, duplicate, timestamp sai, sai asset, null hoặc giá trị âm. Có 8 giá trị bằng 0 ở những ngày đầu; chúng được giữ nguyên và ghi trong quality policy vì zero hợp lệ ở raw nhưng không được đưa thẳng vào logarithm.

Canonical SHA-256 là `c0cd16263f6ebf33ef2c431a057fc827612bdd67b0312927f308e31b8fbe4f8c`; manifest SHA-256 là `862aa7b185903259b6ab56f72d7ffd46570c6827e4cee0234ffb694ca6bb5362`. Raw pages, canonical JSONL và manifest nằm trong snapshot riêng tư bị Git ignore; bản tóm tắt không chứa raw ở [evidence JSON](evidence/e4-fee-backfill-2026-10-03.json).

Theo tài liệu Coin Metrics, `FeeTotNtv` là tổng phí native; với Ethereum gồm execution fee và blob fee, được cấu thành từ base fee, priority fee và blob fee, đồng thời vẫn tính phần phí bị burn. Vì semantics thay đổi qua EIP-1559, Merge và Dencun, task kế tiếp E4-02 phải khóa công thức, phân đoạn sự kiện, chiều tín hiệu, warm-up và quyền phát hành trước khi viết feature. Ứng viên hiện tại là giả thuyết `ln(SMA30(FeeTotNtv) / SMA365(FeeTotNtv))`; đây là activity proxy nghiên cứu, không gọi là Puell Multiple.

Snapshot không cung cấp `source_available_at` hoặc lịch sử revision; kết quả chỉ là reconstructed audit. E4-01 không đăng ký tài khoản, không truy cập email và không mua API.

E4-04 chạy exploratory evaluation trên đúng cửa sổ Core 2020-01-01..2025-10-01: Fee Activity AP `0.240946`, Core `0.554249`, E7 `0.553773`, nhóm giá `0.545430`. Paired moving-block bootstrap 90 ngày cho chênh lệch Fee Activity trừ Core có CI 95% `[-0.624877; -0.129710]`; các baseline khác cũng âm. Các regime cho kết quả khác nhau mạnh, trong đó post-Merge/pre-Dencun chỉ có 3 nhãn dương. Quyết định: giữ E4 ở R&D-only, không đưa vào Core hoặc public metric; đây là bằng chứng mô tả reconstructed, không phải kết luận nhân quả.
