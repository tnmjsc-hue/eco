# Engine và UI đánh giá chéo vĩ mô

[MACRO_PROBABILITY.md](MACRO_PROBABILITY.md) đặc tả mô hình ECO prospective theo regime cho ETH 7 ngày. Nhãn có điều kiện của v1 không thành phần trăm; cổng hiệu chỉnh/holdout riêng, chưa có mẫu đủ hạn thì probabilities=null. Không phải consensus thị trường.

Sidecar [MACRO_MARKET.md](MACRO_MARKET.md) thêm số đo thị trường theo ngày bằng protocol riêng `macro-market-v1.0.0`. Khối này xác minh input/parent/snapshot độc lập, không sửa fields `surprise` hoặc `market_confirmation` của assessment v1 và không dùng daily changes để xác nhận phản ứng do sự kiện.

Engine dùng đặc tả chuẩn [MACRO_CROSS_INDICATOR_RULES.md](MACRO_CROSS_INDICATOR_RULES.md), `macro-cross-v1.0.1` / `macro-assessment-v1.0.1`. Ngưỡng, reducer, bảng tài sản và thứ tự ưu tiên được đóng băng ở `configs/macro/macro-cross-v1.0.1.json`; SHA-256 canonical `7a8f1e8fb29a70978588a4ec320ddb0d96437c6a319600592e3cf0622a20f86a`. Không sửa ý nghĩa dưới cùng version.

## Luồng thực thi

1. `eco.calendar` tải nguồn chính thức, kiểm parser và backup raw vào R2 private/readback trước khi đổi calendar pointer.
2. `eco.macro_adapter` chỉ đọc body đã pin theo source URL/hash của parent. BLS ánh xạ bằng series ID; PCE core reparse nhãn bảng nguồn, không lấy vị trí trong `details`; claims dùng initial claims đã điều chỉnh mùa vụ và đổi số lượng sang nghìn. Mọi số chuẩn hóa là chuỗi Decimal. Thiếu body/metadata được ghi rõ và không tạo phiếu thay thế; body bị sửa hash làm toàn batch fail.
3. `eco.macro_assessment.assess(bundle, calendar, batch_status, as_of, previous_assessment, ruleset)` là hàm thuần, không IO hoặc đồng hồ. Caller cung cấp cutoff/status vintage đã pin. Engine kiểm hash/parent, chọn kỳ rồi vintage, chặn fallback từ kỳ lỗi, gom I/L/G/A và tạo output có provenance/rules/evidence.
4. `eco.macro_pipeline` ghi normalized bundle, status proof và ruleset theo hash trong `public/data/macro-assessment/inputs`. Assessment/manifest và records bất biến; pointer chỉ đổi cuối cùng, có lock và kiểm predecessor. Cache hiện hành giữ toàn bộ artifact gốc, kể cả timestamp/status proof. Status refresh ngoài artifact pin proof bất biến của lần kiểm nguồn mới, không thêm assessment/ledger. Lần batch sau bị lỗi dùng proof refresh mới nhất đã biết, thay vì lấy timestamp cũ trong assessment. Replay của một write bị ngắt giữ proof và bytes ban đầu.
5. UI xác minh checksum của assessment, manifest, calendar parent và ba input trước khi hiển thị. Card độc lập bộ lọc lịch. Actual không dùng màu USD đơn biến. Nếu lỗi mạng/hash, parent lệch, pipeline stale/unknown hoặc nguồn quá 48h, giữ ngày/bản gốc và hiện “Chưa đủ bằng chứng” cho nhãn tài sản. Trình duyệt chỉ kiểm tình trạng đủ mới; không tính lại regime.

Raw không vào frontend. Sidecar công khai chỉ giữ các số tổng hợp chính thức, metadata, URL/hash và output nghiên cứu phi thương mại; không có consensus, credential hoặc body nguồn. Không thay methodology/điểm ETH.

## Metadata BEA và giới hạn adapter

PCE chỉ nhận bảng **Personal Income and Related Measures** với phép đổi từ tháng liền trước và hai tên tháng khớp kỳ. Provider contract của các thước đo featured PIO theo [BEA Statistical conventions](https://www.bea.gov/news/pio-release-additional-information), và bảng giá tương ứng [NIPA 2.8.7](https://apps.bea.gov/iTable/?reqid=19&step=3&isuri=1&1921=survey&1903=71). `definition_source_url` ghi nguồn định nghĩa; source hash vẫn pin body bản tin chứa số, không phải nội dung một trang định nghĩa tải ở thời điểm replay. Thay bảng/định nghĩa cần parser version mới và audit. PCE m/m là percent change theo tháng, không đổi thành annualized rate.

GDP phải chứng minh previous thuộc quý liền trước, không phải estimate cùng quý. Các bản legacy có usable_at trùng nhau nhưng khác số và chưa có lineage bị loại `ambiguous_vintage`; không chọn theo event date để giả lập lúc đã biết revision. Một vintage mới có first-seen ledger thật có thể giải quyết ambiguity. Trade chỉ là bối cảnh, không bỏ phiếu USD.

Adapter `official-macro-observations-v1.0.1` sửa metadata lineage sau lượt chạy thật: hash phản hồi BLS có thể đổi trong khi actual/previous giữ nguyên. Thay body/hash/parser được ghi như thay snapshot; chỉ cặp số thay đổi cùng kỳ mới là numeric revision. Migration parser patch với số/hash pin giống nhau giữ thời điểm đã biết, không kế thừa lineage chưa được chứng minh từ v1.0.0. GDP ambiguous dùng placeholder null, giữ mọi candidate ID trong exclusions; không hiển thị một cặp số được chọn theo thứ tự ID. Bản công bố trước sửa lỗi vẫn nguyên bytes, correction tạo assessment mới.

Legacy initial inputs dùng calendar.generated_at làm usable_at; không khẳng định biết số vào giờ công bố lịch sử. Giá trị/source/parser mới có observation ID mới và first_seen_at mới; giá trị giữ nguyên không bị reset tuổi kỳ. Khi source outage và parent immutable giữ nguyên, có thể dùng lại normalized bundle đã xác minh trong manifest trước; pipeline freshness vẫn là cổng độc lập.

## Chạy và kiểm tra

```text
python -m pip install --disable-pip-version-check pypdf==6.10.0
python -m eco.calendar
python -m eco.macro_pipeline
python -m unittest discover -s tests -p 'test_macro*.py' -v
node --test tests/macro.test.mjs tests/calendar.test.mjs
node scripts/check-calendar.mjs http://127.0.0.1:8877/
```

Lệnh calendar cần R2 credential trong process env; macro chỉ dùng parent/body private đã pin và các proof công khai. Không chạy calendar local nếu chưa có backup credential. Browser QA cần Playwright/Chromium hoặc `PLAYWRIGHT_MODULE`/`CHROME_EXECUTABLE`. Workflow `economic-calendar.yml` chạy macro cả khi calendar batch lỗi để cập nhật cổng nguồn cũ; chỉ stage allowlist đã qua kiểm thử. Deploy verifier kiểm cả calendar, macro pointer/status, sáu asset của assessment và proof refresh; bot commit không tự kích hoạt CI push nên workflow tự kiểm trước phát hành.

## Nghiệm thu T01–T48

| Nhóm fixture | Bằng chứng thực thi |
|---|---|
| T01–T33, T37–T40, T43–T48 | `tests/test_macro_assessment.py`: Decimal/orientation, coverage/reducer, semantics, future input, chọn kỳ/vintage, freshness, latest batch/peers, transition và ID/predecessor; router production so 125 expected entries cố định trong oracle độc lập |
| T34–T36, T45–T46 | `tests/test_macro_pipeline.py`: input hash, truncated parent, giữ pointer, lock/path guards, cache, immutable records và replay write bị ngắt |
| Adapter | Cùng file: PCE headline/core/period/definition, sai bảng không được chứng minh metadata, raw tamper và first-seen/revision. Parser BLS/DOL cơ sở còn có `tests/test_calendar.py`; private snapshot integration chỉ chạy local với body đã restore/readback hash |
| T41–T42 | `tests/macro.test.mjs` kiểm schema/hash/parent/template; `scripts/check-calendar.mjs` chạy browser 4 viewport, 8 locale, đổi timezone/filter, mạng/checksum fail, giữ ngày gốc, không gọi provider và hồi quy Core 10 |

Đây là đánh giá có điều kiện theo policy ECO, chưa phải mô hình phản ứng thị trường được kiểm định. Missing/unsupported/expired khác neutral; coverage không phải xác suất. Các locale ngoài tiếng Việt có thể fallback tiếng Anh cho copy macro mới; số/ngày dùng locale và múi giờ đang chọn.

Kết quả chạy/deploy thực tế và bước tiếp theo ghi ở [HANDOFF](HANDOFF.md). Các ca tổng hợp là fixture kiểm thử, không được đưa vào live data.
