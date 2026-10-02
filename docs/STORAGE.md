# Lưu trữ dữ liệu ECO trên Cloudflare

**Kiểm tra ngày 2026-10-03.** Cloudflare R2 đã được kích hoạt trong tài khoản đang dùng cho Pages. Bucket riêng `eco-eth-private` đã tạo ở lớp **Standard**, vùng tự chọn **Asia Pacific**, `Public Access: Disabled`, kích thước ban đầu `0 B`. Bucket `storage` đã có từ trước và không thuộc dự án này; không dùng hoặc sửa bucket đó.

Token R2 `eco-eth-snapshot-pipeline` đã được tạo với quyền **Object Read & Write** chỉ trên `eco-eth-private`, có hạn đến **2027-10-03**. Access Key ID và Secret Access Key được mã hóa DPAPI tại `%APPDATA%\ETH-CBBI\r2-access-key-id.dpapi` và `%APPDATA%\ETH-CBBI\r2-secret-access-key.dpapi`, ngoài repo. Đã thử `PutObject` → `GetObject` so khớp nội dung → `DeleteObject` trên một object không nhạy cảm; cả ba thành công. Đây là xác minh credential/bucket, chưa phải pipeline lưu snapshot thật.

## Vai trò của từng nơi lưu trữ

| Nơi | Dùng cho | Trạng thái |
|---|---|---|
| Cloudflare Pages `eco-tnmp` | Website và JSON tĩnh **được phép công bố** tại `eco.tnmp.cloud` | Đang chạy; GitHub `main` tự triển khai |
| R2 `eco-eth-private` | Snapshot raw, hash, manifest chạy batch, bản sao lưu release và tài liệu kiểm toán riêng tư | Bucket và credential đã kiểm tra; chưa có dữ liệu hoặc pipeline tự động |
| D1 / KV | Chỉ mục truy vấn hoặc trạng thái cập nhật nhiều lần nếu sau này có nhu cầu thật | Chưa tạo; bản đầu không cần database server |

Trang giới thiệu chưa có engine, dữ liệu ETH đã kiểm định hoặc điểm số. `public/data/status.json` chỉ khai báo trạng thái phát hành, không chứa dữ liệu ETH. Việc bucket tồn tại **không** đồng nghĩa pipeline đã kết nối hoặc dữ liệu được sao lưu. Cloudflare Pages không chạy batch Python định kỳ thay cho pipeline.

## Quy tắc dữ liệu

1. Dữ liệu provider, snapshot raw và artifact chưa rõ quyền phát hành chỉ nằm ở local hoặc R2 riêng tư; không commit vào repo public và không bật R2 public access/custom domain cho bucket này.
2. Mỗi snapshot phải có SHA-256, thời điểm quan sát/sẵn có/tải, provider, phiên bản và manifest. R2 object key nên có tên bất biến, ví dụ `raw/<provider>/<retrieved-at>/<sha256>.json`; không ghi đè bản đã dùng để tính điểm.
3. Chỉ sau D02 và các gate phát hành mới đưa JSON release được phép công bố vào Pages. Dùng đường dẫn có version/ID release bất biến; client đọc một manifest trỏ đến đúng release để tránh trộn version. Điểm đã công bố không được sửa đè.
4. Frontend không nhận R2 token hoặc API key của provider. Nếu sau này cần API động, tạo endpoint chỉ đọc dữ liệu công khai đã kiểm định; không bind bucket raw riêng tư trực tiếp vào Pages Functions.
5. Kiểm tra chi phí/usage của R2 định kỳ. R2 Standard có allowance theo tháng trên Free nhưng vượt allowance có thể phát sinh phí; dashboard hiện báo `$0.00` billable usage ở thời điểm kiểm tra. Giữ bucket này ở Standard nếu muốn dùng allowance Free.

## Kết nối pipeline với bucket khi S02/S04 bắt đầu

Token giới hạn bucket đã có; **không tạo thêm token trùng**. Nếu cần xoay vòng: vào Cloudflare Dashboard **R2 Object Storage → Manage API Tokens**, tạo token mới cùng phạm vi, kiểm tra credential mới, cập nhật secret store rồi thu hồi token cũ. Không dùng Global API Key, token Pages hiện có hoặc token quyền toàn tài khoản.

Trên máy chạy pipeline, đọc hai file DPAPI bằng **cùng tài khoản Windows** và chuyển vào tiến trình dưới tên `R2_ACCESS_KEY_ID`, `R2_SECRET_ACCESS_KEY`; thêm `R2_ACCOUNT_ID`, `R2_BUCKET` từ cấu hình. Endpoint S3: `https://<account-id>.r2.cloudflarestorage.com`. DPAPI gắn với máy/tài khoản Windows hiện tại, nên runner khác cần secret store riêng và cấp credential theo quy trình an toàn. Không ghi giá trị vào `.env.example`, log, URL, commit hoặc frontend. Nếu dùng GitHub Actions, thêm secret ở repo Settings → Secrets and variables → Actions, không đặt vào Pages build env vì Pages chỉ đọc release public. Việc chuyển credential sang runner chưa thực hiện.

**Chưa thực hiện:** gắn runner, upload snapshot thật, kiểm tra restore, lịch batch. Agent sau phải ghi lệnh/đầu ra thực tế vào `docs/HANDOFF.md`; không đánh dấu những bước này đã xong.

## Kiểm tra và chi phí

- Dashboard: **R2 Object Storage → eco-eth-private → Objects/Settings**: xác nhận bucket, `Public Access: Disabled`, lớp Standard và usage.
- Public status: `https://eco.tnmp.cloud/data/status.json` trả JSON trạng thái sau khi commit Pages tương ứng deploy thành công. Nó không đọc R2.
- [R2 pricing](https://developers.cloudflare.com/r2/pricing/): Standard Free allowance 10 GB-month storage, 1 triệu Class A và 10 triệu Class B operations mỗi tháng; egress miễn phí. Vượt mức có thể tính phí; Infrequent Access có mô hình phí khác.
- [R2 bucket mặc định riêng tư](https://developers.cloudflare.com/r2/buckets/create-buckets/) và [R2 API tokens](https://developers.cloudflare.com/r2/api/tokens/).
- [Pages Functions bindings](https://developers.cloudflare.com/pages/functions/bindings/) chỉ cần khi thực sự thêm API động; binding không làm file HTML tĩnh tự đọc bucket.
- [D1 pricing](https://developers.cloudflare.com/d1/platform/pricing/) và [KV pricing](https://developers.cloudflare.com/kv/platform/pricing/) để đánh giá khi có nhu cầu truy vấn/trạng thái động.
