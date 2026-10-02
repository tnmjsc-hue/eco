# ETH Cycle Index — kế hoạch dự án

Mục tiêu: xây dựng chỉ số chu kỳ ETH và website có trải nghiệm tương tự [CBBI](https://colintalkscrypto.com/cbbi/), với phương pháp, dữ liệu và lịch sử tính điểm có thể kiểm chứng.

**Trạng thái ngày 2026-10-03: trang giới thiệu ECO đang chạy tại [eco.tnmp.cloud](https://eco.tnmp.cloud); D01-D05 đã hoàn tất trong phạm vi probe, contract, full-history audit, protocol nghiên cứu và feasibility 9 vị trí.** Chưa có engine, dashboard ETH, điểm hoặc backtest. Snapshot full-history được giữ local và đã sao lưu vào R2 private; website không đọc raw. Quyền công khai dữ liệu và điểm dẫn xuất vẫn chưa được xác nhận.

Chạy probe mẫu bằng `node scripts/audit-coinmetrics.mjs 2026-10-03` hoặc full history bằng `node scripts/backfill-coinmetrics.mjs 2015-08-01 2026-10-03`. Raw response và manifest SHA-256 được ghi vào `data/raw/coinmetrics/` (bị Git ignore); không commit dữ liệu này. Báo cáo tại [data-audit.md](docs/data-audit.md), protocol nghiên cứu tại [ADR-001](docs/ADR-001-core-research-protocol.md), feasibility 9 vị trí tại [metric-feasibility.md](docs/metric-feasibility.md), và giới hạn quyền tại [data-rights.md](docs/data-rights.md). Upload snapshot private lên R2 dùng `node scripts/upload-private-snapshot-r2.mjs <snapshot-dir>` sau khi có `R2_ACCOUNT_ID` cùng credential trong process env.

Kiểm tra bất biến protocol D04 và register feasibility D05 bằng `node scripts/validate-research-artifacts.mjs`. Lệnh này chỉ xác minh hợp đồng research/config, không chạy engine, backtest, live source probe hoặc xác nhận quyền phát hành.

Chạy live probe D05 không cần API key bằng `node scripts/audit-d05-feasibility.mjs 2026-10-03`. Raw response/manifest được giữ trong `data/raw/d05/` (bị Git ignore); chỉ summary/hash evidence không chứa raw được commit.

## Đọc theo thứ tự

1. [Kế hoạch chi tiết](docs/MASTER_PLAN.md): phạm vi, 9 chỉ số đối chiếu, công thức bản đầu, dữ liệu, kiến trúc, giao diện, kiểm định và tiêu chí hoàn thành.
2. [Nghiên cứu và bằng chứng](docs/RESEARCH.md): nguồn chính thức, phiên bản CBBI đã đọc, kết quả thử API và giới hạn chưa xác minh.
3. [Danh sách công việc và bàn giao](docs/HANDOFF.md): thứ tự thực hiện, điều kiện nghiệm thu, trạng thái và prompt cho agent kế tiếp.
4. [Triển khai website](docs/DEPLOYMENT.md): cấu hình GitHub → Cloudflare Pages → `eco.tnmp.cloud`, kiểm tra và rollback.
5. [Lưu trữ dữ liệu](docs/STORAGE.md): Pages cho JSON công khai, R2 riêng tư cho snapshot và giới hạn kết nối hiện tại.
6. [Quy tắc agent](AGENTS.md): cách tiếp tục và cập nhật tiến độ.

## Quyết định nền tảng

- Giữ trải nghiệm CBBI: điểm 0–100, biểu đồ ETH và điểm lịch sử, màu theo mức điểm, từng metric, bật/tắt metric và trang giải thích.
- Không đổi ticker BTC thành ETH rồi giữ nguyên mọi công thức. ETH cần phương pháp riêng, đặc biệt sau The Merge và với dữ liệu dựa trên tài khoản.
- Bản đầu đề xuất: `core-v0.1`, 4 thành phần có đường dữ liệu khả thi; 9 thành phần là mục tiêu nghiên cứu `extended-v0.x`, không giả lập cho đủ số lượng.
- Điểm thể hiện mức nóng/lạnh tương đối theo mô hình; **80/100 không có nghĩa là 80% xác suất tạo đỉnh**.
- Tách lịch sử tính lại theo dữ liệu hiện có và lịch sử điểm thực sự đã công bố; không dùng biểu đồ hồi cứu để tuyên bố khả năng dự báo.

Tên làm việc trong mã: `eth-cycle-index`. `ETH-CBBI` là tên thư mục hiện tại; trang giới thiệu dùng tên ECO, còn tên của chỉ số phát hành chính thức sẽ được chốt khi làm sản phẩm.
