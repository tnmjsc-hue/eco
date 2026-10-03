# Bàn giao triển khai ETH Cycle Index

**Cập nhật: 2026-10-03.** Trạng thái: **CORE_ENGINE_TESTED / EXPERIMENTAL_DASHBOARD_VERIFIED / DAILY_BATCH_READY_FOR_HOSTED_VERIFICATION**. Điểm tại phiên bàn giao 41.379812239861 ngày 2026-10-01; ngày 2026-10-02 còn thiếu MVRV. Không phải sản phẩm vận hành realtime hoàn chỉnh.

Tài liệu chuẩn: [MASTER_PLAN.md](MASTER_PLAN.md). Bằng chứng nghiên cứu: [RESEARCH.md](RESEARCH.md). Triển khai web: [DEPLOYMENT.md](DEPLOYMENT.md). Quy tắc agent: [AGENTS.md](../AGENTS.md).

## 1. Đã hoàn thành và chưa hoàn thành

Đã đọc website/FAQ/một số file engine chính thức của CBBI; chốt SHA tham chiếu; kiểm tra workspace; thử một số truy vấn dữ liệu ETH thật; viết bộ kế hoạch và checklist tiếp tục.

**Có engine Python, lockfile web, 28 test Python + 5 test Node, primary backtest khóa trước và dashboard ETH với score thật.** Lịch sử là reconstructed; Core không đạt success rule so với tất cả baseline. Daily batch đã implement, thử fetch/R2 thật và local browser auto-refresh; hosted workflow/deploy cần xác minh ở nhật ký cuối phiên. Snapshot/release bất biến, revision/first-publication store riêng. Scope phi thương mại theo [ADR-002](ADR-002-experimental-research-preview.md). Network incremental, prospective history/shadow 30 ngày và restore drill chưa hoàn tất. Không mua API trả phí, không có agent khác.

## 2. Bắt đầu từ đâu

Khi tiếp tục, kiểm tra Git/deploy, workflow daily enabled và `/data/status.json`. Xem [DAILY_UPDATES](DAILY_UPDATES.md) trước thao tác scheduler. Tiếp theo S04 tối ưu network incremental có full audit/restore, O03 fault+restore drills, O04 shadow; Q02 correlation/ablation/regime, Q04 protocol mở rộng. Không đổi weights trên cùng holdout để ép kết quả.

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
| Tech | Python batch + static ES modules/ECharts/Lucide; JSON tĩnh có manifest, ADR-002 |
| Dữ liệu trả phí | Chưa chọn và chưa mua; không chặn Core nếu Community đủ |
| Giao diện | Tiếng Việt trước, cấu trúc tương tự CBBI, tên/nhận diện riêng |
| Phạm vi hiện tại | Dashboard Core reconstructed Experimental; gate sản phẩm vận hành còn riêng |

## 4. Backlog thực thi

Trạng thái hợp lệ: `TODO`, `IN_PROGRESS`, `BLOCKED`, `DONE`, `REJECTED`. `REJECTED` cho ý tưởng nghiên cứu bị loại có lý do; `BLOCKED` cần ghi dependency còn thiếu và công việc độc lập tiếp theo.

### P0 — dữ liệu và khóa nghiên cứu

| ID | Trạng thái | Dependency | Công việc / đầu ra | Nghiệm thu |
|---|---|---|---|---|
| R00 | DONE | — | Nghiên cứu sơ bộ và bộ Markdown | Có bằng chứng live probe, upstream SHA và bàn giao |
| D01 | DONE | R00 | Probe capability từng metric; lưu raw response, request metadata/hash, report | Probe mẫu đúng ETH/1d; phân biệt HTTP access error với payload không có dữ liệu; không log key |
| D02 | DONE | R00 | Chốt diễn giải nhãn/ngày UTC và ranh giới quyền Coin Metrics; `docs/data-contract.md`, `docs/data-rights.md` | Period mapping có nguồn chính thức; research local được giữ riêng tư; quyền public/derived/export/commercial và vintage lịch sử được nêu rõ là chưa xác nhận |
| D03 | DONE | D01,D02 | Tải toàn lịch sử 4 input; report gaps, invalid, duplicates, first/last valid | Snapshot hash + range; report kiểm tra được; không công khai raw; mapping kỳ đã chốt |
| D04 | DONE | D03 | Khóa Core config và protocol research; ADR-001, machine validation | Invariants công thức/normalizer/label/test/baseline/bootstrap/success được code-validated trước backtest; chưa tuyên bố engine/backtest đã chạy |
| D05 | DONE | D01,D02 | Audit nguồn cho E3/E4/E8/E9; report và JSON register 9 vị trí | E1-E9 có source, coverage/evidence, rights, vintage và quyết định; unknown được ghi rõ, không cần mua để lập report |

**Gate G0:** Core inputs có lịch sử hữu dụng, timestamps và quyền nghiên cứu rõ; chốt giới hạn. D05 không chặn Core nhưng phải hoàn tất trước tuyên bố có kế hoạch dữ liệu đầy đủ cho cả 9 metric.

### P1 — nền dự án và pipeline

| ID | Trạng thái | Dependency | Công việc / đầu ra | Nghiệm thu |
|---|---|---|---|---|
| S01 | DONE | R00 | Cấu trúc Python/web, Git, lockfile, syntax/tests, ignores/env names | Setup/test/build Windows + Ubuntu CI thực tế đạt; staged hash/secret scan sạch |
| S02 | DONE | D03,S01 | Coin Metrics adapter với pagination, retry và cache raw | Fixtures 200/403/429/500/network/schema/pagination/duplicate/wrong ETH; full fetch live 4081 rows không mất/trùng ngày |
| S03 | DONE | S02,D02 | Canonical schema và quality validation | Offline loader + adapter kiểm hash/schema/calendar/closed-day/provenance; missing/null được giữ đúng |
| S04 | IN_PROGRESS | S03 | Incremental update và revision store | Daily release diff/idempotency/revision; network incremental còn tách riêng |

**Gate G1:** từ snapshot dựng được cùng canonical dataset, checksum và quality report. Live source fail không phá snapshot hợp lệ cũ.

### P2 — engine toán học

| ID | Trạng thái | Dependency | Công việc / đầu ra | Nghiệm thu |
|---|---|---|---|---|
| M01 | DONE | D04,S03 | E1/E5 raw functions | Fixture SMA tính tay, gap ngày lịch và warm-up đạt trên offline D03 |
| M02 | DONE | D04,S03 | E6 causal log trend | OLS so NumPy, fit chỉ u<t, gốc cố định và prefix đạt |
| M03 | DONE | D04,S03 | E7 và E2 diagnostic | R=M/V, population std toàn quá khứ; E2 không bỏ phiếu, tests đạt |
| M04 | DONE | M01,M02,M03 | Causal normalizer và configuration version | q05/q95 linear, ngày biên, min obs, clipping/null/degenerate đạt |
| M05 | DONE | M04 | Group composite và custom aggregation | 4/4, weights, empty/invalid/missing và custom toàn chuỗi đạt |
| M06 | IN_PROGRESS | M05,S04 | Replay theo ngày và audit không nhìn tương lai | Offline replay/prefix/future shock đã đạt; vận hành incremental/vintage S04 chưa có |

**Gate G2:** engine đúng công thức và không rò rỉ thời gian trong tính toán. Gate này chưa chứng minh chỉ số dự báo hữu ích.

### P3 — kiểm định

| ID | Trạng thái | Dependency | Công việc / đầu ra | Nghiệm thu |
|---|---|---|---|---|
| Q01 | DONE | D04,M06 | Primary evaluation harness, future-drawdown labels và calendar-year stability folds | Offline reconstructed evaluation 2101 ngày, 10000 bootstrap cùng ngày/baseline; future-label tests đạt |
| Q02 | IN_PROGRESS | Q01 | Báo cáo Core, baselines, correlation, ablation, regime analysis | Primary report + CI/folds/sensitivity đã có; correlation/ablation/regime mở rộng chưa làm |
| Q03 | DONE | Q02 | Quyết định Experimental / cần sửa, ADR-002 | Preview nghiên cứu; chưa chứng minh incremental utility; không đổi model/holdout, không thay gate vận hành |
| Q04 | TODO | D05,Q02 | Nghiên cứu ứng viên mở rộng theo protocol riêng | Công thức và source đủ rõ mới code; kết quả nhận/loại từng metric |

**Gate G3:** báo cáo giải thích được điều chỉ số đo, điều chưa đo và mức phát hành phù hợp. Không ép kết quả đạt bằng việc chọn lại các đỉnh.

### P4 — dữ liệu public và giao diện

| ID | Trạng thái | Dependency | Công việc / đầu ra | Nghiệm thu |
|---|---|---|---|---|
| A01 | DONE | M05,D02 | JSON Schema, manifest, history/latest/methodology và export contract | Schema 1.0.0, hash/pointer/version/null; CSV có provenance/licence; scope phi thương mại |
| U01 | TODO | R00 | UI audit CBBI và wireframe ETH | Có ảnh/ghi nhận chức năng thực, responsive, danh sách khác biệt có lý do |
| U02 | DONE | U01,A01 | Dashboard nghiên cứu | Thay intro bằng app thật, không mock/fixture live; chart/null/error states được kiểm browser |
| U03 | DONE | U02,M06 | Tích hợp dữ liệu thật và custom mode | Reconstructed snapshot; custom toàn 366 ngày so engine; selected date/nearest/null kiểm trực tiếp |
| U04 | DONE | U03,Q03 | Methodology/CSV/accessibility/responsive | 360/390/768/1440 không overflow; semantic controls, UI/JSON/CSV khớp; chưa audit accessibility bằng screen reader |

**Gate G4:** người dùng hiểu được điểm, nguồn, ngày, version, custom mode và tình trạng dữ liệu; không có số giả được trình bày như chỉ số thật.

### P5/P6 — vận hành và phát hành

| ID | Trạng thái | Dependency | Công việc / đầu ra | Nghiệm thu |
|---|---|---|---|---|
| O01 | IN_PROGRESS | S04,A01 | Atomic release publisher, checksums, release pointer | Local publisher/immutable allowlist/hash/pointer tests đạt; fault/rollback drill và incremental còn thiếu |
| O02 | IN_PROGRESS | O01,M06 | CI và scheduled batch theo hosting thực | Daily workflow + repo Secrets + main deploy hook đã cấu hình; chờ hosted run/build/domain checksum verification |
| O03 | TODO | O02,U04 | Runbook, backup và fault drills | Thử provider outage, missing day, bad payload, rollback và restore |
| O04 | TODO | O03 | Chạy shadow >=30 ngày, lưu as_published | Báo cáo đủ scheduled/actual runs, lag, incidents; không tự coi 30 ngày là chứng minh mô hình |
| O05 | TODO | O04,Q03,D02 | Chuẩn bị release: tên/domain/mục đích sử dụng/rights | Checklist rõ; bản build review được; xử lý phần cần quyết định ở bước phát hành |
| O06 | TODO | O05 | Phát hành khi người dùng đã yêu cầu/cho phép; verification sau phát hành | URL hoạt động, version đúng, nguồn/giới hạn công khai; cập nhật bàn giao |

**Gate G6:** ứng dụng vận hành và dữ liệu trung thực; nếu E3/E8 hoặc metric khác chưa đạt thì công bố đúng phạm vi Core, không ghi “bản ETH giống hệt 9 metric của CBBI”.

## 5. Lệnh CLI thực tế và mục tiêu

Lệnh thực tế đã chạy có trong [README](../README.md): `python -m eco.pipeline compute`, `python -m eco.pipeline publish`, unittest, Node tests, browser QA. Các lệnh `uv/eth-cycle` bên dưới là thiết kế cũ, **vẫn chưa có entry point**; không nhầm với CLI đã implement.

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

### Phiên dashboard 2026-10-03 — trước deploy

- Yêu cầu: hoàn thiện dashboard có score thật trong một phiên; người dùng xác nhận nghiên cứu phi thương mại. Scope/điều chỉnh rights và hosting được ghi ADR-002; không mua API, đổi provider/weights hay giả 9 metric.
- Files: `eco/*`, `tests/*`, `requirements.txt`, package/lockfile/build/browser QA, CI, `.gitattributes`, `.env.example`, `configs/release-policy.json`, `public/index.html/styles.css/app.js/data-model.js/_headers/vendor`, data schema/pointer/status/versioned release; README/AGENTS/DEPLOYMENT/STORAGE/rights/research/report/ADR/HANDOFF.
- Data: D03 canonical SHA-256 `aa78757fcaee33ef23ecf3ebd92791a685df2617f2b3874f5f5183d16babdd03`; release `core-c899a808bda65db96be3`, schema 1.0.0, `core-v0.1.0`, `reconstructed`. 4080 source rows, 4081 calendar rows (1 pending), 2978 scores. Latest 41.379812239861 ngày 2026-10-01. 2026-10-02 chưa đóng tại retrieval UTC, không có score; không sửa manifest/raw cũ.
- Engine: Python 3.12.14 / NumPy 2.3.5, `python -m unittest discover -s tests -v` 19/19 PASS. SMA tính tay/calendar gap, causal OLS so NumPy, population std, linear quantiles/boundary/degenerate, weights/custom/null, prefix/future shock, actual retrieval cutoff, hash/path/schema, rights/allowlist/immutable/idempotent publication đều có tests. Replay 3000 ngày đầu snapshot thật khớp full engine; compute lần hai `idempotent=true`.
- Research: 2101 complete-label days, 10000/10000 bootstrap hợp lệ, AP Core 0.55424872, success=false; report công khai không tuyên bố cải thiện.
- Web: Node 24.19.0, pnpm 11.19.0; install frozen lockfile và build vendor thành công. `node --test tests/web.test.mjs` 3/3 PASS; research artifact validator D04/D05 PASS; syntax PASS. Browser Playwright 1.62.1 + Chrome local: 1440/768/390/360 PASS, không overflow/page errors; chart 43667 nonblank pixels; custom E7 toàn 366 ngày khớp; CSV verified; thiếu nguồn/warm-up/empty selection null; refresh lỗi giữ dataset tốt, retry phục hồi.
- Preview local `http://127.0.0.1:8876/` đang chạy bằng Python HTTP server hidden, PID 30216. Raw/computed/test screenshots bị ignore; versioned public JSON bảo toàn bytes qua `.gitattributes`. Không có token trong frontend/Git.
- Chưa có Linux CI result, production deploy mới hoặc Pages status của commit mới tại thời điểm ghi phần này; phải xác minh sau push trước báo hoàn thành. Scheduler/vintage/shadow/restore/fault drills và Q02 mở rộng vẫn còn.

| Việc | Kết quả | Không được suy rộng thành |
|---|---|---|
| Liệt kê workspace, kiểm tra `.codegraph` và Git | Workspace ban đầu trống, không graph/Git | Project đã bootstrap |
| Đọc website/FAQ/repo và GitHub tree | Có nguồn + commit xác định | Đã chạy thuật toán CBBI |
| HTTP probe bộ Core ở vài ngày | HTTP 200, có 4 input | Full history đã sạch và đầy đủ |
| HTTP probe CapRealUSD/FeeTotUSD | HTTP 403 cho trường tương ứng | Không có bất kỳ nguồn khác |
| Viết/đọc lại Markdown, kiểm tra liên kết local | Được kiểm tra ở cuối phiên | Tests sản phẩm hoặc backtest đã pass |

## 6.1 Chạy lại audit Coin Metrics

Script hiện có: `node scripts/audit-coinmetrics.mjs [as-of-utc-date]`. Chạy 2026-10-03 với Node v24.19.0, không dùng API key; tạo 12 request riêng (4 metric × 3 khoảng) cho `eth` / `1d`. Raw JSON và `manifest.json` nằm trong `data/raw/coinmetrics/` và bị Git ignore.

Kết quả cửa sổ mẫu, không phải full audit: cả 12 request trả HTTP 200 và payload có dữ liệu. 2015-08-01..12: PriceUSD, CapMrktCurUSD và CapMVRVCur có 5 giá trị từ 2015-08-08; SplyCur có 12. 2018-01-01..03: cả bốn có 3 giá trị. Request gần nhất dùng khoảng 2026-09-30..10-02; cả bốn trả 2 dòng từ 2026-09-30 đến 2026-10-01. Các hash response, timestamp request/completion và header đã chọn ở manifest riêng tư `data/raw/coinmetrics/coinmetrics-2026-10-03-2026-10-02T175134924Z/manifest.json`; không commit raw data.

Timestamp response là `00:00:00Z`; tài liệu metric mô tả dữ liệu theo kỳ daily UTC/cuối ngày, nên canonical dùng phần ngày nhãn làm `observation_date` và nửa đêm ngày kế làm biên cuối kỳ mở. Điều này không chứng minh thời điểm availability hoặc lịch sử revision. Tài liệu quyền xác nhận Community non-commercial và archive ghi CC BY-NC 4.0; quyền thương mại/phân phối output ECO chưa được xác nhận. D02 hoàn tất trong phạm vi ghi nhận mapping/giới hạn, không phải quyền phát hành. Chưa có engine, score, `methodology_version` hay backtest.

Lệnh đã chạy: `node --version` → `v24.19.0`; `node scripts/audit-coinmetrics.mjs 2026-10-03` → 12/12 HTTP 200 có payload; `node --check scripts/audit-coinmetrics.mjs` và `git diff --check` sạch; `git check-ignore -v .../manifest.json` xác nhận ignore theo `data/raw/`. Git có cảnh báo line-ending LF→CRLF trên Windows. Không có test engine vì chưa có engine.

### Nhật ký 2026-10-03 — D01 probe, D02 hợp đồng và D03 full-history

- Yêu cầu: kiểm tra tiến độ, hoàn thiện phần đã xác nhận, commit và deploy. Bắt đầu D01/D02 theo backlog; không hiển thị dữ liệu ETH hoặc điểm lên website.
- Đã thêm `scripts/audit-coinmetrics.mjs`, `docs/data-audit.md`, `docs/data-contract.md`, `docs/data-rights.md`; README/HANDOFF ghi lệnh chạy và kết quả. Script dùng Node built-in, probe từng metric riêng ở đầu lịch sử, mốc 2018 và cửa sổ mới nhất; lưu raw/manifest dưới `data/raw/` đã ignore.
- D01: 12/12 HTTP 200, có payload đúng `eth`/`1d`; kết quả cửa sổ và hash xem báo cáo. Đánh dấu `DONE` trong phạm vi probe capability, không phải full audit.
- D02: tài liệu metric chính thức chốt ánh xạ nhãn/ngày UTC và biên kỳ kế tiếp; không chứng minh availability hoặc revision. Quyền research được giới hạn ở audit local/private phi thương mại theo điều khoản; quyền public/derived/export/commercial và retention cần xác nhận. D02 `DONE` chỉ trong phạm vi ghi nhận ranh giới này, không phải cấp quyền phát hành.
- D03: thêm `scripts/backfill-coinmetrics.mjs`; runner phân trang tuần tự, retry 429/5xx/network có giới hạn, kiểm tra host pagination, giữ raw từng trang và tạo canonical JSONL/hash cùng quality report riêng tư. Ngày kết thúc là ngày đóng gần nhất trước `as-of`; không nội suy hoặc lọc raw.
- Dữ liệu/version: Coin Metrics Community API v4, ETH, 1d, bốn input Core, không key. Snapshot local tại `data/raw/coinmetrics/<run-id>/`, bị ignore; chưa có `methodology_version`.
- Kiểm tra: Node v24.19.0; `node --check scripts/backfill-coinmetrics.mjs` pass; `node scripts/backfill-coinmetrics.mjs 2015-08-01 2026-10-03` tải 5 trang/4.080 dòng. Requested 2015-08-01..2026-10-02; response có 4.080 ngày unique 2015-08-01..2026-10-01, thiếu row ngày 2026-10-02; duplicate 0, invalid timestamp 0, invalid numeric 0, zero/negative 0. Không thiếu field. `PriceUSD`, `CapMrktCurUSD`, `CapMVRVCur`: mỗi metric 7 null, first valid 2015-08-08; `SplyCur`: 0 null, first valid 2015-08-01. Tất cả last valid 2026-10-01. Canonical SHA-256 `aa78757fcaee33ef23ecf3ebd92791a685df2617f2b3874f5f5183d16babdd03`; 5 raw page hashes và manifest ở `data/raw/coinmetrics/coinmetrics-backfill-2026-10-03-2026-10-02T182337734Z/`, không commit. `git check-ignore` xác nhận raw bị ignore. Chưa có engine test vì engine chưa tồn tại.
- D03 `DONE` nghĩa là full-history audit có report và snapshot có thể kiểm chứng, không có nghĩa dữ liệu không có gaps hoặc đã phù hợp làm điểm. Thời điểm source availability/vintage không được trả về; quyền phát hành vẫn chưa xác nhận.
- Phát hành: chỉ code/docs/progress status được phát hành, không phát hành dữ liệu ETH. Trước commit xem toàn bộ staged diff và kiểm secret; xác nhận deployment production success và Pages/custom domain HTTP 200. Giữ `score_available=false`, `data_release_available=false`.
- Trở ngại: vintage/availability lịch sử và quyền public/commercial chưa giải quyết. Task sẵn sàng tiếp theo: S01 (tooling/fixtures) và D04 (khóa protocol trước khi xem backtest); D05 vẫn cần đánh giá đủ 9 vị trí. Không trình bày Core như tương đương hoàn chỉnh.

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
Hiện có trang giới thiệu công khai và private full-history audit đã sao lưu R2; chưa có engine/dashboard/score. D01-D05 đã có bằng chứng; task tiếp theo S01/S02/S03 là pipeline, quality tests và cache/private storage integration theo rights gate. Giữ raw riêng tư.
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
- Kiểm tra triển khai: commit `ddb8c7bd57f55bd1cc8e90024c285940ec348e67` đã push lên `main`; Pages API ghi deployment `4ac954e0-1787-4dbe-9af4-7ec117cdfd40` là `production` / `success` cho đúng commit. Cả `https://eco-tnmp.pages.dev/data/status.json` và `https://eco.tnmp.cloud/data/status.json` trả HTTP 200, `Content-Type: application/json`, nội dung `score_available=false` và `data_release_available=false`. Lần truy cập ngay sau push còn trả HTML cũ ngắn hạn; kiểm tra lại sau khi deploy hoàn tất đã trả JSON đúng.
- Lệnh kiểm tra: `ConvertFrom-Json` cho status file, `git diff --cached --check`, quét staged diff theo mẫu credential, boto3 S3 put/get/delete, `Invoke-RestMethod` Pages deployments, `Invoke-WebRequest` cả hai hostname. Không có test engine hoặc data snapshot mới.

### Nhật ký 2026-10-03 — hoàn tất D02 có giới hạn và D03 full-history

- Yêu cầu: tiếp tục code phần đã xác nhận. Chốt cách diễn giải ngày UTC từ tài liệu metric, ghi rõ giới hạn vintage/rights, tải full-history, cập nhật tiến độ công khai nhưng không phát hành raw data hoặc score.
- Thay đổi: thêm `scripts/backfill-coinmetrics.mjs` với pagination tuần tự, retry hữu hạn cho network/429/5xx, kiểm tra pagination host, raw response theo trang, canonical JSONL, SHA-256, nguồn timestamp/hash trang và quality report. Cập nhật `docs/data-contract.md`, `docs/data-rights.md`, `docs/data-audit.md`, `docs/HANDOFF.md`, `public/index.html`, `public/data/status.json`.
- D02: ngày UTC từ nhãn `time` là observation date; `period_end_utc` dùng nửa đêm đầu ngày kế tiếp làm biên kỳ mở. Không suy diễn thời điểm availability/revision. Quyền public display/derived/export/commercial/retention vẫn chưa xác nhận; D02 complete chỉ nghĩa là đã ghi rõ bằng chứng và giới hạn.
- D03: Coin Metrics Community API v4, ETH, 1d, 4 input; 5 trang, 4.080 rows/unique dates từ 2015-08-01 đến 2026-10-01. Requested end 2026-10-02 thiếu một ngày; giữ nguyên gap. Duplicate 0, invalid timestamp/value 0, zero/negative 0. PriceUSD/CapMrktCurUSD/CapMVRVCur có 7 null mỗi metric và first valid 2015-08-08; SplyCur không null và first valid 2015-08-01. Cả bốn last valid 2026-10-01. Không có revision-status field trong response.
- Snapshot riêng tư `data/raw/coinmetrics/coinmetrics-backfill-2026-10-03-2026-10-02T182337734Z/`; canonical SHA-256 `aa78757fcaee33ef23ecf3ebd92791a685df2617f2b3874f5f5183d16babdd03`. Raw + manifest bị `.gitignore`; không stage/commit. Đây là audit hoàn tất, không khẳng định dữ liệu gap-free hoặc được phép công khai.
- Kiểm tra: `node --check scripts/backfill-coinmetrics.mjs`; chạy backfill thành công; `git check-ignore -v` cho manifest; `node -e` parse `public/data/status.json`; `git diff --check` sạch. Chưa có engine nên không có test engine/backtest.
- Trang chủ thể hiện D02/D03 complete có giới hạn, D04/engine vẫn chưa bắt đầu; `score_available=false`, `data_release_available=false`, `methodology_version=null`. Bước tiếp theo: S01 tooling/fixtures và D04 khóa protocol; D05 tiếp tục nghiên cứu các vị trí còn lại trong mục tiêu 9 metric.
- Git/Pages: commit `a2cfcc60e8318c1c6c9f5861fffb3b90ce214cdf` đã push `main`; `git ls-remote origin refs/heads/main` trả cùng SHA. Sau push, Pages hostname và `eco.tnmp.cloud` đều HTTP 200, title ECO và nội dung mới khớp (hero full-history, trạng thái D02/D03, ngày thiếu); `/data/status.json` trên cả hai host ghi D02/D03 complete nhưng `score_available=false`, `data_release_available=false`. Nội dung mới đã được phục vụ trên production. Deployment ID/stage không lấy được từ API credential trong phiên này; không ghi ID hoặc stage suy đoán. Chưa phát hành dataset hoặc score.

### Nhật ký 2026-10-03 — công khai tiến độ D01 trên trang chủ

- Người dùng phản hồi trang chủ chưa có thay đổi nhìn thấy. Nguyên nhân: commit trước chỉ cập nhật tài liệu và script audit, không sửa `public/`.
- Đã cập nhật hero và mục tiến độ để thể hiện D01 probe mẫu đã xong, D02 đang xác minh thời gian/quyền, D03 full-history và engine/dashboard chưa bắt đầu; có link tới báo cáo probe. Thêm `public/progress.css` cho bố cục responsive của danh sách trạng thái.
- `public/data/status.json` công khai metadata tiến độ D01-D03, số request mẫu và cờ sẵn sàng; giữ `score_available=false`, `data_release_available=false`, `methodology_version=null`. Không public raw response hoặc điểm ETH.
- File liên quan được đồng bộ: `docs/DEPLOYMENT.md`, `docs/STORAGE.md`.
- Commit `8bcf69ba7e85f02ac078473ee68a52c769fa9f1c` đã push `main`; Pages deployment `e72d41f9-213e-4c7a-8c3b-900d2a2b4ddb` là `production/success`, đúng commit. `https://e72d41f9.eco-tnmp.pages.dev/`, `https://eco-tnmp.pages.dev/` và `https://eco.tnmp.cloud/` đều trả HTTP 200; kiểm tra nội dung xác nhận hero D01, tiến độ D02, link báo cáo và CSS mới.
- `/progress.css` và `/data/status.json` trả HTTP 200 trên cả ba host. JSON live trả `D01=complete`, `D02=in_progress`, `D03=not_started`, `score_available=false`, `data_release_available=false`, `methodology_version=null`.
- Kiểm tra giao diện bằng trình duyệt tại viewport mặc định và 390×844: hero/progress hiển thị, nội dung xuống dòng đúng, không thấy chồng lấn; đã reset viewport. Kiểm tra cục bộ: `ConvertFrom-Json`, các asset tồn tại, `git diff --check` đều đạt. Không có engine/test engine để chạy.
- Website vẫn là trang giới thiệu và tiến độ nghiên cứu, chưa phải dashboard ETH. Bước tiếp theo của sản phẩm giữ nguyên: hoàn tất D02 trước khi bắt đầu D03; S01 còn `IN_PROGRESS`.

### Nhật ký 2026-10-03 — khóa D04/D05 và chuẩn bị lưu trữ R2

- Yêu cầu: hoàn thiện D04-D05 và chuẩn bị dữ liệu để website gọi nhanh. Không bỏ qua quyền phát hành; raw snapshot phải giữ private.
- D04 `DONE`: thêm [ADR-001](ADR-001-core-research-protocol.md) và `configs/research/core-v0.1.0.json`. Khóa 4 metric Core, công thức/warm-up, q05/q95 causal 1460 ngày, test window/label 365 ngày drawdown, baselines, average precision, paired 90-day block bootstrap và success rule trước khi chạy backtest. Protocol là đặc tả nghiên cứu, chưa có engine hoặc tests xác minh.
- D05 `DONE`: thêm [metric-feasibility.md](metric-feasibility.md) cho E1-E9. `FeeTotNtv` có 3/3 sample rows HTTP 200 và catalog ETH 1d range; `FeeTotUSD`, `TxTfrValAdjUSD`, `SplyAct1yr` trả HTTP 403 trong probe timeseries; catalog vẫn mô tả một số cặp asset/metric. Glassnode docs có RHODL/dormancy endpoints nhưng entitlement và ETH coverage chưa xác minh. Giữ E4 là R&D candidate; không đổi Core hoặc giả đủ 9 metric.
- R2: thêm `scripts/upload-private-snapshot-r2.mjs`, signer S3 SigV4 Node built-in, chỉ nhận complete snapshot dưới `data/raw/coinmetrics`, upload raw+canonical+manifest vào prefix versioned `raw/coinmetrics/<run-id>/`, GET từng object và verify SHA-256; `--dry-run` không upload. Dry-run snapshot D03 liệt kê 7 object, canonical SHA-256 `aa78757fcaee33ef23ecf3ebd92791a685df2617f2b3874f5f5183d16babdd03`.
- Upload thật chưa thực hiện: R2 access/secret keys đã có DPAPI ngoài repo nhưng `R2_ACCOUNT_ID` không có trong repo/environment; API token Pages hiện tại không trả danh sách account. Đã yêu cầu người dùng cung cấp riêng Account ID (không cần secret). Không được ghi “đã lưu cloud” trước khi PUT + GET readback thành công.
- Website: cập nhật progress để D04/D05 hoàn tất, Engine/dashboard chưa bắt đầu, snapshot raw còn local/private; `score_available=false`, `data_release_available=false`. R2 private không được frontend truy cập trực tiếp. Luồng nhanh sau khi qua rights gate: static versioned JSON trong Pages/CDN immutable cache; nếu dùng Worker/Pages Function thì chỉ đọc `public-releases/`, không đọc `raw/`.
- Kiểm tra: D05 live catalog + các sample HTTP statuses đã được chạy và ghi trong báo cáo; `node --check scripts/upload-private-snapshot-r2.mjs` pass; dry-run xác nhận 7 object; JSON config/status parse pass, score/data release gates vẫn false; `git diff --check` sạch. Chưa có test R2 PUT/GET mới vì thiếu Account ID; chưa có tests engine.
- Bước tiếp theo: hoàn tất upload+readback khi có Account ID; sau đó S01-S03 xây pipeline/fixtures/schema và M01-M06 engine theo ADR. Chỉ tạo public data endpoint sau xác nhận quyền, không phát raw snapshot.
- Git/Pages: commit `46bf172f006c3d2001863f231836bf064293d58a` đã push `main`; `git ls-remote` trả cùng SHA. Sau deploy, Pages hostname và `eco.tnmp.cloud` đều HTTP 200, nội dung xác nhận D04/D05 và snapshot local/private; status JSON live ghi D04/D05 complete, `score_available=false`, `data_release_available=false`. Deployment ID/stage không được API credential hiện tại liệt kê; xác minh dựa trên nội dung production thực tế.

### Nhật ký 2026-10-03 — upload snapshot D03 vào R2 private

- Người dùng cung cấp Cloudflare Account ID để tiếp tục upload đã chuẩn bị. Dùng credential S3 mã hóa DPAPI ngoài repo trong environment của tiến trình, không in hoặc ghi key vào log/repo.
- Upload thành công vào bucket `eco-eth-private`, prefix `raw/coinmetrics/coinmetrics-backfill-2026-10-03-2026-10-02T182337734Z/`: 7 object gồm canonical JSONL, 5 trang raw và manifest. Script GET đọc ngược cả 7 object; tất cả `readback_verified=true`. Canonical SHA-256 giữ nguyên `aa78757fcaee33ef23ecf3ebd92791a685df2617f2b3874f5f5183d16babdd03`.
- Cập nhật `docs/STORAGE.md`, `README.md`, status JSON và dòng D03 trên trang chủ: ghi rõ bản sao R2 private đã xác minh nhưng website không đọc raw. `score_available=false`, `data_release_available=false`, quyền phát hành chưa xác nhận; không thay đổi lịch sử điểm vì chưa có điểm nào công bố.
- Kiểm tra upload thực tế: lệnh `node scripts/upload-private-snapshot-r2.mjs data/raw/coinmetrics/coinmetrics-backfill-2026-10-03-2026-10-02T182337734Z` thành công; 7/7 GET + SHA-256 đạt. Snapshot local được giữ nguyên và bị Git ignore.
- Phát hành web: commit `1195b98` đã push lên `main`. `https://eco.tnmp.cloud/` và `https://eco-tnmp.pages.dev/` đều trả HTTP 200; HTML mới có dòng snapshot R2 private. `/data/status.json` trên cả hai host trả `private_r2_verified`, `score_available=false`, `data_release_available=false`.
- Tiếp theo: kiểm tra restore độc lập, rồi S01-S03 (tooling, adapter/fixtures, canonical schema/quality); sau đó M01-M06 theo ADR-001. Không tạo endpoint đọc `raw/` hoặc public dataset trước khi rights gate thông qua.

### Nhật ký 2026-10-03 — củng cố nghiệm thu D04/D05

- Đối chiếu lại yêu cầu người dùng với repo. D04/D05 đã có research outputs, nhưng tìm thấy phần 8.2 của `MASTER_PLAN.md` còn holdout 2025 và label đỉnh tùy chọn mâu thuẫn ADR-001; D05 chưa có register máy đọc được.
- ADR-001 và `configs/research/core-v0.1.0.json` giữ nguyên, không đổi methodology hay tham số đã khóa. Sửa phần 8.2 để ADR-001 là nguồn chuẩn duy nhất cho `core-v0.1.0`, và phân loại các phân tích ngoài protocol thành exploratory/version mới.
- Thêm `configs/research/metric-feasibility-v0.1.0.json` cho E1-E9 với source URLs, coverage/evidence, rights, vintage và quyết định. Thêm `scripts/validate-research-artifacts.mjs` kiểm invariants D04 và completeness/safety policy của register D05. Đây là validation hợp đồng nghiên cứu, không phải test engine/backtest hoặc live refresh nguồn.
- Cập nhật README, report feasibility và trang chủ để liên kết protocol/register, đồng bộ `MASTER_PLAN.md`, status JSON và HANDOFF. Không đổi dữ liệu đầu vào, điểm, `methodology_version`, quyền công bố hay trạng thái engine.
- Kiểm tra: `node --check scripts/validate-research-artifacts.mjs`; `node scripts/validate-research-artifacts.mjs` trả `D04 protocol invariants: PASS` và `D05 feasibility register E1-E9: PASS`; parse JSON config/status; `git diff --check`. Engine/backtest chưa tồn tại, không ghi là đã kiểm thử.
- Phát hành: commit `b919c83` đã push `main`; sau cập nhật, `https://eco.tnmp.cloud/` và `https://eco-tnmp.pages.dev/` trả HTTP 200, có link Protocol/Feasibility. Status trên cả hai host ghi `research_artifacts_validation=passed`, `score_available=false`, `data_release_available=false`.
- Bước tiếp theo vẫn là S01-S03 rồi M01-M06; sau khi đủ engine mới chạy Q01 theo protocol ADR-001. E3/E8/E9 cần evidence entitlement/coverage trước khi chọn; E4 vẫn R&D-only.

### Nhật ký 2026-10-03 — live probe revision cho D05

- Thêm `scripts/audit-d05-feasibility.mjs`, không dùng API key. Script probe catalog Coin Metrics cho 7 candidate metric, timeseries ETH/1d mẫu 2021-01-01..03, và ba trang tài liệu Glassnode; raw body + manifest giữ local dưới `data/raw/d05/` bị ignore.
- Kết quả thực tế: catalog HTTP 200 liệt kê 7 metric 1d; timeseries `FeeTotNtv` HTTP 200, 3/3 giá trị ETH; `CapRealUSD`, `FeeTotUSD`, `FeeBlobTotNtv`, `FeePrioTotNtv`, `SplyAct1yr`, `TxTfrValAdjUSD` HTTP 403. Glassnode indicators/supply/metadata HTTP 200 và có thuật ngữ endpoint liên quan, nhưng không chứng minh entitlement/history/licence.
- Thêm bản tóm tắt không chứa raw tại `docs/evidence/d05-live-probe-2026-10-03.json`, cập nhật report/register context và validator để bắt buộc kiểm tra status/hash/coverage của live revision. D05 vẫn giữ E4 là R&D-only; E3/E8/E9 chưa được chọn; không đổi Core, methodology, score hoặc quyền phát hành.
- Kiểm tra: `node --check scripts/audit-d05-feasibility.mjs`; chạy `node scripts/audit-d05-feasibility.mjs 2026-10-03` thành công; catalog 7 entries; FeeTotNtv 3/3 non-null; các candidate bị chặn 403; docs 3/3 HTTP 200. Tiếp theo sau D05: S01-S03 rồi M01-M06; không công bố raw.
- Phát hành: commit `204b01f` đã push `main`; sau propagation, `https://eco.tnmp.cloud/` và `https://eco-tnmp.pages.dev/` trả HTTP 200, trang có nội dung live probe D05. Status trên cả hai host ghi `d05_live_probe=verified_2026-10-03`, `research_artifacts_validation=passed`, `score_available=false`, `data_release_available=false`.

### Nhật ký 2026-10-03 — làm rõ D05 trên index

- Phản hồi người dùng: index nhìn gần như không đổi vì D05 chỉ nằm trong một dòng tiến độ. Cập nhật `public/index.html` và `public/progress.css` để hero hiển thị `D05 LIVE PROBE VERIFIED` và thêm dải evidence rõ ràng: 7 metric trong catalog, 1/7 timeseries mẫu truy cập được, 3/3 FeeTotNtv rows, 6 candidate trả 403.
- Dải evidence ghi rõ catalog không đồng nghĩa quyền tải dữ liệu, Glassnode mới là tài liệu và khối này không tạo điểm ETH. Không thêm score giả hoặc mở raw data.
- Kiểm tra local: marker hero/evidence CSS/status flags pass; `git diff --check`. Commit `4eaacd7` đã push `main`. Sau deploy, cả `eco.tnmp.cloud/?v=4eaacd7` và Pages hostname hiển thị marker hero cùng khối D05 evidence trong accessibility tree; HTTP 200. Repo sạch.

### Nhật ký 2026-10-03 — dashboard score thật đã deploy và xác minh

- Code commit `c6b1866e09b9f594e3f399e76992f9223482ddb6` đã push `main`. Trước push: 42 staged files được kiểm diff, không có raw/computed/DPAPI/secret; SHA-256 của manifest/history/research **trong Git index** khớp pointer. `.gitattributes` tránh biến đổi bytes theo CRLF.
- Cloudflare Pages API xác nhận deployment `bf62b8d1-bff9-4564-bb90-bb15a7dd3750`, `production`, stage `success`, đúng commit `c6b1866`. Deployment hostname `https://bf62b8d1.eco-tnmp.pages.dev`. Token DPAPI chỉ giải mã trong tiến trình và giải phóng sau gọi, không in/commit.
- `https://eco.tnmp.cloud/` và `https://eco-tnmp.pages.dev/` HTTP 200, title dashboard mới. Pointer cả hai host là `core-c899a808bda65db96be3`; manifest/history/research tải HTTP 200 và hashes byte thực **khớp local/index**. Score 41.379812239861 ngày 2026-10-01, `score_available=true`, `series_type=reconstructed`. Không thay release version hoặc data sau push.
- Headers thực: versioned history/research `public, max-age=31536000, immutable`; pointer `public, max-age=0, must-revalidate`. Website không gọi raw R2/provider. History 1.237.334 bytes chưa nén; dữ liệu đã tính sẵn và cache trên Pages/CDN.
- Production browser QA chạy trực tiếp `https://eco.tnmp.cloud/?v=c6b1866`: viewport 1440/768/390/360, score/date/coverage, missing/pending/warm-up null, custom E7 366 ngày, CSV, Enter/Space controls, network failure preservation+retry đều PASS; 43667 chart nonblank pixels, 0 page errors. Ảnh thật trong `test-results/` ignored; không tự nhận đã audit screen reader.
- [GitHub Actions run 37058646492](https://github.com/tnmjsc-hue/eco/actions/runs/37058646492) `completed/success`, đúng SHA. Job Ubuntu thực thi Python/pnpm setup, install pinned/frozen, rebuild vendor không diff, 19 engine/gate tests, research validator, 3 public contract tests, syntax và whitespace, mọi step success. S01 DONE; O02 chỉ IN_PROGRESS vì scheduled batch chưa có.
- Có follow-up commit bàn giao và bổ sung keyboard QA; không đổi engine, UI assets, release dữ liệu hoặc methodology. Đây là preview nghiên cứu phi thương mại **đã chạy thật**, không phải full operational release. Backtest chưa chứng minh incremental utility; không che kết quả không đạt.
- Tiếp theo: TODO sẵn sàng S02 adapter fixtures, rồi S04 incremental/vintage; O02 scheduled batch, O03 restore/fault drills, O04 shadow >=30 ngày; Q02 report mở rộng và Q04 protocol metric mở rộng. Không mua nguồn trả phí hay tune trên cùng primary holdout theo quán tính.

### Nhật ký 2026-10-03 — daily update implement và local verification

- Yêu cầu người dùng: tự cập nhật chỉ số hằng ngày. Thêm `.github/workflows/daily-update.yml`, `eco/daily.py`, `scripts/daily-fetch.mjs`, `scripts/verify-daily-deploy.mjs`, adapter tests và daily gate/revision/ledger tests. Lịch 10:17, thử lại 14:17 Việt Nam; không phụ thuộc máy Windows bật. Không dùng subagent.
- Adapter timeout 30s/4 attempts/backoff tối đa 30s, pagination ETH query/cycle/quality guards; raw cache private. R2 uploader GET kiểm tồn tại/hash, không ghi đè object khác nội dung, timeout 60s/readback mỗi file. Các token hiện có chỉ giới hạn bucket; không tạo token rộng, không chuyển raw sang Pages/Artifact GitHub.
- GitHub repo admin/secrets public-key API đã xác minh. Cấu hình ba Actions Secrets bằng libsodium sealed box từ DPAPI trong process; deploy hook `eco-daily-index` branch main, DPAPI hook ngoài repo. Không lưu PAT cá nhân/Pages API token trong runner. Helper vận hành và dependency PyNaCl ở ngoài tracked code/ignored, không stage.
- Live fetch 2026-10-03T02:00:41.628Z: 5 pages/4081 observations, không gaps/duplicates/invalid; canonical SHA `33264b50fc555e3591cdd61be0301ed84f62505f86a55bd1c3807a9e97d3f976`. R2 7/7 PUT/GET hash PASS. Giá/cap/supply có ngày 2026-10-02 nhưng MVRV null; giữ Core ngày 2026-10-01 41.379812239861. Release public `core-9a0d250ffc41a1ddffaa` thêm observation partial, reason `new_closed_utc_observations`, không sửa release `core-c899a808bda65db96be3`. `methodology_version`, weights, origin và protocol giữ nguyên.
- Diff daily idempotent theo giá/coverage/reasons và score tolerance 1e-8; numeric equivalence giữ giá trị cũ, không tạo correction giả giữa Windows/Linux. Revisions thêm release/lý do; bản ghi Core đầu tiên cho ngày mới chỉ tạo một lần. Chưa có record ngày 2026-10-02 vì Core chưa hợp lệ; không backfill giả as-published. `recorded_at` không được gọi là provider availability hoặc first HTTP availability.
- Dashboard polling 15 phút + visibility refresh, latest tự tiến khi có release, historical selection giữ nguyên, lag/error/source-pending rõ, checksum và giữ dữ liệu khi lỗi. Browser test dùng response fixtures chỉ trong QA để kiểm timer/new release, không đưa fixture vào dữ liệu public.
- Local PASS: 28 unittest Python; 5 Node tests; frozen research validator; syntax app/deploy script; diff whitespace. Browser local 1440/768/390/360, chart 43668 nonblank pixels, custom 366 ngày, CSV/keyboard/network retry + auto timer/latest/historical giữ đúng, 0 page errors. Snapshot replay idempotent đã giữ pointer; đợi hosted run để xác minh cross-runtime/credential/deploy thực.
- Network hiện refresh toàn range để bắt revision ngày cũ. S04 chưa DONE về incremental network; O03 restore/fault drill toàn chuỗi và O04 >=30 ngày còn chưa làm. Hosted workflow và production verification sẽ ghi thêm khi thực sự hoàn tất.
