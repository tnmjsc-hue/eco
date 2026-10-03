# ADR-006 — Tích hợp bảy thành phần trên dashboard Experimental

Ngày quyết định: 2026-10-03. Trạng thái: chấp nhận theo yêu cầu trực tiếp của người dùng trong phiên này.

Người dùng yêu cầu tích hợp ba proxy đã hoàn thành vào bốn chỉ số đầu. Dashboard chính dùng version mới `extended-v0.1.0`; chế độ Core 4 vẫn đối chiếu được. Đây là mở rộng phạm vi preview nghiên cứu, chưa phải nghiệm thu mô hình dự báo hoặc sản phẩm vận hành đầy đủ. Không thay hợp đồng `core-v0.1.0`, `network-proxies-v0.1.0` hay tên/công thức E3/E8/E9 gốc.

## Quyết định trước kiểm định tổng hợp

Điểm Extended = 75% Core + 25% mean(P3, P8, P9). E1/E5/E6 mỗi thành phần 12,5%; E7 37,5%; mỗi proxy 8⅓%. Giữ tỷ lệ nội bộ Core và giới hạn ảnh hưởng của nhóm proxy còn đang thăm dò. Đây là lựa chọn thiết kế, không tối ưu theo AP đã biết. Bảy thành phần tương quan; không quảng cáo bảy nguồn xác nhận độc lập. Tỷ trọng sàn cao/hoạt động cao không tự chứng minh rủi ro giảm giá.

Đồng trọng số bảy metric sẽ tăng ảnh hưởng nhóm giá và proxy, đồng thời giảm mạnh E7; chưa có bằng chứng để chọn cách đó. Giữ ba proxy ở tab riêng không đáp ứng yêu cầu tích hợp mới. Core cũ không bị sửa và vẫn có thể chọn trên dashboard.

## Cổng dữ liệu và phát hành

Protocol riêng được lưu/hash trước lần tính tổng hợp đầu tiên. Chỉ ghép component đã chuẩn hóa từ hai release cha đã xác minh hash, ETH/daily UTC, phương pháp và quyền Community phi thương mại. Ghép đúng ngày quan sát; thiếu một trong bảy thì Extended null. Hai nguồn cập nhật lệch ngày không được forward-fill hoặc dùng score gần nhất thay ngày hiện tại. Chỉ hiển thị ngày có điểm với ngày gốc; status ghi chờ component nếu cần.

Release Extended giữ parent release IDs, manifest/history hashes, protocol/engine hashes, attribution và revision. Không sửa file đã công bố; correction tạo release khác. Lịch sử reconstructed không trở thành as-published, thời điểm nguồn sẵn có vẫn không biết. Arkham là nhánh nguồn riêng cần xác minh đơn vị, coverage, vintage nhãn và quyền tải/lưu/công khai; không thay Coin Metrics dưới version này.

## Phạm vi thay thế ADR-005

ADR-005 và protocol proxy vẫn giữ nguyên cho công bố ba chuỗi metric riêng. Theo yêu cầu mới, ADR này cho phép dùng các chuỗi đó trong **preview Experimental mới**. Điều kiện của ADR-005 về prospective validation vẫn áp dụng trước tuyên bố hiệu quả dự báo hoặc vận hành sản phẩm đầy đủ. Holdout đã dùng lại nên báo cáo tổng hợp chỉ có giá trị thăm dò; phải báo cả kết quả bất lợi và giữ trọng số đã khóa.
