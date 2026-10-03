# ADR-004 — ETH NVT proxy E9

Ngày khóa protocol: 2026-10-03. Version `e9-nvt-candidate-v0.1.0`, protocol `e9-nvt-v0.1.0-protocol-1`. Trạng thái: triển khai riêng cho nghiên cứu; nguồn và licence còn chặn chạy dữ liệu thật. Chưa chấp nhận E9 vào Core hoặc phát hành điểm E9.

## Công thức và nguồn

Giữ giả thuyết trong backlog: `ln(CapMrktCurUSD / SMA90(TxTfrValAdjUSD))`. Hai trường phải là native ETH trên Ethereum L1, cùng Coin Metrics, daily UTC và USD. Cửa sổ 90 ngày lịch bao gồm ngày t; thiếu một ngày hoặc null transfer thì feature null. Zero thật được giữ, chỉ tính log khi mẫu số dương. Vốn hóa phải dương hoặc null. Tính log dưới dạng hiệu hai log để tránh overflow tỷ số.

[Transfer Value của Coin Metrics](https://gitbook-docs.coinmetrics.io/network-data/network-data-overview/transactions/transfer-value) mô tả điều chỉnh account-based theo thay đổi số dư ròng trong mỗi giờ. Không suy rộng thành lọc hết bridge/MEV hoặc tự chuyển cùng chủ thể. Không đại diện toàn bộ hoạt động ERC20, stablecoin hay L2. Provider có thể sửa dữ liệu lịch sử; ngày tải không chứng minh dữ liệu có sẵn trong lịch sử. Chỉ dùng nhãn reconstructed khi chưa có vintage.

[NVTAdj90 tính sẵn](https://gitbook-docs.coinmetrics.io/network-data/network-data-overview/economics/valuation) có công thức vốn hóa hiện tại chia SMA90 adjusted transfer USD, nhưng probe ETH Community cũng bị từ chối. Không dùng `NVTAdj`, native transfer, free-float cap hoặc transfer chưa điều chỉnh làm đầu vào thay thế dưới version này. Nếu có quyền với nguồn thay thế, mở source contract và version riêng trước khi tính.

## Chuẩn hóa và kiểm định

Normalizer dùng q05/q95 trên 1.460 ngày lịch trước t, tối thiểu 365 raw observations, linear quantile và clip 0–100. Không dùng ngày t để đặt biên của chính nó. Giá trị cao biểu thị vốn hóa cao tương đối với transfer value đã điều chỉnh; không có calibration xác suất và không gọi là CVDD.

Protocol được khóa trước triển khai hoặc xem kết quả E9. So sánh E9 với Core, E7 và nhóm giá trên cùng tập ngày có label drawdown 50% trong 365 ngày tiếp theo. Composite thử nghiệm chỉ trong harness: nhóm giá 50%, E7 25%, E9 25%; ablation bỏ E9 phục hồi Core, bỏ E7, bỏ nhóm giá. Bootstrap paired moving-block 90 ngày lịch, 10.000 replicates, seed 20261003. Báo cáo Spearman, coverage/warm-up, AP/AUC/ngưỡng 90 và bốn regime London/Merge/Dencun. Cửa sổ Core đã xem chỉ dùng mô tả; kể cả AP tăng cũng không chứng minh utility ngoài mẫu.

## Cổng dữ liệu và phát hành

So sánh bỏ E9 phục hồi trọng số Core ban đầu (nhóm giá 50%, E7 50%); đây là comparator Core, không phải renormalize toàn bộ ba trọng số của composite thử nghiệm. Với hai ablation còn lại, renormalize các trọng số còn lại: bỏ E7 cho nhóm giá 2/3 và E9 1/3; bỏ nhóm giá cho E7/E9 mỗi chỉ số 1/2. Harness ghi chính sách này để tránh diễn giải chênh lệch như tác động nhân quả riêng của E9.

Key truy cập không đồng nghĩa licence cho cache, nghiên cứu, chart, derived hoặc CSV. Backend kiểm hồ sơ quyền riêng tư có bằng chứng và thời hạn trước backfill/compute. Snapshot raw, canonical, manifest và kết quả chi tiết ở thư mục Git-ignored, có SHA-256; key chỉ lấy từ environment, không log/lưu trong URL hoặc response đã lưu. Khi provider trả pagination có key, response được khử key trước lưu và manifest ghi cả hash response tải về lẫn hash bytes lưu, không gọi chúng là cùng một bản.

Không chạy E9 trong daily Core khi source chưa đạt, không thêm số giả hoặc sửa trọng số Core. E9-01/02/04 chưa DONE chỉ vì có adapter/fixture. Khi được cấp quyền: probe chính key → backfill closed UTC → kiểm hash/coverage/licence → compute/evaluate → quyết định nghiên cứu → quyền public và gate X02 nếu cần phát hành. Điểm Core đã công bố và `core-v0.1.0` giữ nguyên.

## Các lựa chọn đã cân nhắc

- Community API/CSV hiện tại: không có adjusted transfer ETH được tải; không đủ để hoàn tất E9.
- NVT tính sẵn: không truy cập được trong probe hiện tại; có quyền sau này vẫn cần contract mới cho đầu vào ratio.
- Archive công khai chính thức: query lịch sử được kiểm tra chưa trả snapshot phù hợp; không lấy bản sao bên thứ ba thiếu provenance/licence.
- Tự tổng hợp traces/account balances: là pipeline dữ liệu/phương pháp độc lập, cần archive infrastructure, kiểm netting, định giá và coverage; chưa chọn làm thay thế trong phiên này.
- Network Data Pro/trial: cùng provider/đơn vị thuận lợi, nhưng cần cấp key và quyền cụ thể. Chưa có chi phí được duyệt, không mua gói.
