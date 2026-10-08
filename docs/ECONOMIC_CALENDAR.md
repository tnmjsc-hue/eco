# Lịch kinh tế và kịch bản USD / vàng / crypto

CAL-02, ngày 08/10/2026; `us-macro-calendar-v1.1.0`, schema `1.1.0`. Tab `#calendar` độc lập với methodology, điểm và lịch sử Core 10.

## Hai lớp lịch và quyền dữ liệu

Bảng ECO dùng lịch và số liệu của cơ quan công bố Mỹ. Mục **Lịch mở rộng MQL5** tải [widget chính thức của MetaQuotes](https://www.mql5.com/en/economic-calendar/widgets) khi người xem mở mục đó; widget hiển thị nhiều quốc gia, Actual, Forecast và Previous do MetaQuotes vận hành. ECO giữ nguyên mã nhúng mà trình tạo widget cung cấp và có liên kết mở [lịch MQL5 đầy đủ](https://www.mql5.com/en/economic-calendar). Dữ liệu widget không đi vào batch, JSON công khai, kịch bản ECO hay điểm ETH. [Điều khoản MQL5](https://www.mql5.com/en/about/terms) hạn chế truy cập tự động và sao chép/phân phối lại; do đó không scrape MQL5 thành nguồn batch. Sự kiện, múi giờ và số trong widget là của bên thứ ba, có thể khác bảng ECO.

| Nguồn ECO | Đường dữ liệu | Phạm vi |
|---|---|---|
| BLS | [iCalendar](https://www.bls.gov/help/hlpiCAL.htm), `https://www.bls.gov/schedule/news_release/bls.ics`; [API v2](https://www.bls.gov/developers/api_signature_v2.htm) | CPI, NFP, PPI, JOLTS và các bản tin lao động/giá khác; năm series số liệu mùa vụ |
| BEA | [iCalendar](https://www.bea.gov/news/schedule/icalendar), [lịch công bố đầy đủ](https://www.bea.gov/news/schedule/full) và từng bản tin | GDP, PCE, cán cân thương mại, giao dịch/vị thế đầu tư quốc tế |
| Federal Reserve | [FOMC](https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm) và [lịch sự kiện theo tháng](https://www.federalreserve.gov/newsevents/calendar.htm) | FOMC, biên bản, Beige Book, sản xuất công nghiệp, tín dụng tiêu dùng |
| DOL | [lịch và kho weekly claims](https://oui.doleta.gov/unemploy/claims_arch.asp), PDF thông cáo từng ngày | Weekly initial jobless claims; ngoại lệ ngày nghỉ trong lịch nguồn |

Lịch ECO lọc theo USD và các sự kiện Mỹ; không tuyên bố bao phủ PMI tư nhân, sự kiện toàn cầu hoặc toàn bộ diễn văn. Widget MQL5 bù khoảng trống xem lịch toàn cầu nhưng không cấp quyền tái sử dụng dữ liệu. Nội dung cơ quan chính thức được trích theo trường số/lịch cần thiết, dẫn link bản gốc; không sao chép hình ảnh, logo hay bài viết. Attribution không hàm ý cơ quan nguồn bảo chứng ECO. Xem [BLS copyright](https://www.bls.gov/bls/linksite.htm), [BEA FAQ 145](https://www.bea.gov/help/faq/145) và [Fed disclaimer](https://www.federalreserve.gov/disclaimer.htm).

## Kết quả gắn sự kiện

Mỗi sự kiện giữ `scheduled_at`, `source_title`, `reference_period`, `data_vintage_at` và `data_status` riêng. Đã qua giờ dự kiến **không** tự động chuyển thành đã công bố. Hàng chưa đối chiếu được đúng kỳ để `actual/previous` null và UI nói rõ chưa xác minh.

- BEA GDP, PCE và trade lấy `actual/previous` từ đúng bản tin có tiêu đề/kỳ tương ứng. PCE có thêm Core PCE; GDP là % annualized; trade là tỷ USD.
- DOL lấy initial claims đã điều chỉnh mùa vụ từ PDF đúng ngày công bố; kỳ tham chiếu là tuần kết thúc, đơn vị nghìn. Kiểm ngày công bố và chuỗi tuần, không gán continuing claims vào initial claims.
- BLS chỉ gắn năm series vào **sự kiện gần nhất đã qua** khi kỳ API khớp kỳ suy ra từ ngày công bố. Đây là **vintage mới nhất tại lúc batch tải**, có thể đã được revision; không được coi là số đúng bản tin tại thời điểm lịch sử. Các sự kiện BLS khác vẫn null nếu không có parser nguồn đúng kỳ.
- `forecast` trong bảng ECO vẫn null vì các nguồn sơ cấp này không cung cấp consensus đã được cấp quyền. `previous` không thay thế `forecast`; không tự tính surprise từ hai cột đó. Widget MQL5 hiển thị dự báo riêng của MetaQuotes.

Năm series BLS seasonally adjusted: `CUSR0000SA0` CPI index; `CES0000000001` NFP level (nghìn); `LNS14000000` thất nghiệp %; `WPSFD4` PPI final demand index; `JTS000000000000000JOL` job openings (nghìn). CPI/PPI tính `100 × (index_month/index_previous_month − 1)` và làm tròn một chữ số; NFP là chênh lệch hai mức lao động tháng. Thiếu tháng thì null. API warning catalog có thể đi cùng data hợp lệ, lỗi status/thiếu series bị chặn. Footnote `P` là sơ bộ. [FAQ BLS](https://www.bls.gov/developers/api_faqs.htm) nêu độ trễ và revision.

`reference_period` là thời kỳ quan sát; `scheduled_at` là giờ dự kiến; `retrieved_at` là lần tải body; `checked_at` là lần HTTP/cache gần nhất. Thời điểm số liệu thật được đăng lên API có thể không biết. Snapshot hiện tại không tạo vintage lịch sử để backtest point-in-time. Kịch bản USD/vàng/crypto là suy luận có điều kiện từ [cơ chế Fed](https://www.federalreserve.gov/monetarypolicy/monetary-policy-what-are-its-goals-how-does-it-work.htm), [World Gold Council](https://www.gold.org/goldhub/research/the-impact-of-monetary-policy-on-gold) và [IMF WP 2023/163](https://www.imf.org/en/publications/wp/issues/2023/08/04/the-crypto-cycle-and-us-monetary-policy-534834). `high/medium` là mức ECO tự phân loại, không phải xác suất, dự báo giá hay khuyến nghị giao dịch.

## Lịch chạy và tài nguyên

| Cron UTC | Giờ Việt Nam | Vai trò |
|---|---|---|
| `37 0 * * *` | 07:37 hằng ngày | Rà lại lịch BLS, BEA, Fed, DOL và BLS API |
| `37 13,18 * * 1-5` | 20:37 và 01:37 hôm sau, thứ Hai–Sáu UTC | Bắt kết quả sau các khung giờ công bố Mỹ |

GitHub có thể chạy trễ; job dùng concurrency chung với batch ETH. Lịch nguồn được cache 20 giờ giữa các lần quét, ép refresh ở 00 UTC; BLS API cache 4 giờ. BEA/DOL bản tin vừa công bố cache 4 giờ; DOL PDF cũ cache 180 ngày. GET có ETag/Last-Modified khi nguồn hỗ trợ; cache nội bộ có hash. Lịch Fed tháng chỉ tải các tháng trong cửa sổ 45 ngày trước và 180 ngày sau. Browser chỉ tải JSON release bất biến của ECO khi mở tab, revalidate pointer/status mỗi 15 phút khi đang xem; widget MQL5 chỉ tải khi người xem mở mục tương ứng.

## Snapshot, phát hành và lỗi

`python -m eco.calendar` lưu toàn bộ response nguồn, canonical JSON và manifest dưới `data/raw/calendar/<run-id>` (Git ignored). Body PDF DOL được mã hóa base64 trong snapshot JSON để giữ bytes/hash. SigV4 PUT/GET từng object vào prefix riêng `raw/calendar/<run-id>/` của bucket private `eco-eth-private`; manifest upload cuối và mọi object phải readback đúng hash trước khi đổi pointer. Không bind raw/R2 vào frontend; secret chỉ qua môi trường/DPAPI hoặc Actions Secrets.

Release `public/data/calendar/releases/calendar-<20hex>/calendar.json` là bất biến; `latest.json` pin path/hash/schema. CAL-01 `calendar-66b4e31ed958b40e784f` được giữ nguyên; CAL-02 thêm release con với `revision.reason=expanded_official_coverage_and_period_matched_results`. `status.json` ghi heartbeat/lỗi. Nội dung không đổi không sinh release mới. Fetch/parse/coverage/R2 fail thì giữ pointer tốt; UI fail mạng/hash giữ bản đã xác minh. Hơn 48 giờ từ batch success thì cảnh báo lịch cũ. Không biến lỗi thành số 0 và không phát hành dữ liệu raw có bản quyền.

Tại lần kiểm CAL-02 ngày 08/10/2026: 111 sự kiện trong cửa sổ, 17 có `actual/previous`, 25 response nguồn và 27 object private readback. Đây là số đếm snapshot, có thể thay đổi ở batch sau; không phải cam kết mọi sự kiện đã qua đều có actual.

## Kiểm tra và bước tiếp

```text
python -m unittest discover -s tests -p test_calendar.py -v
node --test tests/calendar.test.mjs
node scripts/check-calendar.mjs http://127.0.0.1:8877/
```

Browser QA kiểm ngày VN/ET, bốn viewport, tám locale, filter, hash/network fallback và Core 10. Widget cần kiểm trong browser tương tác có hỗ trợ bên thứ ba; đầu nối headless có thể nhận HTTP 404 từ Tradays dù trình duyệt ứng dụng hiển thị. Các kiểm chứng thực tế và deploy ghi `HANDOFF.md`.

Bước kế nếu muốn đưa consensus/global event **vào JSON ECO**: chọn provider có quyền backend/cache/public derived rõ ràng, timestamp availability và lịch revision, rồi tạo adapter/version khác. Không đổi nguồn, đơn vị hoặc phân loại dưới `us-macro-calendar-v1.1.0`.
