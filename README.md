# ETH Cycle Index — kế hoạch dự án

Mục tiêu: xây dựng chỉ số chu kỳ ETH và website có trải nghiệm tương tự [CBBI](https://colintalkscrypto.com/cbbi/), với phương pháp, dữ liệu và lịch sử tính điểm có thể kiểm chứng.

**Trạng thái ngày 2026-10-03: đã triển khai trang giới thiệu ECO tại [eco.tnmp.cloud](https://eco.tnmp.cloud); engine và dashboard ETH chưa triển khai.** Workspace đã được khởi tạo Git và đã đẩy trang tĩnh lên `tnmjsc-hue/eco`. Không có chỉ số ETH đã tính hoặc backtest đã chạy. Trang công khai hiện chỉ mô tả dự án và nêu rõ chưa có điểm số.

## Đọc theo thứ tự

1. [Kế hoạch chi tiết](docs/MASTER_PLAN.md): phạm vi, 9 chỉ số đối chiếu, công thức bản đầu, dữ liệu, kiến trúc, giao diện, kiểm định và tiêu chí hoàn thành.
2. [Nghiên cứu và bằng chứng](docs/RESEARCH.md): nguồn chính thức, phiên bản CBBI đã đọc, kết quả thử API và giới hạn chưa xác minh.
3. [Danh sách công việc và bàn giao](docs/HANDOFF.md): thứ tự thực hiện, điều kiện nghiệm thu, trạng thái và prompt cho agent kế tiếp.
4. [Triển khai website](docs/DEPLOYMENT.md): cấu hình GitHub → Cloudflare Pages → `eco.tnmp.cloud`, kiểm tra và rollback.
5. [Quy tắc agent](AGENTS.md): cách tiếp tục và cập nhật tiến độ.

## Quyết định nền tảng

- Giữ trải nghiệm CBBI: điểm 0–100, biểu đồ ETH và điểm lịch sử, màu theo mức điểm, từng metric, bật/tắt metric và trang giải thích.
- Không đổi ticker BTC thành ETH rồi giữ nguyên mọi công thức. ETH cần phương pháp riêng, đặc biệt sau The Merge và với dữ liệu dựa trên tài khoản.
- Bản đầu đề xuất: `core-v0.1`, 4 thành phần có đường dữ liệu khả thi; 9 thành phần là mục tiêu nghiên cứu `extended-v0.x`, không giả lập cho đủ số lượng.
- Điểm thể hiện mức nóng/lạnh tương đối theo mô hình; **80/100 không có nghĩa là 80% xác suất tạo đỉnh**.
- Tách lịch sử tính lại theo dữ liệu hiện có và lịch sử điểm thực sự đã công bố; không dùng biểu đồ hồi cứu để tuyên bố khả năng dự báo.

Tên làm việc trong mã: `eth-cycle-index`. `ETH-CBBI` là tên thư mục hiện tại; trang giới thiệu dùng tên ECO, còn tên của chỉ số phát hành chính thức sẽ được chốt khi làm sản phẩm.
