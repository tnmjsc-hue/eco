# Bàn giao triển khai ETH Cycle Index

**Cập nhật: 2026-10-03.** Trạng thái tổng: **PLANNING_COMPLETE / PUBLIC_LANDING_PAGE_DEPLOYED / ENGINE_NOT_STARTED**.

Tài liệu chuẩn: [MASTER_PLAN.md](MASTER_PLAN.md). Bằng chứng nghiên cứu: [RESEARCH.md](RESEARCH.md). Triển khai web: [DEPLOYMENT.md](DEPLOYMENT.md). Quy tắc agent: [AGENTS.md](../AGENTS.md).

## 1. Đã hoàn thành và chưa hoàn thành

Đã đọc website/FAQ/một số file engine chính thức của CBBI; chốt SHA tham chiếu; kiểm tra workspace; thử một số truy vấn dữ liệu ETH thật; viết bộ kế hoạch và checklist tiếp tục.

**Đã có Git repository và trang giới thiệu tĩnh tại `eco.tnmp.cloud`. Chưa có engine, dependency, full dataset, điểm ETH, test engine, backtest, dashboard hoặc scheduler.** Trang giới thiệu không phải bản phát hành chỉ số. Không có API trả phí được mua. Không có công việc nào đang chạy nền. Không có agent khác đang giữ task.

## 2. Bắt đầu từ đâu

Khi người dùng yêu cầu triển khai, bắt đầu **D01** và **D02**, sau đó **D03**. Mục tiêu đầu tiên là một audit dữ liệu có thể tái lập, chưa phải dashboard có số đẹp. Có thể bootstrap tối thiểu S01 để hỗ trợ audit, nhưng không mở rộng kiến trúc trước khi biết dữ liệu.

Nếu dữ liệu bị chặn, giữ evidence lỗi và làm task độc lập như schema/fixtures/UI; không dùng BTC thay ETH. Chỉ hỏi người dùng khi thực sự cần lựa chọn chi phí, tài khoản, mục đích thương mại hoặc phát hành, kèm kết quả cụ thể đã chuẩn bị.

## 3. Mặc định đã có để không hỏi lại từ đầu

| Chủ đề | Mặc định đề xuất |
|---|---|
| Tên mã | `eth-cycle-index`; chưa coi là thương hiệu cuối |
| Bản đầu | `core-v0.1`, E1/E5/E6/E7; giữ mục tiêu nghiên cứu 9 thành phần |
| Dữ liệu | Coin Metrics Community, đúng 4 trường đã probe |
| Giá và ngày | USD, daily UTC, chỉ ngày đã đóng; xác minh provider timestamp trước |
| Normalizer | Causal q05/q95, 1.460 ngày lịch, tối thiểu 365 raw observations |
| Weights | Nhóm giá 50%, định giá 50%; không cộng NUPL thành phiếu mới |
| Thiếu input | Core null, giữ last valid có ngày/stale rõ ràng |
| Lịch sử | Reconstructed lúc backfill; as_published chỉ từ lúc vận hành |
| Tech | Python batch + React/TypeScript; JSON tĩnh có manifest |
| Dữ liệu trả phí | Chưa chọn và chưa mua; không chặn Core nếu Community đủ |
| Giao diện | Tiếng Việt trước, cấu trúc tương tự CBBI, tên/nhận diện riêng |
| Phạm vi hiện tại | Trang giới thiệu đã chạy tại `eco.tnmp.cloud`; engine/dashboard chưa triển khai |

## 4. Backlog thực thi

Trạng thái hợp lệ: `TODO`, `IN_PROGRESS`, `BLOCKED`, `DONE`, `REJECTED`. `REJECTED` cho ý tưởng nghiên cứu bị loại có lý do; `BLOCKED` cần ghi dependency còn thiếu và công việc độc lập tiếp theo.

### P0 — dữ liệu và khóa nghiên cứu

| ID | Trạng thái | Dependency | Công việc / đầu ra | Nghiệm thu |
|---|---|---|---|---|
| R00 | DONE | — | Nghiên cứu sơ bộ và bộ Markdown | Có bằng chứng live probe, upstream SHA và bàn giao |
| D01 | TODO | R00 | Probe capability từng metric; lưu raw response, request metadata/hash, report | Xác nhận đúng ETH/1d; phân biệt 403 với missing data; không log key |
| D02 | TODO | R00 | Đọc timestamp, lag, revision và điều khoản provider; `docs/data-contract.md`, `docs/data-rights.md` | Ánh xạ thời gian cụ thể; biết quyền research/public chart/derived/export và phần chưa rõ |
| D03 | TODO | D01,D02 | Tải toàn lịch sử 4 input; report gaps, invalid, duplicates, first/last valid | Snapshot hash + range; không coi mẫu probe là full audit; source period mapping đã chốt |
| D04 | TODO | D03 | Khóa Core config và protocol research; ADR-001 | Thông số mục 4, split, label, baseline và tiêu chí được ghi trước khi xem kết quả |
| D05 | TODO | D01,D02 | Audit nguồn cho E3/E4/E8/E9, báo cáo khả thi 9 vị trí | Mỗi vị trí có endpoint/plan/rights/history hoặc lý do không khả thi; không cần mua để lập report |

**Gate G0:** Core inputs có lịch sử hữu dụng, timestamps và quyền nghiên cứu rõ; chốt giới hạn. D05 không chặn Core nhưng phải hoàn tất trước tuyên bố có kế hoạch dữ liệu đầy đủ cho cả 9 metric.

### P1 — nền dự án và pipeline

| ID | Trạng thái | Dependency | Công việc / đầu ra | Nghiệm thu |
|---|---|---|---|---|
| S01 | IN_PROGRESS | R00 | Init cấu trúc dự án, Git nếu chưa có, lockfile, lint/test, `.gitignore`, `.env.example` | Lệnh setup Windows và Linux được thử; chưa commit dữ liệu riêng hoặc secret |
| S02 | TODO | D03,S01 | Coin Metrics adapter với pagination, retry và cache raw | Fixtures 200/403/429/schema mismatch; backfill không mất/trùng ngày |
| S03 | TODO | S02,D02 | Canonical schema và quality validation | Date/period_end đúng; negative/zero/null có reason; lưu provenance |
| S04 | TODO | S03 | Incremental update và revision store | Chạy hai lần idempotent; đổi raw input tạo revision, không ghi đè vintage |

**Gate G1:** từ snapshot dựng được cùng canonical dataset, checksum và quality report. Live source fail không phá snapshot hợp lệ cũ.

### P2 — engine toán học

| ID | Trạng thái | Dependency | Công việc / đầu ra | Nghiệm thu |
|---|---|---|---|---|
| M01 | TODO | D04,S03 | E1/E5 raw functions | Rolling đúng ngày lịch, đủ warm-up, fixture tính tay |
| M02 | TODO | D04,S03 | E6 causal log trend | Fit chỉ `u<t`, ngày gốc khóa, prefix invariance |
| M03 | TODO | D04,S03 | E7 và E2 diagnostic | R=M/V có provenance; sigma quá khứ; E2 không được tính vào Core |
| M04 | TODO | M01,M02,M03 | Causal normalizer và configuration version | q05/q95 đúng cửa sổ, min observations, clipping/null/degenerate tests |
| M05 | TODO | M04 | Group composite và custom aggregation | 4/4 policy, weights, empty selection, fixture trung bình |
| M06 | TODO | M05,S04 | Replay theo ngày và audit không nhìn tương lai | Same snapshot + same version tái lập; future append không đổi prefix |

**Gate G2:** engine đúng công thức và không rò rỉ thời gian trong tính toán. Gate này chưa chứng minh chỉ số dự báo hữu ích.

### P3 — kiểm định

| ID | Trạng thái | Dependency | Công việc / đầu ra | Nghiệm thu |
|---|---|---|---|---|
| Q01 | TODO | D04,M06 | Walk-forward harness, labels, purge/embargo | Chỉ đánh giá label hoàn tất; split và periods rõ; không random shuffle |
| Q02 | TODO | Q01 | Báo cáo Core, baselines, correlation, ablation, regime analysis | Kết quả có uncertainty và giới hạn dữ liệu revised; không chỉ đưa chart đẹp |
| Q03 | TODO | Q02 | Quyết định Experimental / cần sửa, ADR-002 | Lý do dựa evidence; nếu đổi model thì version mới, không lặp chọn trên cùng holdout |
| Q04 | TODO | D05,Q02 | Nghiên cứu ứng viên mở rộng theo protocol riêng | Công thức và source đủ rõ mới code; kết quả nhận/loại từng metric |

**Gate G3:** báo cáo giải thích được điều chỉ số đo, điều chưa đo và mức phát hành phù hợp. Không ép kết quả đạt bằng việc chọn lại các đỉnh.

### P4 — dữ liệu public và giao diện

| ID | Trạng thái | Dependency | Công việc / đầu ra | Nghiệm thu |
|---|---|---|---|---|
| A01 | TODO | M05,D02 | JSON Schema, manifest, history/latest/methodology và export contract | null/status/version thống nhất; chỉ dữ liệu được phép công khai |
| U01 | TODO | R00 | UI audit CBBI và wireframe ETH | Có ảnh/ghi nhận chức năng thực, responsive, danh sách khác biệt có lý do |
| U02 | TODO | U01,A01 | Dashboard bằng fixture rõ nhãn | Hero, charts, metric cards, trạng thái lỗi; không giả fixture là live |
| U03 | TODO | U02,M06 | Tích hợp dữ liệu thật và custom mode | Toggle đúng toàn lịch sử; ngày hover và điểm gần nhất không lẫn |
| U04 | TODO | U03,Q03 | Methodology/FAQ, CSV, accessibility, responsive | UI/JSON/CSV khớp; 360/768/1440px; keyboard và null gaps đúng |

**Gate G4:** người dùng hiểu được điểm, nguồn, ngày, version, custom mode và tình trạng dữ liệu; không có số giả được trình bày như chỉ số thật.

### P5/P6 — vận hành và phát hành

| ID | Trạng thái | Dependency | Công việc / đầu ra | Nghiệm thu |
|---|---|---|---|---|
| O01 | TODO | S04,A01 | Atomic release publisher, checksums, release pointer | Gián đoạn upload không sinh mixed-version; rollback bằng pointer |
| O02 | TODO | O01,M06 | CI và scheduled batch theo hosting thực | Logs không secret; retry hữu hạn; freshness status độc lập score record |
| O03 | TODO | O02,U04 | Runbook, backup và fault drills | Thử provider outage, missing day, bad payload, rollback và restore |
| O04 | TODO | O03 | Chạy shadow >=30 ngày, lưu as_published | Báo cáo đủ scheduled/actual runs, lag, incidents; không tự coi 30 ngày là chứng minh mô hình |
| O05 | TODO | O04,Q03,D02 | Chuẩn bị release: tên/domain/mục đích sử dụng/rights | Checklist rõ; bản build review được; xử lý phần cần quyết định ở bước phát hành |
| O06 | TODO | O05 | Phát hành khi người dùng đã yêu cầu/cho phép; verification sau phát hành | URL hoạt động, version đúng, nguồn/giới hạn công khai; cập nhật bàn giao |

**Gate G6:** ứng dụng vận hành và dữ liệu trung thực; nếu E3/E8 hoặc metric khác chưa đạt thì công bố đúng phạm vi Core, không ghi “bản ETH giống hệt 9 metric của CBBI”.

## 5. Lệnh CLI mục tiêu — chưa tồn tại

Các lệnh dưới đây là giao diện đề xuất cho agent triển khai, **chưa chạy được ở trạng thái hiện tại**. S01 phải tạo package/entry point trước, sau đó thay phần này bằng lệnh thực tế đã xác minh.

```text
uv sync --frozen
uv run eth-cycle data audit --asset eth --provider coinmetrics
uv run eth-cycle data backfill --asset eth --start 2015-08-01
uv run eth-cycle compute --methodology core-v0.1.0 --snapshot <snapshot-id>
uv run eth-cycle research walk-forward --config configs/research/core-v0.1.yaml
uv run eth-cycle export --run <run-id> --output public-data/releases/<release-id>
uv run pytest
uv run ruff check .
```

`--frozen` chỉ có ý nghĩa sau khi S01 tạo lockfile hợp lệ. Không dán nguyên placeholder `<...>` vào shell; thay bằng ID thực. Lệnh web/build sẽ bổ sung sau khi scaffold theo môi trường triển khai được chọn.

## 6. Kiểm tra đã thực hiện trong phiên lập kế hoạch

| Việc | Kết quả | Không được suy rộng thành |
|---|---|---|
| Liệt kê workspace, kiểm tra `.codegraph` và Git | Workspace ban đầu trống, không graph/Git | Project đã bootstrap |
| Đọc website/FAQ/repo và GitHub tree | Có nguồn + commit xác định | Đã chạy thuật toán CBBI |
| HTTP probe bộ Core ở vài ngày | HTTP 200, có 4 input | Full history đã sạch và đầy đủ |
| HTTP probe CapRealUSD/FeeTotUSD | HTTP 403 cho trường tương ứng | Không có bất kỳ nguồn khác |
| Viết/đọc lại Markdown, kiểm tra liên kết local | Được kiểm tra ở cuối phiên | Tests sản phẩm hoặc backtest đã pass |

## 7. Quyết định chờ đến đúng giai đoạn

1. Mục đích phi thương mại hay thương mại: ảnh hưởng quyền dữ liệu, cần chốt trước public release; chưa cản việc nghiên cứu local theo điều khoản phù hợp.
2. Ngân sách provider trả phí: chỉ hỏi sau khi D05 cung cấp metric cụ thể, coverage, quyền và báo giá thực.
3. Trang giới thiệu hiện dùng tên ECO, repo `tnmjsc-hue/eco`, Cloudflare Pages và domain `eco.tnmp.cloud`. Tên của chỉ số chính thức vẫn cần chốt trước release dữ liệu; việc có domain không chứng minh đã đạt gate dữ liệu/phương pháp.
4. Mục tiêu tuyệt đối đủ 9 card hoạt động hay bộ metric ít hơn nhưng tốt hơn: mặc định tiếp tục nghiên cứu 9 vị trí, không nhượng bộ tính đúng để đủ số. Nếu có metric bất khả thi, trình evidence và đề xuất thay thế.

## 8. Prompt cho agent kế tiếp

```text
Tiếp tục triển khai dự án ETH Cycle Index trong workspace này.
Đọc AGENTS.md, README.md, docs/MASTER_PLAN.md, docs/RESEARCH.md, docs/HANDOFF.md và docs/DEPLOYMENT.md.
Kiểm tra trạng thái thực tế trước khi làm. Bắt đầu task TODO đầu tiên đã đủ dependency.
Hiện có trang giới thiệu công khai, chưa có engine/dashboard hoặc full dataset; ưu tiên D01/D02/D03 và hoàn tất S01.
Giữ phạm vi Core E1/E5/E6/E7, daily UTC, causal normalization và provenance có version.
Không dùng dữ liệu giả cho chỉ số thật; không gọi score là xác suất; không dùng BTC thay ETH.
Website được phép tự deploy sau khi code và kiểm tra theo docs/DEPLOYMENT.md. Không tự mua dịch vụ hoặc công bố điểm ETH/dữ liệu khi các gate chưa đạt.
Kết thúc bằng cập nhật trạng thái task, bằng chứng kiểm tra và bước tiếp theo trong HANDOFF.md.
```

## 9. Mẫu nhật ký mỗi phiên

```text
Ngày / người hoặc agent:
Task ID và trạng thái trước → sau:
File đã thay đổi:
Methodology version / data snapshot / code commit:
Lệnh đã chạy và kết quả thực tế:
Kết quả có thể kiểm chứng:
Quyết định mới / lý do / ảnh hưởng lịch sử:
Trở ngại và dependency:
Task tiếp theo:
```

### Nhật ký 2026-09-29 — phiên lập kế hoạch

- R00: DONE. Các task triển khai: TODO.
- Tạo `README.md`, `AGENTS.md`, `docs/MASTER_PLAN.md`, `docs/RESEARCH.md`, `docs/HANDOFF.md`.
- Kết quả: kế hoạch phương pháp, kiến trúc, roadmap, tiêu chí nghiệm thu và bằng chứng khả thi sơ bộ của dữ liệu Core.
- Phiên bản tham chiếu upstream: `efd6dcf08b9b8619c63b8669dee0990b4f076aac`; chưa có code commit của dự án.
- Không chạy test sản phẩm vì chưa có mã nguồn. Không có snapshot dataset đầy đủ hoặc điểm ETH để bàn giao.
- Tiếp theo: D01/D02, rồi D03; dùng S01 ở mức tối thiểu khi cần môi trường audit.

### Nhật ký 2026-10-02 — hướng dẫn kết nối GitHub và Cloudflare

- Yêu cầu phiên này: hướng dẫn dùng repo `tnmjsc-hue/eco` và Cloudflare Free để phục vụ `eco.tnmp.cloud`; chưa yêu cầu triển khai ứng dụng hoặc phát hành website. Trạng thái backlog không đổi.
- File sửa: `docs/HANDOFF.md`. Chưa có `methodology_version`, snapshot dữ liệu hoặc code commit mới.
- Kiểm tra thực tế: `git status --short --branch` tại `E:\ETH-CBBI` báo không phải Git repository; `.codegraph/` không tồn tại; GitHub hiển thị `tnmjsc-hue/eco` là repo public trống. `Resolve-DnsName tnmp.cloud -Type NS` trả `gina.ns.cloudflare.com` và `jeff.ns.cloudflare.com`; truy vấn công khai cho `eco.tnmp.cloud` chưa trả CNAME/A trong phiên.
- Đã đọc tài liệu Cloudflare Pages về Git integration, build static HTML, custom domain và giới hạn Free (tài liệu cập nhật 2026). Hướng dẫn đề xuất tạo một `public/index.html` tối thiểu, kết nối Pages với branch `main`, output `public`, kiểm tra `*.pages.dev`, rồi thêm custom domain trong Pages để Cloudflare tự tạo CNAME cho zone đang quản lý.
- Giới hạn: chưa đăng nhập hoặc thay đổi tài khoản GitHub/Cloudflare của người dùng; chưa tạo site, DNS record, build hay chạy test sản phẩm. Chưa xác minh quyền dữ liệu để công bố dashboard ETH.
- Bước kế tiếp của dự án vẫn là D01/D02, sau đó D03; nếu người dùng yêu cầu dựng website, bắt đầu từ nội dung có nhãn rõ và tuân thủ gate phát hành trong kế hoạch.

### Nhật ký 2026-10-03 — hướng dẫn quyền API và lưu credential

- Yêu cầu phiên này: hướng dẫn lấy credential GitHub/Cloudflare để dùng về sau. Không có token nào được người dùng cung cấp trong phiên; không tạo, kiểm tra, lưu hay sử dụng secret.
- File sửa: `docs/HANDOFF.md`. Backlog và methodology/data version không đổi.
- Đã đối chiếu tài liệu chính thức: GitHub khuyên dùng GitHub CLI/Git Credential Manager hoặc fine-grained PAT; Cloudflare Pages Git integration dùng GitHub App qua trình duyệt; Cloudflare API dùng token giới hạn Account Pages và/hoặc Zone DNS thay cho Global API Key.
- Quyết định: kết nối Pages qua giao diện không cần người dùng cung cấp API token. Nếu cần tự động hóa, chỉ yêu cầu token đúng tác vụ và lưu ngoài repo, mã hóa theo tài khoản Windows; không gửi token qua chat và không commit vào Git.
- Kiểm tra sản phẩm: không chạy vì chưa có app, repo local, token hay pipeline. Task dự án tiếp theo vẫn D01/D02 rồi D03.

### Nhật ký 2026-10-03 — xác nhận credential Cloudflare Pages local

- Người dùng đã tự lưu token Cloudflare Pages vào `%APPDATA%\ETH-CBBI\cloudflare-pages.dpapi` bằng PowerShell, ngoài workspace và Git repository.
- Chỉ kiểm tra sự tồn tại, kích thước file và khả năng `ConvertTo-SecureString` bằng cùng tài khoản Windows; kết quả `VALID_ENCRYPTED_FILE bytes=654`. Lần kiểm tra đầu với nội dung chưa `Trim()` báo `CANNOT_DECRYPT` do ký tự xuống dòng từ `Set-Content`; kiểm tra sau khi `Trim()` thành công.
- Không đọc token ra chuỗi thường, không in token, không gọi Cloudflare API, không lưu secret vào tài liệu. Chưa xác nhận token có quyền Pages hay còn hiệu lực; chỉ xác nhận định dạng lưu trữ local.
- Task dự án tiếp theo vẫn D01/D02 rồi D03. Khi thật sự cần dùng API, giải mã trong tiến trình và kiểm tra quyền bằng endpoint phù hợp mà không đưa giá trị token vào log.

### Nhật ký 2026-10-03 — triển khai trang giới thiệu ECO

- Yêu cầu: kiểm tra và triển khai website từ GitHub lên `eco.tnmp.cloud`. Đây là trang giới thiệu dự án, không phải dashboard chỉ số ETH; O06 của sản phẩm chỉ số vẫn TODO. S01 chuyển `TODO` → `IN_PROGRESS` vì đã khởi tạo Git và `.gitignore`, nhưng chưa có lockfile/lint/test/`.env.example` và chưa thể đánh dấu DONE.
- File tạo/sửa trong workspace: `.gitignore`, `public/index.html`, `public/styles.css`, `public/favicon.svg`, `README.md`, `docs/HANDOFF.md`. Chỉ `.gitignore` và `public/*` được commit/push lên repo public; tài liệu kế hoạch vẫn local, untracked.
- Git remote: `https://github.com/tnmjsc-hue/eco.git`; branch `main`; commit đầu `906e579` (landing page), commit cập nhật `0e7cce0` (sửa nhãn liên kết mã nguồn). `git push origin main` thành công; `git ls-remote origin refs/heads/main` xác nhận commit đầu, sau đó GitHub UI và Cloudflare ghi nhận commit mới.
- Cloudflare Pages account ID do người dùng cung cấp; project `eco-tnmp`, GitHub source `tnmjsc-hue/eco`, production branch `main`, framework `None`, build command trống, build output `public`. Pages build và deploy hai commit `906e579` và `0e7cce0` đều `success`/`production` theo Pages API. Pages hostname `eco-tnmp.pages.dev`.
- Trong Pages Custom domains, đã kích hoạt `eco.tnmp.cloud`. Cloudflare DNS hiển thị CNAME `eco.tnmp.cloud → eco-tnmp.pages.dev`, Proxied, TTL Auto. Sau `Check DNS records`, Pages UI hiển thị `Active` và `SSL enabled`.
- Kiểm tra HTTP thực tế: `https://eco-tnmp.pages.dev/` trả 200; `https://eco.tnmp.cloud/` trả 200, title `ECO — Nghiên cứu chu kỳ Ethereum`, có thông báo chưa có điểm ECO. Sau commit thứ hai, Pages API xác nhận deploy thành công; lần truy cập custom domain đầu còn nội dung cũ ngắn hạn, lần kiểm tra lại sau khoảng 10 giây đã hiển thị nhãn mới `Theo dõi mã nguồn website`. Đã mở và kiểm tra trực quan desktop qua trình duyệt.
- Bảo mật/dữ liệu: token Pages local chỉ dùng trong tiến trình để verify/list API, không in hoặc commit. Không có dataset, `methodology_version`, điểm ETH, backtest hay secret trong trang public. Minh họa biểu đồ được ghi rõ không phải dữ liệu ETH thực.
- Trở ngại: `python` CLI không có trong PATH, nên không chạy local HTTP server; không có test engine vì engine chưa tồn tại. Tiếp theo: D01/D02 để audit nguồn ETH, rồi D03; hoàn tất S01 khi có pipeline và lockfile thực tế.

### Nhật ký 2026-10-03 — runbook tự triển khai cho agent sau

- Yêu cầu: ghi Markdown để agent sau khi hoàn thành code có thể tự triển khai website lên `eco.tnmp.cloud`. Đã tạo `docs/DEPLOYMENT.md` với cấu hình thực tế, quy trình push `main`, điều kiện kiểm tra, cách xác minh Pages/domain, credential và rollback; cập nhật `AGENTS.md`, `README.md`, `docs/MASTER_PLAN.md`, `docs/HANDOFF.md` để trỏ tới runbook và phản ánh quyền deploy mới. Không thay đổi code trang trong phiên này.
- Quyết định: người dùng đã cho phép deploy website thông thường sau khi code và kiểm tra, không cần hỏi lại về thao tác Git/Pages. Quyền này không bỏ qua D02, Q03, O05 và các gate liên quan trước khi công bố điểm ETH/dữ liệu thật; lý do là trang public đã chạy nhưng engine, data rights và kiểm định chưa xong. Không ảnh hưởng lịch sử điểm vì chưa có điểm nào được công bố.
- Kiểm tra thực tế: `.codegraph/` vắng; `git status --short --branch` trước sửa là `main...origin/main`, tài liệu còn untracked; quét các file định commit theo mẫu token/account ID không trả file; `git diff --cached --check` không báo lỗi; kiểm tra link Markdown nội bộ trả `LOCAL_MARKDOWN_LINKS_OK`.
- Commit tài liệu `eef2f48dcc3778d17cd6e5a8a967b1c22f4ac06d` đã push lên `origin/main`. Pages API trả `success`/`deploy`/`production` cho commit `eef2f48`; `git ls-remote origin refs/heads/main` trả đúng SHA. `https://eco.tnmp.cloud/` trả HTTP 200, title ECO và thông báo chưa có điểm. Không có `methodology_version`, data snapshot hoặc test engine mới.
- Task dự án kế tiếp vẫn D01/D02 rồi D03; S01 còn `IN_PROGRESS`. Khi code website thay đổi, agent dùng `docs/DEPLOYMENT.md` và cập nhật cấu hình Pages nếu output không còn là `public`.

### Nhật ký 2026-10-03 — kết nối lưu trữ Cloudflare

- Yêu cầu: kiểm tra Cloudflare có nơi lưu dữ liệu và kết nối cho ECO. Đã tạo R2 bucket `eco-eth-private`, lớp Standard, `Public Access: Disabled`; bucket `storage` có sẵn không bị sửa. Đã tạo token `eco-eth-snapshot-pipeline` quyền Object Read & Write chỉ trên bucket này, hạn đến 2027-10-03, theo đồng ý cụ thể của người dùng.
- Hai khóa S3 lưu mã hóa DPAPI ngoài repo tại `%APPDATA%\ETH-CBBI\r2-access-key-id.dpapi` và `r2-secret-access-key.dpapi`. Không in/commit khóa. Đã dùng boto3 cài tạm ngoài repo để `PutObject`, `GetObject` so khớp byte và `DeleteObject` một object kiểm tra không nhạy cảm; kết quả `R2_PUT_GET_OK` và `R2_TEST_OBJECT_DELETED`.
- File sửa/tạo: `docs/STORAGE.md`, `public/data/status.json`, `README.md`, `AGENTS.md`, `docs/DEPLOYMENT.md`, `docs/HANDOFF.md`. JSON trạng thái chỉ ghi `score_available=false`, `data_release_available=false`; không có điểm ETH, dataset hay `methodology_version` mới.
- Quyết định: Pages tiếp tục phát JSON công khai đã qua gate; R2 riêng tư giữ raw snapshots khi pipeline có. D1/KV chưa cần cho web tĩnh một chỉ số ngày. Không bind bucket raw vào Pages Functions vì sẽ mở thêm đường truy cập dữ liệu riêng tư. Lựa chọn khác: D1 cho query động hoặc KV cho trạng thái nhỏ, xem lại khi có yêu cầu cụ thể. Không ảnh hưởng lịch sử điểm vì chưa phát hành điểm nào.
- Chưa có runner/pipeline snapshot, backup/restore thực tế hoặc lịch batch. Task tiếp theo của dự án: D01/D02 rồi D03; S01 vẫn IN_PROGRESS.
