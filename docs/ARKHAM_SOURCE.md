# Arkham ETH — nguồn đối chiếu và kế hoạch dữ liệu

Kiểm tra ngày 2026-10-03 qua [trang ETH](https://arkm.com/explorer/token/ethereum), [API Guide](https://arkm.com/docs), API Reference và điều khoản chính thức. Trang token truy cập được không cần tài khoản: entity balance changes, top flows, on-chain exchange flow, top holders, transfers và nhóm theo entity. Đã thao tác nhóm theo entity thành công. Dữ liệu chuyển hiển thị trong phiên xem có thời gian cũ và yêu cầu đăng nhập để xem đầy đủ; đây không phải chứng cứ series daily hoàn chỉnh hoặc dữ liệu realtime.

Dashboard đã thêm đường đối chiếu Arkham ETH và [Binance](https://arkm.com/explorer/entity/binance), kèm mô tả phạm vi. Điểm ECO 7 vẫn ghép các component Coin Metrics theo version đã khóa. Arkham có nhánh nguồn/định nghĩa riêng, chưa thay provider của `exchange_share` dưới version cũ.

## Dùng được gì, cần kiểm gì

| Dữ liệu / endpoint chính thức | Ứng dụng ETH | Ranh giới phải giữ |
|---|---|---|
| `GET /token/holders/ethereum?groupByEntity=true` | Nhận diện cohort sàn, custody, cầu nối, staking; đo độ tập trung của tập đã quan sát | Top holders giới hạn 100 mỗi page và `offset+limit <= 1000`; không đại diện toàn bộ holder/sàn. Response tách theo chain. Nhãn `prediction` không phải xác nhận. Không tự dựng tổng exchange share từ danh sách top |
| `GET /portfolio/timeSeries/entity/{entity}?pricingId=ethereum&chains=ethereum` | Chuỗi số dư ETH theo sàn để đối chiếu P3; cohort phải khóa/version riêng | Tài liệu xác nhận daily UTC, map ngày → chain → pricing ID. Chưa có response thật để chốt đơn vị/schema/lịch sử hữu dụng. Phải kiểm tất cả địa chỉ/chuyển custody, overlap và nhãn sửa hồi cứu |
| `GET /transfers/histogram` với `base=type:cex`, `chains=ethereum`, `tokens=ethereum`, `granularity=1d` | Dòng vào/ra sàn làm diagnostic độc lập của P3; có count và historical USD value | API key bắt buộc; browser session/anonymous không được phép. `base` bắt buộc. Cửa sổ không khớp ngày cho bucket một phần; `timeLte` inclusive. Thiếu bucket không tự biến thành 0 |
| `GET /transfers`, `/history/entity/{entity}`, intelligence updates | Kiểm tx/trace và lưu lịch sử sửa nhãn; hỗ trợ nghiên cứu activity/spending của cohort | Mẫu giao dịch hoặc histogram có base filter không phải toàn bộ native ETH network; không đủ để thay AdrActCnt, Dormancy, coin age hay NVT adjusted transfer value |

Các endpoint được xác minh trên [API Reference](https://arkm.com/docs#api-reference), không suy từ API nội bộ trình duyệt. Homepage/API coverage claim không thay audit ETH field-by-field.

## Các lỗi diễn giải đã phát hiện trên trang token

- Mặc định `ALL NETWORKS`: khi đối chiếu native Ethereum phải lọc Ethereum L1. Không cộng ETH/WETH/L2/bridge như các nguồn cung mới độc lập.
- Hợp đồng Beacon Deposit giữ lịch sử ETH đã nạp; địa chỉ này không đại diện số ETH hiện còn staking sau withdrawals. Không lấy tỷ trọng của nó làm staking supply hoặc holder đang nắm giữ.
- Entity CEX/custodian/bridge/fund và predicted labels khác nhau. Một ví custody cho tổ chức không tự động là exchange inventory. Không double-count địa chỉ dưới entity và address cùng lúc.
- Giá/vốn hóa trang token lấy dữ liệu pricing từ CoinGecko; timestamp và UTC close chưa được xác minh. Không ghép giá intraday đó với component daily Coin Metrics.

## Truy cập và quyền

[Getting Access](https://arkm.com/docs#getting-started/access) yêu cầu account, API plan hoặc trial được xét duyệt, rồi key. Tài liệu công bố mức subscription bắt đầu $100; chưa mua hoặc cam kết chi phí. Biểu mẫu `/api` yêu cầu Full Name, Email, Use case, đăng nhập và API Terms. Sau khi người dùng cung cấp tên thật/xác nhận điều khoản, tài khoản miễn phí và xác minh email đã hoàn tất; mật khẩu random lưu DPAPI ngoài repo. CAPTCHA do người dùng hoàn tất. Không có credential trong evidence, Git hoặc frontend.

**Trial hiện hành đã kiểm trên browser sau đăng nhập:** cần thẻ, miễn phí 30 ngày rồi tự kích hoạt Starter **1.500 USD/tháng**. Không submit/kích hoạt luồng trial đó hoặc nhập thẻ. Đã gửi yêu cầu trial nghiên cứu thủ công không thẻ/không tự gia hạn/0 USD đến `support@arkm.com`, địa chỉ quan sát được trong menu Contact Support chính thức. Thư có trong Sent lúc **18:03 ngày 2026-10-03 (Việt Nam)**; Arkham xác nhận **[Request received] lúc 18:06**, còn chờ xét duyệt trial/quyền. Đây là xác nhận nhận thư, chưa là API entitlement hoặc licence.

[Using with AI Agents](https://arkm.com/docs#resources/coding-agents) mô tả MCP, coding agent và x402. Tuy nhiên [API Terms](https://arkm.com/api-terms-of-service) mục 1.2 giới hạn Authorized Users là người, mục 8.2 hạn chế chia sẻ và công khai dữ liệu/dẫn xuất. Hướng dẫn kỹ thuật không tự thay điều khoản cấp quyền. Cần xác nhận bằng văn bản theo trial/subscription cho automation của backend, lưu raw private/R2, giữ revision và công khai chỉ số/CSV dẫn xuất phi thương mại. Không bật x402 hoặc request bằng key khi quota/đơn giá chưa được xác định.

Probe `node scripts/probe-arkham.mjs 2026-10-02` chỉ dùng endpoint chính thức không key, không gửi email, không đăng ký account/chấp nhận terms và không tiêu thụ credit. Raw response (có thể chứa IP trong error HTML) nằm trong `data/raw/arkham/` bị Git ignore; báo cáo chỉ in metadata/hash. HTTP 401/403 không phải series rỗng, không là coverage 0. Coverage và quyền public còn `null/false` cho tới khi có bằng chứng thật.

Probe thực tế 2026-10-03: cả holders và histogram trả HTTP 403, content-type HTML, tại perimeter Cloudflare. Không phân biệt được entitlement của backend từ response này; không gọi đây là thiếu lịch sử ETH. [Evidence chỉ chứa metadata/hash](evidence/arkham-source-2026-10-03.json), SHA-256 `7cec3683f806293d8319b0c680d90658e08b8d96c78c0ef71c5cbd5a4641fe59`. Browser đọc trang/tài liệu được sau security verification tự hoàn tất; không giải CAPTCHA hoặc dùng session cookie để vượt cổng API.

[Hồ sơ trial](ARKHAM_TRIAL_REQUEST.md) đã gửi theo yêu cầu trực tiếp của người dùng. [Evidence đăng ký/gửi/nhận](evidence/arkham-registration-2026-10-03.json), SHA-256 `8d037205929c7b723663dc905b529f520cef2ae229b2b7ee1e9ed3d6879a5241`, chỉ có metadata/hash; bản định danh, thư và screenshot private. Evidence probe cũ giữ nguyên: account chưa tồn tại tại lần probe trước. Chưa có API key, quota/đơn giá và quyền backend/cache/public derived được cấp; lịch sử/coverage vẫn chưa xác minh.

## Thứ tự triển khai khi cổng truy cập đạt

1. Xin trial phi thương mại, giới hạn cohort 5–10 sàn, hỏi rõ quota và quyền tải/caching/derived publication/CSV. Thống nhất quyền agent/backend với phần API Terms đang hạn chế. Credential chỉ ở backend/DPAPI/Actions Secrets; không đưa key trong URL, frontend hay chat.
2. Một sample daily timeSeries cho Binance ETH L1, kiểm chuỗi ngày UTC, đơn vị ETH, token-native identity, status nguồn và dates thực; tiếp đó cohort 5–10 sàn với danh sách entity/version/hash. Chốt ngày earliest/latest thật, gaps, nhãn confidence và vintage available-at (unknown giữ null).
3. Chia lịch sử theo quota đã xác minh; snapshot raw + request filters + hashes + manifest, private R2 PUT/GET readback. Không gọi full-history chỉ vì trang UI có top holders.
4. Đối chiếu daily balances với SplyExNtv theo cùng ngày. Báo coverage cohort và chênh lệch, không coi cohort nhỏ là tổng số dư trên mọi sàn. Dòng vào/ra dùng hai histogram `in/out`, UTC 00:00:00–23:59:59, loại nội bộ entity và double-count khi định nghĩa cho phép. Buckets thiếu là unknown trừ khi nguồn xác nhận đầy đủ và zero.
5. Khóa source/normalizer/weights dưới version Arkham candidate riêng **trước** full backtest; có causal prefix/revision tests, AP so với Core/Extended, correlation/ablation/regime và kiểm định prospective. Chỉ thêm vào aggregate sau ADR/version mới, giữ tất cả score/release cũ.

Không có Arkham score mới được giả lập từ bảng UI, không tuyên bố đã backfill hoặc có quyền API/derived publication khi mới đọc tài liệu. Nguồn này hữu ích nhất trước mắt cho cohort exchange balance/flow và kiểm chất lượng P3; E8/E9 cần định nghĩa/quyền coverage riêng.
