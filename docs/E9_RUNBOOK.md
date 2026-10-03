# Thực hiện E9 — ETH NVT proxy

Ngày 2026-10-03: phần code/protocol/fixture đã được triển khai; **chưa có backfill, điểm hoặc backtest ETH thật cho E9**. Source gate vẫn bị chặn. E9-01/02/04 chưa DONE; E9-03 có implementation sẵn nhưng nghiệm thu snapshot thật còn chờ nguồn. [ADR-004](ADR-004-e9-nvt-candidate.md) và [config](../configs/research/e9-nvt-candidate-v0.1.0.json) là hợp đồng của ứng viên, tách khỏi Core.

## Bằng chứng truy cập

[Probe E9](evidence/e9-source-access-2026-10-03.json) lưu hash và kết quả thực của catalog được cấp quyền, catalog toàn sản phẩm, 6 sample và 5 nguồn tài liệu/CSV chính thức. Catalog toàn sản phẩm có ETH adjusted transfer USD từ 2015-08-08, NVTAdj90 từ 2015-11-05; catalog Community được cấp quyền chỉ có vốn hóa trong các trường E9 đã kiểm tra. Sample vốn hóa trả 200 với đủ 3 ngày; adjusted USD/native và NVTAdj/NVTAdj90/free-float đều trả 403. CSV ETH hiện tại có 32 cột, không có adjusted transfer hoặc NVT. Catalog toàn sản phẩm không chứng minh entitlement, lịch sử đã tải hoặc quyền công bố.

Không tìm thấy thư cấp API từ Coin Metrics/Talos/Glassnode trong Gmail được người dùng cho phép đọc. Chưa đăng ký tài khoản, chưa gửi email/form và chưa mua gói. [Chương trình miễn phí Talos](https://www.talos.com/academic-program) yêu cầu là sinh viên/chuyên gia học thuật đang hoạt động với email đại học, có thời gian duyệt 1–2 tuần; Gmail không tự chứng minh đủ điều kiện. [Form demo](https://www.talos.com/request-a-demo) cần người liên hệ, công ty và chấp thuận Terms/Privacy/marketing; đây là gửi hồ sơ cho provider, không phải thao tác tự cấp một API key. Chưa có báo giá hoặc cam kết cấp trial miễn phí cho dự án này.

## Code đã có

- [Adapter/probe](../scripts/e9-coinmetrics.mjs): audit không key; backfill có key với licence riêng; retry/timeout, đúng host/query ETH và pagination, không theo redirect mang key. Key chỉ từ `COINMETRICS_API_KEY` trong environment. URL lưu/log không chứa key; response pagination được khử key trước lưu, giữ hash transport và hash bản lưu riêng.
- [Engine](../eco/nvt.py): công thức 90 ngày lịch, xử lý null/zero/gap, chuẩn hóa nhân quả, coverage/warm-up. Harness so E9 và composite thử nghiệm với Core/E7/nhóm giá; correlation, ablation, bootstrap và regime. Không sửa Core.
- [Pipeline riêng](../eco/nvt_pipeline.py): kiểm licence còn hạn, bằng chứng licence SHA, binding manifest, raw/canonical SHA, đối chiếu giá trị canonical với raw, UTC đã đóng, đúng metrics/provider/range. Protocol khóa bằng SHA. Output chỉ ở `data/computed/e9-*`, bất biến theo input/protocol/code/licence; không có lệnh publish E9.

## Mở source gate

Yêu cầu provider cấp **ETH/1d `CapMrktCurUSD` và `TxTfrValAdjUSD`, từ 2015-08-08 đến ngày UTC đã đóng**, đủ dữ liệu để tái dựng SMA90, normalizer và cửa sổ nghiên cứu. Xác nhận riêng quyền cache snapshot private, nghiên cứu dẫn xuất, thời hạn trial; quyền chart/derived score/CSV ở `eco.tnmp.cloud` cần được ghi riêng nếu muốn phát hành. Không suy rộng CC BY-NC của Community cho Network Data Pro.

Nội dung yêu cầu đã chuẩn bị để gửi sau khi có quyền gửi và thông tin người liên hệ:

> We are developing a noncommercial Ethereum research dashboard at eco.tnmp.cloud. We request a no-cost evaluation entitlement for Coin Metrics Network Data Pro: asset ETH, daily UTC, CapMrktCurUSD and TxTfrValAdjUSD, from 2015-08-08 through the latest closed UTC day. Please confirm permission to cache immutable private snapshots and compute derived NVT research, trial expiry, historical revision/availability information, and whether public derived scores/charts/CSV require a separate licence. We do not authorize a paid subscription or recurring charge. Our current Community requests return HTTP 403 for ETH adjusted transfers and NVTAdj90. Please confirm whether a no-cost evaluation is available and its precise scope before provisioning. Contact email: tnmjsc@gmail.com.

Lưu key ở secret store hoặc environment của backend, không gửi key trong chat/commit/frontend. Lưu văn bản cấp quyền ngoài public repo, ví dụ `secrets/e9-provider-grant.txt`. Sau khi kiểm đúng scope, tạo `secrets/e9-rights.json` với `verification_status=verified`, provider `coinmetrics_network_data`, asset `eth`, frequency `1d`, metrics đúng thứ tự `["CapMrktCurUSD", "TxTfrValAdjUSD"]`, `private_cache=true`, `private_research=true`, `valid_from`, `valid_until`, `evidence_file` và `evidence_sha256` của văn bản thật. Không tạo quyền giả bằng cách điền các trường này khi chưa có bằng chứng.

## Chuỗi chạy khi được cấp quyền

Audit no-key có thể chạy lại bằng `pnpm audit:e9`; raw/manifest ở `data/raw/e9-source` private. Muốn giữ evidence public cho lần audit mới, dùng `--evidence-out` với filename mới, không sửa evidence cũ đã khóa.

Khi key và licence đạt, chạy backend theo trình tự (thay ngày và snapshot bằng giá trị thực, không chạy placeholder):

```text
node scripts/e9-coinmetrics.mjs backfill 2015-08-08 <as-of-UTC-date> --rights-file secrets/e9-rights.json
node scripts/upload-private-snapshot-r2.mjs <E9-snapshot-dir>
python -m eco.nvt_pipeline <D03-Core-snapshot-dir> <E9-snapshot-dir> --rights-file secrets/e9-rights.json
```

Uploader dùng token bucket `eco-eth-private` hiện có, PUT/GET kiểm hash; không tạo quyền mới. Kiểm coverage từng trường, first/last valid, gaps/duplicates/null/zero/revision và ngày cuối; snapshot incomplete hoặc licence hết hạn sẽ bị chặn. Nhãn reconstructed giữ nguyên vì chưa biết historical `source_available_at`.

Đọc `research-private.json`, ghi báo cáo summary chỉ khi quyền công bố summary được xác nhận; nêu AP/CIs/Spearman/ablation và các bias L1/native/hourly netting. Dùng holdout Core đã xem chỉ ở mức exploratory. Quyết định giữ nghiên cứu/loại/promote có ADR và bằng chứng thật; promote cần kiểm định mới cùng cổng X02. Sau đó mới xem daily adapter/public release riêng; lịch Core hiện tại không dùng E9.
