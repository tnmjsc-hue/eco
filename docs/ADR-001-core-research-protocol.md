# ADR-001 — Khóa protocol nghiên cứu Core ETH

- Trạng thái: Accepted cho nghiên cứu `core-v0.1.0`; chưa phải phương pháp phát hành.
- Ngày khóa: 2026-10-03.
- Bối cảnh: D03 đã tạo full-history snapshot hiện tại; chưa xem kết quả backtest hoặc chọn tham số dựa trên nhãn tương lai.
- Phạm vi: định nghĩa phép tính, protocol đánh giá và quyết định giữ/bỏ Core. Không cấp quyền phát hành data và không tuyên bố xác suất.

## Quyết định

Giữ Core gồm E1/E5/E6/E7, dùng ETH native mainnet và bộ Coin Metrics Community hiện có: `PriceUSD`, `CapMrktCurUSD`, `SplyCur`, `CapMVRVCur`, daily UTC. MVRV và NUPL dẫn xuất không phải hai nguồn xác nhận độc lập. Metric thiếu, ngày chưa đóng hoặc dữ liệu không hợp lệ cho điểm chính thức thì `core=null`; không chia lại trọng số.

Raw features và normalization giữ nguyên thông số trong [MASTER_PLAN.md, mục 4](MASTER_PLAN.md):

- E1 `ma_cycle`: `ln(SMA111(P)_t / (2*SMA350(P)_t))`.
- E5 `ma_2y`: `ln(P_t / SMA730(P)_t)`.
- E6 `log_trend`: OLS nhân quả trên `ln(P_u) ~ a_t + b_t*ln(age_u)` với `u<t`, tối thiểu 730 quan sát; ngày gốc cố định bởi snapshot/version.
- E7 `mvrv_z`: `R_t=M_t/V_t`, `sigma_t=std(M_u,u<t,ddof=0)` với tối thiểu 365 quan sát; `x_t=(M_t-R_t)/sigma_t`.
- Mọi SMA/cửa sổ dùng calendar UTC đã reindex, không dùng số dòng còn lại sau khi bỏ gaps. Giá trị t hiện tại chỉ dùng khi ngày đã đóng; nguồn không có `source_available_at` lịch sử nên không gọi reconstructed backtest là as-published.
- Với từng raw feature, normalizer dùng `[t-1460d,t-1d]`, quantile tuyến tính q05/q95, tối thiểu 365 raw observations; clip về `[0,100]`. Degenerate bounds hoặc thiếu warm-up trả null có reason.
- Tổng hợp: price group `mean(E1,E5,E6)`, valuation group `E7`; `core=0.50*price_group+0.50*valuation_group`. Tương đương trọng số E1/E5/E6 `1/6` mỗi metric và E7 `1/2`; đủ 4/4 mới có điểm.

### Protocol đánh giá đã đăng ký trước

- Ý nghĩa score: thước đo tương đối nóng/lạnh theo lịch sử causal gần; không phải xác suất, fair value hoặc nhãn “đỉnh chu kỳ”.
- Primary label: `y_t=1` khi giá thấp nhất trong 365 ngày kế tiếp, từ `t+1` đến hết `t+365` ngày, không cao hơn `0.50*P_t` (drawdown tối thiểu 50% tính từ giá đóng ngày t); ngược lại `0`. Đây là nhãn future drawdown, không đồng nghĩa nhãn đỉnh.
- Primary test window: `2020-01-01` đến ngày mới nhất có đủ 365 ngày label hoàn tất. Với snapshot D03 hiện tại, giới hạn dữ liệu là `2025-10-01`; tính lại end date từ manifest ở lần chạy thực. Ngày không đủ horizon bị right-censored và không đưa vào primary metric.
- Giai đoạn trước test dùng cho warm-up causal, không dùng để tìm threshold/weights. Không fit model, tune threshold hay chọn ngày đỉnh trên primary test.
- Primary metric: average precision (non-interpolated PR-AUC); luôn báo prevalence. Secondary: ROC-AUC, precision/recall ở ngưỡng score `>=90`, và 180 ngày / drawdown 30% sensitivity. Sensitivity chỉ mô tả, không thay primary sau khi thấy kết quả.
- Baselines khóa trước: (1) normalized E7 một mình; (2) mean equally-weighted của bốn normalized raw features; (3) normalized price-group trung bình E1/E5/E6. So sánh cùng ngày khả dụng và cùng test window.
- Uncertainty: paired moving-block bootstrap 90 ngày, 10.000 lần, seed `20261003`; giữ cùng block resample cho Core và baselines. Nếu số event/block không đủ để ước lượng ổn định, báo “không đủ bằng chứng”, không diễn giải CI rỗng/thất thường.
- Chỉ kết luận “có bằng chứng incremental ranking utility” nếu chênh lệch average precision của Core so với **từng** baseline có lower bound CI 95% lớn hơn 0 và hướng chênh lệch dương trong đa số calendar-year folds có positive labels. Nếu không đạt: “chưa chứng minh cải thiện”; không tối ưu lại trên cùng test. Mọi protocol/weights/label change tạo version và cần một khoảng holdout mới.
- Giới hạn bắt buộc trong report: backtest là reconstructed trên snapshot hiện tại; provider availability và vintage/revision lịch sử chưa biết, do đó không chứng minh kết quả có thể tái tạo realtime/as-published. Báo riêng số ngày/gap/null bị loại và warm-up.

## Lựa chọn thay thế và lý do

- Dùng “đỉnh chu kỳ” thủ công: không chọn vì nhãn chủ quan và dễ chọn ngày sau khi nhìn chart.
- Gọi 0–100 là xác suất: không chọn vì chưa có probabilistic model hoặc calibration.
- Dùng MVRV và NUPL như hai phiếu độc lập: không chọn vì NUPL suy ra đại số từ MVRV.
- Tối ưu trọng số/threshold trên toàn lịch sử: không chọn vì leakage và selection bias.

## Ảnh hưởng lịch sử

Chưa có score nào được công bố nên ADR không sửa lịch sử điểm. Mọi kết quả tương lai mang `reconstructed`, snapshot hash và protocol version riêng; `as_published` chỉ bắt đầu khi có pipeline vintage thực, quyền phát hành và release gate.

## Điều kiện triển khai

ADR khóa ý định nghiên cứu, không thay test. D04 có thể hoàn thành; S03 phải implement schema/quality rules, M01-M06 phải có fixtures và prefix-invariance, Q01 phải thực thi protocol; không ghi protocol này là đã được code xác minh.
