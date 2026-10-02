# Kết quả nghiên cứu Core v0.1.0

Ngày chạy: 2026-10-03 giờ Việt Nam. Engine: `eco/core.py`, harness: `eco/research.py`. Dữ liệu ETH Coin Metrics Community snapshot D03, canonical SHA-256 `aa78757fcaee33ef23ecf3ebd92791a685df2617f2b3874f5f5183d16babdd03`. Công thức và protocol không thay đổi sau kết quả.

## Kết quả chính

- Lịch sử nguồn: 4.080 ngày 2015-08-01..2026-10-01, 7 ngày đầu giá/vốn hóa/MVRV null. 2026-10-02 chưa đóng tại UTC retrieval; giữ pending null, không tính score.
- Core: 2.978 ngày hợp lệ từ 2018-08-07; đầu kỳ thiếu do SMA/OLS/normalizer warm-up. Giá trị gần nhất 41.379812239861 ngày 2026-10-01; UI làm tròn half-up 41, CSV 41.3798. Không có điểm cho ngày pending.
- Primary evaluation: 2.101/2.101 ngày trong 2020-01-01..2025-10-01, không loại ngày nào trong cửa sổ này. 648 positive labels, prevalence 0.3084245597. Các ngày sau test end bị right-censored cho horizon chính; không đưa vào đánh giá.
- Paired calendar moving-block bootstrap: 90 ngày, 10.000/10.000 replicates hợp lệ, seed 20261003. Ngày t của label chỉ nhìn t+1..t+365; label tương lai không tham gia engine tính score.

| Model | AP | ROC-AUC | Precision ≥90 | Recall ≥90 |
|---|---:|---:|---:|---:|
| Core | 0.554249 | 0.828303 | 0.195122 | 0.012346 |
| E7 độc lập | 0.553773 | 0.838236 | 0.238095 | 0.023148 |
| Bốn metric đồng trọng số | 0.547971 | 0.815298 | 0.347826 | 0.012346 |
| Nhóm giá độc lập | 0.545430 | 0.798289 | 0.444444 | 0.012346 |

| Core trừ baseline | Δ AP | CI 95% | Năm Δ dương / năm có nhãn dương | Success rule |
|---|---:|---|---:|---|
| E7 độc lập | +0.000475 | [-0.044709; 0.037276] | 3/5 | Không đạt |
| Đồng trọng số | +0.006277 | [-0.025221; 0.035943] | 2/5 | Không đạt |
| Nhóm giá | +0.008819 | [-0.085004; 0.076300] | 3/5 | Không đạt |

**Kết luận: chưa chứng minh incremental ranking utility của Core so với từng baseline.** AP dương so với baseline ở point estimate không đủ để vượt gate. Threshold 90 có 41 ngày được dự đoán dương, chỉ 8 đúng nhãn; không quảng cáo threshold này thành tín hiệu tạo đỉnh.

## Sensitivity, không thay primary

Trên cùng cửa sổ ngày: horizon 180d, drawdown 50% có prevalence 0.175155, AP 0.289330, ROC-AUC 0.730858. Horizon 365d, drawdown 30% có prevalence 0.485483, AP 0.640111, ROC-AUC 0.709387. Không dùng sensitivity để đổi nhãn hoặc ép kết luận đạt.

Calendar-year folds có nhãn dương: 2020, 2021, 2022, 2024, 2025; 2023 không có nhãn dương, không đưa vào majority rule. Chi tiết số không làm tròn có trong `research.json` cùng release.

## Giới hạn và quyết định

Current-vintage reconstructed: unknown historical availability/revisions, chưa có data-vintage backtest hoặc vận hành shadow. Nhiều feature dùng cùng giá, MVRV/NUPL phụ thuộc đại số; không phải bốn nguồn độc lập. Nhãn drawdown không đồng nghĩa nhãn đỉnh. Chưa làm correlation/ablation/regime report mở rộng (Q02 còn IN_PROGRESS), không tuyên bố đã xong toàn bộ nghiên cứu.

[ADR-002](ADR-002-experimental-research-preview.md) cho phép preview nghiên cứu phi thương mại, công khai kết quả không đạt. Không đổi methodology `core-v0.1.0`, không tune weights. Công việc tiếp theo là vintage/incremental pipeline và thiết kế protocol mở rộng/holdout mới trước bất kỳ cải tiến phương pháp nào.
