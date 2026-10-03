# Task cho các chỉ số ETH còn lại

**Lập ngày 2026-10-03.** Phạm vi: bóc tách Q04 thành backlog E2/E3/E4/E8/E9. Đây là kế hoạch thực thi; các task dưới đây chưa được triển khai trong phiên lập danh sách.

Core `core-v0.1.0` đã có E1/E5/E6/E7. E2 đã có raw `nupl_diagnostic` trong [`eco/core.py`](../eco/core.py) và test công thức trong [`tests/test_core.py`](../tests/test_core.py), nhưng publisher hiện chỉ xuất bốn component Core. E3/E4/E8/E9 chưa có engine được chấp nhận. Bằng chứng nguồn dùng ở đây là D05 ngày 2026-10-03 trong [metric-feasibility.md](metric-feasibility.md) và [live probe](evidence/d05-live-probe-2026-10-03.json); phiên này không chạy lại API.

## 1. Thứ tự ưu tiên và mức sẵn sàng

| Ưu tiên | ID | Chỉ số | Hiện trạng | Việc bắt đầu được |
|---|---|---|---|---|
| 1 | E2 | ETH NUPL dẫn xuất | Raw đã có: `1 - 1/MVRV`; phụ thuộc cùng nguồn định giá với E7 | Chốt hợp đồng diagnostic và phần còn thiếu ở JSON/UI |
| 2 | E4 | ETH Fee Activity Multiple | `FeeTotNtv` có sample HTTP 200, 3/3 ngày; chưa audit full history | Audit lịch sử phí ETH, thành phần phí và quyền dùng |
| 3 | E9 | ETH NVT proxy | `TxTfrValAdjUSD` có catalog ETH nhưng sample Community trả 403 | Xác minh đường dữ liệu được phép truy cập và licence |
| 4 | E3 | ETH realized-value age ratio | Chưa xác minh endpoint/lịch sử age bands ETH; RHODL tham chiếu hiện chỉ có bằng chứng BTC | Audit metadata, age bands và phương pháp tài khoản ETH |
| 4 | E8 | ETH dormancy/spending proxy | Chưa xác minh entitlement/history dormancy ETH; `SplyAct1yr` sample trả 403 | Audit nguồn dormancy account-based và định nghĩa tuổi ETH |

Ưu tiên triển khai E2 rồi E4; audit nguồn E9/E3/E8 có thể làm độc lập trong lúc chờ các dependency nghiên cứu. Một sample truy cập được chưa chứng minh có dữ liệu đủ dài hoặc quyền phát hành. E2 giữ vai trò diagnostic, không tự thêm thành phiếu độc lập cạnh E7.

## 2. Task chung và dependency

Task cha **Q04 vẫn `TODO`**, dependency D05 đã `DONE`, Q02 còn `IN_PROGRESS`. Có thể chuẩn bị source contract và audit dữ liệu ngay; khóa protocol đánh giá mở rộng sau khi hoàn tất correlation/ablation/regime của Q02. Không phải chờ đủ cả năm nguồn mới nghiên cứu một ứng viên đã đạt cổng dữ liệu.

| ID | Trạng thái | Dependency | Công việc và nghiệm thu |
|---|---|---|---|
| X00 | DONE | D05 | Lập mẫu source contract cho từng ứng viên: endpoint/asset/đơn vị/UTC, thành phần dữ liệu, coverage/gaps, lag/vintage/revision, quyền cache/chart/derived/CSV và manifest SHA-256. Unknown ghi rõ; không gán `retrieved_at` thành `source_available_at`. |
| X01 | BLOCKED | Q02, X00, source/spec đã audit của ứng viên | Khóa config và ADR nghiên cứu riêng trước khi code/chạy đánh giá: công thức, chiều tín hiệu, warm-up, normalizer nhân quả, nhóm/trọng số nếu có composite, baseline, success rule và giới hạn thử tham số. Holdout Core đã xem kết quả chỉ dùng exploratory; đánh giá xác nhận cần holdout mới hoặc prospective. Chưa gán một version extended chính thức trong phiên lập task. |
| X02 | BLOCKED | Engine/test và quyết định nghiên cứu của ứng viên, quyền phát hành nguồn đó | Với ứng viên được chấp nhận ở mức phù hợp: cập nhật schema/manifest/JSON/CSV/UI, daily adapter riêng, snapshot R2 private và readback, immutable release/revision; kiểm local và production theo DEPLOYMENT. ADR ghi phạm vi Experimental hoặc sản phẩm vận hành. Gate vận hành đầy đủ S04/M06/O01/O03/O04 vẫn theo HANDOFF. |

X01/X02 áp dụng **theo từng ứng viên**; E2 có thể được công bố dưới vai trò diagnostic mà không trở thành thành phần composite. Đổi provider, đơn vị, thành phần, trọng số hoặc chuẩn hóa cần methodology version mới; giữ nguyên lịch sử Core đã công bố.

## 3. E2 — ETH NUPL dẫn xuất

| ID | Trạng thái | Dependency | Công việc và nghiệm thu |
|---|---|---|---|
| E2-01 | DONE | D05, M03 | Kiểm kê raw diagnostic đã có và chốt contract: `1 - 1/CapMVRVCur`, cùng provider/ngày/snapshot với E7; raw có thể âm; missing/invalid trả null có reason. Ghi rõ derived NUPL và quan hệ với MVRV, không trình bày như series NUPL độc lập từ provider. |
| E2-02 | BLOCKED | E2-01, X01 | Nếu cần điểm 0–100, triển khai normalizer diagnostic theo protocol riêng; kiểm prefix/future shock, warm-up/null và tương quan với E7. Ghi quyết định giữ raw hay có thêm điểm chuẩn hóa; không thêm trọng số chính thức vì có thêm card. |
| E2-03 | BLOCKED | E2-02, X02 áp dụng cho diagnostic | Xuất JSON/CSV và card/series diagnostic: raw và normalized phân biệt rõ, nguồn/ngày/version/null nhất quán. Kiểm UI và engine khớp; custom mode và composite chính thức không tự nhận thêm E2. |

Không viết lại hàm raw như thể chưa có. Phần chưa hoàn thành là contract đầy đủ, chuẩn hóa nếu được chọn và tích hợp public đúng vai trò.

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
| E9-01 | TODO | D05 | Xác minh entitlement của `TxTfrValAdjUSD` hoặc nguồn thay thế cụ thể: ETH daily, định nghĩa adjusted transfer value, coverage và quyền nghiên cứu/public/derived/CSV. Lưu evidence 403 hiện có. Nếu cần trả phí, chuẩn bị metric/plan/coverage/licence/báo giá thực để người dùng quyết định; không tự mua. |
| E9-02 | BLOCKED | E9-01, X00 | Tải full history và audit cặp vốn hóa/transfer value cùng provider, currency và ngày UTC. Document filters cho internal transfers/contracts/bridge/MEV, revision và gaps; mẫu số phải dương. Nguồn mới là candidate dataset có provenance riêng. |
| E9-03 | BLOCKED | E9-02, X01 | Implement giả thuyết đã khóa `ln(M/SMA90(adjusted_native_transfer_value_USD))` cùng normalizer causal; kiểm rolling calendar, missing/zero, đơn vị và prefix. Không đổi sang volume chưa điều chỉnh mà giữ cùng định nghĩa/version. |
| E9-04 | BLOCKED | E9-03 | Báo cáo utility tăng thêm, correlation/ablation, độ ổn định và sai lệch transfer value. ADR nhận/giữ Experimental/loại; tên công khai là NVT proxy, không gọi là CVDD. |

## 6. E3 — ETH realized-value age ratio

| ID | Trạng thái | Dependency | Công việc và nghiệm thu |
|---|---|---|---|
| E3-01 | TODO | D05 | Xác minh endpoint/metadata ETH realized-cap age bands hoặc realized-cap HODL waves, plan/entitlement/history và licence. Cần bằng chứng asset ETH thực; tài liệu RHODL BTC không đáp ứng task. |
| E3-02 | BLOCKED | E3-01, X00 | Audit snapshot lịch sử và đặc tả nhóm trẻ/già, cách định tuổi/realized value account-based, đơn vị, lag/warm-up, mẫu số và chiều tín hiệu. Giải thích ảnh hưởng staking, hợp đồng và self-transfers. Không suy ra age cohorts chỉ từ aggregate MVRV. |
| E3-03 | BLOCKED | E3-02, X01 | Implement công thức ratio đã được khóa và normalizer; fixture cohorts tính tay, missing/zero, biến động cohort và prefix-invariance. Cohort schema/methodology provider đổi phải tạo candidate/version riêng. |
| E3-04 | BLOCKED | E3-03 | Đánh giá tính độc lập với E7/E2, utility và regime stability; ADR nhận/giữ Experimental/loại. Nếu không có nguồn đủ kiểm chứng, đóng nghiên cứu bằng evidence và quyết định loại hoặc đề xuất thay thế rõ nghĩa. |

## 7. E8 — ETH dormancy/spending proxy

| ID | Trạng thái | Dependency | Công việc và nghiệm thu |
|---|---|---|---|
| E8-01 | TODO | D05 | Xác minh ETH account-based dormancy/spending endpoint, entitlement, daily history và quyền sử dụng; document tuổi ETH, volume và đối tượng bị loại. `SplyAct1yr` chỉ là candidate active-supply, không đồng nghĩa dormancy. |
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
