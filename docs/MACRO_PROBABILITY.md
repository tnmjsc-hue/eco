# Mô hình xác suất ETH theo kịch bản vĩ mô

`macro-probability-v1.0.0` là mô hình nghiên cứu riêng của ECO. Không gọi là đồng thuận thị trường: chưa có tập dự báo độc lập trước tin. Không đổi `macro-cross-v1.0.1`, điểm ETH hoặc nhãn có điều kiện. Protocol được chốt trước code, tham số dưới đây là quyết định nghiên cứu ECO, không phải ngưỡng được tài liệu tham khảo chứng minh.

## Mục tiêu và dữ liệu

- Điều kiện là **regime R01–R09 đã được engine xác lập**, không lấy nhãn “bất lợi” làm xác suất giảm. Không hỗ trợ USD/vàng khi chưa có tập dữ liệu prospective tương ứng.
- Dự báo ba lớp cho ETH/USD giữa hai observation UTC cách nhau đúng 7 ngày: giảm nếu return < −1%, đi ngang nếu −1% ≤ return ≤ 1%, tăng nếu > 1%. Return = `(P_end/P_base−1)*100`, Decimal trước phân lớp. Đây là biến động giữa observation ngày, không phải cửa sổ quanh tin, giá khớp lệnh hay bằng chứng nhân quả.
- `issued_at` thật của lần chạy đầu đủ điều kiện; `base_date = date_utc(issued_at)+1`, `end_date = base_date+7`. Chọn ngày tương lai để không lấy giá trước khi ghi nhận bối cảnh làm điểm xuất phát. Các case sau có base ≥ end case trước; không đếm những cửa sổ 7 ngày chồng nhau như mẫu độc lập. Không backfill case ở ngày lịch sử.
- Bối cảnh phải hash-verified với **calendar parent và toàn bộ input**, có source proof/status mới nhất ≤ cutoff và không quá 48 giờ; assessment không quá 48 giờ. Missing/stale/conflict regime không nhận case. Một lần kiểm lại không sửa case đầu tiên.
- Giá chỉ lấy từ parent Core 10 `core-v0.2.0`, ETH/Coin Metrics Community CC BY-NC 4.0 đã xác minh đầy đủ manifest/history. Missing, zero/negative, endpoint chưa đóng hoặc future parent không thành nhãn. Không forward-fill. Nhãn đầu tiên chỉ tạo sau end date từ hai ngày chính xác trong parent đã biết; `resolved_at` là lần engine thực ghi nhãn, không giả là giờ công bố nguồn. Nhãn/số/hash parent bất biến; sửa nguồn sau đó cần revision/version riêng. Sau 30 ngày quá end mà thiếu nhãn, giữ case chưa giải quyết và không lùi endpoint.
- Lịch sử giá reconstructed không biến thành lịch sử kịch bản point-in-time. Audit ban đầu: 5 assessment/2 ngày/1 regime, **0 nhãn prospective đã đủ hạn**. Không huấn luyện bằng những assessment cũ hoặc fixture tổng hợp.

## Ước lượng và kiểm định tách biệt

Estimator, power/log scoring và bootstrap dùng Decimal precision 28 / ROUND_HALF_EVEN cố định trong context riêng; số đầu ra được lưu dạng chuỗi, làm tròn 15 chữ số thập phân. Không phụ thuộc context của caller, rounding của JavaScript hoặc hàm log/power floating point của hệ điều hành; frontend chỉ xác minh và hiển thị output đã pin.

Với 90 nhãn đầu, baseline `b_k=(N_k+1)/(N+3)`. Trong regime r, `q_rk=(n_rk+12*b_k)/(n_r+12)`. Đây là shrinkage multinomial: ít mẫu co về tần suất chung, không ép xác suất theo cơ chế kể chuyện. Không hiển thị prior 1/3 như một dự báo khi chưa có mẫu.

45 case hiệu chỉnh kế tiếp phải được phát hành **sau khi toàn bộ nhãn train đã được ghi nhận**. Chọn temperature trong [0,5; 0,75; 1; 1,5; 2] theo log loss trên calibration; `p_k=q_k^(1/T)/sum(q_j^(1/T))`. Tie ưu tiên gần 1 rồi T nhỏ. 45 case test kế tiếp phải phát hành sau khi nhãn calibration đã được ghi nhận. Embargo theo `resolved_at`, không random split. Train/calibration/test đầu tiên được giữ cố định, không retrain từ holdout hoặc lựa chọn lại test khi kết quả xấu. Case thiếu nhãn trong một phase chưa cho phép tiến phase đó.

Cổng toàn bộ: đủ 90/45/45; multiclass Brier cải thiện ít nhất 0,01 so với baseline chung; log loss không tệ hơn baseline; ECE từng lớp với 5 bins cố định ≤0,15; CI95 delta Brier bằng moving-block bootstrap 4 case/2.000 lần/seed 20261009 có cận trên <0. Cổng riêng regime hiện tại: ≥30 train, ≥15 calibration và ≥15 test; Brier/log loss/ECE của nhóm cũng phải đạt. Báo số mẫu, baseline, loss, bins và CI; điểm Brier thấp chưa tự chứng minh calibration.

Các ngưỡng là cổng nghiên cứu hữu hạn, không bảo đảm xác suất đúng trong tương lai. 180 cửa sổ không chồng nhau cần tối thiểu khoảng 3,5 năm, còn embargo/thiếu nguồn/regime hiếm có thể kéo dài. Đây là giới hạn thực của phương án prospective với horizon 7 ngày. Muốn kết quả sớm hơn cần lịch sử point-in-time hợp lệ hoặc protocol mới có mục tiêu khác, không hạ cổng trong cùng version.

Trước khi đủ cổng, `probabilities=null`, trạng thái `collecting`, `awaiting_calibration`, `awaiting_test` hoặc `validation_failed`; vẫn công bố protocol, case có điều kiện, số mẫu và kết quả âm nếu có. Khi đạt mới ghi xác suất vào **case mới sau khi test đã biết**; không viết lại những case cũ. Live card luôn nêu mô hình ECO/ngày/horizon và giới hạn kiểm định, không gọi là consensus hoặc khuyến nghị giao dịch.

## Công bố và vận hành

`python -m eco.macro_probability` đọc các artifact public đã được backup/xác minh ở pipeline cha, không tải feed mới hoặc mở token. Case, outcome, protocol và report đều hash/immutable; latest đổi cuối cùng, lock cùng cơ chế macro. Status kiểm tra riêng; lỗi giữ pointer tốt và ghi `error`. Report pin toàn bộ refs/parent/input; replay write bị ngắt giữ timestamp ban đầu. Workflow calendar chạy sau macro, stage đúng allowlist khi test đạt; browser xác minh hashes/semantics/parent và giữ bản gốc khi lỗi, hạ trạng thái đủ mới. Dữ liệu raw không vào public.

Chạy spec oracle trước sửa; `test_macro*.py`, Node macro/calendar/probability contracts và `scripts/check-calendar.mjs`. Tests tổng hợp chỉ xác minh engine, không dùng làm bằng chứng khả năng dự báo. Cần nghiệm thu hosted batch/deploy/checksum/browser riêng và ghi kết quả trong HANDOFF.

Tham khảo phương pháp: [Gneiting & Raftery — Proper scoring rules](https://sites.stat.washington.edu/people/raftery/Research/PDF/Gneiting2007jasa.pdf) cho Brier/log scoring; [Arrieta-Ibarra và cộng sự — Metrics of Calibration](https://www.jmlr.org/beta/papers/v23/22-0658.html) cho việc kiểm calibration tách khỏi accuracy và giới hạn binning. Các nguồn không xác nhận mô hình ECO đã được hiệu chỉnh hoặc ngưỡng ở trên.
