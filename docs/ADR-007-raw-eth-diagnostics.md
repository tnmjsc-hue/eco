# ADR-007 — E2 và hai chỉ số bối cảnh ETH

Ngày khóa: 2026-10-03, trước implementation và tính lịch sử ba series. Người dùng yêu cầu hoàn thiện E2 → nguồn cung → số dư sàn. Protocol [diagnostics-v0.1.0](../configs/research/diagnostics-v0.1.0.json) có phiên bản riêng, raw diagnostics only, không normalizer hoặc điểm tổng hợp.

SHA-256 của protocol canonical JSON: `fb7f5b80ca84ffc4babb8b5ffe823574500f13fed31fc03a3a25922da76afc4a`.

## Quyết định

- E2 `nupl_diagnostic = 1 - 1/CapMVRVCur(t)`, đơn vị ratio, hiển thị phần trăm bằng nhân 100. Dùng helper đã có và **đúng snapshot Core cha**; xác minh replay Core khớp lịch sử cha. Đây là biến đổi MVRV, không thêm phiếu độc lập hoặc quảng cáo là tỷ lệ holder có lãi.
- C1 `supply_change_30d = 100 * (SplyCur(t)/SplyCur(t-30) - 1)`, đơn vị phần trăm. Dùng snapshot network cha. `SplyCur` là current issued supply của provider, khác circulating/free-float supply; chênh lệch không tách gross issuance và burn.
- C2 `exchange_balance_change_30d = SplyExNtv(t) - SplyExNtv(t-30)`, đơn vị ETH. Dùng cùng snapshot network cha và giữ flags của cả cửa sổ. Đây là thay đổi số dư ở các địa chỉ được nhận diện, không phải đo đầy đủ nạp/rút hoặc hành vi holder. Nhãn sàn có thể đổi; `flash` phải được nêu trên UI/CSV.

C1/C2 yêu cầu đủ **31 ngày lịch UTC liên tục**, gồm t và t-30, không chỉ lấy hai dòng cách nhau 30 index. Missing/invalid/zero denominator trả null có reason; số âm và chênh lệch bằng 0 hợp lệ được giữ. E2 không positive-MVRV thì null, không ép về 0/50. Đánh giá t chỉ dùng ngày <=t; ngày tải và ngày khả dụng không được nhập làm một.

## Nguồn, lưu trữ và vận hành

Đầu vào Community đã có quyền nghiên cứu phi thương mại CC BY-NC theo ADR-002 và evidence network đã khóa. Không dùng Arkham/trial chưa được cấp quyền. Snapshot private R2 phải readback hash; tải lại **đúng snapshot cha** bằng bucket token hiện có, không tạo token hoặc quyền mới. Backend kiểm raw/canonical/UTC/schema/receipt và parent manifest/history SHA trước tính.

Phát hành riêng `/data/diagnostics/`: JSON history, báo cáo mô tả coverage/regime, manifest, revisions và first-publication records. Publisher allowlist giữ raw/provenance chi tiết/credentials private. Pointer atomic, lịch sử đã xuất immutable. Hai daily jobs hiện có cập nhật diagnostics sau batch cha thành công; thất bại giữ bản tốt, ghi status và job failure.

UI có tab Chẩn đoán, ba giá trị đúng đơn vị, ngày quan sát, biểu đồ chọn metric/range, CSV và giải thích. API key, raw storage và implementation details không xuất hiện trong luồng sản phẩm.

## Nghiên cứu và ảnh hưởng lịch sử

Mục đích là hiển thị các đại lượng raw có thể kiểm chứng, **không phát hành score dự báo**. Báo cáo coverage/giá trị âm/null/regime không được diễn giải là hiệu quả dự báo; AP/bootstrap/ablation của một composite mới nằm ngoài protocol này. Lựa chọn normalizer, chiều dự báo hoặc thêm trọng số về sau cần protocol/version và kiểm định mới.

Giữ `core-v0.1.0`, `network-proxies-v0.1.0`, `extended-v0.1.0`, trọng số và lịch sử điểm hiện tại. E4 tiếp tục R&D-only. C1/C2 không hoàn thành RHODL/Dormancy/NVT gốc bằng đổi tên.
