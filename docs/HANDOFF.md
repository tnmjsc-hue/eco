# Bàn giao triển khai ETH Cycle Index

**Cập nhật: 2026-10-03.** Trạng thái tổng: **D01-D05_RESEARCH_COMPLETE / CORE_PROTOCOL_FROZEN / ENGINE_NOT_STARTED**.

Tài liệu chuẩn: [MASTER_PLAN.md](MASTER_PLAN.md). Bằng chứng nghiên cứu: [RESEARCH.md](RESEARCH.md). Triển khai web: [DEPLOYMENT.md](DEPLOYMENT.md). Quy tắc agent: [AGENTS.md](../AGENTS.md).

## 1. Đã hoàn thành và chưa hoàn thành

Đã đọc website/FAQ/một số file engine chính thức của CBBI; chốt SHA tham chiếu; kiểm tra workspace; thử một số truy vấn dữ liệu ETH thật; viết bộ kế hoạch và checklist tiếp tục.

**Đã có Git repository, trang giới thiệu tĩnh tại `eco.tnmp.cloud`, full-history snapshot Coin Metrics riêng tư đã audit và protocol Core/research đã khóa. Snapshot chưa được upload lên R2. Chưa có engine, lockfile, điểm ETH, test engine, backtest, dashboard hoặc scheduler.** Trang giới thiệu không phải bản phát hành chỉ số. Không có API trả phí được mua. Không có công việc nào đang chạy nền. Không có agent khác đang giữ task.

## 2. Bắt đầu từ đâu

Khi người dùng yêu cầu triển khai, kiểm tra task `IN_PROGRESS` và TODO đầu tiên có dependency đủ. D01-D05 đã có report; D04 chỉ khóa protocol, không có nghĩa đã code/test engine. S01 pipeline còn dang dở. Snapshot D03 chưa upload R2 và không được frontend đọc; snapshot hiện tại chưa được phép công khai.

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
| D01 | DONE | R00 | Probe capability từng metric; lưu raw response, request metadata/hash, report | Probe mẫu đúng ETH/1d; phân biệt HTTP access error với payload không có dữ liệu; không log key |
| D02 | DONE | R00 | Chốt diễn giải nhãn/ngày UTC và ranh giới quyền Coin Metrics; `docs/data-contract.md`, `docs/data-rights.md` | Period mapping có nguồn chính thức; research local được giữ riêng tư; quyền public/derived/export/commercial và vintage lịch sử được nêu rõ là chưa xác nhận |
| D03 | DONE | D01,D02 | Tải toàn lịch sử 4 input; report gaps, invalid, duplicates, first/last valid | Snapshot hash + range; report kiểm tra được; không công khai raw; mapping kỳ đã chốt |
| D04 | DONE | D03 | Khóa Core config và protocol research; ADR-001 | Công thức, normalizer, split, label, baseline, bootstrap và success rule được ghi trước backtest; chưa tuyên bố đã code/test |
| D05 | DONE | D01,D02 | Audit nguồn cho E3/E4/E8/E9, báo cáo khả thi 9 vị trí | Mỗi vị trí có nguồn/coverage/quyền/lịch sử hoặc phần chưa xác minh và lý do chưa chọn; không cần mua để lập report |

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
Hiện có trang giới thiệu công khai và private full-history audit; chưa có engine/dashboard/score, snapshot chưa lên R2. D01-D05 đã có bằng chứng; task tiếp theo S01/S02/S03 là pipeline, quality tests và cache/private storage integration theo rights gate. Giữ raw riêng tư.
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
