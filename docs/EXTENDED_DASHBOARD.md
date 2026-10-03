# ECO 7 — dashboard Experimental

Ngày triển khai: 2026-10-03. Quyết định mới theo người dùng: [ADR-006](ADR-006-extended-experimental-dashboard.md). Protocol `extended-v0.1.0-protocol-1`, hash `719b9873e7e96546f829df915051d993dafbb960e53878495c1bce249c948bcb`, được khóa trước lần kiểm định tổng hợp đầu tiên.

## Thành phần và dữ liệu

E1/E5/E6 mỗi thành phần 12,5%, E7 37,5%; `exchange_share` (E3 proxy), `address_activity` (E8 proxy), `value_per_transfer` (E9 proxy) mỗi thành phần 8⅓%. Tổng = 75% Core + 25% mean(proxy). Chuẩn hóa/công thức mỗi chuỗi giữ version cha; không chọn lại trọng số sau kết quả. Bảy metric có tương quan; E2 không thêm phiếu, E4 vẫn research candidate.

Input là release Core `core-f677f7dd1f1749cc6dce` và proxy `proxy-f9edb79c4231efbbb9fe` đã có snapshot raw/R2 readback ở nhánh cha. Pipeline ECO 7 pin manifest/hash history của hai cha; chỉ công bố chuỗi dẫn xuất theo Community CC BY-NC 4.0. Không tải thêm raw hoặc bind R2 vào frontend.

Lịch tổng hợp 4.081 ngày UTC 2015-08-01–2026-10-02; 2.979 ngày đủ điểm, đầu tiên 2018-08-07. Proxy cha có 4.083 ngày từ 2015-07-30 nhưng Core bắt đầu 2015-08-01 nên phạm vi tổng hợp theo Core. Thiếu bất kỳ thành phần nào thì null, kể cả khi proxy cập nhật chậm hơn Core; không forward-fill. `exchange_share` giữ cờ flash. Last valid ngày 2026-10-02: ECO 7 `31.979753577249287`, Core `40.009962172523664`.

## Kiểm định cùng ngày

2.102 ngày 2020-01-01–2025-10-02, 649 nhãn giảm tối thiểu 50% trong 365 ngày tiếp theo. Lịch sử reconstructed, availability quá khứ unknown, holdout đã dùng lại nên chỉ kết quả thăm dò. Paired moving-block bootstrap 90 ngày, 10.000 lần, seed 20261003; weighted AP giữ ties và đối chiếu độc lập với `eco.research.ap`.

| Mô hình | AP | Δ AP ECO 7 − baseline | CI 95% |
|---|---:|---:|---|
| ECO 7 | 0,533890 | — | — |
| Core | 0,554702 | −0,020812 | [−0,060266; 0,008061] |
| E7 riêng | 0,554274 | −0,020384 | [−0,093304; 0,029546] |
| Nhóm giá riêng | 0,545849 | −0,011959 | [−0,114131; 0,057021] |

Không chứng minh nâng chất lượng dự báo: point estimate AP thấp hơn ba baseline và CI đều chứa 0. UI/JSON hiển thị kết quả bất lợi, không sửa trọng số để ép đạt. Report còn có Spearman matrix bảy thành phần, ablation bỏ từng thành phần rồi chuẩn hóa lại weights đã khóa, London/Merge/Dencun regime, ROC-AUC và ngưỡng 90. ECO 7 chưa có dự báo ≥90 trong tập này; không dùng ngưỡng đó để quảng cáo precision.

## Cập nhật và kiểm tra

`python -m eco.seven` xác minh hai pointer/manifest/files, phương pháp/quyền, calendar, score/reason/flags; join đúng ngày, tính report và immutable derived release, cuối cùng thay pointer atomic. Artifact nằm trong `/data/extended/`, tính private mirror tại `data/computed/extended/` (Git ignore). `eco/extended.py` ứng viên E4 giữ nguyên; không dùng lại module đó cho ECO 7.

Hai workflow Core/proxy gọi `eco.seven` sau batch cha thành công, cùng concurrency `daily-eth-publication`; vẫn chạy theo 10:17/14:17 và 10:47/14:47 giờ Việt Nam. Chỉ stage allowlist public; kiểm tất cả checksum Core/proxy/Extended sau Pages deploy. Khi parent/source/regression lỗi, giữ pointer cũ, status failed; khi có ngày mới nhưng thiếu proxy thì last valid giữ ngày gốc và status source_pending. Raw/credentials không đi vào public hay Git.

Kiểm local: `python -m unittest discover -s tests -v`, `node --test tests/*.test.mjs`, `node scripts/validate-research-artifacts.mjs`, `git diff --check`. Browser QA: `scripts/check-dashboard.mjs` kiểm mặc định 7/7, Core nguyên vẹn, CSV 366 ngày với bảy metric/reasons/flags, custom E7/empty, keyboard, network-failure/retry, auto-refresh và giữ ngày lịch sử; `scripts/check-proxies.mjs` giữ coverage/formulas/flash/CSV độc lập. Production/CI/hosted evidence ghi tại HANDOFF sau khi xác minh thực tế.

Arkham đang ở source candidate với [evidence](ARKHAM_SOURCE.md) và [hồ sơ trial](ARKHAM_TRIAL_REQUEST.md). Không thay dữ liệu Coin Metrics hay số ECO 7 từ Arkham khi coverage/licence chưa đạt.
