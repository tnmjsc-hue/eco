# ADR-008 — Tích hợp metric hợp lệ vào Core 10 Experimental

Ngày khóa: 2026-10-03, trước code/tính điểm/backtest mới. Trạng thái: chấp nhận phạm vi nghiên cứu phi thương mại theo yêu cầu tích hợp Core của người dùng. Protocol máy: `configs/research/core-v0.2.0.json`.

E1/E5/E6/E7 và ba proxy đã qua source/coverage/licence; E2/C1/C2 cũng đã qua replay, exact-parent và R2 readback trong ADR-007. Nguồn hợp lệ cho phép tính thành phần nghiên cứu, chưa chứng minh giá trị dự báo. Phiên bản `core-v0.2.0` mới tích hợp cả ba, giữ các release `core-v0.1.0`, `extended-v0.1.0`, `diagnostics-v0.1.0` bất biến. Raw diagnostics vẫn giữ hợp đồng không có score của ADR-007; chuẩn hóa nằm trong Core mới.

| Thành phần | Chiều raw trước chuẩn hóa | Trọng số |
|---|---|---:|
| E1/E5/E6 | Giữ nguyên điểm cha, mỗi thành phần | 12,5% |
| E7 | Điểm MVRV-Z cha | 18,75% |
| E2 | NUPL, lớn hơn → điểm cao hơn | 18,75% |
| P3 exchange_share | Điểm tỷ trọng sàn cha | 3,125% |
| C2 exchange_balance_pressure | Số dư sàn t trừ t−30, lớn hơn → điểm cao hơn | 3,125% |
| C1 supply_scarcity | Âm của % thay đổi nguồn cung 30 ngày | 6,25% |
| P8 address_activity | Điểm hoạt động địa chỉ cha | 6,25% |
| P9 value_per_transfer | Điểm giá trị mỗi transfer cha | 6,25% |

Ngân sách nhóm bằng ECO 7: giá 37,5%, định giá 37,5%, mạng 25%. E2 và E7 chia ngân sách cùng nhóm MVRV; không coi là hai bằng chứng độc lập. Mạng chia đều bốn họ sàn/nguồn cung/địa chỉ/transfer; hai phép đo sàn chia ngân sách họ sàn. Trọng số chọn theo cấu trúc thông tin, không tối ưu theo kết quả lịch sử.

E2 phản ánh lợi nhuận chưa thực hiện cao hơn theo MVRV. C1 là giả thuyết mức khan hiếm tương đối khi tăng cung ròng giảm, có thể liên quan nhu cầu/burn nhưng chịu thay đổi cơ chế London/Merge/Dencun; điểm cao không đồng nghĩa giá sắp giảm. C2 là giả thuyết lượng ETH tăng trên địa chỉ được gắn nhãn sàn làm tăng lượng có thể giao dịch; không đo gross inflow hoặc chứng minh bán. Tài liệu [Coin Metrics Exchange Supply](https://gitbook-docs.coinmetrics.io/network-data/network-data-overview/exchange/exchange-supply) xác định số dư theo nhãn, có thể thiếu địa chỉ. [Current Supply](https://gitbook-docs.coinmetrics.io/network-data/network-data-overview/supply/current-supply) xác định total issued supply; [Ethereum issuance](https://ethereum.org/roadmap/merge/issuance/) mô tả đổi cơ chế phát hành/burn. Các nguồn xác nhận ngữ nghĩa, không xác nhận chiều dự báo đã chọn.

Ba feature mới dùng q05/q95 tuyến tính trên raw hợp lệ của **1.460 ngày lịch trước t**, tối thiểu 365 quan sát, loại t khỏi fit rồi clip 0–100. Giữ lịch diagnostic đầy đủ trước khi join lịch Core; giữ signed/zero/null và cờ flash; cửa sổ raw 30 ngày không đổi. Không fill, không biến thiếu thành 0/50; thiếu bất kỳ thành phần bắt buộc thì composite null. Dataset reconstructed, `source_available_at=null`, không giả lịch sử as-published.

Đánh giá cùng ngày hoàn tất nhãn future drawdown −50% trong 365 ngày, từ 2020; baseline Core 4/ECO 7/E7/nhóm giá, paired block bootstrap 90 ngày ×10.000 seed 20261003, correlation/ablation/regime. Holdout đã dùng, mọi kết quả là thăm dò; không retune khi kết quả kém, không gọi score là xác suất. E4 chưa đạt bằng chứng bổ sung và giữ R&D; original RHODL/Dormancy/NVT vẫn chờ entitlement, proxy không đổi tên thành original.

Phương án không chọn: thêm ba metric đồng trọng số sẽ đếm lặp MVRV/sàn; sửa ECO 7 dưới version cũ làm thay đổi lịch sử; giữ toàn bộ ở tab diagnostics không đáp ứng yêu cầu tích hợp. Phiên bản mới là quyết định nghiên cứu thay thế, không tuyên bố hoàn thành tương đương chín metric gốc.

Phát hành chỉ sau xác minh hash/version/licence/readback của bốn release cha và lineage diagnostic/ECO 7 đúng Core + network cha, replay normalization, tests và UI. Parent revision tạo release mới và revision ledger; first-publication chỉ ghi ngày thực sự công bố, giữ bản trước. Daily fail giữ pointer cũ; không publish mixed-vintage hoặc mất coverage đã có. GitHub main → Pages và domain phải kiểm thật. Không công khai raw/private credentials, không mở rộng quyền thương mại.
