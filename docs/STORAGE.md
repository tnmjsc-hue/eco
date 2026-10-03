# Lưu trữ dữ liệu ECO trên Cloudflare

**Kiểm tra ngày 2026-10-03.** Cloudflare R2 đã được kích hoạt trong tài khoản đang dùng cho Pages. Bucket riêng `eco-eth-private` đã tạo ở lớp **Standard**, vùng tự chọn **Asia Pacific**, `Public Access: Disabled`, kích thước ban đầu `0 B`. Bucket `storage` đã có từ trước và không thuộc dự án này; không dùng hoặc sửa bucket đó.

Token R2 `eco-eth-snapshot-pipeline` đã được tạo với quyền **Object Read & Write** chỉ trên `eco-eth-private`, có hạn đến **2027-10-03**. Access Key ID và Secret Access Key được mã hóa DPAPI tại `%APPDATA%\ETH-CBBI\r2-access-key-id.dpapi` và `%APPDATA%\ETH-CBBI\r2-secret-access-key.dpapi`, ngoài repo. Đã thử `PutObject` → `GetObject` so khớp nội dung → `DeleteObject` trên một object không nhạy cảm; cả ba thành công. Đây là xác minh credential/bucket, chưa phải pipeline lưu snapshot thật.

## Vai trò của từng nơi lưu trữ

| Nơi | Dùng cho | Trạng thái |
|---|---|---|
| Cloudflare Pages `eco-tnmp` | Website và JSON tĩnh **được phép công bố** tại `eco.tnmp.cloud` | Đang chạy; GitHub `main` tự triển khai |
| R2 `eco-eth-private` | Snapshot raw, hash, manifest chạy batch, bản sao lưu release và tài liệu kiểm toán riêng tư | Snapshot D03 đã upload; 7/7 object đọc ngược và khớp SHA-256 |
| D1 / KV | Chỉ mục truy vấn hoặc trạng thái cập nhật nhiều lần nếu sau này có nhu cầu thật | Chưa tạo; bản đầu không cần database server |

Dashboard Core nghiên cứu có engine và score reconstructed, không phải sản phẩm vận hành realtime. `public/data/status.json` ghi scope experimental/noncommercial và daily-update status; `public/data/latest.json` trỏ manifest/history/research versioned. Scheduled batch chạy GitHub Actions, không chạy trong Pages. Mỗi snapshot mới phải upload R2 private + readback toàn bộ trước public release; xem [DAILY_UPDATES](DAILY_UPDATES.md).

## Quy tắc dữ liệu

1. Dữ liệu provider, snapshot raw và artifact chưa rõ quyền phát hành chỉ nằm ở local hoặc R2 riêng tư; không commit vào repo public và không bật R2 public access/custom domain cho bucket này.
2. Mỗi snapshot phải có SHA-256, thời điểm quan sát/sẵn có/tải, provider, phiên bản và manifest. R2 object key nên có tên bất biến, ví dụ `raw/<provider>/<retrieved-at>/<sha256>.json`; không ghi đè bản đã dùng để tính điểm.
3. Chỉ sau D02 và các gate phát hành mới đưa JSON release được phép công bố vào Pages. Dùng đường dẫn có version/ID release bất biến; client đọc một manifest trỏ đến đúng release để tránh trộn version. Điểm đã công bố không được sửa đè.
4. Frontend không nhận R2 token hoặc API key của provider. Nếu sau này cần API động, tạo endpoint chỉ đọc dữ liệu công khai đã kiểm định; không bind bucket raw riêng tư trực tiếp vào Pages Functions.
5. Kiểm tra chi phí/usage của R2 định kỳ. R2 Standard có allowance theo tháng trên Free nhưng vượt allowance có thể phát sinh phí; dashboard hiện báo `$0.00` billable usage ở thời điểm kiểm tra. Giữ bucket này ở Standard nếu muốn dùng allowance Free.

## Lưu snapshot private vào bucket

Đã thêm `scripts/upload-private-snapshot-r2.mjs`. Script chỉ nhận snapshot hoàn tất nằm dưới `data/raw/coinmetrics/`, upload từng file dưới prefix bất biến `raw/coinmetrics/<run-id>/`, upload `manifest.json` cuối cùng và GET đọc lại từng object để so SHA-256. Chế độ `--dry-run` chỉ liệt kê object key, kích thước và hash, không cần credential.

```powershell
node scripts/upload-private-snapshot-r2.mjs data/raw/coinmetrics/<run-id> --dry-run
node scripts/upload-private-snapshot-r2.mjs data/raw/coinmetrics/<run-id>
```

Lệnh upload cần `R2_ACCOUNT_ID`, `R2_BUCKET=eco-eth-private`, `R2_ACCESS_KEY_ID`, `R2_SECRET_ACCESS_KEY` trong environment của tiến trình. Access/secret keys không được truyền trên command line. Snapshot D03 đã upload thật với 7 object dưới `raw/coinmetrics/coinmetrics-backfill-2026-10-03-2026-10-02T182337734Z/`. Script GET đọc lại đủ 7 object và xác minh hash thành công; canonical SHA-256 `aa78757fcaee33ef23ecf3ebd92791a685df2617f2b3874f5f5183d16babdd03`. Manifest được upload cuối cùng. Account ID và credential không ghi vào repo hoặc log. Bản local vẫn được giữ làm nguồn đối chiếu.

## Luồng đọc từ website và cache

Bucket private không được gọi trực tiếp từ browser và không bind prefix `raw/` vào Pages Functions. Frontend không được giữ S3 key, API key hay signed URL dài hạn. Dữ liệu public chỉ được xuất sau rights/release gates: ưu tiên JSON release đã version hóa trong Pages/CDN, ví dụ `data/releases/<release-id>/history.json` với `Cache-Control: public, max-age=31536000, immutable`; một manifest/latest pointer nhỏ dùng cache ngắn hoặc revalidate. Nếu cần endpoint, Worker/Pages Function chỉ đọc prefix `public-releases/` đã được duyệt, không đọc raw. Browser tải đúng release theo manifest để nhanh và không trộn version.

Phiên 2026-10-03, người dùng xác nhận nghiên cứu phi thương mại; [ADR-002](ADR-002-experimental-research-preview.md) áp dụng CC BY-NC 4.0 cho Community chart/derived scores/CSV với attribution. Preview đã có publisher `eco/pipeline.py`: raw/canonical/engine details không nằm trong allowlist, chỉ history/research/manifest được xuất. Frontend xác minh SHA-256 và phiên bản, không gọi provider/R2. `_headers` đặt immutable cache cho release và revalidate pointer. Quyền thương mại, nguồn mở rộng và gate vận hành đầy đủ không được suy rộng từ preview.

## Kết nối pipeline với bucket khi S02/S04 bắt đầu

Token giới hạn bucket đã có; **không tạo thêm token trùng**. Nếu cần xoay vòng: vào Cloudflare Dashboard **R2 Object Storage → Manage API Tokens**, tạo token mới cùng phạm vi, kiểm tra credential mới, cập nhật secret store rồi thu hồi token cũ. Không dùng Global API Key, token Pages hiện có hoặc token quyền toàn tài khoản.

Trên máy chạy pipeline, đọc hai file DPAPI bằng **cùng tài khoản Windows** và chuyển vào tiến trình dưới tên `R2_ACCESS_KEY_ID`, `R2_SECRET_ACCESS_KEY`; thêm `R2_ACCOUNT_ID`, `R2_BUCKET` từ cấu hình. Endpoint S3: `https://<account-id>.r2.cloudflarestorage.com`. DPAPI gắn với máy/tài khoản Windows hiện tại, nên runner khác cần secret store riêng và cấp credential theo quy trình an toàn. Không ghi giá trị vào `.env.example`, log, URL, commit hoặc frontend. Nếu dùng GitHub Actions, thêm secret ở repo Settings → Secrets and variables → Actions, không đặt vào Pages build env vì Pages chỉ đọc release public. Việc chuyển credential sang runner chưa thực hiện.

**Daily batch:** dùng lại bucket-limited S3 token trong GitHub Actions Secrets, không đưa Pages API token/Git credential cá nhân vào runner. Deploy hook main có secret riêng; bản DPAPI ở `%APPDATA%\ETH-CBBI\cloudflare-daily-hook.dpapi`. Snapshot 2026-10-03T02:00:41.628Z đã upload/readback 7/7, canonical `33264b50fc555e3591cdd61be0301ed84f62505f86a55bd1c3807a9e97d3f976`, 4081 observation đến 2026-10-02; MVRV ngày cuối còn null. Website chỉ đọc output public, không prefix raw. Restore độc lập và shadow 30 ngày chưa thực hiện; evidence hosted scheduler ghi HANDOFF.

## Kiểm tra và chi phí

**Readback E2/C1/C2, 2026-10-03:** script `restore-private-snapshot-r2.mjs` dùng token bucket hiện có, chỉ GET các object snapshot cha đã upload. Core `2026-10-03T091053030Z` 7/7, canonical `59bda78805616259b93c63cef5aec50a0f33db768fe8e8d7c272e44bab5ccdfb`; network `2026-10-03T084645399Z` 8/8, canonical `405c4eaf20e23123643ed08acf00d4ce6df2f0ce41f82c975ebf7d4730628637`. Local file khác hash/extra files/symlink bị từ chối, không ghi đè hoặc xóa. Receipt/private replay inputs bị Git ignore; manifest public chỉ hash/readback metadata. Frontend chỉ đọc derived diagnostics Pages. Chạy daily thật lần hai `unchanged`; readback hai snapshot không thay nghiệm thu restore/fault drill O03 toàn hệ thống.

- Dashboard: **R2 Object Storage → eco-eth-private → Objects/Settings**: xác nhận bucket, `Public Access: Disabled`, lớp Standard và usage.
- Public status: `https://eco.tnmp.cloud/data/status.json` trả JSON trạng thái sau khi commit Pages tương ứng deploy thành công. Nó không đọc R2.
- [R2 pricing](https://developers.cloudflare.com/r2/pricing/): Standard Free allowance 10 GB-month storage, 1 triệu Class A và 10 triệu Class B operations mỗi tháng; egress miễn phí. Vượt mức có thể tính phí; Infrequent Access có mô hình phí khác.
- [R2 bucket mặc định riêng tư](https://developers.cloudflare.com/r2/buckets/create-buckets/) và [R2 API tokens](https://developers.cloudflare.com/r2/api/tokens/).
- [Pages Functions bindings](https://developers.cloudflare.com/pages/functions/bindings/) chỉ cần khi thực sự thêm API động; binding không làm file HTML tĩnh tự đọc bucket.
- [D1 pricing](https://developers.cloudflare.com/d1/platform/pricing/) và [KV pricing](https://developers.cloudflare.com/kv/platform/pricing/) để đánh giá khi có nhu cầu truy vấn/trạng thái động.
