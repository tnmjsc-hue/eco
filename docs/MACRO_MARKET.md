# Số đo thị trường bên cạnh lịch kinh tế

Protocol `macro-market-v1.0.0`, schema `macro-market-v1.0.0`. Đây là sidecar độc lập; không sửa `macro-cross-v1.0.1`, assessment/ledger đã phát hành hoặc Core 10. Chốt protocol trước triển khai theo §16 của đặc tả macro.

## Nguồn, quyền và phạm vi

| Metric ID | Nguồn cố định | Đơn vị | Tuổi tối đa |
|---|---|---|---|
| `treasury_2y` | Fed H.15 `RIFLGFCY02_N.B` | percent, chênh lệch bps | 7 ngày |
| `treasury_10y` | Fed H.15 `RIFLGFCY10_N.B` | percent, chênh lệch bps | 7 ngày |
| `real_yield_10y` | US Treasury daily real yield XML `TC_10YEAR` | percent, chênh lệch bps | 7 ngày |
| `usd_broad` | Fed H.10 `JRXWTFB_N.B` | index, thay đổi percent | 14 ngày |
| `eth_usd` | Coin Metrics Community, giá ETH trong Core 10 đã xác minh | USD, thay đổi percent | 4 ngày |
| `gold_usd` | Chưa có nguồn được phép phát hành | null | Không áp dụng |

[Fed cho phép phân phối thông tin do Board tạo với dẫn nguồn](https://www.federalreserve.gov/disclaimer.htm). Treasury là dữ liệu cơ quan liên bang Mỹ; [17 USC §105](https://www.copyright.gov/title17/92chap1.html#105) áp dụng với tác phẩm Chính phủ Mỹ. Không suy rộng quyền này tới dữ liệu bên thứ ba. ETH giữ CC BY-NC 4.0/ADR-002 và attribution của parent đã công bố. Không công khai body raw, credential hoặc data thương mại.

Fed H.10 công bố trễ: chỉ số USD broad không phải ICE DXY, không phải quote intraday. Fed DDP đang có kế hoạch ngừng dịch vụ; nguồn đổi phải protocol mới, không fallback âm thầm. Treasury real yields không phải nominal yields trừ CPI. Không dùng BTC, ETF vàng hoặc giá phái sinh thay vàng spot.

## Hợp đồng tính toán

- `as_of` là cutoff UTC do caller cung cấp. `usable_at <= as_of`; feed mới giữ `retrieved_at` thật, usable_at từ lúc tải đúng content. ETH imported từ parent có `retrieved_at=null`, `knowledge_basis=verified_parent_computed_at`, usable_at từ computed_at đã pin: không giả timestamp tính là timestamp tải nguồn. Mỗi observation date phải là ngày trước cutoff UTC (bảo thủ với feed ngày); ngày hiện tại/tương lai bị loại. Không coi retrieval/check time là ngày quan sát hoặc giờ công bố.
- Parser kiểm đúng series ID, unit, multiplier và định dạng số hữu hạn; không ánh xạ qua thứ tự cột. XML xác định trường `NEW_DATE` và `TC_10YEAR`. Null/ND không thành 0. Trùng ngày khác giá trị bị từ chối. Calendar dates và timestamp malformed bị từ chối.
- Chọn hai ngày quan sát hợp lệ liên tiếp mới nhất, cho phép cuối tuần/ngày nghỉ. Khoảng cách trên 7 ngày bị chặn. Nếu endpoint có ngày mới nhất nhưng giá trị bị thiếu, giữ `missing_latest_value`, không lùi về số cũ để gắn nhãn mới.
- Lợi suất: `(latest - previous) * 100` bps. USD/ETH: `(latest / previous - 1) * 100` percent, previous > 0. Decimal, không làm tròn trước tính. Chỉ làm tròn khi hiển thị.
- Tuổi tính từ ngày quan sát, không từ lần tải. Quá biên vẫn giữ số/ngày và nhãn `stale`; lỗi tải giữ release cũ và status lỗi. Không nói mọi metric cùng ngày. Cặp số theo ngày là `daily_change`, **không xác nhận phản ứng do sự kiện** hoặc dự báo giá.
- `event_reaction.status=not_measured`, reason `no_verified_intraday_window`; không có giá trước/sau quanh timestamp công bố thực. `consensus.status=unavailable`, reason `no_approved_pre_release_consensus`; current-vintage forecast tải sau tin không chứng minh consensus trước tin. Không tính surprise, không đổi forecast null của calendar v1.
- Feed consensus tương lai cần entitlement phân phối, mapping metric/unit/SA/kỳ, snapshot hash ghi nhận **trước giờ công bố thực**, actual first-release cùng metric và cửa sổ cố định. Feed intraday cần quote trước/sau có timestamp, tolerance, nguồn/đơn vị/cửa sổ và sự kiện đồng thời. Chưa có các đầu vào này thì không bật nhánh ngầm.

## Công bố và vận hành

Batch `python -m eco.macro_market` tạo raw snapshot private, manifest hash và R2 PUT/GET readback trước publication. Dùng token bucket hiện có, prefix `raw/macro-market/`; không bind frontend. Public chỉ gồm các cặp số đã trích, protocol, source hash/provenance, hash parent ETH và receipt. ID từ hash input/protocol và predecessor nếu có; chỉ cache theo bản hiện hành. A → B → A tạo publication thứ ba; cache/check lại không sửa bytes release cũ. Status heartbeat ghi riêng. Lock, immutable collision và pointer atomic dùng cùng quy tắc macro hiện có.

Frontend kiểm checksum release/manifest/normalized input/protocol, đúng metric registry, thời gian, formula, enum, parent ETH full hash. Lỗi mạng/hash giữ ngày gốc với nhãn lỗi; kiểm tuổi lại tại render. Không có provider request từ browser. Module thị trường refresh cùng lịch, locale/timezone không thay ID hoặc delta.

Actions cache chỉ giữ body nguồn liên bang công khai của calendar/market, không snapshot raw riêng, ETH inputs hoặc credential. Runner mất cache phục hồi timestamp lần tải đầu của đúng source URL/hash từ input immutable đã verify, rồi xác minh body tải lại cùng hash; không tạo vintage mới chỉ vì runner mới tải cùng content. Publisher đối chiếu normalized input hash và toàn bộ manifest snapshot với receipt, không chấp nhận receipt của payload khác.

Chạy `test_macro*.py`, Node `macro-market.test.mjs` và macro/calendar contracts, browser `scripts/check-calendar.mjs`. Fixtures tổng hợp chỉ trong tests; live artifacts phải nguồn thật/backup thật. Đối chiếu Decimal, bps/percent, giá trị âm của real yields, missing/latest/cutoff/age/holiday/revision/hash/lock và provider outage. Việc đo daily changes không phải nghiệm thu consensus hoặc intraday reaction; HANDOFF phải ghi riêng phần đã hoàn thành và phần bị thiếu đầu vào.
