# Lịch kinh tế và kịch bản USD / vàng / crypto

CAL-01, ngày 08/10/2026; phiên bản `us-macro-calendar-v1.0.0`. Tab `#calendar` độc lập với methodology, điểm và lịch sử Core 10.

## Nguồn và phạm vi

| Nguồn | Đường dữ liệu thật | Nội dung |
|---|---|---|
| BLS | [iCalendar](https://www.bls.gov/help/hlpiCAL.htm), `https://www.bls.gov/schedule/news_release/bls.ics` | CPI, NFP, PPI, JOLTS, ECI, năng suất, giá xuất nhập khẩu |
| BEA | [iCalendar](https://www.bea.gov/news/schedule/icalendar), `https://www.bea.gov/news/schedule/ics/online-calendar-subscription.ics` | GDP, Personal Income and Outlays/PCE, thương mại |
| Fed | [FOMC](https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm) | Ngày cuối cuộc họp định kỳ; 14:00 ET là thông lệ, gắn `≈` để xác minh statement |
| BLS Public Data API | [API v2](https://www.bls.gov/developers/api_signature_v2.htm), POST `https://api.bls.gov/publicAPI/v2/timeseries/data/` | Một request gồm năm series, không API key |

Chọn nguồn sơ cấp miễn phí, có thể tái lập, thay cho feed thương mại/consensus của Forex Factory. Lịch có ngày/giờ, USD, mức ảnh hưởng, sự kiện, actual/forecast/previous và trạng thái; mobile chuyển hàng thành card. Phạm vi là các tin Mỹ chủ chốt; chưa bao gồm lịch toàn cầu, PMI tư nhân, weekly claims, phát biểu hoặc sự kiện riêng của crypto.

[BLS copyright](https://www.bls.gov/bls/linksite.htm) cho phép tái sử dụng nội dung public domain và yêu cầu ghi nguồn. [BEA FAQ 145](https://www.bea.gov/help/faq/145) và [Fed disclaimer](https://www.federalreserve.gov/disclaimer.htm) cho phép đối với nội dung không có ngoại lệ chỉ rõ. Chỉ chọn lịch/số liệu chính thức, không sao chép hình ảnh, logo, bài viết hoặc nội dung bên thứ ba có quyền riêng. Attribution không hàm ý cơ quan nguồn bảo chứng ECO.

## Hợp đồng dữ liệu và đánh giá

Lịch nguồn không có consensus hoặc actual gắn từng event, nên `actual/forecast/previous` của sự kiện đều null, UI hiện `—` và giải thích cạnh bảng. Đã qua giờ dự kiến không xác nhận công bố. Khối **Số liệu BLS mới nhất** giữ kỳ tham chiếu riêng, không tự gán vào hàng lịch.

Năm series đều seasonally adjusted: `CUSR0000SA0` CPI index; `CES0000000001` tổng việc làm phi nông nghiệp, nghìn; `LNS14000000` thất nghiệp %; `WPSFD4` PPI final demand index; `JTS000000000000000JOL` job openings, nghìn. CPI/PPI = `100 × (index_month/index_previous_month − 1)`, một chữ số thập phân. NFP = hiệu mức việc làm hai tháng, nghìn. Hai series còn lại là mức tháng. Kỳ trước dùng cùng phép biến đổi và đúng tháng trước; thiếu tháng → null. Warning catalog vẫn có thể đi cùng data hợp lệ; thiếu series/status lỗi bị chặn. Footnote `P` là sơ bộ. [FAQ API](https://www.bls.gov/developers/api_faqs.htm) nêu độ trễ cập nhật; số liệu có thể được revision.

`reference_period` là tháng quan sát; `scheduled_at` là giờ công bố dự kiến; `sources.*.retrieved_at` là lúc thực tải response; `checked_at` là lần HTTP/cache kiểm gần nhất. Thời điểm công bố thực và thời điểm API lần đầu có số liệu không được cung cấp, được coi là không biết. Không dùng vintage này để tuyên bố backtest point-in-time.

Mức `high/medium` là phân loại ECO, không do nguồn cấp và không phải xác suất. Kịch bản theo inflation/labor/growth/policy so với kỳ vọng thị trường, không dùng kỳ trước như forecast hoặc tự kết luận surprise/buy/sell. Diễn giải do ECO tổng hợp từ [cơ chế Fed](https://www.federalreserve.gov/monetarypolicy/monetary-policy-what-are-its-goals-how-does-it-work.htm), [World Gold Council](https://www.gold.org/goldhub/research/the-impact-of-monetary-policy-on-gold) và [IMF WP 2023/163](https://www.imf.org/en/publications/wp/issues/2023/08/04/the-crypto-cycle-and-us-monetary-policy-534834). Đây là suy luận có điều kiện; quan hệ của nhóm tài sản không xác định phản ứng từng sự kiện, coin hoặc stablecoin. Chưa backtest đánh giá từng event.

## Lịch cập nhật và tài nguyên

| Cron UTC | Giờ Việt Nam | Mục đích |
|---|---|---|
| `37 0 * * *` | 07:37 mỗi ngày | Ba lịch và một POST BLS |
| `37 13,18 * * 1-5` | 20:37 và 01:37 hôm sau, thứ Hai–Sáu UTC | Kết quả sau khung công bố Mỹ 08:30/10:00/14:00 ET |

GitHub có thể trễ hoặc chờ concurrency `daily-eth-publication`. Job chia sẻ khóa với hai batch ETH để không tranh commit. Đây là batch; chưa xác nhận đã quan sát cron tương lai chỉ bằng việc tạo workflow.

Actions Cache chỉ giữ response official công khai dưới `data/raw/calendar/cache`, không credential, Coin Metrics hoặc Arkham. Cache repo public không phải kho bí mật. Cache SHA-256 được kiểm trước khi dùng. Lịch có TTL 20 giờ giữa các run, refresh lúc 00h UTC, conditional ETag/Last-Modified; BLS API TTL 4 giờ, tối đa ba POST tự động/ngày, cuối tuần một. Job không cài NumPy hoặc tải lịch sử ETH.

Canonical content hash bỏ timestamp attempt. Dữ liệu không đổi giữ release/pointer; một status heartbeat/ngày hoặc failure/recovery có thể tạo commit. Trình duyệt lazy-load khi vào tab, revalidate hai JSON nhỏ mỗi 15 phút khi mở/visible, giữ release immutable. Không gọi API nguồn từ browser.

## Snapshot, phát hành và lỗi

`python -m eco.calendar` tạo snapshot private gồm bốn source records, canonical JSON và manifest dưới `data/raw/calendar/<run-id>`. UTF-8 response được bảo toàn qua chuỗi JSON và hash riêng; nguồn cached giữ timestamp tải ban đầu. Dùng lại token bucket-limited qua environment, SigV4 PUT/GET tại `raw/calendar/<run-id>/` trong `eco-eth-private`. Kiểm bất biến object, upload manifest cuối và readback tất cả trước publication. Không cấp credential mới hoặc bind raw vào frontend. Cache công khai và snapshot R2 private có vai trò khác nhau.

Public `releases/calendar-<20hex>/calendar.json` bất biến; `latest.json` pin hash/path/schema; `status.json` ghi trạng thái. Release mới có ID cha/lý do `official_schedule_or_latest_vintage_update`; không sửa release cũ. Pointer đổi atomic; client kiểm SHA-256, version, allowed host, schema, null consensus và receipt backup. Status heartbeat không chứng minh snapshot số liệu có vintage mới.

Nguồn/parse/coverage/cache/R2 lỗi giữ pointer tốt và status error; workflow chỉ stage allowlist calendar, không stage release khi batch fail. UI lỗi mạng/hash giữ nội dung tốt và retry. Hơn 48 giờ batch success thì cảnh báo cũ. Raw, credential và snapshot chưa được phép không commit. Chưa diễn tập rollback production.

## Kiểm tra và tiếp tục

```text
python -m unittest discover -s tests -p test_calendar.py -v
node --test tests/calendar.test.mjs
node scripts/check-calendar.mjs http://127.0.0.1:8877/
```

Browser QA dùng Playwright/Chrome có sẵn hoặc `PLAYWRIGHT_MODULE`/`CHROME_EXECUTABLE`. Kiểm filter, ngày FOMC Việt Nam/ET, 1440/768/390/360, locale, lỗi mạng/hash, không gọi provider và regression chart Core 10. Kết quả thực, Actions/Pages/domain được ghi HANDOFF.

Tab mới có English/Tiếng Việt. Calendar ở các lựa chọn ngôn ngữ khác tạm fallback English, ngày/số vẫn theo locale; các tab trước giữ translation packs hiện hữu.

Muốn thêm global coverage, consensus hoặc actual gắn từng release: mở adapter/version mới sau kiểm coverage, đơn vị, availability và quyền public. Không tự thay provider hoặc đoán giá trị dưới version hiện hành.
