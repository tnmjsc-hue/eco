# Nghiên cứu nguồn và bằng chứng kiểm tra

Ngày kiểm tra: **2026-09-29**, môi trường local `E:\ETH-CBBI`, Windows/PowerShell. Đây là research log cho việc lập kế hoạch, không phải data audit hoàn chỉnh.

## 1. Trạng thái workspace lúc bắt đầu

- `Get-ChildItem -Force` không trả file/directory trong workspace.
- `Test-Path .codegraph` trả `False`; vì vậy bỏ qua CodeGraph theo chỉ dẫn người dùng.
- `git status --short --branch` báo chưa phải Git repository.
- Chưa có application, dữ liệu dự án, package manifest, test hoặc pipeline cần tiếp tục. Các file Markdown hiện tại được tạo trong phiên lập kế hoạch.

## 2. Nguồn gốc CBBI đã đọc

| Nguồn | Kết luận sử dụng |
|---|---|
| [Website CBBI](https://colintalkscrypto.com/cbbi/) | 9 metric, điểm tổng hợp và biểu đồ giá tô màu theo điểm; có bật/tắt metric |
| [FAQ](https://colintalkscrypto.com/cbbi/faq.html) | Giải thích điều chỉnh hồi quy, thay đổi lịch sử và lịch cập nhật; không hứa dự đoán ngày/giá tương lai |
| [Repository chính thức](https://github.com/Zaczero/CBBI) | Python implementation, README và license |
| [Commit cố định](https://github.com/Zaczero/CBBI/tree/efd6dcf08b9b8619c63b8669dee0990b4f076aac) | SHA lấy từ GitHub API `/repos/Zaczero/CBBI/commits/main` trong phiên |
| [main.py](https://github.com/Zaczero/CBBI/blob/efd6dcf08b9b8619c63b8669dee0990b4f076aac/main.py) | Clip từng metric trước tổng hợp và serialize JSON |
| [utils.py](https://github.com/Zaczero/CBBI/blob/efd6dcf08b9b8619c63b8669dee0990b4f076aac/utils.py) | Cách đánh dấu cực trị trên chuỗi và các helper |
| [Pi Cycle](https://github.com/Zaczero/CBBI/blob/efd6dcf08b9b8619c63b8669dee0990b4f076aac/metrics/pi_cycle.py) | Có SMA111 và SMA350 nhân 2, nhưng còn nhiều xử lý chuẩn hóa và cực trị |
| [2 Year MA](https://github.com/Zaczero/CBBI/blob/efd6dcf08b9b8619c63b8669dee0990b4f076aac/metrics/two_year_moving_average.py) | Dùng log deviation và các mô hình biên; không đơn thuần đổi tỷ số ra phần trăm |
| [MVRV](https://github.com/Zaczero/CBBI/blob/efd6dcf08b9b8619c63b8669dee0990b4f076aac/metrics/mvrv_z_score.py) | Có logic liên quan Bitcoin halving và hiệu chỉnh riêng; không chuyển thẳng sang ETH |
| [Trolololo](https://github.com/Zaczero/CBBI/blob/efd6dcf08b9b8619c63b8669dee0990b4f076aac/metrics/trolololo.py) | Hệ số và ngày gốc dành cho BTC; ETH cần model riêng |
| [Woobull](https://github.com/Zaczero/CBBI/blob/efd6dcf08b9b8619c63b8669dee0990b4f076aac/metrics/woobull_topcap_cvdd.py) | Lấy Top/CVDD từ dữ liệu Bitcoin bên ngoài; chưa có bằng chứng thay asset sang ETH được |
| [LICENSE](https://github.com/Zaczero/CBBI/blob/efd6dcf08b9b8619c63b8669dee0990b4f076aac/LICENSE) | Upstream mang license AGPL-3.0; cần kiểm tra nghĩa vụ nếu dùng mã nguồn đó |

Kết luận thiết kế: kế thừa trải nghiệm và cấu trúc composite; mặc định viết engine ETH riêng với causal normalization. Đây là quyết định của dự án, không phải hướng dẫn của tác giả CBBI.

Giới hạn: chưa clone/chạy upstream; chưa snapshot mọi file; chưa tái lập score BTC hiện tại; chưa thực hiện browser visual audit. Website được đọc ở dạng nội dung trích xuất, không phải ảnh chụp bố cục đã xác minh.

## 3. Kiểm tra Coin Metrics Community API

Thực hiện HTTP GET bằng PowerShell, không có API key. Trường `end_time` dùng đúng request dưới đây; bảng số dòng là kết quả thực tế, không phải giả định về tính inclusive của mọi API.

Base URL: `https://community-api.coinmetrics.io/v4/timeseries/asset-metrics`.

### 3.1 Kết quả các probe

| Probe | Metrics và khoảng thời gian | HTTP | Kết quả |
|---|---|---|---|
| A | PriceUSD, CapMrktCurUSD, CapRealUSD, CapMVRVCur, SplyCur, FeeTotUSD; 2021-01-01..2021-01-03 | 403 | Thông báo từ chối `CapRealUSD` cho ETH/1d |
| B | PriceUSD, CapMrktCurUSD, SplyCur, FeeTotUSD; cùng khoảng | 403 | Thông báo từ chối `FeeTotUSD` cho ETH/1d |
| C | CapMVRVCur; cùng khoảng | 200 | 3 dòng MVRV |
| D | PriceUSD; 2015-08-01..2015-08-10 | 200 | 3 dòng, từ 2015-08-08 |
| E | PriceUSD, CapMrktCurUSD, SplyCur, CapMVRVCur; 2021-01-01..2021-01-03 | 200 | 3 dòng, cả 4 trường có dữ liệu |
| F | Cùng 4 trường; 2026-09-25..2026-09-28 | 200 | 4 dòng, cả 4 trường có dữ liệu |
| G | CapMVRVCur; 2015-08-01..2015-08-10 | 200 | 3 dòng, từ 2015-08-08 |

Probe A/B không chứng minh các trường còn lại bị cấm; chính probe E xác nhận bộ Core truy cập được. HTTP 403 phản ánh quyền của request Community tại thời điểm thử, không chứng minh metric không tồn tại ở gói khác.

### 3.2 Một số giá trị phản hồi, chỉ để đối chiếu adapter

| Ngày do API trả | PriceUSD | CapMrktCurUSD, rút gọn | CapMVRVCur |
|---|---:|---:|---:|
| 2021-01-01 | 730.91432063121 | 83,392,527,577.6079 | 1.672616430722 |
| 2021-01-02 | 775.296622443016 | 88,467,283,101.4569 | 1.74242746175 |
| 2021-01-03 | 990.365324956166 | 113,022,171,397.9615 | 2.02839789176 |
| 2026-09-28 | 2689.03811857978 | 328,290,112,075.4039 | 1.14520093874074125 |

Các số trên là dữ liệu mẫu provider trả tại lần thử, không phải chỉ số ETH của dự án hoặc thông tin giá để giao dịch. Raw timestamp có dạng `2021-01-01T00:00:00.000000000Z`; chưa chốt ánh xạ period-end. Không dùng bảng đã làm tròn làm golden dataset cho production.

Hai probe 2015 trả PriceUSD `1.19999` cho cả ba ngày; MVRV lần lượt `5.78278879`, `4.88081534`, `4.62344756`. Cần audit chất lượng thời kỳ đầu và tác động đến hồi quy, không tùy tiện xóa các ngày này.

### 3.3 Lệnh tái kiểm tra đã sử dụng

Các lệnh sau truy cập nguồn ngoài; dữ liệu có thể đã thay đổi khi chạy lại. Chỉ probe, không tự tải toàn bộ lịch sử.

```powershell
$uri = 'https://community-api.coinmetrics.io/v4/timeseries/asset-metrics?assets=eth&metrics=PriceUSD,CapMrktCurUSD,SplyCur,CapMVRVCur&frequency=1d&start_time=2021-01-01&end_time=2021-01-03&page_size=3'
Invoke-RestMethod -Uri $uri | ConvertTo-Json -Depth 8
```

[Request Core lịch sử](https://community-api.coinmetrics.io/v4/timeseries/asset-metrics?assets=eth&metrics=PriceUSD,CapMrktCurUSD,SplyCur,CapMVRVCur&frequency=1d&start_time=2021-01-01&end_time=2021-01-03&page_size=3)

[Request Core gần ngày nghiên cứu](https://community-api.coinmetrics.io/v4/timeseries/asset-metrics?assets=eth&metrics=PriceUSD,CapMrktCurUSD,SplyCur,CapMVRVCur&frequency=1d&start_time=2026-09-25&end_time=2026-09-28&page_size=4)

Chưa lưu nguyên response body ra snapshot/hash trên đĩa trong phiên lập kế hoạch. Agent thực hiện task D01 phải tạo bằng chứng machine-readable có timestamp và checksum trước khi dựa vào chúng để tái lập kết quả.

### 3.4 Suy ra realized cap: điều biết và điều chưa biết

[Định nghĩa Coin Metrics](https://docs.coinmetrics.io/network-data/network-data-overview/market/market-capitalization) cho `CapMVRVCur = CapMrktCurUSD / CapRealUSD`. Vì thế có thể tính `derived_realized_cap = CapMrktCurUSD / CapMVRVCur`, dùng hai đầu vào cùng provider/ngày/snapshot, với mẫu số dương.

Đây là phép suy ra, không phải đã gọi thành công CapRealUSD. Chưa so sánh với series trực tiếp do không có quyền endpoint. Cần ghi rõ sai số do precision, khả năng revision lệch nhau, phương pháp ETH account-based và giới hạn sử dụng dữ liệu dẫn xuất. Không được dùng phép suy ra để tuyên bố mọi dataset premium đều truy cập miễn phí.

## 4. Nguồn dữ liệu bổ sung và giới hạn

| Nguồn chính thức | Nội dung đã kiểm tra | Giới hạn với kế hoạch |
|---|---|---|
| [Coin Metrics API](https://docs.coinmetrics.io/api/v4/) | Community endpoint không cần key; có rate limits | Kiểm tra lại rate limit hiện hành lúc code, không hardcode theo suy đoán |
| [Coin Metrics archive](https://github.com/coinmetrics/data) | CSV theo coin, README ghi CC BY-NC 4.0 và khả năng thay đổi bộ metric | Chưa tải CSV ETH, chưa xác minh đầy đủ lịch sử; không mặc định dùng thương mại |
| [Coin Metrics realized cap account-based](https://github.com/coinmetrics/docs-website/blob/master/asset-metrics/market/caprealusd.md) | Quy ước lần hoạt động cuối theo tài khoản khác UTXO | Không coi đây là chi phí mua thực của từng người |
| [Glassnode indicators](https://docs.glassnode.com/basic-api/endpoints/indicators) | Có endpoint RHODL (docs ghi BTC) và account-based dormancy/NUPL | Không xác minh entitlement, quyền gói hoặc ETH coverage |
| [Glassnode metadata](https://docs.glassnode.com/basic-api/metadata) | Metadata giúp xác định asset/metric coverage và đặc tính dữ liệu | Cần probe với quyền thực; nhãn sàn có thể thay đổi theo thời gian |
| [CoinGecko Demo historical endpoint](https://docs.coingecko.com/demo/reference/coins-id-market-chart) | Tài liệu giới hạn 365 ngày lịch sử ở Demo | Không dùng làm nguồn duy nhất cho 2Y MA và backtest nhiều chu kỳ |
| [Ethereum Merge](https://ethereum.org/roadmap/merge/) | ETH chuyển PoW → PoS, ngày 2022-09-15 | Puell dựa trên miner không giữ nguyên ý nghĩa |
| [Ethereum fork timeline](https://ethereum.org/ethereum-forks/) | Nguồn chuẩn cho các sự kiện giao thức | Trích ngày sự kiện vào config khi triển khai research |
| [ECharts LICENSE](https://github.com/apache/echarts/blob/master/LICENSE) | Nguồn kiểm tra license thư viện biểu đồ đề xuất | Chưa cài thư viện hoặc chốt version |

## 5. Những điều chưa được chứng minh

- Chưa có production canonical dataset/engine; D03 đã audit full-history snapshot riêng tư. Còn một missing-row date ở requested end và 7 đầu ngày null cho ba metric định giá.
- Chưa biết độ trễ công bố từng metric theo thời gian, lịch sử revision và vintage dữ liệu cũ.
- Chưa có kết quả backtest, độ chính xác hoặc điểm ETH hiện tại.
- Chưa có bằng chứng E1 với 111/350/2 có tác dụng báo đỉnh ETH.
- D05: E3/E8 chưa có source/entitlement/ETH-history đủ xác minh; E4 `FeeTotNtv` là candidate có sample access; E9 adjusted transfer value có catalog range nhưng timeseries Community bị 403.
- Chưa xác minh tính hữu ích của fee-native hoặc NVT proxy qua Merge, EIP-1559, blob fees, L2, bridge, MEV và internal transfers.
- Chưa có quyền phát hành công khai hoặc thương mại cho mọi loại dữ liệu dự kiến.
- Chưa có visual audit responsive, test app, build, hosting hoặc scheduler thực tế.

## 6. Cách cập nhật research log

Mỗi xác minh mới thêm ngày, URL/endpoint, version/commit, loại bằng chứng (`docs`, `live_probe`, `full_audit`, `backtest`), kết quả và điều vẫn chưa biết. Không ghi đè bằng chứng cũ nếu nguồn thay đổi; ghi sự khác biệt và ảnh hưởng tới kế hoạch.

## 7. Probe cập nhật 2026-10-03

Đã chạy capability probe 12 request và D03 full-history 5 trang/4.080 rows cho bốn input Core. Bằng chứng, hash và phạm vi xem [data-audit.md](data-audit.md); raw response vẫn local private/ignored. D02 đã ghi period mapping; không có `source_available_at` hoặc revision vintage.

Tài liệu hiện hành được đọc lại cho Community API, API Access và kho archive. Tài liệu access mô tả dùng phi thương mại theo Creative Commons; archive ghi CC BY-NC 4.0. Chưa giải quyết quyền thương mại và tái phân phối output ECO. API timestamp là 00:00 UTC; period-end được hiểu theo daily UTC docs, availability lịch sử và revision chưa chốt. Protocol frozen ở [ADR-001](ADR-001-core-research-protocol.md), map 9 vị trí ở [metric-feasibility.md](metric-feasibility.md), rights tại [data-rights.md](data-rights.md).

### 3.8 Probe cập nhật D05 — 2026-10-03

Chạy `node scripts/audit-d05-feasibility.mjs 2026-10-03` không dùng API key. Catalog Coin Metrics HTTP 200 liệt kê 7 metric ETH/1d: `CapRealUSD`, `FeeBlobTotNtv`, `FeePrioTotNtv`, `FeeTotNtv`, `FeeTotUSD`, `SplyAct1yr`, `TxTfrValAdjUSD`, với khoảng thời gian được ghi trong [evidence JSON](evidence/d05-live-probe-2026-10-03.json). Timeseries mẫu 2021-01-01..03 chỉ `FeeTotNtv` trả HTTP 200 và 3/3 giá trị; sáu metric còn lại trả HTTP 403. Điều này phân biệt catalog availability với entitlement của Community timeseries.

Ba trang tài liệu Glassnode Indicators, Supply và Metadata trả HTTP 200; có các thuật ngữ RHODL, `dormancy_account_based`, realized-cap/HODL và ETH/asset. Đây chỉ là bằng chứng tài liệu; không có API key/entitlement để xác minh asset coverage, lịch sử, đơn vị hoặc quyền derived/public/commercial. E3/E8/E9 vẫn chưa được chọn; E4 `FeeTotNtv` vẫn R&D-only. Raw bodies và manifest đầy đủ nằm local trong `data/raw/d05/` và không commit.

### 3.9 Full-history audit E4 — 2026-10-03

Đã chạy `node scripts/backfill-fee-coinmetrics.mjs 2015-07-30 2026-10-03` cho `FeeTotNtv` ETH/1d. Adapter tải 5 trang/4.083 dòng từ 2015-07-30 đến 2026-10-02, không ngày thiếu, duplicate, timestamp sai, sai asset, null hoặc âm; 8 giá trị zero đầu lịch sử được giữ lại và khai báo trong quality policy. Canonical SHA-256 `c0cd16263f6ebf33ef2c431a057fc827612bdd67b0312927f308e31b8fbe4f8c`, manifest SHA-256 `862aa7b185903259b6ab56f72d7ffd46570c6827e4cee0234ffb694ca6bb5362`. Raw pages/canonical/manifest private và bị Git ignore; summary ở [evidence/e4-fee-backfill-2026-10-03.json](evidence/e4-fee-backfill-2026-10-03.json).

Đây là bằng chứng coverage và quality hiện tại, không phải bằng chứng source availability/vintage hoặc quyền public riêng cho candidate. `FeeTotNtv` vẫn R&D-only. Theo tài liệu Fee Metrics của Coin Metrics, Ethereum `FeeTotNtv` bao gồm execution và blob fees, được tạo bởi base/priority/blob fees và vẫn tính phần bị burn; E4-02 phải khóa semantics qua Merge/EIP-1559/Dencun trước khi viết feature.

## 8. Engine, kiểm định và quyền preview — 2026-10-03

Loại evidence: `docs`, `engine_tests`, `backtest`, `browser_qa`. Đọc lại [Community Data chính thức](https://docs.coinmetrics.io/packages/coin-metrics-community-data): trang trực tiếp dẫn [CC BY-NC 4.0](https://creativecommons.org/licenses/by-nc/4.0/) và [legal code](https://creativecommons.org/licenses/by-nc/4.0/legalcode.en). Link Labs cũ redirect về trang Talos, không dùng trang redirect để suy diễn điều khoản Community. Người dùng xác nhận “Phi thương mại, công bố nghiên cứu”; áp dụng scope licence và attribution theo ADR-002, không cấp quyền commercial/nguồn khác. Ghi nhận rights-unconfirmed cũ vẫn mô tả thời điểm trước xác nhận.

Engine causal thực thi frozen ADR-001; 19 unit tests Python, 3 tests web và kiểm 3.000 ngày prefix của snapshot thật đã đạt. Dataset/current vintage không đổi; Core gần nhất 41.379812239861 ngày 2026-10-01, lịch sử reconstructed. Kiểm UTC retrieval phát hiện as-of caller dùng 2026-10-03 trong khi retrieval UTC là 2026-10-02: ngày 02/10 chưa đóng, giữ pending null, không coi là gap sau đóng.

Primary evaluation 2.101 ngày, 648 positives, 10.000 paired 90-day bootstrap replicates, seed 20261003; Core AP 0.55424872, mọi CI Δ so baseline qua 0. Chưa chứng minh incremental utility; không tune lại model. Chi tiết [core-research-report.md](core-research-report.md), quyết định [ADR-002](ADR-002-experimental-research-preview.md). Q02 correlation/ablation/regime đã hoàn tất; vintage realtime/shadow vẫn chưa hoàn tất.

E2-01 đã chốt contract diagnostic `nupl_diagnostic = 1 - 1/CapMVRVCur` với cùng provider/ngày/snapshot E7. Không thêm E2 vào composite; invalid hoặc thiếu MVRV trả null có reason. Evidence tóm tắt tại [evidence/e2-nupl-diagnostic-2026-10-03.json](evidence/e2-nupl-diagnostic-2026-10-03.json); đây không phải một public release mới.

E4-04 exploratory evaluation trên cửa sổ Core 2020-01-01..2025-10-01 cho Fee Activity AP `0.240946`, thấp hơn Core `0.554249`, E7 `0.553773` và nhóm giá `0.545430`; CI moving-block 90 ngày của Fee Activity trừ từng baseline đều nằm dưới 0. Regime trước/sau London, Merge và Dencun khác nhau mạnh, nên chỉ giữ E4 ở R&D-only và không thêm vào Core. Bằng chứng đầy đủ tại [evidence/e4-candidate-evaluation-2026-10-03.json](evidence/e4-candidate-evaluation-2026-10-03.json); không diễn giải là xác suất hay quan hệ nhân quả.

Dashboard thật thay trang intro: Playwright Chrome kiểm 360/390/768/1440, custom E7 366 ngày khớp engine, CSV/null/refresh failure preservation và canvas nonblank đạt; không có page errors. Không mua API, không dùng BTC hoặc metric giả.
