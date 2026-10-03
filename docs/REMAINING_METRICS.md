# Task cho các chỉ số ETH còn lại

**Lập ngày 2026-10-03, cập nhật sau chuỗi triển khai cùng ngày.** Phạm vi: bóc tách Q04 thành backlog E2/E3/E4/E8/E9. Chuỗi Q02 → X00 → E2-01 → E4-04 đã hoàn tất. E2 đã có raw diagnostic public cùng C1 nguồn cung/C2 số dư sàn theo ADR-007, đã xác minh production và hai hosted daily; E4 giữ R&D-only. Core vẫn bốn thành phần.

Core `core-v0.1.0` vẫn có E1/E5/E6/E7. E2 dùng helper `nupl_diagnostic` trong [`eco/core.py`](../eco/core.py), đúng snapshot Core cha; publisher/UI/CSV/daily riêng tại `/data/diagnostics/` đã đạt local, production và hai hosted daily ([runbook](ETH_DIAGNOSTICS.md)). Publisher Core vẫn chỉ xuất bốn component. E4 đã có full-history audit, protocol, engine riêng và đánh giá exploratory, nhưng bị giữ R&D-only. E9 đã có code/protocol/fixtures riêng; nguồn vẫn chặn backfill và kiểm định ETH thật. E3/E8 chưa có source/entitlement/history/rights đủ để tính. Bằng chứng D05 tại [metric-feasibility.md](metric-feasibility.md); tiến độ E9 tại [E9_RUNBOOK.md](E9_RUNBOOK.md).

## 1. Thứ tự ưu tiên và mức sẵn sàng

**CORE10-01 `DONE` (2026-10-03):** E2/C1/C2 chuẩn hóa và tích hợp trong `core-v0.2.0`, Core 10 Experimental; E2 chia ngân sách định giá, hai metric sàn chia họ sàn. Dashboard 10 thành phần có Core 4/ECO 7 bất biến. CI/Pages/năm release chain/ba UI và hai hosted daily đã success; [CORE_TEN](CORE_TEN.md), [ADR-008](ADR-008-core-ten-experimental.md), [evidence](evidence/core-ten-publication-2026-10-03.json). Các mục bốn thành phần/raw bên dưới mô tả version cũ, vẫn giữ nguyên hợp đồng.

**Bổ sung theo yêu cầu 2026-10-03:** ba metric thay thế vai trò E3/E8/E9 đã có source contract mới, full-history ETH thật, engine, đánh giá exploratory và public research artifacts/UI. Xem [NETWORK_PROXIES](NETWORK_PROXIES.md) và [ADR-005](ADR-005-network-research-proxies.md). Đây là `exchange_share`, `address_activity`, `value_per_transfer` dưới `network-proxies-v0.1.0`. Original RHODL/Dormancy/adjusted-NVT contracts và probe lịch sử vẫn giữ trạng thái nguồn cũ; không đổi tên metric mới thành bản tương đương hoặc ghép vào Core. Production đã xác minh tại eco.tnmp.cloud/#extended; hosted daily run thành công. Bằng chứng cuối phiên trong HANDOFF.

| Task bổ sung | Source/backfill | Engine/evaluation | Publication/UI |
|---|---|---|---|
| P3 · Exchange supply share | DONE · ETH Community/4.083 ngày/CC BY-NC/R2 | DONE · causal/history/10k bootstrap | DONE · derived research/CSV/coverage, provisional flash |
| P8 · Address activity intensity | DONE · ETH Community/4.083 ngày/CC BY-NC/R2 | DONE · causal/history/10k bootstrap | DONE · derived research/CSV/coverage |
| P9 · Capitalization per transfer count | DONE · ETH Community/4.083 ngày/CC BY-NC/R2 | DONE · causal/history/10k bootstrap | DONE · derived research/CSV/coverage |

Hướng giải quyết chi tiết source gate E9-01/E3-01/E8-01, điều kiện nghiệm thu và phương án thay thế tại [REMAINING_SOURCE_RESOLUTION.md](REMAINING_SOURCE_RESOLUTION.md).

| Ưu tiên | ID | Chỉ số | Hiện trạng | Việc bắt đầu được |
|---|---|---|---|---|
| 1 | E2 | ETH NUPL dẫn xuất | Protocol raw diagnostic, exact-parent replay, JSON/UI/CSV/daily đã đạt local | Đã xác minh CI/Pages/domain/hosted daily; không thêm phiếu Core |
| 2 | E4 | ETH Fee Activity Multiple | Full-history `FeeTotNtv` audit, protocol và engine đã xong; exploratory kém Core | Giữ R&D-only; chỉ mở revision/prospective nếu có câu hỏi nghiên cứu mới |
| 3 | E9 | ETH NVT proxy | `TxTfrValAdjUSD` có catalog ETH nhưng sample Community trả 403 | Xác minh đường dữ liệu được phép truy cập và licence |
| 4 | E3 | ETH realized-value age ratio | Chưa xác minh endpoint/lịch sử age bands ETH; RHODL tham chiếu hiện chỉ có bằng chứng BTC | Audit metadata, age bands và phương pháp tài khoản ETH |
| 4 | E8 | ETH dormancy/spending proxy | Chưa xác minh entitlement/history dormancy ETH; `SplyAct1yr` sample trả 403 | Audit nguồn dormancy account-based và định nghĩa tuổi ETH |

E2 và E4 đã qua các task được phép theo dependency. Audit nguồn E9/E3/E8 có thể làm độc lập; một sample truy cập được chưa chứng minh có dữ liệu đủ dài hoặc quyền phát hành. E2 giữ vai trò diagnostic, không tự thêm thành phiếu độc lập cạnh E7.

## 2. Task chung và dependency

Task cha **Q04 vẫn `TODO`** vì E3/E8/E9 chưa qua source gate; dependency D05 và Q02 đã `DONE`. X00 đã hoàn tất; E2-01 và toàn bộ nhánh E4 đã hoàn tất ở phạm vi được phép. Không phải chờ đủ cả năm nguồn mới nghiên cứu một ứng viên đã đạt cổng dữ liệu.

| ID | Trạng thái | Dependency | Công việc và nghiệm thu |
|---|---|---|---|
| X00 | DONE | D05 | Lập mẫu source contract cho từng ứng viên: endpoint/asset/đơn vị/UTC, thành phần dữ liệu, coverage/gaps, lag/vintage/revision, quyền cache/chart/derived/CSV và manifest SHA-256. Unknown ghi rõ; không gán `retrieved_at` thành `source_available_at`. |
| X01 | PARTIAL · DONE raw diagnostics | Q02, X00, source/spec đã audit của ứng viên | Khóa config và ADR nghiên cứu riêng trước khi code/chạy đánh giá: công thức, chiều tín hiệu, warm-up, normalizer nhân quả, nhóm/trọng số nếu có composite, baseline, success rule và giới hạn thử tham số. Holdout Core đã xem kết quả chỉ dùng exploratory; đánh giá xác nhận cần holdout mới hoặc prospective. Chưa gán một version extended chính thức trong phiên lập task. |
| X02 | PARTIAL · DONE raw diagnostics | Engine/test và quyết định nghiên cứu của ứng viên, quyền phát hành nguồn đó | Với ứng viên được chấp nhận ở mức phù hợp: cập nhật schema/manifest/JSON/CSV/UI, daily adapter riêng, snapshot R2 private và readback, immutable release/revision; kiểm local và production theo DEPLOYMENT. ADR ghi phạm vi Experimental hoặc sản phẩm vận hành. Gate vận hành đầy đủ S04/M06/O01/O03/O04 vẫn theo HANDOFF. |

X01/X02 áp dụng **theo từng ứng viên**; E2 có thể được công bố dưới vai trò diagnostic mà không trở thành thành phần composite. Đổi provider, đơn vị, thành phần, trọng số hoặc chuẩn hóa cần methodology version mới; giữ nguyên lịch sử Core đã công bố.

## 3. E2 — ETH NUPL dẫn xuất

| ID | Trạng thái | Dependency | Công việc và nghiệm thu |
|---|---|---|---|
| E2-01 | DONE | D05, M03 | Kiểm kê raw diagnostic đã có và chốt contract: `1 - 1/CapMVRVCur`, cùng provider/ngày/snapshot với E7; raw có thể âm; missing/invalid trả null có reason. Ghi rõ derived NUPL và quan hệ với MVRV, không trình bày như series NUPL độc lập từ provider. |
| E2-02 | DONE · giữ raw | E2-01, X01 cho diagnostic | ADR-007 khóa raw ratio/%, không thêm normalizer hoặc điểm 0–100. Prefix/future shock, null, signed values đã kiểm; phụ thuộc MVRV được công bố. Protocol `diagnostics-v0.1.0` riêng. |
| E2-03 | DONE · raw diagnostic public | E2-02, X02 cho diagnostic | JSON/CSV/card/chart/daily/revision đã đạt trên dữ liệu thật 4.074 ngày hợp lệ; CI/Pages/domain/bốn viewport/hai hosted workflow đều success. Custom/composite không nhận thêm E2. |

Không viết lại hàm raw đã có. E2/C1/C2 giữ raw diagnostic theo [ADR-007](ADR-007-raw-eth-diagnostics.md); kết quả/gates/lineage tại [ETH_DIAGNOSTICS](ETH_DIAGNOSTICS.md). C1/C2 có engine/gates/UI/CSV/daily riêng, 4.053 ngày hợp lệ mỗi chỉ số. X01/X02 đã hoàn tất theo phạm vi raw diagnostics trên production; Q04 tổng thể và E3/E8/E9 gốc vẫn chưa DONE.

| Task bối cảnh mới | Trạng thái | Nghiệm thu |
|---|---|---|
| C1 · Thay đổi nguồn cung 30 ngày | DONE · raw diagnostic | Protocol/ETH snapshot/readback/calendar window/engine/UI/CSV/revision/daily/production; 4.053 ngày hợp lệ, giữ số âm và null |
| C2 · Thay đổi số dư sàn 30 ngày | DONE · raw diagnostic | Cùng cổng C1, thêm flash/nhãn sàn/đơn vị ETH/thay đổi ròng; 4.053 ngày hợp lệ, không gán thành gross nạp/rút |

## 4. E4 — ETH Fee Activity Multiple

| ID | Trạng thái | Dependency | Công việc và nghiệm thu |
|---|---|---|---|
| E4-01 | DONE | D05 | Backfill `FeeTotNtv` ETH/1d đến ngày UTC đã đóng; snapshot/manifest/hash riêng, report first/last valid, gaps/duplicates/invalid và vintage chưa biết. Xác minh licence cùng thành phần execution/blob/burn/tips qua các giai đoạn; chưa coi ba ngày mẫu là full-history audit. |
| E4-02 | DONE | E4-01, X00 | Chốt giả thuyết và source contract: ứng viên hiện có `ln(SMA30(FeeTotNtv)/SMA365(FeeTotNtv))`. Phân biệt với giả thuyết FeeUSD cũ trong MASTER_PLAN; lựa chọn native ETH hoặc USD phải có lý do/version riêng. Khóa calendar window, guard mẫu số, warm-up, chiều tín hiệu và phân đoạn nâng cấp; không tự gọi phí thấp là thị trường lạnh. |
| E4-03 | DONE | E4-02 | Implement adapter/canonical và feature/normalizer riêng. Fixture tính tay, thiếu ngày, zero/null, prefix/future shock; dữ liệu E4 bị lỗi không làm hỏng daily Core bốn input. |
| E4-04 | DONE | E4-03 | Đánh giá so với Core, E7 và nhóm giá trên cùng ngày; correlation/ablation, regime trước/sau nâng cấp và ảnh hưởng L2. Ghi quyết định nhận/giữ Experimental/loại theo protocol; nêu coverage và giới hạn, không gọi là Puell Multiple. |

`FeeTotUSD`, phí priority và blob riêng đã trả 403 trong probe D05. Nếu nghiên cứu cần chúng, mở task quyền truy cập tương ứng; không thay thế ngầm hoặc mua API trong task backfill.

## 5. E9 — ETH NVT proxy

| ID | Trạng thái | Dependency | Công việc và nghiệm thu |
|---|---|---|---|
| E9-01 | BLOCKED | D05 | Probe riêng mới: catalog thực sự có quyền chỉ cho vốn hóa; adjusted USD/native và NVT tính sẵn đều 403; CSV chính thức không có transfer/NVT. Đã đọc định nghĩa netting theo giờ, kiểm Gmail và đường cấp quyền miễn phí. [Evidence](evidence/e9-source-access-2026-10-03.json); thiếu key và licence đúng scope, không mua gói. |
| E9-02 | BLOCKED | E9-01, X00 | Adapter backfill có licence/expiry/hash và khử key đã có. Chưa tải full history ETH thật, chưa audit coverage/gaps/revisions. Cần cặp vốn hóa/adjusted transfer USD cùng provider/UTC; không thay nguồn ngầm. |
| E9-03 | IN_PROGRESS | E9-02, X01 | Protocol [ADR-004](ADR-004-e9-nvt-candidate.md) và engine riêng đã implement/test công thức, calendar/null/zero, warm-up/prefix; pipeline kiểm raw/canonical/provenance/licence. Nghiệm thu trên snapshot ETH thật còn bị dependency E9-02 chặn; chưa DONE. |
| E9-04 | BLOCKED | E9-03 | Harness correlation/ablation/regime/paired bootstrap đã có, fixture đã chạy. Chưa có kết quả ETH thật, không ghi AP hoặc utility giả. Chờ snapshot hợp lệ để ra quyết định nghiên cứu; tên là NVT proxy, không phải CVDD. |

## 6. E3 — ETH realized-value age ratio

| ID | Trạng thái | Dependency | Công việc và nghiệm thu |
|---|---|---|---|
| E3-01 | BLOCKED | D05 | Đã audit source gate: tài liệu có endpoint RHODL/realized-cap HODL waves nhưng RHODL ghi phạm vi BTC, endpoint cần API key; no-key probes 401, chưa có ETH entitlement/history/unit/licence. Evidence [remaining-source-audit](evidence/remaining-source-audit-2026-10-03.json). Cần endpoint ETH được cấp quyền trước E3-02; không thay bằng BTC. |
| E3-02 | BLOCKED | E3-01, X00 | Audit snapshot lịch sử và đặc tả nhóm trẻ/già, cách định tuổi/realized value account-based, đơn vị, lag/warm-up, mẫu số và chiều tín hiệu. Giải thích ảnh hưởng staking, hợp đồng và self-transfers. Không suy ra age cohorts chỉ từ aggregate MVRV. |
| E3-03 | BLOCKED | E3-02, X01 | Implement công thức ratio đã được khóa và normalizer; fixture cohorts tính tay, missing/zero, biến động cohort và prefix-invariance. Cohort schema/methodology provider đổi phải tạo candidate/version riêng. |
| E3-04 | BLOCKED | E3-03 | Đánh giá tính độc lập với E7/E2, utility và regime stability; ADR nhận/giữ Experimental/loại. Nếu không có nguồn đủ kiểm chứng, đóng nghiên cứu bằng evidence và quyết định loại hoặc đề xuất thay thế rõ nghĩa. |

## 7. E8 — ETH dormancy/spending proxy

| ID | Trạng thái | Dependency | Công việc và nghiệm thu |
|---|---|---|---|
| E8-01 | BLOCKED | D05 | Đã audit source gate: Glassnode có `dormancy_account_based` nhưng no-key probe 401 và chưa có ETH entitlement/history; Coin Metrics `SplyAct1yr` sample 403, định nghĩa là active supply chứ không phải dormancy. Evidence [remaining-source-audit](evidence/remaining-source-audit-2026-10-03.json). Cần nguồn dormancy ETH được cấp quyền trước E8-02; không đổi tên active supply. |
| E8-02 | BLOCKED | E8-01, X00 | Audit full-history snapshot và chốt công thức proxy, units, denominator, lag/warm-up, chiều tín hiệu và bias của staking/withdrawal/contracts/self-transfers. Nếu nguồn chỉ là active supply, mở định nghĩa/version thay thế riêng trước khi code. |
| E8-03 | BLOCKED | E8-02, X01 | Implement feature/normalizer đã khóa; fixture tính tay, missing/zero, calendar windows, replay/prefix và kiểm thay đổi heuristic của provider. Không gắn nhãn Reserve Risk cho proxy khác nghĩa. |
| E8-04 | BLOCKED | E8-03 | Correlation/ablation với E3/E7, regime analysis và utility ngoài mẫu theo protocol; ADR nhận/giữ Experimental/loại. Ghi cụ thể trường hợp dữ liệu/phương pháp không đủ, không điền số giả. |

## 8. Cổng nghiệm thu mỗi ứng viên

1. **Nguồn:** ETH thật, định nghĩa/endpoint/đơn vị/coverage và quyền phù hợp có evidence; raw riêng tư, hash và manifest đầy đủ.
2. **Phương pháp:** source contract và protocol khóa trước triển khai/đánh giá; dữ liệu khả dụng tại thời điểm tính được phân biệt với ngày quan sát/ngày tải. Không có historical availability thì chỉ báo reconstructed.
3. **Engine:** fixture, calendar/null/warm-up và replay/prefix đạt; test này chưa chứng minh hữu ích dự báo hoặc vintage lịch sử.
4. **Nghiên cứu:** có baseline, correlation/ablation/regime, uncertainty và quyết định nhận/loại minh bạch; chưa đủ bằng chứng vẫn được ghi đúng kết quả.
5. **Public:** chỉ sau rights và release gate tương ứng; schema/JSON/CSV/UI đúng vai trò/version, snapshot R2 readback, immutable history và deploy/domain verification.

Hoàn thành audit D05 hoặc viết thiết kế không đồng nghĩa các chỉ số đã `DONE`. Mục tiêu vẫn là giải quyết đủ chín vị trí bằng triển khai được kiểm chứng hoặc quyết định nghiên cứu rõ ràng cho từng vị trí.
