# ECO — Dashboard Ethereum 7 chỉ số

Mục tiêu: xây dựng chỉ số chu kỳ ETH và website có trải nghiệm tương tự [CBBI](https://colintalkscrypto.com/cbbi/), với phương pháp, dữ liệu và lịch sử tính điểm có thể kiểm chứng.

**Phiên 2026-10-03: ECO 7 đã chạy trên [production](https://eco.tnmp.cloud/) với dữ liệu ETH thật.** Điểm ngày 2026-10-02 là 31.979753577249287 (UI 32/100), đủ 7/7 thành phần; Core 4 đối chiếu giữ nguyên 40.009962172523664 (UI 40/100). Lịch sử reconstructed; kiểm định mở rộng chưa chứng minh cải thiện so với Core. Đây là **Experimental research preview**, không phải xác suất, tín hiệu đầu tư hay bản đủ 9 metric. Quyền phi thương mại và phiên bản riêng: [ADR-002](docs/ADR-002-experimental-research-preview.md), [ADR-006](docs/ADR-006-extended-experimental-dashboard.md). CI, hosted daily và production hashes/browser đã xác minh, xem [HANDOFF](docs/HANDOFF.md).

Dashboard dùng native ES modules, ECharts và Lucide trên Pages static `public`; engine Python 3.12 + NumPy 2.3.5. Snapshot raw giữ local/R2 private; web lấy versioned JSON đã tính sẵn, không gọi API provider hay bucket raw. Daily batch chạy GitHub Actions dự kiến **10:17**, kiểm tra lại **14:17 giờ Việt Nam**, và dashboard kiểm tra release mới mỗi 15 phút khi đang mở. Xem [runbook cập nhật](docs/DAILY_UPDATES.md). Chưa hoàn thành shadow 30 ngày; biểu đồ vẫn reconstructed.

**Ba metric ETH đã tích hợp vào ECO 7:** tỷ trọng ETH trên sàn (E3 proxy), cường độ địa chỉ hoạt động (E8 proxy), vốn hóa/lượt chuyển ETH (E9 proxy). Tab Mở rộng giữ công thức/coverage và CSV riêng. Nguồn thật 4.083 ngày đến 2026-10-02; các proxy có định nghĩa riêng, không tương đương RHODL/Dormancy/NVT gốc. Core 4 giữ nguyên phiên bản và trọng số. [Phương pháp và kết quả thực thi](docs/NETWORK_PROXIES.md), [ADR-005](docs/ADR-005-network-research-proxies.md). Lịch proxy kiểm tra 10:47/14:47 Việt Nam; cờ exchange `flash` được nêu là tạm thời.

**Theo yêu cầu tích hợp mới:** dashboard chính mặc định ECO 7 Experimental, `extended-v0.1.0` = 75% Core + 25% trung bình ba proxy. Điểm 31.979753577249287 (UI 32), đủ 7/7 ngày 2026-10-02. Có chế độ Core 4 (40 cùng ngày), tùy chỉnh bảy thành phần, lịch sử/CSV cùng ngày UTC và manifest pin hai release cha. Core/proxy cũ bất biến. [ADR-006](docs/ADR-006-extended-experimental-dashboard.md), [kết quả ECO 7](docs/EXTENDED_DASHBOARD.md). Kiểm định mở rộng thăm dò chưa chứng minh cải thiện so với Core.

Arkham được thêm làm đường đối chiếu holders/flow trên dashboard; đã kiểm API docs, giới hạn coverage và probe 403. [Kế hoạch nguồn](docs/ARKHAM_SOURCE.md) và [hồ sơ xin trial](docs/ARKHAM_TRIAL_REQUEST.md) đã thực hiện: account miễn phí đã xác minh email, yêu cầu trial nghiên cứu không thẻ/không tự gia hạn đã gửi support và có thư xác nhận nhận. Chưa có key/quyền dữ liệu, còn chờ Arkham duyệt; chưa đưa Arkham vào điểm tính.

## Lệnh thực tế

Setup với Python 3.12, Node 24 và pnpm 11.19.0:

```text
python -m pip install -r requirements.txt
pnpm install --frozen-lockfile
pnpm build
python -m unittest discover -s tests -v
node --test tests/*.test.mjs
node scripts/validate-research-artifacts.mjs
python -m http.server 8876 --bind 127.0.0.1 --directory public
```

Mở `http://127.0.0.1:8876/`. `pnpm build` copy vendor assets + licences vào `public/vendor`; không build/publish dữ liệu mới. Pages vẫn không cần build command. CI kiểm engine/gate, lockfile/build vendor, public hashes và research protocol; browser QA script `scripts/check-dashboard.mjs` cần Playwright cùng Chromium hoặc biến `PLAYWRIGHT_MODULE`/`CHROME_EXECUTABLE` cho runtime có sẵn.

Tính từ snapshot private đã audit, sau đó publish đúng scope phi thương mại được chấp thuận (thay snapshot/release bằng path thực; không chạy placeholder):

```text
python -m eco.pipeline compute data/raw/coinmetrics/coinmetrics-backfill-2026-10-03-2026-10-02T182337734Z
python -m eco.pipeline publish data/computed/core-c899a808bda65db96be3
```

Lệnh compute kiểm hash raw/canonical, ETH/schema/timestamps và frozen protocol. Output private `data/computed`; public publisher có rights gate và allowlist, không copy engine details hoặc raw. Không đổi policy thành commercial để bỏ gate. Release assets immutable; pointer đổi sau xác minh. `.gitattributes` giữ nguyên bytes JSON versioned qua Windows/Linux để checksum không đổi do CRLF.

`python -m eco.daily` chạy toàn bộ daily fetch → R2 PUT/GET hash → compute/research theo protocol cố định → diff/revision/first-publication records → static release/status. Cần credential R2 chỉ trong environment; workflow dùng Actions Secrets. Nếu dữ liệu không đổi, pointer giữ nguyên. Nếu thiếu input cho ngày mới hoặc nguồn lỗi, không tạo số thay thế, giữ score cũ với ngày gốc. Network hiện refresh toàn range để phát hiện revision ngoài cửa sổ ngắn, chưa tối ưu tải incremental.

Chạy probe mẫu bằng `node scripts/audit-coinmetrics.mjs 2026-10-03` hoặc full history bằng `node scripts/backfill-coinmetrics.mjs 2015-08-01 2026-10-03`. Raw response và manifest SHA-256 được ghi vào `data/raw/coinmetrics/` (bị Git ignore); không commit dữ liệu này. Báo cáo tại [data-audit.md](docs/data-audit.md), protocol nghiên cứu tại [ADR-001](docs/ADR-001-core-research-protocol.md), feasibility 9 vị trí tại [metric-feasibility.md](docs/metric-feasibility.md), và giới hạn quyền tại [data-rights.md](docs/data-rights.md). Upload snapshot private lên R2 dùng `node scripts/upload-private-snapshot-r2.mjs <snapshot-dir>` sau khi có `R2_ACCOUNT_ID` cùng credential trong process env.

Kiểm tra bất biến protocol D04 và register feasibility D05 bằng `node scripts/validate-research-artifacts.mjs`. Lệnh này chỉ xác minh hợp đồng research/config, không chạy engine, backtest, live source probe hoặc xác nhận quyền phát hành.

Chạy live probe D05 không cần API key bằng `node scripts/audit-d05-feasibility.mjs 2026-10-03`. Raw response/manifest được giữ trong `data/raw/d05/` (bị Git ignore); chỉ summary/hash evidence không chứa raw được commit.

## Đọc theo thứ tự

E9 NVT proxy có adapter có key/licence, engine và harness nghiên cứu riêng; nguồn adjusted transfer ETH hiện vẫn bị chặn, chưa có backfill/backtest E9 thật. Hướng chạy và điều kiện tiếp tục ở [E9_RUNBOOK.md](docs/E9_RUNBOOK.md). `pnpm audit:e9` chỉ kiểm truy cập, không phát hành E9 hoặc thay Core.

1. [Kế hoạch chi tiết](docs/MASTER_PLAN.md): phạm vi, 9 chỉ số đối chiếu, công thức bản đầu, dữ liệu, kiến trúc, giao diện, kiểm định và tiêu chí hoàn thành.
2. [Nghiên cứu và bằng chứng](docs/RESEARCH.md): nguồn chính thức, phiên bản CBBI đã đọc, kết quả thử API và giới hạn chưa xác minh.
3. [Danh sách công việc và bàn giao](docs/HANDOFF.md): thứ tự thực hiện, điều kiện nghiệm thu, trạng thái và prompt cho agent kế tiếp.
4. [Triển khai website](docs/DEPLOYMENT.md): cấu hình GitHub → Cloudflare Pages → `eco.tnmp.cloud`, kiểm tra và rollback.
5. [Lưu trữ dữ liệu](docs/STORAGE.md): Pages cho JSON công khai, R2 riêng tư cho snapshot và giới hạn kết nối hiện tại.
6. [Quy tắc agent](AGENTS.md): cách tiếp tục và cập nhật tiến độ.

## Quyết định nền tảng

- Giữ trải nghiệm CBBI: điểm 0–100, biểu đồ ETH và điểm lịch sử, màu theo mức điểm, từng metric, bật/tắt metric và trang giải thích.
- Không đổi ticker BTC thành ETH rồi giữ nguyên mọi công thức. ETH cần phương pháp riêng, đặc biệt sau The Merge và với dữ liệu dựa trên tài khoản.
- Bản đầu đề xuất: `core-v0.1`, 4 thành phần có đường dữ liệu khả thi; 9 thành phần là mục tiêu nghiên cứu `extended-v0.x`, không giả lập cho đủ số lượng.
- Điểm thể hiện mức nóng/lạnh tương đối theo mô hình; **80/100 không có nghĩa là 80% xác suất tạo đỉnh**.
- Tách lịch sử tính lại theo dữ liệu hiện có và lịch sử điểm thực sự đã công bố; không dùng biểu đồ hồi cứu để tuyên bố khả năng dự báo.

Tên làm việc trong mã: `eth-cycle-index`; dashboard preview dùng ECO. `ETH-CBBI` là tên thư mục. Phát hành sản phẩm vận hành đầy đủ còn các gate riêng trong HANDOFF.
