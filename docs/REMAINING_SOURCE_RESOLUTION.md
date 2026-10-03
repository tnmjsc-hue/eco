# Hướng giải quyết E9-01, E3-01 và E8-01

Ngày đối chiếu: **2026-10-03**, giờ Việt Nam. Đây là hướng thực thi cho cổng nguồn; không phải kết quả full-history audit hoặc quyết định chấp nhận metric vào Core.

## 1. Phạm vi của các task -01

Ba task xác định một nguồn có thể được sử dụng cho ứng viên ETH: endpoint đúng, asset/frequency/đơn vị rõ, lịch sử đủ cho câu hỏi nghiên cứu, quyền tài khoản và quyền sử dụng phù hợp. Việc backfill/audit toàn lịch sử nằm ở task -02, triển khai feature ở -03, kiểm định ở -04.

| Task | Dữ liệu cần tìm | Bằng chứng hiện tại | Thiếu để mở task -02 |
|---|---|---|---|
| E9-01 | Giá trị chuyển ETH gốc đã điều chỉnh, tính theo USD mỗi ngày | `TxTfrValAdjUSD` có catalog ETH/1d 2015-08-08..2026-10-02; Community sample 403 | Quyền lấy series, điều chỉnh áp dụng cho ETH, phạm vi licence và lịch sử tài khoản thực sự được tải |
| E3-01 | Realized value phân theo tuổi của ETH, có cohort trẻ/già | Có tài liệu `rcap_hodl_waves`/RHODL; sample và metadata không key 401 | Metadata xác nhận ETH, cohort/đơn vị/tuổi/cost basis và quyền tải/công bố |
| E8-01 | Tuổi ETH đã được chi tiêu hoặc dormancy có phương pháp phù hợp ETH | `dormancy_account_based` không key 401; `SplyAct1yr` Community 403 | Metric thực sự hỗ trợ ETH, cách xác định tuổi/volume và quyền tải/công bố |

401/403 mô tả quyền của request đã thử. Chúng không chứng minh provider không có dữ liệu, cũng không xác định gói phải mua. Catalog range không chứng minh một tài khoản có thể tải toàn range hoặc series không có gaps.

## 2. E9-01 — ETH NVT proxy

### Dữ liệu và định nghĩa

Ứng viên hiện tại cần `TxTfrValAdjUSD`, cùng provider/ngày UTC với `CapMrktCurUSD`. Giả thuyết downstream là `ln(CapMrktCurUSD / SMA90(TxTfrValAdjUSD))`; chưa chạy nó trong task -01.

Theo [Coin Metrics Transfer Value](https://gitbook-docs.coinmetrics.io/network-data/network-data-overview/transactions/transfer-value), adjusted transfer value của account chains dùng native units nhận bởi những account có thay đổi net balance trong giờ đó. Định nghĩa này cần được đối chiếu với cách provider xử lý contract calls, vòng chuyển nội bộ, bridge và MEV; không coi chữ adjusted là bằng chứng tất cả noise đã được loại.

### Trình tự giải quyết

1. Tra coverage và catalog hiện tại cho `TxTfrValAdjUSD`/`TxTfrValAdjNtv`, `asset=eth`, `frequency=1d`; ghi ngày đầu/cuối và đơn vị. Hai field native/USD phải có lineage rõ nếu chọn phương án chuyển đổi.
2. Xác minh entitlement cụ thể của Network Data Pro, demo hoặc quyền nghiên cứu nếu provider cung cấp. Yêu cầu xác nhận đúng metric, ETH, lịch sử và quota; không chọn gói chỉ dựa trên việc xem được biểu đồ.
3. Bằng credential được cấp, thử các cửa sổ nhỏ ở đầu lịch sử, 2017/2021 và gần nhất. Kiểm finite/nonnegative, missing/null, timestamp và pagination. Mẫu số khi tính NVT phải dương; không thay data bị chặn bằng 0.
4. Chốt quyền lưu snapshot private/R2, tính feature, công bố điểm và chart tại `eco.tnmp.cloud`, xuất CSV; ghi rõ quyền tồn tại sau khi dừng subscription và nghĩa vụ attribution.
5. Xuất source contract và evidence. Khi access và licence đạt, mở E9-02 để backfill/audit toàn lịch sử; giữ dataset/protocol riêng nếu semantics thay đổi.

### Phương án thay thế

- Nếu `TxTfrValAdjNtv` được cấp quyền còn USD không được cấp, chỉ nghiên cứu native-to-USD sau khi xác minh cách provider định giá theo ngày. Không mặc định phép nhân với giá cuối ngày tạo cùng metric USD.
- Nếu chỉ có unadjusted transfer value, đó là một giả thuyết NVT khác, cần tên/version và đánh giá sai lệch riêng.
- Tự xây từ Ethereum execution data là một dự án dữ liệu: cần archive/traces, net balance theo giờ, prices, audit sai lệch và licence của dịch vụ dữ liệu; không phải workaround đổi tên volume.

Kiểm đọc bổ sung trong phiên giải thích: header archive chính thức `coinmetrics/data/csv/eth.csv` trả 200 nhưng không có `TxTfrValAdjUSD`, `TxTfrValAdjNtv` hoặc `SplyAct1yr`; Community sample adjusted native trả 403. Đây là kiểm tại thời điểm đọc, không phải full audit archive. [Repo và giấy phép archive](https://github.com/coinmetrics/data).

## 3. E3-01 — realized-value age ratio

### Dữ liệu và định nghĩa

Cần bảng cohort ETH theo ngày: mốc tuổi của từng band, giá trị vốn hóa thực hiện hoặc phần trăm vốn hóa thực hiện trong band, và định nghĩa thời điểm mua/chuyển. Aggregate MVRV không cho biết phân bố cohort.

[Glassnode Supply](https://docs.glassnode.com/basic-api/endpoints/supply) mô tả Realized Cap HODL Waves là các band cost basis, tổng tỷ trọng bằng 100%. Tài liệu RHODL và links minh họa BTC không xác minh được asset ETH của một tài khoản. Tài liệu hiện tại dẫn đến metadata để tra asset; không kết luận BTC-only từ link ví dụ.

### Trình tự giải quyết

1. Dùng metadata lọc `a=ETH`, `i=24h` rồi tra `/supply/rcap_hodl_waves` và các endpoint cohort liên quan. Kiểm `parameters`, `queried`, `timerange`, descriptors và PIT variant nếu có. Đối chiếu cả asset ETH gốc và phạm vi network; token chạy trên Ethereum không đồng nghĩa ETH.
2. Nếu ETH được hỗ trợ, thử một sample có nhiều ngày. Xác định field band, đơn vị USD hay share, các band có tổng hợp đủ không, và cohort trẻ/già có lịch sử cần thiết không. Tỷ trọng phải được kiểm theo scale provider, không giả định 0..1 thay vì 0..100.
3. Yêu cầu phương pháp account-based: tuổi được reset khi nào; chuyển nội bộ, staking, withdrawals, contracts và bridge xử lý ra sao; cost basis được phân bổ thế nào khi gửi một phần số dư.
4. Xác nhận lịch sử full-range, revision/PIT, licence cho cache và derived/public/CSV. Nếu chỉ có history hiện tại mutable, dùng nhãn reconstructed; không gán retrieval thành historical availability.
5. Chốt source contract. Nếu không có RHODL ETH nhưng có cohort ETH hợp lệ, nghiên cứu tỷ lệ cohort riêng ở E3-02/X01; các bands và market-age weighting chưa được tự chốt trong task -01.

### Phương án thay thế

Một provider cohort khác phải có cùng bộ chứng cứ asset/semantics/history/rights. Tự xây ETH cohorts đòi mô hình age/cost-basis ledger được khóa trước, quy tắc partial transfer/staking/bridge và xử lý lịch sử toàn chuỗi; đó là phương pháp ECO riêng. Nếu không có nguồn hoặc phương pháp kiểm chứng được, ghi quyết định loại ứng viên hiện tại với lý do; không dùng RHODL BTC hoặc suy cohort từ MVRV.

## 4. E8-01 — ETH dormancy/spending proxy

### Dữ liệu và định nghĩa

Cần lượng ETH thực sự chi tiêu và tuổi của phần ETH đó theo một quy tắc account-based. Một dạng dormancy có thể là `ETH-days destroyed / spent ETH volume`, nhưng chỉ khóa công thức khi đầu vào và quy tắc tuổi đã rõ.

Điểm cần chỉnh trong diễn giải cũ: `dormancy_account_based` có hậu tố account_based nhưng [tài liệu Indicators](https://docs.glassnode.com/basic-api/endpoints/indicators) mô tả nó là Entity-Adjusted Dormancy, loại chuyển giữa địa chỉ cùng entity và minh họa BTC/UTXO. Tên endpoint không chứng minh hỗ trợ Ethereum. [Active supply của Coin Metrics](https://gitbook-docs.coinmetrics.io/network-data/network-data-overview/supply/active-supply) đo lượng supply đã hoạt động trong một cửa sổ; không cung cấp tuổi bình quân của ETH đã chi tiêu.

### Trình tự giải quyết

1. Tra metadata toàn bộ metrics ETH/24h rồi kiểm endpoint dormancy/CDD/age-related tìm được. Không chỉ thử một endpoint có tên account_based.
2. Với endpoint có ETH, lấy metadata mô tả đơn vị và một sample. Nếu dùng ratio, cả tuổi bị tiêu hủy và spent volume phải cùng provider, phạm vi giao dịch và ngày UTC.
3. Xác minh quy tắc tuổi, partial spending, entity filters, transfers nội bộ, hợp đồng, staking/withdrawals, bridge và phạm vi L1/L2. Có heuristic/entity labels thì ghi revision và PIT policy.
4. Chốt coverage/entitlement và quyền private cache/derived/public/CSV, rồi xuất source contract.
5. Chỉ sau source gate đạt mới mở E8-02 để full-history audit và khóa feature; không tự gọi proxy khác nghĩa là Reserve Risk.

### Phương án thay thế

Nếu không có dormancy ETH, có thể mở một ứng viên active-supply/inactivity riêng khi được cấp dữ liệu và licence. Nó có câu hỏi nghiên cứu và version khác. Nếu tự xây dormancy, cần quy tắc phân bổ tuổi của số dư account được công khai, ledger theo lịch sử và kiểm bias; không thể lấy ngày hoạt động gần nhất của ví rồi gọi là tuổi từng ETH.

## 5. Quyền API, coverage và công bố là ba cổng riêng

[Glassnode API](https://docs.glassnode.com/basic-api/api) hiện mô tả Light API cho Advanced: lịch sử 14 ngày, daily, 50 calls/ngày. Phạm vi này không đủ backfill chu kỳ nhiều năm. Professional phụ thuộc quyền của gói đã cấu hình; cần xác nhận endpoint ETH, history depth và API credits cụ thể. Trang pricing có mô tả gói/FAQ cần đối chiếu với báo giá hoặc quyền tài khoản thực tế; chưa có báo giá được chấp thuận trong dự án.

[Terms của Glassnode](https://studio.glassnode.com/terms-and-conditions) yêu cầu authorization cho public display và quyền redistribution riêng. Phi thương mại không tự mở quyền này. CC BY-NC 4.0 của [Coin Metrics Community](https://docs.coinmetrics.io/packages/coin-metrics-community-data) cũng không tự cấp licence của Network Data Pro/Glassnode.

Đăng ký tài khoản có thể là bước tạo tài khoản/demo; không tự hoàn tất source gate. Trước mua, cần bộ xác nhận provider: metric/asset/đơn vị, lịch sử/resolution, API quota, sample, quyền public derived outputs/CSV/cache và tổng chi phí gồm backfill/daily. Chưa gửi thư hoặc đặt mua trong phiên giải thích này.

## 6. Nghiệm thu và thứ tự thực hiện

Đầu ra của từng task -01:

1. Source contract: provider/endpoint/metric/asset/network/unit/frequency, calendar/timestamp và semantics.
2. Coverage: catalog/metadata theo đúng ETH, khoảng lịch sử tài khoản được cấp; các sample đầu/giữa/cuối và giới hạn.
3. Access evidence: request parameters đã loại secret, HTTP status, schema/sample summary, timestamps và hashes; quota/plan được xác nhận.
4. Rights matrix: private cache/R2, chart, derived score, CSV, public raw, attribution, retention sau subscription; unknown ghi rõ.
5. Quyết định: mở task -02 khi đủ cổng, giữ BLOCKED khi cần entitlement, hoặc loại nguồn/đề xuất phương pháp khác có version rõ.

Thứ tự đề xuất: **E9 → E3 → E8**. E9 đã có metric ETH và công thức giả thuyết; E3/E8 cần xác minh thêm tính phù hợp của metric/account semantics. Một yêu cầu coverage/licence chung cho provider có thể giải quyết nhiều endpoint, nhưng quyết định của ba ứng viên vẫn riêng.

Probe kế tiếp cần hỗ trợ key qua environment/header (Glassnode hỗ trợ `X-Api-Key`), metadata ETH, sample nhiều cửa sổ và phân loại adaptive: unauthorized, forbidden, unsupported asset, no rows, schema error, valid sample. Kết luận phải dựa trên response thực; không cố định 401/403 hoặc copy facts cũ khi provider thay metadata. Full-history/gaps/causality/utility vẫn thuộc task -02/-03/-04.
