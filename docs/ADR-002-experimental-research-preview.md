# ADR-002 — Phát hành dashboard Core nghiên cứu

- Ngày: 2026-10-03 (Asia/Saigon).
- Quyết định: Accepted cho **Experimental research preview**, không phải sản phẩm tín hiệu hoặc bản phát hành vận hành hằng ngày.
- Phương pháp: giữ nguyên `core-v0.1.0` / `core-v0.1.0-protocol-1`.

## Bằng chứng và phạm vi

Engine Python đã thực thi công thức khóa ở ADR-001. Snapshot D03 có SHA-256 `aa78757fcaee33ef23ecf3ebd92791a685df2617f2b3874f5f5183d16babdd03`; chỉ có giá/metric ngày UTC đã đóng đến 2026-10-01. Có 2.978 ngày Core hợp lệ từ 2018-08-07; điểm ngày cuối 41.379812239861. Không thay điểm thiếu bằng 0 hoặc 50.

Đánh giá chính 2020-01-01..2025-10-01 có 2.101 ngày, 648 nhãn dương, prevalence 0.30842456. AP Core 0.55424872; E7 độc lập 0.55377329; đồng trọng số 0.54797135; nhóm giá 0.54543010. CI bootstrap 95% của cả ba chênh lệch đều đi qua 0. **Chưa chứng minh incremental ranking utility theo protocol.** Không sửa weights/normalizer sau khi thấy kết quả. Báo cáo: [core-research-report.md](core-research-report.md).

Lịch sử chỉ là `reconstructed` trên current vintage; chưa biết historical availability/revisions. Gate vận hành shadow 30 ngày, scheduler, fault drills và `as_published` **chưa đạt**. Không đánh dấu O04/O05/O06 DONE và không gọi preview là sản phẩm đã kiểm chứng dự báo. Preview công bố phép tính và kết quả nghiên cứu, không thay cổng phát hành sản phẩm đầy đủ.

## Quyền dữ liệu cho preview

Người dùng xác nhận trực tiếp: **“Phi thương mại, công bố nghiên cứu”** trong phiên này. Tài liệu chính thức [Coin Metrics Community Data](https://docs.coinmetrics.io/packages/coin-metrics-community-data) liên kết trực tiếp tới [CC BY-NC 4.0](https://creativecommons.org/licenses/by-nc/4.0/). [Legal code](https://creativecommons.org/licenses/by-nc/4.0/legalcode.en), section 2(a)(1), cho phép chia sẻ và tạo/chia sẻ adapted material cho NonCommercial; section 3 quy định attribution, license link, ghi thay đổi và không suy diễn endorsement.

Áp dụng phạm vi giấy phép này cho Community inputs đã chọn, price chart, derived scores và CSV nghiên cứu phi thương mại. Ghi Coin Metrics Community Data, licence, việc chuyển đổi và disclaimer trong UI/manifest/CSV. Đây là quyết định dự án dựa trên giấy phép công khai, không phải giấy chấp thuận riêng của provider hay tư vấn pháp lý. Commercial/API trả phí/Glassnode/upstream licence khác không được cấp quyền bởi quyết định này. Nếu thêm quảng cáo, thu phí hoặc bán tín hiệu phải mở lại rights gate.

Điều chỉnh quyết định trước đây đòi thư riêng cho mọi hình thức công bố: giấy phép công khai trực tiếp + xác nhận mục đích đã đủ cho phạm vi phi thương mại nêu trên; không suy rộng thành quyền thương mại. Frozen protocol vẫn giữ ghi chú rights-unconfirmed tại thời điểm khóa, không sửa âm thầm config.

## Thời gian UTC

Manifest D03 ghi `as_of_utc=2026-10-03` nhưng tải lúc `2026-10-02T18:23:37.734Z`. Vì vậy 2026-10-02 **chưa đóng lúc tải**. Engine kiểm tra cutoff bằng ngày UTC thực của `retrieved_at`, không chỉ tham số as-of. Public release giữ 2026-10-02 là hàng null/pending để thể hiện request; không coi đây là gap của ngày đã đóng hoặc tạo score. Audit cũ vẫn giữ nguyên như bằng chứng request.

## Lưu trữ và giao diện

Giữ Pages static output `public` đang vận hành; native JavaScript ES modules + ECharts + Lucide, Python batch. React/TypeScript là stack đề xuất khi chưa có app; không đổi cấu hình hosting để thêm framework không cần thiết cho một dashboard tĩnh. Dependencies web có lockfile, vendor dist/license được build local và commit; Pages không cần npm trong build. Lựa chọn này giảm số thành phần vận hành, không đổi hợp đồng engine.

Raw và engine details giữ private/git-ignored. Public publisher chỉ chấp nhận `history.json`, `research.json`, manifest; kiểm SHA-256, allowlist, rights policy và không ghi đè release đã công bố. Pointer đổi sau khi đủ file; Git/Pages triển khai toàn bộ commit. CDN cache immutable cho versioned data, revalidate pointer. UI xác minh hashes và giữ bản tốt trước đó khi refresh lỗi.

## Lựa chọn khác

- Tối ưu lại để có report đẹp: không chọn; cần phương pháp/holdout mới.
- Trì hoãn toàn bộ UI tới sau 30 ngày shadow: không chọn cho **preview nghiên cứu** đã ghi rõ giới hạn; không bỏ gate vận hành của sản phẩm.
- Phát raw/cho frontend đọc R2 private: không chọn; không cần để dựng dashboard và tăng bề mặt dữ liệu.
- Giả đủ 9 metric: không chọn. E2 diagnostic phụ thuộc MVRV; E3/E4/E8/E9 vẫn có quyết định R&D riêng.

## Ảnh hưởng lịch sử

Chưa có score ETH nào công bố trước phiên này. Đây là release reconstructed đầu tiên, không phải chuyển lịch sử hồi cứu thành as-published. Sửa nguồn/code sau này phải tạo release/revision mới và ghi lý do; không ghi đè asset đã công bố.
