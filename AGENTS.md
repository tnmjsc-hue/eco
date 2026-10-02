# Hướng dẫn agent tiếp tục dự án

<!-- CODEGRAPH_START -->
## CodeGraph
If `.codegraph/` exists, use it before grep/find:
- Use MCP tool `codegraph_explore` or shell `codegraph explore "<query>"` to locate symbols and call paths.
- Skip if `.codegraph/` is missing.
<!-- CODEGRAPH_END -->

## Bắt đầu mỗi phiên

1. Đọc `README.md`, `docs/HANDOFF.md`, `docs/DEPLOYMENT.md`, rồi phần liên quan trong `docs/MASTER_PLAN.md` và `docs/RESEARCH.md`.
2. Kiểm tra trạng thái filesystem/Git thực tế; không giả định các thư mục hoặc lệnh dự kiến đã tồn tại.
3. Chọn task `TODO` đầu tiên đã đủ dependency; đánh dấu `IN_PROGRESS` trong bàn giao.
4. Hoàn thành một phần có thể kiểm chứng, ghi bằng chứng và bước tiếp theo. Không đánh dấu `DONE` nếu mới viết thiết kế.

## Ràng buộc thực hiện

- Trang giới thiệu ECO đã được triển khai công khai; engine và dashboard ETH vẫn chưa có. Người dùng đã yêu cầu agent sau khi code xong tự triển khai website lên `eco.tnmp.cloud` theo `docs/DEPLOYMENT.md`. Quyền này áp dụng cho lần deploy code website thông thường sau kiểm tra, không phải quyền mua API hoặc bỏ qua các cổng dữ liệu/phương pháp trước khi công bố điểm ETH.
- Khi người dùng yêu cầu triển khai tiếp, thực hiện các task sẵn sàng; không hỏi lại về lựa chọn kỹ thuật thường lệ đã có mặc định trong kế hoạch.
- Viết giải thích và tài liệu sản phẩm bằng tiếng Việt; tên biến, metric ID và schema bằng tiếng Anh.
- Không thay ETH bằng dữ liệu BTC, không suy diễn metric chưa có thành số 0 hoặc số 50.
- Không gắn nhãn xác suất cho điểm 0–100 nếu chưa có mô hình xác suất và kiểm định calibration riêng.
- Mọi feature/normalizer tại ngày t chỉ được dùng dữ liệu có thể biết tại thời điểm tính. Ngày quan sát, ngày dữ liệu sẵn có và ngày tải dữ liệu là ba khái niệm riêng.
- MVRV và NUPL dẫn xuất có phụ thuộc đại số; không quảng cáo là hai nguồn xác nhận độc lập.
- Không tự đổi provider, đơn vị, trọng số, ngày gốc, thành phần hoặc chuẩn hóa dưới cùng `methodology_version`.
- Giữ snapshot đầu vào, hash và manifest; dữ liệu có bản quyền không được mặc định commit hoặc công khai.
- Giữ điểm đã công bố bất biến. Bản sửa đổi thêm revision riêng và ghi lý do.
- Không commit secret; không đưa API key vào frontend hoặc log URL. Dùng biến môi trường và `.env.example` chỉ có tên biến.
- Không tự động gửi email, Telegram hoặc tin nhắn ngoài dự án từ cấu hình upstream.
- Không tự ý rút từ 9 metric xuống 4 rồi gọi là bản tương đương hoàn chỉnh: `core` là giai đoạn trung gian, phần còn lại phải có quyết định nghiên cứu rõ ràng.

## Quy trình bàn giao

Cập nhật `docs/HANDOFF.md` sau mỗi phiên: task, file đã sửa, lệnh kiểm tra và kết quả thực tế, dữ liệu/version sử dụng, trở ngại và task kế tiếp. Quyết định mới cần ghi lý do, lựa chọn thay thế và ảnh hưởng đến lịch sử điểm. Nếu chưa có test hoặc chưa thể chạy, ghi rõ; không điền kết quả giả định.

Khi sửa website, dùng GitHub `main` → Cloudflare Pages `eco-tnmp` theo `docs/DEPLOYMENT.md`, xác minh build và `https://eco.tnmp.cloud/` trước khi báo hoàn thành. Push `main` là hành động phát hành; không push khi chưa kiểm tra diff, secret và các cổng phát hành dữ liệu áp dụng.

## Công cụ và cấu trúc

Stack đề xuất là Python cho pipeline và TypeScript/React cho web. Đây là lựa chọn thiết kế, chưa cài đặt. Nếu môi trường hiện tại có quy trình Sites được người dùng áp dụng khi triển khai website, sử dụng quy trình đó cho lớp web/hosting và giữ nguyên hợp đồng dữ liệu của engine.

Chỉ dùng subagent khi người dùng hoặc chỉ dẫn áp dụng yêu cầu; bộ tài liệu này không tự cấp quyền tạo agent song song.
