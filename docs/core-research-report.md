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

## Q02 — tương quan, ablation và regime

Phần này chạy lại trên đúng snapshot D03 và cùng cửa sổ primary, không thay công thức, trọng số, nhãn, holdout hoặc success rule. Các số đầy đủ được ghi trong `research.json`; các phân tích dưới đây là mô tả bổ sung, không thay primary.

### Tương quan thành phần

Tính Spearman trên score chuẩn hóa nhân quả của toàn bộ 2.978 ngày Core hợp lệ (pairwise complete, `n=2.978` cho mọi cặp). E5 và E7 có tương quan rất cao (`rho=0,963090`); các cặp còn lại cũng dương, từ 0,585969 đến 0,773270. Đây là bằng chứng các thành phần không độc lập về mặt thông tin. E2/NUPL không đưa vào ma trận vì là phép biến đổi đại số từ MVRV/E7 và vẫn là diagnostic.

| Cặp | Spearman rho | n |
|---|---:|---:|
| E1–E5 | 0,773270 | 2.978 |
| E1–E6 | 0,585969 | 2.978 |
| E1–E7 | 0,730516 | 2.978 |
| E5–E6 | 0,720498 | 2.978 |
| E5–E7 | 0,963090 | 2.978 |
| E6–E7 | 0,710872 | 2.978 |

### Ablation

Ablation giữ trọng số frozen của Core và chỉ chuẩn hóa lại tổng trọng số của tập còn lại để tạo một phép so sánh mô tả. `Δ AP` được ghi là `AP(Core) − AP(ablation)`; CI 95% dùng cùng 10.000 lần paired moving-block bootstrap 90 ngày như primary.

| Phân tích | AP | Δ AP | CI 95% của Δ |
|---|---:|---:|---|
| Core đầy đủ | 0,554249 | — | — |
| Bỏ E1 | 0,563010 | −0,008762 | [−0,025815; 0,001437] |
| Bỏ E5 | 0,558682 | −0,004433 | [−0,016079; 0,013840] |
| Bỏ E6 | 0,543124 | +0,011124 | [−0,008864; 0,042123] |
| Bỏ E7 | 0,545430 | +0,008819 | [−0,085004; 0,076300] |

Ở cửa sổ hồi cứu này, bỏ E1 hoặc E5 cho AP điểm cao hơn, còn bỏ E6 hoặc E7 cho AP điểm thấp hơn. Mọi CI đều đi qua 0 nên chưa có cơ sở bỏ hoặc tăng trọng số thành phần. Bỏ E7 trùng với nhóm giá; bỏ cả E1/E5/E6 trùng với E7 đơn lẻ, vì vậy không xem các phép này là bằng chứng mới hay phiếu độc lập.

### Regime theo mốc giao thức

Phân đoạn theo ngày quan sát UTC: trước London/EIP-1559 (trước 2021-08-05), London đến trước Merge (2021-08-05..2022-09-14), sau Merge đến trước Dencun (2022-09-15..2024-03-12), và sau Dencun (từ 2024-03-13). Nhãn vẫn là future drawdown của ngày quan sát; một nhãn có thể nhìn qua ranh giới regime.

| Regime | n | Nhãn dương | Prevalence | Core AP | Core ROC-AUC | E7 AP | Nhóm giá AP |
|---|---:|---:|---:|---:|---:|---:|---:|
| Trước London | 582 | 75 | 0,128866 | 0,233032 | 0,563261 | 0,156822 | 0,240660 |
| London → Merge | 406 | 288 | 0,709360 | 1,000000 | 1,000000 | 0,999205 | 0,999941 |
| Sau Merge, trước Dencun | 545 | 3 | 0,005505 | 0,609524 | 0,995695 | 0,587302 | 0,866667 |
| Sau Dencun | 568 | 282 | 0,496479 | 0,913665 | 0,940200 | 0,926749 | 0,869404 |

Chênh lệch prevalence và số event giữa các regime rất lớn; regime sau Merge trước Dencun chỉ có 3 nhãn dương, còn AP cao ở London → Merge phụ thuộc mạnh vào phân bố nhãn. Vì vậy bảng này chỉ là kiểm tra ổn định mô tả, chưa chứng minh mô hình bền vững qua nâng cấp giao thức hay có quan hệ nhân quả.

## Giới hạn và quyết định

Current-vintage reconstructed: unknown historical availability/revisions, chưa có data-vintage backtest hoặc vận hành shadow. Nhiều feature dùng cùng giá, MVRV/NUPL phụ thuộc đại số; không phải bốn nguồn độc lập. Nhãn drawdown không đồng nghĩa nhãn đỉnh. Q02 đã hoàn tất phần correlation/ablation/regime trên cùng protocol; các kết quả vẫn là exploratory và không thay thế đánh giá prospective.

[ADR-002](ADR-002-experimental-research-preview.md) cho phép preview nghiên cứu phi thương mại, công khai kết quả không đạt. Không đổi methodology `core-v0.1.0`, không tune weights. Công việc tiếp theo là vintage/incremental pipeline và thiết kế protocol mở rộng/holdout mới trước bất kỳ cải tiến phương pháp nào.
