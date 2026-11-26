# Lịch kinh tế và kịch bản USD / vàng / crypto

CAL-02, ngày 08/10/2026; `us-macro-calendar-v1.1.0`, schema `1.1.0`. Tab `#calendar` độc lập với methodology, điểm và lịch sử Core 10.

## Lịch toàn cầu Forex Factory

Ngày 26/11/2026 người dùng xác nhận đã được cấp phép dùng nguồn. Bảng chính đọc snapshot `forex-factory-calendar-v1.0.0` từ tên miền lịch chính thức. Ghép dải 30 ngày trước/sau theo ngày Việt Nam bằng URL range công khai. Parser đọc state JSON nhúng trong HTML, đối chiếu phạm vi ngày và ID từng hàng với bảng HTML. Lịch Weekly Export JSON được đối chiếu, nhưng chỉ có lịch, dự báo và kỳ trước. [Lịch Forex Factory](https://calendar.forexfactory.com/calendar).

- Hiển thị số thực tế, dự báo và kỳ trước theo chuỗi giá trị nguồn. Khi có điều chỉnh, bảng dùng số kỳ trước đã sửa và hiện cả số trước điều chỉnh. Ô trống giữ dấu —.
- Epoch được đổi sang UTC khi lưu. Bảng và bộ lọc dùng giờ Việt Nam (UTC+7). Sự kiện được nhóm theo ngày Việt Nam và xếp theo giờ trong ngày. Sự kiện cả ngày hoặc chưa rõ giờ đứng đầu nhóm theo ngày và nhãn nguồn, không có đếm ngược. Thời điểm lấy snapshot tách biệt với giờ công bố dự kiến và chưa đo được giờ nguồn nhận tin.
- Đếm ngược cập nhật mỗi giây cho sự kiện đang theo dõi. Sau giờ dự kiến, sự kiện có chỉ tiêu số chuyển sang chờ trong tối đa một giờ nếu snapshot chưa có actual, sau đó hiển thị chưa có số thực tế. Bản phát hành mới có actual sẽ hiện số nguồn. Trình duyệt đang mở kiểm tra snapshot mỗi phút. Thời gian có snapshot mới tùy vào lượt batch bên dưới.
- `python -m eco.forex_factory` lưu HTML gzip, bản chuẩn hóa và manifest vào R2 riêng tư với từng SHA-256 và readback. Release công khai chỉ gồm trường lịch chuẩn hóa và provenance; pointer đối chiếu hash của release bất biến. Nội dung không đổi giữ release, chỉ cập nhật lần kiểm. Lỗi HTML, R2 hoặc checksum giữ bản tốt gần nhất. Chạy cùng batch lịch kinh tế hiện hữu, tải từ backend, không gọi nguồn từ trang ECO.
- Dự báo trong bảng là từ snapshot hiện hành. Đánh giá v1 cần vintage dự báo thật sự ghi nhận trước công bố và định nghĩa metric đã kiểm chứng. Kịch bản ECO tiếp tục lấy input đã pin từ luồng số liệu chính thức bên dưới.

## Số liệu chính thức Mỹ dùng trong đánh giá ECO

| Nguồn ECO | Đường dữ liệu | Phạm vi |
|---|---|---|
| BLS | [iCalendar](https://www.bls.gov/help/hlpiCAL.htm), `https://www.bls.gov/schedule/news_release/bls.ics`; [API v2](https://www.bls.gov/developers/api_signature_v2.htm) | CPI, NFP, PPI, JOLTS và các bản tin lao động/giá khác; năm series số liệu mùa vụ |
| BEA | [iCalendar](https://www.bea.gov/news/schedule/icalendar), [lịch công bố đầy đủ](https://www.bea.gov/news/schedule/full) và từng bản tin | GDP, PCE, cán cân thương mại, giao dịch/vị thế đầu tư quốc tế |
| Federal Reserve | [FOMC](https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm) và [lịch sự kiện theo tháng](https://www.federalreserve.gov/newsevents/calendar.htm) | FOMC, biên bản, Beige Book, sản xuất công nghiệp, tín dụng tiêu dùng |
| DOL | [lịch và kho weekly claims](https://oui.doleta.gov/unemploy/claims_arch.asp), PDF thông cáo từng ngày | Weekly initial jobless claims; ngoại lệ ngày nghỉ trong lịch nguồn |

Luồng số liệu chính thức dùng trong đánh giá ECO bao phủ các sự kiện Mỹ liệt kê bên trên. Nội dung cơ quan chính thức được trích theo trường số/lịch cần thiết, dẫn link bản gốc; không sao chép hình ảnh, logo hay bài viết. Attribution không hàm ý cơ quan nguồn bảo chứng ECO. Xem [BLS copyright](https://www.bls.gov/bls/linksite.htm), [BEA FAQ 145](https://www.bea.gov/help/faq/145) và [Fed disclaimer](https://www.federalreserve.gov/disclaimer.htm).

## Kết quả gắn sự kiện

Mỗi sự kiện giữ `scheduled_at`, `source_title`, `reference_period`, `data_vintage_at` và `data_status` riêng. Đã qua giờ dự kiến **không** tự động chuyển thành đã công bố. Hàng chưa đối chiếu được đúng kỳ để `actual/previous` null và UI nói rõ chưa xác minh.

- BEA GDP, PCE và trade lấy `actual/previous` từ đúng bản tin có tiêu đề/kỳ tương ứng. PCE có thêm Core PCE; GDP là % annualized; trade là tỷ USD.
- DOL lấy initial claims đã điều chỉnh mùa vụ từ PDF đúng ngày công bố; kỳ tham chiếu là tuần kết thúc, đơn vị nghìn. Kiểm ngày công bố và chuỗi tuần, không gán continuing claims vào initial claims.
- BLS chỉ gắn năm series vào **sự kiện gần nhất đã qua** khi kỳ API khớp kỳ suy ra từ ngày công bố. Đây là **vintage mới nhất tại lúc batch tải**, có thể đã được revision; không được coi là số đúng bản tin tại thời điểm lịch sử. Các sự kiện BLS khác vẫn null nếu không có parser nguồn đúng kỳ.
- `forecast` trong bảng ECO vẫn null vì các nguồn sơ cấp này không cung cấp consensus đã được cấp quyền. `previous` không thay thế `forecast`; không tự tính surprise từ hai cột đó.
Số thực tế và kỳ trước trong bảng lịch được trình bày trung tính.

Năm series BLS seasonally adjusted: `CUSR0000SA0` CPI index; `CES0000000001` NFP level (nghìn); `LNS14000000` thất nghiệp %; `WPSFD4` PPI final demand index; `JTS000000000000000JOL` job openings (nghìn). CPI/PPI tính `100 × (index_month/index_previous_month − 1)` và làm tròn một chữ số; NFP là chênh lệch hai mức lao động tháng. Thiếu tháng thì null. API warning catalog có thể đi cùng data hợp lệ, lỗi status/thiếu series bị chặn. Footnote `P` là sơ bộ. [FAQ BLS](https://www.bls.gov/developers/api_faqs.htm) nêu độ trễ và revision.

`reference_period` là thời kỳ quan sát; `scheduled_at` là giờ dự kiến; `retrieved_at` là lần tải body; `checked_at` là lần HTTP/cache gần nhất. Thời điểm số liệu thật được đăng lên API có thể không biết. Snapshot hiện tại không tạo vintage lịch sử để backtest point-in-time. Kịch bản USD/vàng/crypto là suy luận có điều kiện từ [cơ chế Fed](https://www.federalreserve.gov/monetarypolicy/monetary-policy-what-are-its-goals-how-does-it-work.htm), [World Gold Council](https://www.gold.org/goldhub/research/the-impact-of-monetary-policy-on-gold) và [IMF WP 2023/163](https://www.imf.org/en/publications/wp/issues/2023/08/04/the-crypto-cycle-and-us-monetary-policy-534834). `high/medium` là mức ECO tự phân loại, không phải xác suất, dự báo giá hay khuyến nghị giao dịch.

## Lịch chạy và tài nguyên

| Cron UTC | Giờ Việt Nam | Vai trò |
|---|---|---|
| `37 0 * * *` | 07:37 hằng ngày | Rà lại lịch BLS, BEA, Fed, DOL và BLS API |
| `37 13,18 * * 1-5` | 20:37 và 01:37 hôm sau, thứ Hai–Sáu UTC | Bắt kết quả sau các khung giờ công bố Mỹ |

GitHub có thể chạy trễ; job dùng concurrency chung với batch ETH. Lịch nguồn được cache 20 giờ giữa các lần quét, ép refresh ở 00 UTC; BLS API cache 4 giờ. BEA/DOL bản tin vừa công bố cache 4 giờ; DOL PDF cũ cache 180 ngày. GET có ETag/Last-Modified khi nguồn hỗ trợ; cache nội bộ có hash. Lịch Fed tháng chỉ tải các tháng trong cửa sổ 45 ngày trước và 180 ngày sau. Browser chỉ tải JSON release bất biến của ECO khi mở tab, revalidate pointer/status mỗi 15 phút khi đang xem; bảng Forex Factory kiểm bản phát hành ECO mỗi phút khi tab đang mở.

## Snapshot, phát hành và lỗi

`python -m eco.calendar` lưu toàn bộ response nguồn, canonical JSON và manifest dưới `data/raw/calendar/<run-id>` (Git ignored). Body PDF DOL được mã hóa base64 trong snapshot JSON để giữ bytes/hash. SigV4 PUT/GET từng object vào prefix riêng `raw/calendar/<run-id>/` của bucket private `eco-eth-private`; manifest upload cuối và mọi object phải readback đúng hash trước khi đổi pointer. Không bind raw/R2 vào frontend; secret chỉ qua môi trường/DPAPI hoặc Actions Secrets.

Release `public/data/calendar/releases/calendar-<20hex>/calendar.json` là bất biến; `latest.json` pin path/hash/schema. CAL-01 `calendar-66b4e31ed958b40e784f` được giữ nguyên; CAL-02 thêm release con với `revision.reason=expanded_official_coverage_and_period_matched_results`. `status.json` ghi heartbeat/lỗi. Nội dung không đổi không sinh release mới. Fetch/parse/coverage/R2 fail thì giữ pointer tốt; UI fail mạng/hash giữ bản đã xác minh. Hơn 48 giờ từ batch success thì cảnh báo lịch cũ. Không biến lỗi thành số 0 và không phát hành dữ liệu raw có bản quyền.

Fetch nguồn và R2 PUT/GET thử tối đa ba lần khi gặp timeout/lỗi vận chuyển hoặc HTTP 408/425/429/5xx tạm thời. HTTP 429 tuân theo `Retry-After` dạng giây, tối đa 30 giây. HTTP 4xx khác, redirect, body quá lớn, checksum và parser không được retry. Readback hash vẫn bắt buộc trước công bố. Status lỗi chỉ ghi source key/mã lỗi rút gọn, không ghi URL, response body hay credential.

Tại lần kiểm CAL-02 ngày 08/10/2026: 111 sự kiện trong cửa sổ, 17 có `actual/previous`, 25 response nguồn và 27 object private readback. Đây là số đếm snapshot, có thể thay đổi ở batch sau; không phải cam kết mọi sự kiện đã qua đều có actual.

## Kiểm tra và bước tiếp

```text
python -m unittest discover -s tests -p test_calendar.py -v
node --test tests/calendar.test.mjs
node scripts/check-calendar.mjs http://127.0.0.1:8877/
```

Browser QA kiểm ngày VN/ET, bốn viewport, tám locale, filter, hash/network fallback và Core 10. Widget cần kiểm trong browser tương tác có hỗ trợ bên thứ ba; đầu nối headless có thể nhận HTTP 404 từ Tradays dù trình duyệt ứng dụng hiển thị. Các kiểm chứng thực tế và deploy ghi `HANDOFF.md`.

Bước kế nếu muốn đưa consensus/global event **vào JSON ECO**: chọn provider có quyền backend/cache/public derived rõ ràng, timestamp availability và lịch revision, rồi tạo adapter/version khác. Không đổi nguồn, đơn vị hoặc phân loại dưới `us-macro-calendar-v1.1.0`.
