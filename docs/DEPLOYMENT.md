# Triển khai website ECO lên `eco.tnmp.cloud`

**Xác minh lần cuối: 2026-10-03.** Tài liệu này là runbook cho agent tiếp tục dự án. Người dùng đã yêu cầu các agent sau khi hoàn thành code có thể tự triển khai lên domain; với thay đổi website đã qua kiểm tra, không cần hỏi lại về thao tác đẩy Git và deploy thông thường. Vẫn phải tuân thủ các cổng dữ liệu, phương pháp và quyền sử dụng trước khi công bố điểm ETH hoặc dữ liệu mới.

## 1. Hệ thống đang chạy

| Thành phần | Giá trị đã kiểm tra |
|---|---|
| Git remote | `https://github.com/tnmjsc-hue/eco.git` (repo public) |
| Nhánh production | `main` |
| Cloudflare Pages project | `eco-tnmp` |
| Git integration | `tnmjsc-hue/eco` → Pages; push `main` tự build/deploy |
| Framework preset hiện tại | `None` |
| Build command hiện tại | Trống; trang HTML tĩnh không cần build |
| Build output directory hiện tại | `public` từ root repo |
| Pages hostname | `https://eco-tnmp.pages.dev/` |
| Domain chính | `https://eco.tnmp.cloud/` |
| DNS | CNAME `eco` → `eco-tnmp.pages.dev`, Proxied, TTL Auto |
| Trạng thái đã xác minh | Pages production success; custom domain Active, SSL enabled; HTTPS 200 |

Cloudflare Dashboard: **Workers & Pages → eco-tnmp → Deployments / Custom domains / Settings**. [Tài liệu Git integration](https://developers.cloudflare.com/pages/configuration/git-integration/) và [build configuration](https://developers.cloudflare.com/pages/configuration/build-configuration/) của Cloudflare là nguồn đối chiếu khi giao diện hoặc hành vi thay đổi.

**Hiện trạng sản phẩm:** `public/index.html` là dashboard Core **Experimental research preview** với điểm ETH reconstructed thật, research report và custom/CSV. Engine Python batch; web static ES modules + vendor ECharts/Lucide. Đã bổ sung scheduled daily batch theo [DAILY_UPDATES](DAILY_UPDATES.md); chưa hoàn thành shadow 30 ngày hoặc gate sản phẩm vận hành. [ADR-002](ADR-002-experimental-research-preview.md) ghi scope phi thương mại.

## 2. Quy trình triển khai cho agent

1. Đọc `AGENTS.md`, `README.md`, `docs/HANDOFF.md` và phần kế hoạch liên quan. Xác nhận `git remote -v`, nhánh hiện tại, trạng thái `git status --short --branch`, và commit production hiện tại. Không giả định workspace sạch hoặc Cloudflare vẫn giữ cấu hình cũ.
2. Hoàn thành thay đổi và chạy `python -m unittest discover -s tests -v`, `node --test tests/web.test.mjs`, `node scripts/validate-research-artifacts.mjs`, `node --check public/app.js`, `git diff --check`. Khi thay dependencies, `pnpm install --frozen-lockfile` và `pnpm build`. Kiểm browser bằng `scripts/check-dashboard.mjs` trên local và production: ngày null, custom toàn chuỗi, CSV, lỗi mạng, viewport 360/390/768/1440 và chart nonblank.
3. Kiểm tra tập file sắp công khai. Repo là public: không stage `.env`, API key, file DPAPI, snapshot raw có bản quyền, dữ liệu chưa được phép công khai hoặc artifact nghiên cứu riêng. Dùng `git add` với đường dẫn cụ thể, rồi xem `git diff --cached --stat`, `git diff --cached` và `git diff --cached --check` trước commit.
4. Commit thay đổi đã kiểm tra và đẩy nhánh `main` lên `origin`. Cloudflare Pages sẽ tự build và deploy; không cần upload tay hoặc tạo API token cho mỗi lần push. Không dùng `git push --force` trên `main`.
5. Trong Pages **Deployments**, xác nhận deployment `production` của commit vừa đẩy có trạng thái `Success`. Mở cả `https://eco-tnmp.pages.dev/` và `https://eco.tnmp.cloud/`; xác nhận HTTPS, nội dung mới và asset liên quan. Nội dung ở domain riêng có thể cập nhật muộn hơn hostname Pages trong thời gian ngắn; kiểm tra lại trước khi báo hoàn thành.
6. Ghi vào `docs/HANDOFF.md`: task, file, lệnh/test và kết quả thực, commit SHA, Pages deployment/status, HTTP/domain, dữ liệu + `methodology_version` nếu có, lỗi/rollback và bước tiếp theo. Đừng đánh dấu `DONE` nếu mới push mà build hoặc domain chưa được xác minh.

Lệnh PowerShell mẫu cho trang tĩnh hiện tại (chạy từ root repo; thay thông điệp commit theo thay đổi thực tế):

```powershell
git status --short --branch
git remote -v
Test-Path public/index.html
git diff --check
git add -- public/index.html public/styles.css public/favicon.svg
git diff --cached --stat
git diff --cached --check
git commit -m "Describe the verified change"
git push origin main
git rev-parse HEAD
```

Ví dụ trên **không** thay việc xem toàn bộ diff; chỉ stage file thực sự đã sửa. Nếu thay đổi ở file khác, chọn đúng đường dẫn. Sau khi Pages báo `Success`, kiểm tra HTTP:

```powershell
(Invoke-WebRequest 'https://eco-tnmp.pages.dev/' -UseBasicParsing).StatusCode
(Invoke-WebRequest 'https://eco.tnmp.cloud/' -UseBasicParsing).StatusCode
```

HTTP 200 chỉ chứng minh server trả trang; agent còn phải kiểm tra nội dung/version đúng commit và các chức năng vừa sửa. Không tự nhận đã kiểm tra responsive, engine hoặc dữ liệu nếu chưa chạy kiểm tra tương ứng.

## 3. Khi code web chuyển sang React/Vite

Không giữ cấu hình `public` theo quán tính. Sau khi scaffold và thử build local, vào **Pages → Settings → Builds** để đặt root directory, build command và output directory theo cấu trúc thật. Ví dụ Vite ở root thường dùng build command `npm run build` và output `dist`; nếu ứng dụng nằm trong `web/`, đường dẫn phải điều chỉnh theo cấu trúc đó. Cập nhật bảng mục 1 và lệnh mục 2 sau khi xác minh Cloudflare build thành công. [Cloudflare build configuration](https://developers.cloudflare.com/pages/configuration/build-configuration/).

Cloudflare Pages phục vụ web tĩnh. `eco/pipeline.py` compute/publish offline; CI chỉ kiểm code/artifact. `.github/workflows/daily-update.yml` chạy provider → private R2 readback → compute/diff/immutable revision → tests → bot commit main → deploy hook main → production checksums. GitHub `GITHUB_TOKEN` không tự kích hoạt CI push, nên daily job tự kiểm trước commit. Lịch chạy và manual-run evidence xem HANDOFF/DAILY_UPDATES. Network incremental, restore drill và 30-day shadow chưa hoàn tất; không coi CI/Pages success là bằng chứng cho các phần đó.

Lưu trữ theo [STORAGE.md](STORAGE.md): R2 `eco-eth-private` giữ snapshot raw đã readback verify; web chỉ đọc `data/latest.json` → versioned manifest/history/research trên Pages. Scope phi thương mại preview được người dùng xác nhận; status được phép `score_available=true` cho reconstructed experimental, không suy rộng thành product-release/as-published/commercial gates. CDN cache immutable versioned data, revalidate pointer; UI kiểm hash và giữ bản tốt khi refresh lỗi.

## 4. Điều kiện công bố dữ liệu chỉ số

Quyền tự deploy website của người dùng không thay thế các cổng nghiệm thu trong `docs/HANDOFF.md` và `docs/MASTER_PLAN.md`. Trước khi đưa điểm ETH thật hoặc JSON dữ liệu lên domain:

- Xác minh quyền phát hành dữ liệu theo D02; chỉ công khai output được phép phân phối.
- Hoàn thành engine, kiểm thử chống nhìn tương lai, provenance/version, kiểm định và nhãn phát hành phù hợp. `core` là giai đoạn trung gian, không được mô tả là đủ 9 metric.
- Giữ snapshot/hash/manifest, tách `reconstructed` khỏi `as_published`, và không ghi đè điểm đã công bố. Nếu có correction, thêm revision và lý do.
- Đồng bộ nội dung UI, JSON, CSV, ngày dữ liệu và trạng thái stale/null. Không gọi điểm 0–100 là xác suất.

Nếu các điều kiện chưa đạt, vẫn có thể deploy phần giao diện/giải thích với nhãn thử nghiệm rõ ràng, nhưng không trình bày fixture hoặc dữ liệu chưa kiểm định như điểm thật.

## 5. Credential, sự cố và rollback

- Git push trên máy đã được xác minh qua Git Credential Manager. Nếu phiên đăng nhập hết hạn, đăng nhập bằng luồng Git/GitHub chính thức; không dán PAT vào code, URL, log hoặc Markdown.
- Cloudflare Pages API token được người dùng lưu ngoài repo ở `%APPDATA%\ETH-CBBI\cloudflare-pages.dpapi`, mã hóa theo tài khoản Windows. **Git integration không cần token này để tự deploy.** Chỉ dùng khi cần API Pages và không in giá trị giải mã. Account ID/zone ID lấy từ Dashboard khi cần; không lưu secret vào repo.
- Nếu build lỗi, đọc log deployment trong Pages, sửa code/cấu hình rồi push commit sửa. Nếu domain lỗi, kiểm tra trạng thái Custom domains, SSL và CNAME `eco`; đừng tự đổi DNS khi Pages vẫn cấu hình đúng.
- Nếu bản mới gây lỗi, ưu tiên phục hồi bằng `git revert <bad-commit>` rồi push `main`, hoặc dùng Pages Deployments để rollback bản thành công trước đó nếu cần khôi phục ngay. Ghi commit/deployment cũ và mới, thời điểm và lý do vào `docs/HANDOFF.md`. Quy trình rollback **chưa được thử thực tế**; không ghi là đã diễn tập.
- Nếu lỗi liên quan điểm đã công bố, áp dụng quy tắc revision và lịch sử bất biến trong kế hoạch; rollback giao diện không được âm thầm viết lại lịch sử điểm.

## 6. Bằng chứng đã có

Ngày 2026-10-03, hai commit `906e579` và `0e7cce0` trên `main` đã có Pages deployment `success`/`production`. Cloudflare Custom domains hiển thị `Active` và `SSL enabled` cho `eco.tnmp.cloud`; HTTP GET trên Pages hostname và domain riêng trả 200. Sau commit thứ hai, nội dung mới được thấy trên domain riêng. Đây là bằng chứng cho **quy trình triển khai trang tĩnh hiện tại**, chưa phải kiểm thử cho app React, batch dữ liệu hoặc release chỉ số ETH.
