# Cập nhật chỉ số hằng ngày

## Lịch Và Phạm Vi

- Workflow `.github/workflows/daily-update.yml` trên nhánh `main`: dự kiến **10:17 giờ Việt Nam**, kiểm tra lại **14:17**. Có `workflow_dispatch` để chạy thủ công; không phụ thuộc máy cá nhân bật.
- Chỉ tính ETH Core `core-v0.1.0`, E1/E5/E6/E7, ngày UTC đã đóng. Coin Metrics có thể cập nhật từng metric vào các thời điểm khác nhau. Không lấy ngày local làm cutoff và không lấy MVRV ngày cũ để điền ngày mới.
- Scheduler GitHub có thể trễ; lịch là dự kiến, không phải SLA chính xác đến phút. Trong repo public, GitHub có thể tắt lịch sau 60 ngày không hoạt động. Job ghi status vào Git mỗi lần chạy bình thường; vẫn phải kiểm tra khi repo/workflow bị vô hiệu hóa. [GitHub schedule](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#schedule).
- Đây vẫn là Experimental research preview phi thương mại, không mở gate vận hành đầy đủ hoặc chứng minh hiệu quả phương pháp.

## Luồng Thực Tế

1. `scripts/backfill-coinmetrics.mjs` tải 4 input toàn range đến UTC hôm qua: 30 giây timeout/request, tối đa 4 attempts, backoff/Retry-After tối đa 30 giây, pagination giữ query ETH, giới hạn trang và phát hiện cycle. Raw + canonical + audit/manifest dưới `data/raw` bị ignore.
2. `scripts/daily-fetch.mjs` upload toàn snapshot lên R2 private `eco-eth-private`. Mỗi object được GET/readback SHA-256; object đã có chỉ được dùng nếu hash giống, không ghi đè khác nội dung. Chỉ tạo report thành công khi toàn bộ readback đạt. Không upload raw làm GitHub Artifact/public Git.
3. `python -m eco.daily` kiểm backup gate, loader và frozen protocol rồi tính bằng engine đã kiểm. Research tính lại cùng tham số/protocol với nhãn vừa hoàn tất; không tune trên kết quả mới. Raw/protocol/engine/publisher hashes nằm trong manifest.
4. So dữ liệu/điểm với release trước. Không có input/output mới thì không đổi pointer. Nếu provider mất observation đã có, chặn release. Source revision tạo release riêng, `revision.previous_release_id`, lý do và `changed_dates`; không sửa release cũ. Ngày mới bổ sung được ghi `new_observation_dates`.
5. Public chỉ gồm history/research/manifest, revision summary và bản ghi điểm công bố đầu tiên cho ngày mới. `public/data/publications/YYYY-MM-DD.json` chỉ tạo một lần khi trước đó chưa có Core hợp lệ; không tạo giả bản ghi cho 2015–2026 đã backfill. `recorded_at` là thời gian batch chuẩn bị record, **không phải** thời gian HTTP đầu tiên trả điểm hoặc provider công bố; `public_available_at` và availability provider vẫn null. Chưa có chuỗi prospective 30 ngày để kiểm định.
6. Workflow chạy tests/validation trước commit output public. Nếu batch lỗi, chỉ commit status lỗi, không stage partial release. Không rebase/force-push khi `main` có commit cạnh tranh; job fail và lượt sau checkout lại.
7. Bot push `main` dùng `GITHUB_TOKEN` giới hạn `contents: write`. Vì token này không kích hoạt workflow CI qua push, daily job tự chạy tests trước phát hành. Deploy hook riêng `eco-daily-index` chỉ build Pages `eco-tnmp/main`, không dùng PAT cá nhân trong runner. Job gọi hook rồi chờ hash production của status/pointer/manifest/history/research khớp, quá hạn thì fail. [Quy tắc GITHUB_TOKEN](https://docs.github.com/en/actions/how-tos/write-workflows/choose-when-workflows-run/trigger-a-workflow), [Cloudflare hooks](https://developers.cloudflare.com/pages/configuration/deploy-hooks/).

Refresh toàn range là lựa chọn thận trọng để thấy source revision từ ngày cũ; **S04 chưa DONE** về network incremental. Tối ưu sau này phải có restore/hash/revision tests, không bỏ audit toàn range mà không ghi quyết định. Không xóa releases/snapshots cũ theo quán tính; theo dõi tăng trưởng lưu trữ.

Đối chiếu điểm giữa Windows/Linux dùng sai số tuyệt đối `1e-8` đã có trong contract engine, không áp sai số cho giá/coverage/reasons. Các record tương đương giữ nguyên giá trị công bố trước; không tạo revision giả vì roundoff. Chênh lệch ngoài biên tạo revision riêng. Công thức, trọng số, origin, protocol và `methodology_version` không đổi.

## Credential

Repo có ba Actions Secrets: `R2_ACCESS_KEY_ID`, `R2_SECRET_ACCESS_KEY`, `CLOUDFLARE_DEPLOY_HOOK`. R2 dùng token đã có, giới hạn bucket, hết hạn 2027-10-03; không tạo token rộng. Account ID/bucket không phải secret. Deploy hook URL là secret, không đưa vào log/README/frontend.

Windows giữ DPAPI ngoài repo theo STORAGE; hook mới ở `%APPDATA%\ETH-CBBI\cloudflare-daily-hook.dpapi`. Không lưu credential Git cá nhân vào Actions. Khi rotate, cập nhật Actions Secrets và DPAPI tương ứng; chạy manual job để verify. Secrets chỉ được đưa vào step cần dùng, không truyền sang frontend hoặc job PR.

## Trạng Thái Và Sự Cố

`/data/status.json` có `daily_update`: lịch, `last_attempt_at`, `last_success_at`, `outcome`, target UTC date, snapshot SHA, backup flag và run URL. `source_pending` là pipeline kiểm thành công nhưng Core chưa đủ cho UTC hôm qua; `release_action` cho biết đã tạo release hay không. `failed` giữ lần success và score/release trước, chỉ công khai stage/thông báo đã làm sạch.

Dashboard tự kiểm pointer/status mỗi 15 phút khi tab hiển thị, và khi quay lại tab sau một phút. Khi đang ở “Gần nhất”, ngày mới tự được chọn; nếu đang xem lịch sử, giữ lựa chọn đó. Assets có checksum/immutable cache, pointer/status revalidate. Source lag >48 giờ hoặc attempt >26 giờ hiện cảnh báo; không đổi điểm cũ thành điểm mới. Không có email/Telegram tự gửi.

- Source/429/schema/R2 lỗi: xem run trong GitHub Actions, kiểm stage; không sửa score/null hoặc đổi provider. Job chiều/ngày tiếp theo sẽ thử lại; có thể **Run workflow** sau khi sửa nguyên nhân.
- Deploy lỗi sau bot commit: xem Pages và Actions, sửa hosting/hook; chạy lại job. Pointer Git và production có thể khác tạm thời, job không báo success nếu checksum chưa khớp.
- Git push conflict: không force. Chạy workflow mới từ main đã cập nhật.
- Replay offline: `python -m eco.daily --verified-fetch-report` chỉ dùng report raw/R2 đã xác minh tại `data/computed/daily-fetch.json`; không giả thời gian retrieval thành lúc replay. Lệnh này không thay manual hosted-run verification.
- Pause: disable workflow trong GitHub Actions; nếu dừng dài hạn, cập nhật status/UI `enabled=false` trong một commit có lý do. Không giữ nhãn đang chạy sau khi tắt.

Fault/restore drill toàn chuỗi và shadow >=30 ngày vẫn là O03/O04, chưa nghiệm thu chỉ từ một manual run.

## ECO 7 sau hai batch cha

Theo ADR-006, hai workflow gọi `python -m eco.seven` sau Core/proxy batch thành công, trong cùng concurrency. Artifact riêng `/data/extended/latest.json`, `status.json`, immutable `releases/`; không đổi job/score/version Core hoặc proxy. Join cùng ngày UTC, 7/7 mới có điểm, không forward-fill; ngày mới thiếu proxy giữ last valid ngày gốc và ghi `source_pending`. Parent/hash/rights/regression/computation lỗi giữ pointer tốt cũ và status failed; workflow báo lỗi riêng, không silently thêm proxy vào Core cũ.

Được stage riêng đúng allowlist: Extended status và, khi bước Extended thành công, latest/releases; Node/Python tests và research validators phải đạt trước commit. Deploy verifier hiện kiểm bốn bộ Core/proxy/Extended/diagnostics pointer/status/manifest/history/research trên domain. Website kiểm cả hash/coverage/weights, cho chọn ECO 7/Core 4/custom, giữ dữ liệu đã xác minh khi refresh lỗi. Arkham chưa có key/rights nên không có batch Arkham hoặc credential mới.

## Raw diagnostics sau batch cha

Theo [ADR-007](ADR-007-raw-eth-diagnostics.md), hai workflow gọi `python -m eco.diagnostic_pipeline daily` sau batch cha thành công. Bước này dùng lại bucket token cũ, GET/readback đúng hai snapshot cha, replay Core và xuất E2 NUPL, C1 nguồn cung 30 ngày, C2 số dư sàn 30 ngày; không fetch provider/vintage khác để thay E2. `/data/diagnostics/` có latest/status/releases/revisions/publications riêng, publisher allowlist ba file derived, pointer atomic và ngày missing có reason.

Nếu restore/rights/schema/replay/publish lỗi, diagnostics giữ pointer và bản công bố tốt, chỉ ghi failed stage đã làm sạch; workflow báo failure. Core/proxy/Extended đã đạt gate vẫn có thể được commit, không che lỗi diagnostics. Bot stage status riêng và latest/releases/revisions/publications chỉ khi bước diagnostics thành công. Không có job lịch hoặc secret mới. Status lịch sau Core 10:17/14:17 và network 10:47/14:47 Việt Nam; frontend refresh 15 phút giữ ngày lịch sử, checksum/immutable failure giữ dữ liệu tốt. Chi tiết snapshot/coverage/commands: [ETH_DIAGNOSTICS](ETH_DIAGNOSTICS.md). Đây chưa phải shadow 30 ngày.
