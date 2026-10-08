# Rà soát đặc tả đánh giá chéo macro — 2026-10-09

**Cập nhật bản sửa 2026-10-09 — RESOLVED_IN_SPEC_V1.0.1.** Cả bốn finding bên dưới đã được xử lý trong [đặc tả v1.0.1](MACRO_CROSS_INDICATOR_RULES.md). Phần review v1.0.0 được giữ làm lịch sử; trạng thái CHANGES_REQUIRED bên dưới chỉ áp dụng bản cũ tại `137511f`.

| Finding | Cách sửa | Kiểm tra hồi quy |
|---|---|---|
| F01 | Tách state_id/assessment_id; assessment gắn predecessor; chỉ cache khi state bằng bản hiện hành; replay giữ bytes; publisher có lock/CAS | T45/T46: fresh → stale → fresh có ba assessment; replay/cache, predecessor tương lai và collision bị kiểm |
| F02 | Pin status vintage/hash; chỉ chọn known_at trong cutoff, kiểm check_at ≤ known_at ≤ as_of | T47/T48: timestamp tương lai, missing/naive, chronology và biên 0/48 giờ; thêm future status không đổi cutoff cũ |
| F03 | T15 giới hạn A không mixed, T43 riêng cho conflict dù I thiếu | Oracle cố định 125 trạng thái đối chiếu regime và asset labels, thêm gates và override |
| F04 | T38 có input ngoài batch; T44 gồm nhiều metric/event cùng latest batch; ghép before/after theo metric | Fixture batch membership và replacement NFP/unemployment, giữ ID cũ/mới |

Bộ kiểm [test_macro_cross_spec.py](../tests/test_macro_cross_spec.py) được CI hiện hữu chạy qua unittest discovery. [Oracle JSON](fixtures/macro-cross-v1.0.1.json) chứa 125 expected entries cố định, không tạo expected bằng router. [Mô hình kiểm đặc tả](../scripts/check_macro_cross_spec.py) chỉ hỗ trợ review hợp đồng; agent không dùng nó làm engine production. Các test không nghiệm thu adapter, toàn bộ 48 tình huống UI/engine hoặc publisher IO. Engine/UI/publisher vẫn TODO, tiếp theo CAL-XRULE-02; kết quả lệnh và phát hành ghi trong HANDOFF.

## Review gốc v1.0.0 (giữ nguyên bằng chứng)

**Kết luận: CHANGES_REQUIRED_BEFORE_IMPLEMENTATION.** Phần tài liệu đã commit/deploy đúng, nhưng đặc tả chưa nhất quán hoàn toàn để giao agent triển khai. Engine/UI/publisher vẫn TODO. Các finding dưới đây thuộc hợp đồng thiết kế, chưa phải lỗi engine đang chạy trên production.

Phạm vi: `docs/MACRO_CROSS_INDICATOR_RULES.md` tại commit `137511f70d6e8dd57f8ab6592d44eab97dbd40e9`, SHA-256 `422c11f72ac9958f1c8d62fc13d9c0fa97aae5e7a9d21754c2f5eb6b641f994b`. Số dòng bên dưới thuộc bản này. Rà soát sau yêu cầu kiểm tra lại task vừa hoàn tất; chưa sửa quy tắc hoặc phát hành bản mới trong phiên review.

## F01 — P1: ID của trạng thái xung đột với lịch sử chuyển trạng thái

Vị trí: §11.3, dòng 351–353; liên quan §10, dòng 289–291.

`assessment_id` bỏ qua thời gian và predecessor, trong khi artifact chứa `as_of`, `context_transition`, `change_reason` và `previous_assessment_id`. Chuỗi dưới đây có thể xảy ra với cùng calendar/bundle và observation vẫn còn freshness:

1. A: nguồn vừa kiểm tra, assessment đầu tiên; `change_reason=initial_assessment`.
2. B: quá 48 giờ không kiểm nguồn thành công; chuyển `R_STALE`, ID mới.
3. C: nguồn được kiểm lại thành công, dữ liệu không đổi; mọi field identity trở về A, nhưng predecessor thực là B và reason phải là `pipeline_status_changed`.

C có cùng ID với A. Nếu tạo artifact theo predecessor mới thì cùng ID có nội dung khác, vi phạm bất biến. Nếu dùng lại nguyên A thì transition/as_of của A không mô tả lần phục hồi từ B. Đặc tả chưa giải quyết xung đột này.

Hướng sửa cần chốt: tách ID trạng thái ngữ nghĩa khỏi record công bố/chuyển trạng thái, hoặc đưa predecessor vào identity của artifact được công bố. Cache chỉ tái sử dụng khi không có thay đổi so với bản hiện hành. Thêm fixture A → B → A và replay cùng predecessor; không ghi đè artifact đã công bố.

## F02 — P2: Cutoff chưa áp dụng cho trạng thái kiểm nguồn

Vị trí: §5.2, dòng 120; §5.1 chỉ nêu cutoff của observation.

Theo công thức hiện tại, `as_of=2026-10-09T00:00:00Z` và `last_successful_source_check_at=2026-10-10T00:00:00Z` cho tuổi nguồn -24 giờ, nên `pipeline_stale=false`. Một status từ tương lai có thể làm kết quả tại cutoff cũ chuyển từ stale sang assessed, dù observation tương lai đã bị lọc đúng.

Hướng sửa: pin vintage của batch status, chỉ chấp nhận status đã biết tại cutoff và `last_successful_source_check_at <= as_of`; nếu không có status hợp lệ thì dùng unknown hoặc từ chối input theo policy được chốt. Bổ sung kiểm biên 0/48 giờ và timestamp tương lai.

## F03 — P2: T15 trái thứ tự ưu tiên của bảng kết luận

Vị trí: §9.1, dòng 231–232; T15, dòng 415.

Counterexample khả thi: `I=unknown`, `L=positive`, `G=negative`. Có hai trục dùng được; reducer cho `A=mixed`, nên §9.1 phải chọn `R_CONFLICT`. T15 lại yêu cầu `R_ACTIVITY_ONLY` cho mọi trường hợp I unknown, L/G dùng được.

Trong không gian trừu tượng 125 tổ hợp, 16 trường hợp thỏa tiền đề T15, có 9 trường hợp phải là `R_CONFLICT` theo §9.1. Không nên thay engine để làm test xanh. Nếu giữ thứ tự ưu tiên hiện tại, thu hẹp T15 thành A không mixed và thêm fixture riêng cho conflict khi I thiếu.

## F04 — P2: T38 trái quy tắc batch chứa nhiều metric

Vị trí: §10, dòng 289; T38, dòng 438.

Khi NFP và unemployment cùng cập nhật trong một latest batch, §10 quy định `latest_batch_only`, kể cả nhiều metric. T38 lại yêu cầu `multiple_inputs_changed` khi nhiều input cùng đổi. Hai agent có thể viết hai kết quả khác nhau dù cùng đọc tài liệu.

Hướng sửa: tách fixture nhiều metric trong cùng latest batch và fixture có ít nhất một input đổi ngoài batch. Giữ danh sách changed observation IDs để xác minh, không suy luận nhân quả từ tên trạng thái.

## Bằng chứng kiểm tra và giới hạn

- Script kiểm tra tái lập local: `test-results/macro-spec-review/audit.py`; kết quả: `test-results/macro-spec-review/report.json`. Các file nằm trong thư mục Git ignored, không phải bộ test engine đã đưa vào CI. Script pin nội dung những clause liên quan và hash đặc tả, liệt kê 125 tổ hợp, kiểm đối xứng reducer L/G, tái lập bốn finding trên.
- 125/125 tổ hợp có đường xử lý: R01/R03/R04/R06/R07/R09 mỗi loại 5; R02/R05/R08 mỗi loại 3; R_ACTIVITY_ONLY 7; R_CONFLICT 66; R_INSUFFICIENT 13. Không gian này gồm G=mixed theo yêu cầu 5³; một signal GDP đơn lẻ hợp lệ thực tế không sinh mixed.
- Kết quả trước đây “125 tổ hợp PASS” chỉ chứng minh coverage của routing đã mô phỏng, chưa chứng minh tính nhất quán giữa tất cả clause/fixture. 42 dòng T01–T42 hiện là yêu cầu kiểm thử Markdown, chưa phải 42 test thực thi. CI hiện tại chưa có test riêng cho đặc tả macro này.
- Diff phát hành từ `d1aeac2` đến `137511f` chỉ có AGENTS, README, HANDOFF và đặc tả; AGENTS đã yêu cầu đọc và tuân thủ đặc tả. Không sửa public/runtime/data trong hai commit này.
- [CI 37815777445](https://github.com/tnmjsc-hue/eco/actions/runs/37815777445) completed/success tại đúng SHA `137511f70d6e8dd57f8ab6592d44eab97dbd40e9`; GitHub main vẫn là SHA này lúc kiểm tra.
- Cloudflare Pages deployment `42a651e5-b25e-49d2-a858-6bcb0c9a64ed`, production, success tại cùng SHA. Hai hostname `https://eco.tnmp.cloud/` và `https://eco-tnmp.pages.dev/`: index, latest Core, latest calendar và calendar status đều HTTP 200/hash khớp Git, 8/8. Evidence local: `test-results/macro-spec-review/production-check.json`.
- Không chạy lại toàn bộ engine/browser suite trong phiên chỉ review tài liệu; dùng kết quả CI đúng commit và kiểm lại bytes production. Chưa kiểm định dự báo thị trường hoặc nghiệm thu engine macro.

Task kế tiếp: sửa/chốt bốn hợp đồng trên, thêm kiểm tra tái lập vào repo và cập nhật trạng thái đặc tả/version trước CAL-XRULE-02. Nghiên cứu WLAB và trạng thái Git phân kỳ ở workspace gốc được giữ nguyên.
