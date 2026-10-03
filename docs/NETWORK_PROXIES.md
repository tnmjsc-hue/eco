# Ba metric ETH thay thế đã thực thi

Ngày 2026-10-03. Phương pháp `network-proxies-v0.1.0`, quyết định [ADR-005](ADR-005-network-research-proxies.md). Đây là ba metric mới bổ sung cho dashboard nghiên cứu, giữ vai trò E3/E8/E9 nhưng không tái tạo RHODL, Dormancy/Reserve Risk hoặc NVT theo giá trị chuyển.

| Metric | Giá trị gần nhất, 2026-10-02 UTC | Điểm /100 | Ngày có điểm đầu tiên | Số ngày có điểm |
|---|---:|---:|---|---:|
| `exchange_share` · E3 proxy | SMA30 tỷ trọng ETH trên sàn 12,6272% | 0,0000 | 2016-08-27 | 3.689 |
| `address_activity` · E8 proxy | SMA30 active / funded addresses 0,3988% | 4,1961 | 2016-08-27 | 3.689 |
| `value_per_transfer` · E9 proxy | 142.469,50 USD / (lượt chuyển/ngày) | 19,4713 | 2016-10-26 | 3.629 |

Điểm E3 bằng 0 là kết quả clipping từ dữ liệu hợp lệ, không thay cho thiếu dữ liệu. Cả ba dùng SMA theo ngày lịch và q05/q95 tuyến tính trên tối đa 1.460 ngày trước t, min365. Ngày warm-up/null hiển thị dấu “—” và có lý do trong CSV/JSON. Score cao nghĩa đại lượng của chính metric cao hơn lịch sử gần, không mặc nhiên là cùng mức rủi ro chu kỳ.

## Nguồn, coverage và quyền

Probe [source evidence](evidence/network-proxies-source-2026-10-03.json) ghi 11 HTTP 200, gồm available ETH catalog, dictionary, ba sample 2015/2021/2026, định nghĩa và giấy phép chính thức. Evidence SHA-256 `5d35aa2fa85e6a8ef7d6e538d8f7fc8ac456f366b3efedac54cd01b07200e72d`; sample không được gắn nhãn full-history. Full-history được kiểm riêng từ snapshot dưới đây.

Snapshot private: `data/raw/coinmetrics/coinmetrics-network-proxies-2026-10-03-2026-10-03T084645399Z`, tải lúc `2026-10-03T08:46:45.399Z`. Sáu trường ETH Community `AdrActCnt`, `AdrBalCnt`, `CapMrktCurUSD`, `SplyCur`, `SplyExNtv`, `TxTfrCnt`; 5 pages, 4.083 ngày unique 2015-07-30..2026-10-02, không gap/duplicate/invalid/negative. Vốn hóa có 9 null đầu, bắt đầu 2015-08-08; các trường còn lại không null. Snapshot SHA-256 `405c4eaf20e23123643ed08acf00d4ce6df2f0ce41f82c975ebf7d4730628637`.

8/8 objects (canonical, 5 raw pages, available catalog, manifest) đã PUT/GET vào R2 riêng tư `eco-eth-private`; tất cả readback hashes khớp. Receipt private `data/computed/network-proxies-backup-2026-10-03.json`. Pipeline kiểm raw ↔ canonical từng ngày/trường, timestamp UTC đã đóng, cờ nguồn, exact Community query/schema, catalog hash/entitlement và toàn bộ receipt trước compute. Raw và credential không phát hành.

Community Data theo CC BY-NC 4.0; chỉ publish derived research, attribution/license/changes/no-warranty trong UI/CSV/manifest. Scope phi thương mại theo ADR-002/005. Không cần account/API key/chi phí mua nguồn. E3 giữ cờ `flash` trên 4.083 ngày: dữ liệu tạm thời, địa chỉ sàn được nhận diện hiện tại có thể thay đổi lịch sử. Active addresses không đo tuổi coin hay người dùng; transfer count không phải transfer value. Availability lịch sử chưa biết nên chỉ gọi reconstructed.

Nguồn trực tiếp: [Community licence](https://gitbook-docs.coinmetrics.io/packages/coin-metrics-community-data), [metric dictionary, gồm AdrBalCnt](https://community-api.coinmetrics.io/v4/catalog/metrics), [exchange supply](https://gitbook-docs.coinmetrics.io/network-data/network-data-overview/exchange/exchange-supply), [active addresses](https://gitbook-docs.coinmetrics.io/network-data/network-data-overview/addresses/active-addresses), [native transfers](https://gitbook-docs.coinmetrics.io/network-data/network-data-overview/transactions/transfers). Nguồn Pro/Glassnode và archive ETH đã kiểm trong [E9 runbook](E9_RUNBOOK.md)/[source resolution](REMAINING_SOURCE_RESOLUTION.md) chưa cung cấp adjusted value hoặc holder ages; không suy những trường này từ aggregate.

## Kết quả thực nghiệm

Cùng 2.102 ngày 2020-01-01..2025-10-02, 649 nhãn dương future drawdown ≥50% trong 365 ngày kế tiếp; chỉ horizon hoàn tất. Baseline cuối phiên dùng release Core `core-f677f7dd1f1749cc6dce`, sau khi tích hợp daily commit mới; các ngày đánh giá/giá trị AP không đổi. AP Core 0,554702; E7 0,554274; nhóm giá 0,545849.

| Proxy | AP riêng | AP khi ghép thử 75% Core + 25% proxy | Δ AP so Core | CI bootstrap 95% của Δ |
|---|---:|---:|---:|---|
| Exchange share | 0,290541 | 0,463241 | -0,091461 | [-0,200987; -0,011555] |
| Address activity | 0,385421 | 0,538514 | -0,016188 | [-0,039436; -0,001061] |
| Value per transfer | 0,589979 | 0,568220 | +0,013518 | [-0,002407; +0,049581] |

10.000 paired moving-block bootstrap, block90 ngày lịch, seed20261003. Report còn có ROC-AUC/ngưỡng90, tương quan proxy/Core/E7/giá, baseline E7/giá và các giai đoạn London/Merge/Dencun. Ablation bỏ proxy trả lại Core. Không chọn hướng/weights/cửa sổ sau kết quả; không ghép cả ba thành điểm chính thức.

Holdout Core đã được xem; đây là exploratory, không là bằng chứng ngoài mẫu mới. E9 count proxy có AP riêng cao hơn Core nhưng CI của cải thiện khi ghép đi qua 0. E3/E8 không cải thiện Core theo hướng đã khóa. Quyết định: **công bố ba metric và kết quả nghiên cứu, không promote vào Core**. Chứng minh utility cần holdout mới hoặc chuỗi prospective có vintage; không đổi lịch sử để làm đẹp kết quả.

## Chạy lại và cập nhật

```text
node scripts/proxy-coinmetrics.mjs backfill 2026-10-03
node scripts/upload-private-snapshot-r2.mjs <snapshot-private>
python -m eco.proxy_pipeline build <snapshot-private> <receipt-private.json> <core-release>
python -m eco.proxy_pipeline publish <computed-proxy-release>
python -m eco.proxy_pipeline daily
node scripts/check-proxies.mjs http://127.0.0.1:8876/
```

Chỉ dùng paths thực tế. Uploader cần existing bucket-scoped credentials trong environment; lưu JSON stdout vào receipt ngoài snapshot. `daily` làm fetch/catalog → backup/readback → compute/evaluate → publish. Production luôn 10.000 replicates; fixture ít replicates bị chặn public. Không sửa source evidence đã khóa; audit mới cần file mới.

`public/data/network-proxies/latest.json` chỉ trỏ release đầy đủ có checksum; manifest/derived history/research riêng. Lịch sử đã xuất giữ bất biến, revision ghi ngày sửa/ngày thêm/lý do. Rounding tương đương giữ số đã công bố; snapshot mới có cùng values/baseline/code không tạo release trùng. Mất dữ liệu khả dụng hoặc source/R2 failure giữ pointer trước và status thất bại. Core assets/pointer không đổi.

Workflow `network-proxies-update.yml` kiểm lúc 10:47/14:47 Việt Nam, chung concurrency với Core. Chỉ stage status/pointer/releases proxy; không stage raw. Snapshot vẫn full-refresh; tối ưu incremental và restore/shadow là việc vận hành tiếp theo. Bằng chứng kích hoạt workflow/deploy và kiểm tra thực tế cuối phiên trong HANDOFF.
