# Quy tắc đánh giá chéo sự kiện kinh tế và tác động USD / vàng / crypto

Ngày soạn: **08/10/2026**; rà soát hoàn tất **09/10/2026**, giờ Việt Nam. Mã công việc: `CAL-XRULE-01`.

| Thuộc tính | Giá trị |
|---|---|
| Ruleset đề xuất | `macro-cross-v1.0.0` |
| Schema đầu ra đề xuất | `macro-assessment-v1.0.0` |
| Trạng thái | `SPEC_READY_IMPLEMENTATION_TODO` — đặc tả, chưa phải engine đang chạy |
| Nguồn đầu vào đã đối chiếu | Calendar `us-macro-calendar-v1.1.0`, schema `1.1.0`, remote commit `d1aeac2509e1f1d7ff9dba42fd38a5a5fb8f055b` |
| Sản phẩm | Nhận định có điều kiện về dữ liệu kinh tế mới nhất và bối cảnh liên chỉ số |
| Ngôn ngữ | Giải thích tiếng Việt; ID, enum và field tiếng Anh |

Đây là đặc tả chuẩn cho agent triển khai. **BẮT BUỘC**, **KHÔNG ĐƯỢC** và **CHỈ KHI** là yêu cầu kiểm thử được. Các ngưỡng và bảng quyết định dưới đây là lựa chọn thiết kế nghiên cứu của ECO, chưa được hiệu chỉnh theo khả năng dự báo giá. Agent không tự đổi chúng để có kết luận đẹp hơn.

## 1. Ý đồ sản phẩm

Người đọc cần nhận được năm câu trả lời:

1. Sự kiện có số liệu mới nhất là gì, thuộc kỳ nào, và số liệu thay đổi thế nào?
2. Chỉ số cùng nhóm xác nhận, mâu thuẫn hay chưa đủ dữ liệu để đối chiếu?
3. Lạm phát, lao động và tăng trưởng đang kết hợp thành bối cảnh nào?
4. Bối cảnh đó tạo lực hỗ trợ hoặc sức ép có điều kiện lên USD, vàng và crypto qua cơ chế nào?
5. Điều gì còn thiếu, điều gì sẽ làm nhận định đổi chiều?

Ví dụ ý đồ: trợ cấp thất nghiệp giảm nhẹ một tuần không đủ để kết luận lao động khỏe nếu NFP giảm tốc, tỷ lệ thất nghiệp tăng và JOLTS giảm. Lạm phát tăng trong bối cảnh đó cũng không cho phép kết luận đơn giản rằng cả USD tăng, vàng giảm và crypto giảm với cùng độ rõ ràng.

Engine phải xác định được kết quả chỉ từ input đã pin và ruleset. LLM không nằm trong đường quyết định, không tự phân tích tin tức hoặc sinh thêm luận cứ vào bản phát hành. Câu văn dùng template theo `rule_id` và số liệu có provenance.

## 2. Phạm vi v1 và các ranh giới

- Phạm vi bắt buộc: số liệu Mỹ đã có trong lịch ECO, so với kỳ trước; ba nhóm chính `inflation`, `labor`, `growth`; nhóm đối chiếu `producer_prices`, `weekly_claims`, `trade`.
- Cơ sở đánh giá duy nhất trong v1: `comparison_basis = previous_period`. `actual - previous` là thay đổi so với kỳ trước, **không phải surprise so với thị trường**.
- `forecast` hiện null. `surprise.status` luôn `unavailable`; không lấy forecast trên MQL5, không coi previous là forecast, không suy ra consensus từ màu hoặc tiêu đề.
- Kết quả tài sản là `supportive`, `adverse`, `mixed`, `neutral` hoặc `insufficient_evidence`. Không tính xác suất, mục tiêu giá, điểm mua/bán, leverage hay lợi nhuận kỳ vọng.
- Khung diễn giải là `macro_context_until_next_eligible_update`: bối cảnh cập nhật khi có dữ liệu hợp lệ mới. V1 không dự báo lợi suất trong 5 phút, một ngày hoặc một tuần.
- Lãi suất Fed, thông điệp FOMC, Treasury yields, real yields, USD index, dòng ETF và giá phản ứng chưa có adapter được duyệt trong scope này. `policy_observation.status = unavailable`, `market_confirmation.status = not_measured`. Đường truyền qua lãi suất chỉ là giả thuyết có điều kiện, không phải điều đã quan sát.
- Core 10 ETH tiếp tục dùng methodology riêng. Không đưa nhận định macro vào điểm Core 10, không lấy BTC thay ETH. Nếu UI đặt hai phần cạnh nhau, ghi rõ ngày và phiên bản riêng; không cộng phiếu MVRV/NUPL hoặc suy ra hướng ngắn hạn từ mức nóng/lạnh của Core 10.
- Stablecoin không thuộc nghĩa `crypto_risk_assets`. Nhận định macro chung không phải nhận định riêng về mọi token hoặc riêng về ETH.

## 3. Hợp đồng quan sát chuẩn hóa

Không chạy engine trực tiếp trên tiêu đề dịch hoặc màu của hàng lịch. Adapter phải tạo bản ghi theo schema mới. Schema calendar 1.1.0 thiếu một số field dưới đây; agent phải bổ sung sidecar chuẩn hóa có hash hoặc phát hành calendar schema mới. Không sửa bytes của release calendar đã công bố.

| Field bắt buộc | Kiểu / quy tắc |
|---|---|
| `observation_id` | ID bất biến của metric + kỳ + vintage + source hash |
| `event_id`, `release_family_id` | Sự kiện gốc và họ công bố; NFP/thất nghiệp cùng `employment_report` |
| `metric_id` | Một ID trong bảng §4; không ánh xạ bằng substring tùy ý |
| `provider`, `series_id` | Provider cố định; ID series khi có, null có lý do nếu lấy bản tin |
| `actual`, `previous` | Decimal dưới dạng chuỗi chuẩn hoặc null; từ chối bool, NaN, Infinity |
| `unit`, `transform`, `seasonal_adjustment` | Khớp chính xác registry; thiếu hoặc sai thì loại bản ghi |
| `reference_period`, `previous_period` | Tháng `YYYY-MM`, quý `YYYY-Qn`, hoặc ngày kết thúc tuần `YYYY-MM-DD` |
| `previous_semantics` | Phải là `prior_period_same_measure`; revision của cùng kỳ dùng field riêng |
| `period_end` | Ngày cuối tháng/quý hoặc ngày kết thúc tuần, UTC calendar date |
| `scheduled_at` | Timestamp lịch gốc; chỉ dùng trình bày/thứ tự sự kiện, không chứng minh availability |
| `source_published_at` | Timestamp công bố thực đã xác minh hoặc null; không chép từ lịch dự kiến |
| `source_retrieved_at` | Lúc tải body nguồn thực, không đổi khi dùng cache |
| `first_seen_at` | Lúc hệ thống lần đầu ghi nhận đúng content version, hoặc null với dữ liệu nhập legacy |
| `usable_at`, `knowledge_basis` | Quy tắc §5; bắt buộc timestamp UTC và căn cứ truy vết |
| `data_status` | `official_release` hoặc `current_vintage_period_match`; scheduled không phải quan sát |
| `source_url`, `source_sha256`, `calendar_release_id` | Provenance về đúng bản tin/body/release đã verify |
| `revision_of` | Observation ID cũ khi sửa cùng kỳ; null nếu không có bằng chứng revision |
| `quality_flags` | Mảng enum; ít nhất giữ preliminary, current-vintage, missing semantics nếu có |

Điều kiện so sánh: previous phải là cùng thước đo, cùng đơn vị, cùng điều chỉnh mùa vụ và đúng kỳ liền trước. Ví dụ NFP actual = số việc làm tăng trong tháng này; previous = số việc làm tăng trong tháng trước, không phải tổng số người làm việc. GDP previous phải là tăng trưởng quý trước, không phải estimate trước của cùng quý. Một rate từ `0.1%` lên `0.4%` tăng **0.3 điểm phần trăm**, không tăng 0.3%.

`previous` có thể là giá trị đã revised trong cùng bản tin/current vintage, nhưng phải ghi nguồn. `revision_delta` chỉ tính khi có hai observation bất biến của **cùng metric và cùng kỳ**; không lấy `actual - previous` để tính revision.

Đơn vị chuẩn hóa phải có quy tắc chuyển đổi chính xác: jobs/claims chia 1.000 khi nguồn là người/lượt; không nhân/chia lại khi nguồn đã là nghìn. `pp` là đơn vị delta của rate đo bằng percent; `percent_saar` không đổi thành m/m.

`previous_period` phải bằng tháng trước, quý trước hoặc ngày kết thúc tuần trừ đúng 7 ngày theo tần suất, kể cả biên năm. Provider enum dùng `bls`, `bea`, `dol` đúng bảng registry; `seasonal_adjustment=SA`. `transform` cố định: CPI/PCE/PPI = `percent_change_mom`; NFP = `first_difference_monthly_level`; unemployment/JOLTS/claims/trade = `level`; GDP = `percent_change_qoq_saar`. Transform mô tả số đã chuẩn hóa, không yêu cầu engine áp dụng thêm một lần nữa.

Engine dùng nguyên giá trị public đã xác minh của calendar/source adapter; không làm tròn thêm trước phép trừ/epsilon. Khi adapter dựng lại CPI/PPI hoặc NFP từ series mức, phải tái hiện đúng transformation/precision của calendar version được pin và có golden fixture. Không trộn actual tính từ raw chưa làm tròn với previous đã làm tròn trong release. Thay precision đầu vào cần source/calendar version phù hợp và ruleset version mới nếu làm đổi classification.

## 4. Registry metric và ngưỡng đóng băng

`epsilon` là vùng loại chuyển động nhỏ do ECO đặt ra, **không phải** sai số thống kê hay ngưỡng được cơ quan nguồn xác nhận. Không học ngưỡng trên snapshot ví dụ §13. Đổi registry, vai trò, epsilon, chiều hoặc freshness cần ruleset version mới.

| `metric_id` | Nguồn / trường hiện có | Định nghĩa / đơn vị chuẩn | Chiều `orientation` | `epsilon` | Vai trò |
|---|---|---|---|---:|---|
| `cpi_headline_mom_sa` | BLS `CUSR0000SA0`, kind `cpi` | Thay đổi CPI m/m đã SA, `percent` | +1 = áp lực giá tăng tốc | 0.1 pp | Slot CPI của inflation |
| `pce_headline_mom_sa` | BEA kind `pce`, `actual` | Headline PCE m/m SA, `percent` | +1 | 0.1 pp | PCE fallback khi core không hợp lệ |
| `pce_core_mom_sa` | BEA PCE, detail Core PCE | Core PCE m/m SA, `percent` | +1 | 0.1 pp | PCE ưu tiên |
| `ppi_final_demand_mom_sa` | BLS `WPSFD4`, kind `ppi` | Final-demand PPI m/m SA, `percent` | +1 | 0.1 pp | Đối chiếu chi phí sản xuất |
| `nfp_change_k_sa` | BLS `CES0000000001`, kind `jobs` | Mức tăng NFP tháng, `thousand_jobs` | +1 = đà lao động cải thiện | 25 nghìn | Slot employment report |
| `unemployment_rate_sa` | BLS `LNS14000000`, detail unemployment | Tỷ lệ thất nghiệp SA, `percent` | -1 = tỷ lệ giảm biểu thị chiều cải thiện | 0.1 pp | Cùng slot employment report |
| `jolts_openings_k_sa` | BLS `JTS000000000000000JOL`, kind `jolts` | Số vị trí tuyển dụng SA, `thousand_jobs` | +1 | 100 nghìn | Slot JOLTS của labor |
| `initial_claims_k_sa` | DOL kind `claims` | Initial claims tuần SA, `thousand_claims` | -1 = claims giảm biểu thị chiều cải thiện | 10 nghìn | Đối chiếu tuần; không tự đảo nhóm labor |
| `real_gdp_qoq_saar` | BEA kind `gdp` | Tăng trưởng GDP thực q/q annualized SA, `percent_saar` | +1 = tăng tốc | 0.2 pp | Slot growth |
| `trade_balance_bn_sa` | BEA kind `trade` | Cán cân hàng hóa/dịch vụ SA, `billion_usd` | Không gán | Không áp dụng | Thông tin bổ sung; không bỏ phiếu tài sản |

Adapter BLS lấy metric bằng `series_id`; adapter BEA/DOL phải chứng minh biến, đơn vị và kỳ từ bản tin. Các detail hiện chỉ có `label` phải được gán `metric_id` ở parser có kiểm thử, không dùng thứ tự `details[0]` hoặc text đã dịch trong engine. Nguồn PCE ưu tiên core là lựa chọn để đọc áp lực nền; mục tiêu 2% của Fed là headline PCE theo năm, không được đem so với core m/m trong bảng này.

Các metric chưa có adapter như CPI core, tiền lương, participation, continuing claims, ISM/PMI, retail sales, industrial production, real consumption và Fed target giữ `unsupported_metric`. Một sự kiện có trên lịch không đồng nghĩa có số liệu đánh giá. Muốn mở rộng, bổ sung nguồn/quyền/contract/fixtures và version; không gán số giả.

## 5. Thời gian, vintage, freshness và chọn bản ghi

### 5.1 Cutoff bắt buộc

Hàm nhận `as_of` UTC từ caller; không gọi đồng hồ hệ thống bên trong engine. Chỉ dùng observation có `usable_at <= as_of`, `scheduled_at <= as_of`, `period_end <= date_utc(as_of)`, và source hash đã verify.

- Với ledger mới: `usable_at = max(first_seen_at, source_published_at nếu có)`. `first_seen_at` của một revision là thời điểm thấy revision đó, không kế thừa timestamp của giá trị cũ.
- Với release legacy đã pin: `usable_at = calendar.generated_at`, `knowledge_basis = legacy_snapshot_generated_at`, `first_seen_at = null`, `history_mode = latest_vintage_context`. Đây là mốc bảo thủ để dùng snapshot từ lúc tạo, không khẳng định hệ thống đã nhìn thấy số liệu vào ngày sự kiện lịch sử.
- Khi có bản công bố đầu ra thực: ledger ghi `published_at` riêng. Việc có ledger không biến các input current-vintage thành vintage tại thời điểm sự kiện.
- Cache hit/HTTP 304/`checked_at` không làm số liệu thành observation mới và không kéo dài tuổi kỳ quan sát.

### 5.2 Freshness cố định

`age_days = date_utc(as_of) - period_end`, tính số ngày lịch. Dữ liệu đủ mới nếu `0 <= age_days <= max_age_days`:

| Tần suất | Metric | `max_age_days` |
|---|---|---:|
| Tuần | Initial claims | 21 |
| Tháng | CPI/PCE/PPI/NFP/unemployment/JOLTS/trade | 75 |
| Quý | GDP | 180 |

Tại đúng biên vẫn hợp lệ; thêm một ngày là `stale_observation`. Ngưỡng này là policy kỹ thuật v1, không bảo đảm thông tin kinh tế chưa bị thay thế. Nếu lịch có một sự kiện mới hơn đã qua giờ nhưng chưa có actual, giữ bản hợp lệ cũ với `newer_scheduled_result_pending`; không tự xác nhận nguồn đã công bố hoặc số cũ là số mới.

`pipeline_stale = as_of - last_successful_source_check_at > 48 giờ`. Field này phải từ batch status đáng tin, không lấy thời gian render; thiếu timestamp → `pipeline_status_unknown`. Cả hai trường hợp làm assessment `stale_context`, các asset conclusion thành `insufficient_evidence`; bản tốt cũ vẫn hiển thị dưới nhãn ngày gốc. Mốc đúng 48 giờ chưa stale. Observation vẫn phải qua freshness riêng dù nguồn vừa được kiểm.

### 5.3 Chọn mới nhất và revision

1. Kiểm provenance, timestamp, schema và semantics. Giữ danh sách rejected với reason; không silently drop. Một kỳ mới nhất đã xác định được metric/kỳ/usable_at nhưng actual, previous hoặc semantics lỗi vẫn phải có placeholder để chặn fallback kỳ cũ. Sai hash cấp release là lỗi toàn input; không tạo placeholder từ body chưa xác thực.
2. Với mỗi `(metric_id, reference_period)`, chọn vintage có `usable_at` lớn nhất trong cutoff. Nếu đồng timestamp nhưng khác giá trị mà không có quan hệ revision xác minh: đánh dấu `ambiguous_vintage`, loại metric/kỳ đó; không chọn tùy ý theo ID.
3. Với mỗi metric, chọn kỳ mới nhất trong các bản đã biết, rồi mới kiểm actual/previous/freshness. Nếu kỳ mới nhất bị thiếu hoặc lỗi, không lùi sang kỳ cũ để tạo tín hiệu mới; có thể hiển thị kỳ cũ như background nhưng không cho bỏ phiếu.
4. Bản revision của cùng kỳ GDP thay thế slot của kỳ đó; các estimate không phải nhiều phiếu. `revision_only` là thông báo thay đổi vintage, không phải một kỳ tăng trưởng mới.
5. De-duplicate event và block BLS indicators theo metric/kỳ/vintage/source hash. Cùng một quan sát xuất hiện ở hai nơi chỉ có một contribution.
6. Khi đối chiếu NFP và unemployment, bắt buộc cùng tháng. CPI/PCE và employment/JOLTS được chênh tối đa một tháng; lớn hơn thì chỉ giữ slot có tháng mới hơn, slot cũ chuyển background và gắn `period_gap_excluded`. Chênh một tháng vẫn gắn `period_misaligned`, không gọi là xác nhận cùng kỳ.
7. GDP và nhóm tháng được ghép như bối cảnh khác tần suất, với `mixed_frequency_context`; luôn ghi quý/tháng riêng. Không nội suy GDP ra tháng hoặc gọi tất cả là số liệu của cùng một ngày.

## 6. Tín hiệu đơn: hướng, mức và điều chưa biết

Với metric có orientation và đủ actual/previous hợp lệ:

```text
delta = Decimal(actual) - Decimal(previous)
signed_delta = orientation * delta
if signed_delta >= epsilon: direction = positive
else if signed_delta <= -epsilon: direction = negative
else: direction = flat
```

So sánh bằng Decimal, không dùng số đã định dạng theo locale hoặc float gần biên. Nếu nhận JSON number legacy, parser chuyển sang decimal text chuẩn trước tính, không lấy phần đuôi nhị phân làm dữ liệu. Backend là nguồn kết quả chính; frontend không tính lại rule bằng JavaScript floating point.

| Giá trị `direction` | Nghĩa |
|---|---|
| `positive` | Áp lực giá tăng tốc với nhóm inflation; đà hoạt động cải thiện với labor/growth |
| `negative` | Áp lực giá giảm tốc; hoặc đà hoạt động yếu đi, tùy nhóm |
| `flat` | Có cặp số hợp lệ và thay đổi nằm trong vùng epsilon; không có nghĩa không tác động thị trường |
| `unknown` | Không đủ điều kiện tính; delta có thể null, có reason |

Trường `level_context` giữ hiện trạng để tránh lẫn mức với tốc độ: NFP actual > 0 nhưng delta âm → `jobs_still_added_but_slower`; GDP actual > 0 nhưng delta âm → `positive_growth_decelerating`; rate lạm phát vẫn > 0 nhưng delta âm → `prices_still_rising_more_slowly`. Với NFP/GDP actual bằng 0 hoặc âm, lưu riêng `zero`/`negative` theo actual. Không gọi GDP đang co lại chỉ từ delta âm, hoặc giá tiêu dùng đang giảm chỉ từ lạm phát giảm tốc.

Thất nghiệp giảm chưa đủ để kết luận mọi mặt lao động tốt lên vì participation chưa có. NFP âm được ghi rõ mất việc; không dùng nhãn cải thiện tốc độ để che mức âm. `level_context` là cảnh báo diễn giải; trong v1 nó không âm thầm thay direction hay bảng tài sản. Khi có NFP actual < 0 hoặc GDP actual < 0, gắn thêm `negative_activity_level`, áp dụng chốt crypto ở §9.

Trade chỉ có `delta` và mô tả thâm hụt thu hẹp/mở rộng khi có cặp hợp lệ. Không gán bullish USD chỉ vì cán cân tăng: nhập khẩu giảm có thể phản ánh cầu yếu; chưa có cấu phần để phân biệt.

## 7. Gom nhóm để tránh đếm lặp

### 7.1 Reducer dùng chung

`reduce_directions(items)` không tính trung bình:

1. Có child `mixed` → `mixed`.
2. Cùng có ít nhất một `positive` và một `negative` → `mixed`.
3. Chỉ có positive cùng flat/unknown → `positive`.
4. Chỉ có negative cùng flat/unknown → `negative`.
5. Có flat, không có positive/negative/mixed → `flat`.
6. Không có input dùng được → `unknown`.

Unknown được bỏ khỏi phép so hướng, nhưng vẫn nằm trong coverage và missing reasons. Hai chiều đối nghịch không được triệt tiêu thành flat. Nhiều flat không xác nhận một positive/negative; phải giữ số lượng slot thật cùng chiều.

### 7.2 Nhóm inflation `I`

- Hai slot bỏ phiếu: `cpi` và `pce`.
- Slot PCE lấy core khi core hợp lệ; chỉ fallback headline khi core không hợp lệ. Cả core/headline đều hợp lệ và trái dấu positive/negative → slot PCE `mixed`, reason `core_headline_divergence`. Nếu một flat thì giữ chiều của core theo ưu tiên, không cộng hai phiếu.
- `I = reduce_directions([CPI, PCE])` sau kiểm kỳ §5.3.
- PPI là supporting context: cùng chiều → `producer_consumer_aligned`; đối chiều với I positive/negative → `producer_consumer_divergence`; flat/unknown thì chỉ ghi giá trị/trạng thái. PPI không thay I và không cứu coverage khi CPI/PCE đều thiếu.
- CPI và PCE có liên hệ và cấu phần chồng lấn; hai slot cùng chiều chỉ cho phép nói “hai thước đo tiêu dùng cùng chiều”, không phải “hai bằng chứng thống kê độc lập”.

### 7.3 Nhóm labor `L`

- Slot `employment_report = reduce_directions([NFP, unemployment])`, cùng tháng. Một metric thiếu thì dùng metric còn lại với `partial_employment_report`. Nếu tháng khác nhau, giữ metric thuộc tháng mới hơn; metric cũ background, gắn `employment_period_mismatch`.
- Slot thứ hai là JOLTS. `L = reduce_directions([employment_report, JOLTS])` sau kiểm khoảng cách tháng.
- NFP và unemployment trái chiều → employment_report mixed; JOLTS không được bỏ phiếu để xóa mâu thuẫn đó. Chỉ hiển thị nguồn mâu thuẫn để người dùng đọc.
- Claims tuần so với L: cùng chiều → `weekly_labor_aligned`; đối chiều → `weekly_labor_divergence`; flat → `weekly_move_below_threshold`; L unknown → `weekly_only_context`.
- Claims không phải slot bỏ phiếu của L trong v1 vì một tuần dễ nhiễu. Claims thay đổi mạnh phải được nhắc, nhưng không tự đảo kết luận tháng. Muốn dùng trung bình bốn tuần hoặc persistence phải mở version có lịch sử tuần và quy tắc riêng.

### 7.4 Nhóm growth `G` và hoạt động `A`

- `G` là direction của GDP thực quý mới nhất hợp lệ, một slot duy nhất. Nếu previous là estimate trước cùng quý → `unknown`, reason `same_period_revision_not_growth`.
- Trade, số lượng sự kiện growth trên lịch và các mục chưa có parser không tăng coverage.
- `A = reduce_directions([L, G])`. A là biến dẫn xuất để tra bảng, không phải nhóm độc lập thứ tư và không cộng thêm một phiếu bên cạnh L/G.
- Một nhóm I/L/G `mixed` được tính là có dữ liệu dùng được nhưng không phải hướng nhất quán. `usable_axis_count` đếm I/L/G khác unknown, tối đa 3.

### 7.5 Coverage là dữ liệu, không phải xác suất

Mỗi nhóm ghi `available_slots`, `expected_slots`, `same_direction_slots`, `direction_counts`, `input_observation_ids`, `excluded_observation_ids`, `quality_flags`. Expected slots: I=2, L=2, G=1, A=2; report employment còn ghi subcoverage NFP/unemployment=2. Available đếm child khác unknown, kể cả mixed. `direction_counts` đếm child trong đủ năm enum positive/negative/flat/mixed/unknown. `same_direction_slots` đếm child cùng hướng kết quả nếu kết quả positive/negative/flat; bằng 0 khi mixed/unknown. A chỉ báo coverage L/G, không tăng usable_axis_count.

Nhóm đa slot chỉ có một slot dùng được vẫn có direction và phải ghi `partial`. Assessment `coherent` chỉ khi I/L/G đều dùng được, I/L/G/A đều không mixed, đủ toàn bộ slot/subslot, không current-vintage, period mismatch hoặc supporting divergence. Các trường hợp đủ bảng quyết định nhưng không đạt các điều kiện đó là `partial`; I/L/G/A có mixed là `conflicted`, ưu tiên hơn partial. Các cổng stale/insufficient ở §9 có ưu tiên cao hơn cả hai. Những nhãn này mô tả độ đầy đủ/nhất quán, không nói “độ tin cậy 80%”.

## 8. Các quy tắc liên kết bắt buộc

| Rule ID | Điều kiện | Kết quả bắt buộc |
|---|---|---|
| `X01_EMPLOYMENT_SPLIT` | NFP và unemployment có direction trái dấu cùng kỳ | L mixed; nêu cả hai số, không chọn số thuận với nhận định |
| `X02_CONSUMER_SPLIT` | CPI/PCE trái dấu hoặc core/headline PCE trái dấu | I mixed; đánh giá lạm phát phân hóa |
| `X03_WEEKLY_VS_MONTHLY` | Claims có hướng ngược L có hướng | Giữ L; thêm cảnh báo khác tần suất, giảm assessment từ coherent xuống partial |
| `X04_PRODUCER_VS_CONSUMER` | PPI trái hướng I | Giữ I; ghi chi phí đầu vào và giá tiêu dùng chưa đồng thuận |
| `X05_INFLATION_ACTIVITY_TENSION` | I positive, A negative | Áp lực giá tăng tốc trong khi đà hoạt động yếu; USD/vàng mixed, crypto adverse có điều kiện |
| `X06_DISINFLATION_NONWEAKENING` | I negative, A flat/positive | Áp lực giá giảm tốc, đà hoạt động không yếu đi theo bộ dữ liệu; không khẳng định đã hạ cánh mềm |
| `X07_DISINFLATION_WEAK_ACTIVITY` | I negative, A negative | Kênh kỳ vọng nới lỏng đối nghịch rủi ro hoạt động yếu; crypto mixed |
| `X08_GROWTH_LABOR_SPLIT` | L/G có hướng trái dấu | A mixed; nêu chênh tần suất và kỳ, không ép thành GDP thắng hoặc labor thắng |
| `X09_REVISION` | Giá trị mới của cùng metric/kỳ thay bản đã ghi | Ghi revision và tái tính context mới; không sửa bản đánh giá đã công bố |
| `X10_NO_CONSENSUS` | Mọi assessment v1 | surprise unavailable; cấm template “cao/thấp hơn kỳ vọng” khi mô tả kết quả thực |
| `X11_DUPLICATE_INFORMATION` | Event/indicator hoặc các estimate trùng metric/kỳ | Một contribution cho bản chọn; không tăng coverage |
| `X12_NEGATIVE_ACTIVITY_LEVEL` | NFP actual < 0 hoặc GDP actual < 0 trong bản chọn hợp lệ | Cảnh báo mức âm; nếu crypto base supportive thì chốt thành mixed (§9) |

X01–X04/X08/X09/X11 là explanation/quality rules; thay direction chỉ đúng như §7. X05–X07 chọn diễn giải cho bảng §9. Nhiều X có thể đồng thời kích hoạt, giữ tất cả ID và evidence; không dùng “rule sau cùng thắng”. X12 là override tài sản duy nhất ngoài các cổng dữ liệu.

## 9. Bảng kết luận tài sản và thứ tự ưu tiên

### 9.1 Các cổng trước khi tra bảng

Áp dụng đúng thứ tự:

1. Schema/source/hash không hợp lệ ở cấp release → không xuất assessment mới, giữ bản tốt cũ với error status. Không coi đây là bộ metric tất cả unknown.
2. Pipeline stale/unknown timestamp → `assessment_state=stale_context`, cả ba tài sản `insufficient_evidence` cho context hiện tại. Không sửa bản immutable cũ.
3. `usable_axis_count < 2` → `insufficient_context`, cả ba tài sản `insufficient_evidence`. Vẫn hiển thị direct signal của sự kiện với nhãn “chưa đủ đối chiếu”.
4. I hoặc A là mixed → `regime_id=R_CONFLICT`, ba tài sản `mixed`.
5. I unknown nhưng L/G đủ ít nhất hai axis → `regime_id=R_ACTIVITY_ONLY`, ba tài sản `mixed` do thiếu trục lạm phát.
6. Nếu I và A đều thuộc positive/negative/flat → tra đúng một dòng sau. Mọi tổ hợp còn lại → `R_INSUFFICIENT`, `insufficient_evidence`.

### 9.2 Bảng quyết định đầy đủ khi I/A có hướng

Đây là **giả thuyết diễn giải của ECO**, không phải quan hệ tất định được trích từ cơ quan nguồn.

| `regime_id` | I | A | Mô tả | USD | Gold | Crypto |
|---|---|---|---|---|---|---|
| `R01` | positive | positive | Áp lực giá và đà hoạt động cùng tăng | supportive | adverse | adverse |
| `R02` | positive | flat | Áp lực giá tăng, hoạt động ít đổi | supportive | adverse | adverse |
| `R03` | positive | negative | Áp lực giá tăng, đà hoạt động yếu | mixed | mixed | adverse |
| `R04` | negative | positive | Áp lực giá giảm, đà hoạt động cải thiện | adverse | supportive | supportive |
| `R05` | negative | flat | Áp lực giá giảm, hoạt động ít đổi | adverse | supportive | supportive |
| `R06` | negative | negative | Áp lực giá và đà hoạt động cùng giảm | mixed | supportive | mixed |
| `R07` | flat | positive | Áp lực giá ít đổi, đà hoạt động cải thiện | supportive | adverse | mixed |
| `R08` | flat | flat | Các thay đổi nằm trong vùng ngưỡng | neutral | neutral | neutral |
| `R09` | flat | negative | Áp lực giá ít đổi, đà hoạt động yếu | mixed | supportive | mixed |

Sau bảng, nếu `negative_activity_level=true` và crypto base `supportive`, đổi crypto thành `mixed`, reason `X12_NEGATIVE_ACTIVITY_LEVEL`; các ô khác giữ nguyên. Lý do: tăng tốc từ mức âm chưa đủ để xóa rủi ro giảm hoạt động. Không có override tùy nghi nào khác trong v1.

### 9.3 Cơ chế và điều kiện phải hiện cùng nhãn

Mỗi conclusion luôn kèm `conditional=true`, `mechanism_codes`, `unobserved_conditions`. Chỉ dùng các mã sau:

| Mã | Diễn giải mẫu có điều kiện |
|---|---|
| `RATE_PRESSURE_UP` | Dữ liệu có thể làm giảm dư địa nới lỏng nếu thị trường/Fed đọc là áp lực giá hoặc cầu mạnh hơn |
| `RATE_PRESSURE_DOWN` | Dữ liệu có thể tăng dư địa nới lỏng nếu áp lực giá hạ và Fed phản ứng theo kênh đó |
| `GROWTH_RISK` | Đà hoạt động yếu có thể làm giảm khẩu vị rủi ro; chưa phải chẩn đoán suy thoái |
| `USD_RELATIVE_RATES` | USD có thể được hỗ trợ khi chênh lệch kỳ vọng lãi suất có lợi cho USD; chưa có số liệu chênh lệch quốc tế |
| `USD_DEFENSIVE_DEMAND` | Cầu USD phòng thủ có thể đối nghịch tác động của kỳ vọng giảm lãi suất |
| `GOLD_OPPORTUNITY_COST` | Vàng có thể chịu sức ép nếu lợi suất thực/USD tăng; có thể được hỗ trợ nếu các biến đó giảm |
| `GOLD_HEDGE_DEMAND` | Nhu cầu phòng hộ/bất định có thể hỗ trợ vàng và đối nghịch kênh chi phí cơ hội |
| `CRYPTO_DISCOUNT_LIQUIDITY` | Crypto có thể nhạy với điều kiện tài chính/khẩu vị rủi ro; nới lỏng kỳ vọng không bảo đảm giá tăng |
| `DEMAND_SUPPORT` | Hoạt động cải thiện có thể hỗ trợ khẩu vị rủi ro, đồng thời tạo sức ép lãi suất |
| `NO_MATERIAL_CHANGE` | Thay đổi dưới ngưỡng quy tắc; chưa có tín hiệu hướng đủ rõ từ các số này |

Mapping deterministic theo regime, dùng cùng danh sách cho block bối cảnh rồi asset chọn các mã liên quan: R01/R02 = RATE_PRESSURE_UP, USD_RELATIVE_RATES, GOLD_OPPORTUNITY_COST, CRYPTO_DISCOUNT_LIQUIDITY; R03 lấy danh sách R01 rồi thêm GROWTH_RISK, USD_DEFENSIVE_DEMAND, GOLD_HEDGE_DEMAND; R04/R05 = RATE_PRESSURE_DOWN, USD_RELATIVE_RATES, GOLD_OPPORTUNITY_COST, CRYPTO_DISCOUNT_LIQUIDITY, DEMAND_SUPPORT; R06/R09 = RATE_PRESSURE_DOWN, GROWTH_RISK, USD_DEFENSIVE_DEMAND, GOLD_OPPORTUNITY_COST, GOLD_HEDGE_DEMAND, CRYPTO_DISCOUNT_LIQUIDITY; R07 = RATE_PRESSURE_UP, USD_RELATIVE_RATES, GOLD_OPPORTUNITY_COST, DEMAND_SUPPORT, CRYPTO_DISCOUNT_LIQUIDITY; R08 = NO_MATERIAL_CHANGE.

Với R_CONFLICT/R_ACTIVITY_ONLY, lấy hợp tập các mã theo I/L/G: I positive lấy danh sách R01; I negative lấy danh sách R04 bỏ DEMAND_SUPPORT; L hoặc G positive lấy danh sách R07; L hoặc G negative lấy danh sách R09. Axis mixed lấy hợp của hai hướng positive/negative tương ứng; flat/unknown không thêm mã. Cuối cùng thêm `CHANNEL_DOMINANCE_UNRESOLVED`, loại trùng và sort mã tăng dần. Không dùng A để cộng thêm lần nữa. Đây là liệt kê các kênh đối nghịch, không chọn kênh thắng.

USD nhận các mã RATE/ USD và GROWTH_RISK; Gold nhận RATE/GOLD và GROWTH_RISK; Crypto nhận RATE/CRYPTO/DEMAND và GROWTH_RISK. Mã không liên quan không xuất trong asset đó. `NO_MATERIAL_CHANGE` hoặc `CHANNEL_DOMINANCE_UNRESOLVED` áp dụng cho cả ba. Thiếu context → mechanism_codes rỗng ở kết luận tài sản; direct event vẫn có explanation riêng.

`unobserved_conditions` cố định: USD = `relative_rate_expectations`, `defensive_usd_demand`; Gold = `real_yields`, `usd_path`, `hedging_and_liquidity_demand`; Crypto = `financial_conditions`, `risk_appetite`, `asset_specific_flows`. Không viết “lợi suất thực đã tăng” hoặc “thị trường đã định giá cắt lãi” nếu chỉ có macro event.

## 10. Sự kiện mới nhất khác với bối cảnh mới nhất

`latest_event_batch` là toàn bộ sự kiện có actual hữu hạn, data_status đã xác minh, `usable_at <= as_of`, `scheduled_at <= as_of`, có `scheduled_at` lớn nhất. Cùng giờ lấy cả batch; thứ tự hiển thị theo `event_id` tăng dần. Timestamp lịch chỉ xác định thứ tự trình bày; không được dùng làm thời điểm ta đã biết actual. Sự kiện latest vẫn được hiển thị nếu metric unsupported/semantics không đạt; không lặng lẽ lấy sự kiện cũ hơn rồi gọi là mới nhất.

Block sự kiện gồm direct signals của batch và `event_context_relation`:

- Chỉ xét metric đã map, có direction positive/negative/flat và có trục đối chiếu tương ứng: CPI/PCE/PPI → I; NFP/unemployment/JOLTS/claims → L; GDP → G.
- Loại bỏ chính contribution của batch rồi tính lại trục để so đối chiếu, dùng các slot còn lại trong cùng snapshot. Không thay bằng previous hoặc lôi bản cũ vào làm phiếu. Đây chỉ là `peer_context`, không phải lịch sử “trước khi công bố”. Claims/PPI vốn không bỏ phiếu nên trục peer không đổi. GDP thường không còn peer → unknown.
- Direct flat → `small_change`; direct có hướng bằng peer → `aligned`; ngược peer → `divergent`; peer mixed → `mixed_peers`; không có peer hoặc direct unknown → `not_assessable`.
- Với batch nhiều metric: ưu tiên tổng hợp `divergent` > `mixed_peers` > `aligned` > `small_change` > `not_assessable`; vẫn giữ relation từng metric để không mất thông tin.

`context_transition` chỉ so với assessment immutable ngay trước đó của cùng ruleset, cùng chế độ current context, có `previous.as_of <= as_of` hiện tại. Chỉ mô tả nhãn thay đổi, không quy kết nhân quả cho sự kiện. Nếu không có bản trước → `not_computable`. Nếu chỉ input của latest batch đổi → `latest_batch_only`, kể cả batch có nhiều metric. Nếu có bất kỳ input đổi ngoài latest batch → `multiple_inputs_changed`; nếu không observation nào đổi → `context_only`. Phải xuất danh sách ID thêm/bỏ/thay dưới `changed_observation_ids` và `previous_assessment_id`; việc loại batch để tạo peer không thay thế bản before thật.

Mọi thay đổi ngày, trạng thái freshness hoặc source revision có thể làm context đổi dù sự kiện mới nhất không đổi. `change_reason` phải là một trong `new_observation`, `source_revision`, `freshness_expired`, `pipeline_status_changed`, `source_snapshot_changed`, `multiple_changes`, `initial_assessment`. Không có predecessor → initial_assessment. Còn lại đánh dấu các loại thay đổi quan sát/kỳ mới, revision cùng kỳ, freshness, pipeline; nếu có từ hai loại trở lên → multiple_changes, đúng một loại → mã đó. Nếu không loại nào đổi nhưng hash parent đổi → source_snapshot_changed. Không dựng tin mới từ cache hit.

## 11. Hợp đồng đầu ra và thuật toán

### 11.1 Output bắt buộc

```text
assessment_id, schema_version, ruleset_version, ruleset_sha256
calendar_release_id, calendar_sha256, observation_bundle_sha256
as_of, generated_at, history_mode, comparison_basis
latest_event_batch: event_ids[], scheduled_at, usable_at_max,
  signal_ids[], event_context_relation, per_metric_relations[]
signals[]: metric_id, observation_id, reference_period, previous_period,
  actual, previous, delta, signed_delta, epsilon, direction,
  level_context, excluded_reason, quality_flags[]
axes: inflation, labor, growth, activity
  mỗi axis: direction, available_slots, expected_slots,
  same_direction_slots, direction_counts, input_observation_ids[], excluded_observation_ids[],
  quality_flags[]; labor có employment subcoverage
usable_axis_count, assessment_state, evidence_grade, regime_id
assets: usd, gold, crypto_risk_assets
  mỗi asset: conclusion, conditional, mechanism_codes[],
  unobserved_conditions[], reason_ids[], template_id
surprise: {status: unavailable, reason: no_licensed_consensus}
policy_observation: {status: unavailable}
market_confirmation: {status: not_measured}
triggered_rules[]: rule_id, observation_ids[], numeric_evidence, template_id
context_transition, change_reason, excluded_inputs[], warnings[]
```

Không có latest event đủ điều kiện → `latest_event_batch=null`, reason `no_verified_event`. Có thể vẫn có background snapshot nhưng không dùng template “tin mới nhất cho thấy”.

`assessment_state` gồm `assessed`, `insufficient_context`, `stale_context`; `evidence_grade` gồm `coherent`, `partial`, `conflicted`, `insufficient`, `stale`. Stale/insufficient ưu tiên trước chất lượng nhóm. Hướng unknown dùng enum, số thiếu dùng null; không ép thành 0. `regime_id` ở stale/insufficient là `R_STALE`/`R_INSUFFICIENT`.

V1 dùng `history_mode=latest_vintage_context` cho mọi assessment. Ledger của những output thực đã công bố có published_at riêng; không đổi history_mode chỉ vì output đã được lưu. Toàn bộ enum nêu trong tài liệu là contract; unknown enum phải bị validator từ chối thay vì map sang neutral.

### 11.2 Pseudocode chuẩn

```text
assess(bundle, calendar, batch_status, as_of, previous_assessment, ruleset):
    verify_release_hashes_and_ruleset_or_fail()
    observations, rejected = normalize_and_validate_with_provenance()
    visible = filter_by_usable_at_and_cutoff(observations, as_of)
    latest_event_batch = select_latest_actual_event_batch(calendar.events, provenance, as_of)
    selected = select_latest_period_then_latest_vintage(visible)
    eligible, excluded = apply_semantics_and_freshness(selected, as_of)
    signals = decimal_directions(eligible, registry)
    I, L, G = build_axes_and_supporting_flags(signals)
    A = reduce_directions([L.direction, G.direction])
    regime, assets = gates_then_matrix(I, L, G, A, batch_status, as_of)
    apply_negative_activity_level_override(assets, eligible)
    peer_relations = assess_latest_batch_against_other_slots()
    evidence_grade = grade_by_fixed_rules()
    explanations = templates_from_rules_and_numeric_evidence()
    transition = compare_real_previous_assessment_if_available()
    return canonical_assessment_with_hashes_and_exclusions()
```

### 11.3 Bất biến và idempotency

`assessment_id = macro-<first20(sha256(canonical_identity))>`. `canonical_identity` gồm ruleset hash, calendar release/hash, observation bundle hash, selected/excluded observation IDs và reasons, freshness flags, pipeline stale/unknown flags, history mode, directions/regime/asset labels. Key object sort; mảng ID/reason sort và de-duplicate; UTF-8, JSON compact không khoảng trắng, ensure_ascii=false, không newline khi hash. Decimal dạng chuỗi fixed-point, bỏ trailing zeros và dấu chấm dư, chuẩn hóa -0 thành 0. Không hash thời gian chạy hoặc bản previous vào ID. Hash parent mới tạo identity mới dù conclusion giống; ghi source_snapshot_changed nếu chỉ provenance thay đổi.

Nếu identity không đổi, giữ toàn bộ artifact và timestamp gốc. `checked_at` thuộc status revalidate riêng. So với previous để ghi transition chỉ khi tạo identity mới; cache/refresh giống input không tạo ledger entry mới. Nếu identity đổi do hết freshness hoặc trạng thái pipeline thì ghi đúng reason. Pipeline đã lỗi trước chuẩn hóa không tạo assessment giả rồi tự ghi đè pointer tốt.

Output publish theo allowlist mới, ví dụ `/data/macro-assessment/`; manifest pin calendar parent và observation bundle. Raw/PDF/credential ở private store. Snapshot, source hash, parser version và ruleset hash phải đủ tái lập. Quyền nguồn áp dụng trước publish, không được suy rộng từ việc có link lịch bên thứ ba.

## 12. Nội dung UI cần triển khai đúng

Card đầu có bốn phần cố định:

1. **Số liệu mới nhất:** tên sự kiện, ngày lịch, kỳ quan sát, actual/previous/delta, trạng thái vintage. Ghi “so với kỳ trước”; nếu vùng flat thì “thay đổi nhỏ theo ngưỡng ECO”.
2. **Đối chiếu:** các metric xác nhận và mâu thuẫn có số/kỳ cụ thể; hiện cả missing/unsupported. Không chỉ liệt kê metric cùng hướng.
3. **Bối cảnh:** tên regime và coverage I/L/G; không biểu diễn thành điểm 0–100. Nút chi tiết mở rule IDs/provenance.
4. **USD / Vàng / Crypto:** nhãn, cơ chế có điều kiện và dữ liệu cần quan sát thêm. Mixed dùng màu trung tính kèm chữ “hai chiều”; insufficient không dùng cùng nhãn với neutral.

Template R03 đề xuất: “Các thước đo giá tiêu dùng đang tăng tốc, trong khi đà hoạt động yếu đi. Hai kênh áp lực lãi suất và rủi ro tăng trưởng đối nghịch nhau đối với USD và vàng. Crypto có thể chịu sức ép qua điều kiện tài chính và khẩu vị rủi ro. Chưa đo phản ứng lợi suất, USD hoặc giá tài sản.” Chỉ chèn câu này nếu R03 thực sự kích hoạt; nếu G thiếu thì nói rõ hoạt động đang được đại diện bằng nhóm lao động.

Màu `usdReferenceBias` đơn biến hiện tại không được dùng làm kết luận mới. Khi tích hợp, bỏ hoặc đổi nhãn nó thành “biến động so kỳ trước”, còn màu đánh giá USD phải lấy từ output rules engine. Trade không còn tự được tô như tín hiệu USD từ một phép so actual/previous.

Không có input shock so consensus thì cấm các câu “vượt kỳ vọng”, “thấp hơn dự báo”, “tin tốt/xấu chắc chắn”, “Fed sẽ cắt/tăng”, “giá sẽ tăng/giảm”. Ví dụ giả lập trong tài liệu/test phải gắn fixture, không hiển thị như live data.

## 13. Ví dụ đối chiếu snapshot hiện có

Đây là **ví dụ thiết kế dựa trên release đã pin**, không phải assessment đang được production engine phát hành. Dùng cutoff `2026-10-08T14:52:45.517347Z` (21:52:45 giờ Việt Nam), release `calendar-d881cb2fcd21ed9b685d`, SHA-256 file `c6b9d57f35fa333cd18e0ee517163f53d0bcc19b5236cc91d4fdedb1dc78c63b`. Không gọi snapshot này là dữ liệu mới nhất ở những ngày sau.

| Input trong snapshot | Actual / previous | Delta | Kết quả theo epsilon |
|---|---|---|---|
| Claims công bố 08/10, tuần kết thúc 03/10 | 197 / 199 nghìn | -2 nghìn | flat, nhỏ hơn 10 nghìn |
| NFP tháng 09 | +29 / +133 nghìn | -104 nghìn | negative; vẫn tăng việc làm nhưng chậm hơn |
| Unemployment tháng 09 | 4.2 / 4.1% | +0.1 pp | negative sau orientation=-1 |
| JOLTS tháng 08 | 7.079 / 7.335 nghìn | -256 nghìn | negative; lệch NFP một tháng |
| CPI tháng 08 | 0.4 / 0.1% m/m | +0.3 pp | positive |
| PCE core tháng 08 | 0.2 / 0.1% m/m | +0.1 pp | positive; đúng biên |
| PCE headline tháng 08 | 0.3 / 0.1% m/m | +0.2 pp | positive; không thêm phiếu ngoài PCE core |
| PPI tháng 08 | 0.4 / 0.1% m/m | +0.3 pp | supporting positive |
| GDP quý II | 2.2 / 2.5% SAAR | -0.3 pp | Chỉ negative sau khi adapter chứng minh previous là quý I |
| Trade tháng 08 | -105.6 / -92.8 tỷ USD | -12.8 tỷ | Thông tin thâm hụt, không bỏ phiếu USD |

Các field period/SA/previous semantics còn thiếu trong legacy phải được chứng minh từ source snapshot/parser trước khi engine chấp nhận. Chưa chứng minh thì metric unknown; không dùng bảng ví dụ để điền ngược metadata. GDP đặc biệt chưa được mặc định đủ điều kiện chỉ vì có hai số.

**Expected sau khi xác minh các cặp BLS/PCE/claims theo contract:** I positive; employment_report negative; JOLTS negative; L negative. Claims flat nên `event_context_relation=small_change`; một tuần giảm 2 nghìn không đảo bối cảnh tháng. Nếu GDP chưa đủ semantics, G unknown, A negative theo L, `usable_axis_count=2`; R03 vẫn hợp lệ nhưng evidence partial. Nếu GDP được xác minh thì G negative, A vẫn negative, evidence vẫn partial do BLS current-vintage và lệch tháng.

Kết quả tài sản của ví dụ: USD mixed; Gold mixed; Crypto adverse có điều kiện; surprise unavailable; market confirmation not_measured. Câu mở đầu phải nói **sự kiện claims mới nhất thay đổi nhỏ, bối cảnh từ các số liệu khác vẫn có sức ép**, không nói claims lần này gây ra toàn bộ kết luận đó. `context_transition=not_computable` nếu chưa có assessment trước thực sự được lưu.

## 14. Ma trận kiểm thử bắt buộc trước khi phát hành engine

Fixtures độc lập với `latest.json` đang thay đổi; đóng băng input và as_of. Chạy cùng kết quả trên Windows/Python 3.12 và Ubuntu CI; backend Decimal là chuẩn.

| ID | Fixture / hành vi | Expected |
|---|---|---|
| `T01` | Rate 0.1 → 0.2, epsilon 0.1 | delta đúng 0.1, positive |
| `T02` | Rate 0.2 → 0.1 | negative, không sai float ở biên |
| `T03` | Claims 199 → 197 | flat, weekly_move_below_threshold |
| `T04` | Claims 210 → 200; unemployment 4.1 → 4.2 | Claims positive; unemployment negative |
| `T05` | Previous null; actual=0 trong bản khác có previous=0 | Bản một unknown; bản hai flat, không coi 0 là missing |
| `T06` | NFP 133 → 29; UR 4.1 → 4.2 | employment negative, không gọi mất 104 nghìn việc làm |
| `T07` | NFP 100 → 150; UR 4.1 → 4.2 | employment/L mixed dù JOLTS positive |
| `T08` | CPI positive/PCE negative | I mixed, không flat; nếu đủ axis thì R_CONFLICT |
| `T09` | PCE core flat/headline positive | PCE flat theo core; chỉ một slot |
| `T10` | PCE core negative/headline positive | PCE/I mixed, X02 |
| `T11` | L negative, claims positive >=epsilon | L giữ negative, weekly_labor_divergence, partial |
| `T12` | CPI/PCE thiếu, PPI positive | I unknown; PPI không thay thế consumer |
| `T13` | Chỉ claims có số | Cả ba tài sản insufficient_evidence |
| `T14` | Toàn bộ 9 tổ hợp I/A ở §9.2 | Đúng 9 dòng, không thiếu default |
| `T15` | I unknown, L/G dùng được | R_ACTIVITY_ONLY, cả ba mixed |
| `T16` | GDP +2.5 → +2.2 so quý trước | G negative; GDP còn tăng trưởng dương |
| `T17` | GDP estimate 2.1 → 2.2 cùng quý | Không dùng làm delta q/q; same_period_revision_not_growth |
| `T18` | NFP -150 → -100; I negative, A positive | Base R04 nhưng crypto mixed vì level âm |
| `T19` | Thêm duplicate event/indicator, đổi thứ tự mảng | Hướng/coverage không đổi sau de-dup; parent hash mới vẫn tạo ID mới theo §11.3 |
| `T20` | Thêm observation có usable_at sau cutoff | Mọi kết luận trong cutoff giữ nguyên |
| `T21` | Source đã scheduled nhưng actual chưa biết | Không tạo signal hoặc latest confirmed event |
| `T22` | Revision của kỳ cũ đến sau kỳ mới | Không làm kỳ cũ thành kỳ mới nhất; ledger cũ bất biến |
| `T23` | Kỳ mới nhất thiếu previous nhưng kỳ trước đầy đủ | Metric unknown; không lùi kỳ để bỏ phiếu |
| `T24` | CPI/PCE cách hai tháng | Slot cũ excluded, period_gap_excluded; coverage giảm |
| `T25` | Employment submetrics lệch tháng | Không reducer như cùng tháng; giữ tháng mới, ghi mismatch |
| `T26` | Tuổi đúng 21/75/180 và thêm một ngày | Biên hợp lệ; sau biên stale_observation |
| `T27` | Source check đúng 48h, rồi >48h | Trước đạt; sau stale_context/insufficient_evidence |
| `T28` | Source check không có timestamp | pipeline_status_unknown, stale_context |
| `T29` | Official data nhưng unit/SA/previous semantics sai | Excluded rõ reason, không đoán scale/period |
| `T30` | Trade improvement đứng riêng | Không sinh bullish USD |
| `T31` | Latest claims flat, I positive/L negative | Latest small_change; context R03, không gán nhân quả claims |
| `T32` | Latest gồm CPI và PCE cùng giờ | Giữ cả batch; không phụ thuộc thứ tự input |
| `T33` | Mọi slot hợp lệ đều flat | R08/neutral; khác unknown/insufficient |
| `T34` | Bad source hash / truncated JSON | Không đổi pointer tốt, ghi status error |
| `T35` | Cache hit và cùng identity | Không thêm release/ledger, giữ generated_at |
| `T36` | Revision hoặc freshness làm identity đổi | Tạo artifact mới và reason, không ghi đè bản cũ |
| `T37` | Không có previous assessment | transition not_computable, không dựng before từ previous_period |
| `T38` | Nhiều input cùng đổi | transition multiple_inputs_changed, không gán một event |
| `T39` | Hai vintage cùng usable_at khác số, không lineage | ambiguous_vintage; không chọn theo ID |
| `T40` | Snapshot ví dụ §13, G excluded | I+, L-, G unknown, A-, R03, partial, USD/Gold mixed/Crypto adverse |
| `T41` | UI locale/timezone, lọc lịch, sort và viewport | Không đổi assessment, cutoff hoặc các input vào engine |
| `T42` | Copy template/tooltip/export | Không surprise/probability khi thiếu consensus/calibration; provenance đủ |

Thêm property checks reducer permutation invariance, không mutation input, null không biến thành zero, thêm future data không đổi prefix và duplicate không tăng slot. Kiểm canonical IDs ổn định khi đổi thứ tự source map. Không bỏ gate engine/publication để làm test xanh.

## 15. Hướng triển khai cho code agent kế tiếp

1. Đọc AGENTS/README/HANDOFF/DEPLOYMENT/STORAGE và tài liệu này. Kiểm Git thật: workspace nghiên cứu có commit chưa phát hành; bắt đầu implementation từ production base đã xác minh, không push toàn bộ local main theo quán tính.
2. Đánh dấu `CAL-XRULE-02 IN_PROGRESS`. Tạo registry cấu hình khóa `macro-cross-v1.0.0` và hash trước engine; chốt canonical serialization bằng fixtures. Không sửa protocol Core 10.
3. Bổ sung normalized observation contract ở adapter calendar; chứng minh metric ID, period, SA, previous semantics, source hash và usable_at. Bản nguồn nào thiếu thì giữ unknown. Với raw cần restore, chỉ dùng bucket riêng/quyền hiện có.
4. Viết module thuần `eco/macro_assessment.py` theo pseudocode; không IO/provider/clock bên trong. Publisher/ledger là module riêng, xử lý fail/atomic pointer và snapshots.
5. Viết fixtures §14, public contract validation và templates. CI unit test không bắt buộc cài PDF parser chỉ để mock; integration parser thật có dependency được pin và fixture riêng khi phù hợp.
6. Chạy trên snapshot đã pin để đối chiếu §13; lưu report exclusions và rule traces. Không chỉ in một nhãn cuối mà bỏ bằng chứng.
7. Tích hợp UI/static JSON, cập nhật calendar model/schema nếu cần; thay màu đơn biến bằng nhãn assessment theo §12; giữ EN/VI và fallback của locale khác đúng policy hiện có.
8. Chạy tests/gates/browser và review diff/secret/public rights theo runbook. Chỉ lúc code đạt mới commit/push production, xác minh CI/Pages/hai hostname/hash/UI và cập nhật HANDOFF.

File layout trên là đích đề xuất; agent phải kiểm tra tồn tại trước tạo. Trạng thái hiện tại của toàn bộ bước implementation là **TODO**. Việc có đặc tả này không nghiệm thu engine, parser mới, backtest hoặc deployment.

## 16. Các quyết định đã chốt và ảnh hưởng

| Quyết định | Lý do | Lựa chọn không dùng trong v1 | Ảnh hưởng lịch sử |
|---|---|---|---|
| Trend so kỳ trước, không surprise | Chưa có consensus được cấp quyền/vintage trước tin | Dùng previous giả forecast hoặc scrape MQL5 | Không sửa calendar/Core đã công bố |
| Reducer giữ mixed, không score cộng trọng số | Tránh xóa mâu thuẫn và đếm lặp | Cộng mọi actual xanh thành một điểm bullish | Method riêng; chưa có score history mới |
| Consumer core/headline cùng slot, NFP/UR cùng family | Kiểm soát thông tin liên quan trong cùng release/nhóm | Coi mọi field là xác nhận độc lập | Không đổi trọng số Core10 |
| Claims/PPI supporting, trade context only | Tần suất/ý nghĩa khác; thiếu cấu phần và độ trễ | Đảo bối cảnh từ một tuần hoặc cán cân thương mại | Phải đổi version nếu nâng lên phiếu chính |
| Epsilon cố định và công khai | Kết quả tái lập, hạn chế biến động rất nhỏ | Tune bằng giá sau sự kiện hiện tại | Thay epsilon tạo version mới |
| Nhãn conditional, không đo phản ứng giá | Chưa có market/expectation adapter | Gọi inference là điều thị trường đã làm | Không tạo backtest hoặc performance claim |
| Dữ liệu cũ chỉ latest-vintage context | Không có vintage point-in-time đầy đủ | Tái dựng lịch sử biết trước từ API tải hôm nay | Ledger mới chỉ bắt đầu từ lúc thực phát hành |

Điều kiện mở v2: có nguồn consensus và lịch sử snapshot hợp lệ trước công bố, hoặc thêm market confirmation/metric chính sách. Phải chốt protocol mới về nguồn, quyền, units, timing, normalization, horizon và evaluation trước code; không bật một nhánh v2 ẩn trong `macro-cross-v1.0.0`.

## 17. Cơ sở tham khảo và giới hạn của bằng chứng

Các nguồn dưới đây đã được đối chiếu khi soạn. Chúng hỗ trợ định nghĩa và cơ chế tổng quát; **không** xác nhận epsilon, quorum, bảng R01–R09 hoặc khả năng dự báo của ECO.

- [Federal Reserve — Monetary Policy: Goals and transmission](https://www.federalreserve.gov/monetarypolicy/monetary-policy-what-are-its-goals-how-does-it-work.htm): quan hệ giữa giá cả, việc làm, kỳ vọng lãi suất và điều kiện tài chính. Đây là cơ sở đọc nhiều nhóm thay vì một số đơn lẻ; USD còn phụ thuộc tương quan với nước khác.
- [BLS — Employment Situation Technical Note](https://www.bls.gov/news.release/empsit.tn.htm): payrolls và unemployment thuộc hai khảo sát khác nhau; phải giữ định nghĩa và kỳ. Quyết định gom một release family là policy tổng hợp của ECO, không phải khẳng định hai khảo sát trùng nhau.
- [BEA — Core PCE](https://www.bea.gov/data/personal-consumption-expenditures-price-index-excluding-food-and-energy): core loại food/energy; không đồng nhất với headline hoặc một chỉ số khác đơn vị/kỳ.
- [World Gold Council — The impact of monetary policy on gold](https://www.gold.org/goldhub/research/the-impact-of-monetary-policy-on-gold): chi phí cơ hội, USD và nhu cầu phòng hộ có thể cùng ảnh hưởng vàng. Không dùng một số CPI để khẳng định lợi suất thực hay giá vàng đã đổi.
- [IMF WP/23/163 — The Crypto Cycle and US Monetary Policy](https://www.imf.org/en/publications/wp/issues/2023/08/04/the-crypto-cycle-and-us-monetary-policy-534834): nghiên cứu mối liên hệ crypto với chính sách tiền tệ/khẩu vị rủi ro trong mẫu nghiên cứu; không phải calibration cho phản ứng ETH trước mỗi sự kiện.
- Hợp đồng nguồn và vận hành ECO: [ECONOMIC_CALENDAR.md](ECONOMIC_CALENDAR.md), [MASTER_PLAN.md](MASTER_PLAN.md), [DAILY_UPDATES.md](DAILY_UPDATES.md), [DEPLOYMENT.md](DEPLOYMENT.md), [STORAGE.md](STORAGE.md).

Agent không dùng nguồn tham khảo này để tự bổ sung dữ liệu thiếu, thay provider hoặc mở quyền phân phối. Kết quả nghiệm thu của spec cần được ghi riêng với kết quả nghiệm thu implementation.
