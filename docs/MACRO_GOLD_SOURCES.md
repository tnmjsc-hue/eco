# Nguồn bổ sung cho phân tích vàng — 2026-11-18

## Quyết định nguồn

| Kênh | Nguồn | Kết quả rà | Vai trò hiện tại |
|---|---|---|---|
| Lợi suất thực 10 năm | US Treasury `TC_10YEAR` | Sidecar `macro-market-v1.0.0` đã tải, backup và công bố theo ngày | Số đo ở bảng thị trường; chưa vào kết luận Gold `macro-cross-v1.0.1` |
| USD broad | Fed H.10 `JRXWTFB_N.B` | Sidecar đã có, có độ trễ và không phải DXY | Số đo ở bảng thị trường; chưa vào kết luận Gold |
| Kỳ vọng chính sách hàm ý | [Atlanta Fed Market Probability Tracker](https://www.atlantafed.org/research-and-data/data/market-probability-tracker) | Mô hình của Atlanta Fed dùng quyền chọn SOFR từ CME để ước lượng phân phối cho **bình quân SOFR ba tháng** của các quý tới. Trang công khai kết quả và lịch sử; [điều khoản](https://www.atlantafed.org/terms-of-use) dành quyền riêng cho dữ liệu bên thứ ba. Chưa xác minh quyền tái phân phối output CME-derived trên ECO. | Liên kết tới nguồn gốc; không copy số/xác suất hoặc gọi đó là xác suất quyết định FOMC kế tiếp |
| Giá chuẩn vàng | [LBMA Precious Metal Prices](https://www.lbma.org.uk/prices-and-data/precious-metal-prices) | LBMA/IBA công bố benchmark vàng hai lần/ngày, dữ liệu công khai có độ trễ. [FAQ](https://www.lbma.org.uk/prices-and-data/lbma-gold-price/lbma-gold-price) và [ICE licensing FAQ](https://www.theice.com/publicdocs/IBA_LBMA_Gold_Price_Licensing_FAQ.pdf) nêu quyền redisplay/redistribution riêng. Lịch sử đầy đủ chuyển vào Members' Portal, truy cập nghiên cứu phi thương mại cần duyệt. | Liên kết tới nguồn gốc; `gold_usd` vẫn null |
| Giá vàng tháng | [World Bank Pink Sheet](https://www.worldbank.org/en/research/commodity-markets) | Giá trung bình tháng; [World Bank data licensing](https://datacatalog.worldbank.org/public-licenses) mặc định CC BY 4.0 cho dataset do World Bank sản xuất, nhưng chuỗi gold lấy giá benchmark bên thứ ba và cần xác minh điều khoản riêng. Không đủ tần suất cho phản ứng sự kiện. | Chỉ là ứng viên bối cảnh dài hạn, không đưa vào sidecar ngày |
| Kỳ vọng qua survey | [New York Fed Survey of Market Expectations](https://www.newyorkfed.org/markets/market-intelligence/survey-of-market-expectations) | Thu trước FOMC nhưng kết quả thường công bố sau biên bản họp khoảng ba tuần. | Không giả thành kỳ vọng đã biết trước sự kiện tại ECO |
| FedWatch | [CME FedWatch API](https://www.cmegroup.com/market-data/market-data-api/fedwatch-api.html) | API có phí và [điều khoản phân phối](https://www.cmegroup.com/market-data/files/market-data-license-agreement-updates-june-2026.pdf) riêng. | Không mua/nhập dữ liệu khi chưa có entitlement và quyền công bố |

## Đã thêm vào sản phẩm

Card Gold nói rõ nhãn v1 là kịch bản từ lạm phát/hoạt động; lợi suất thực và USD ở bảng bên dưới là số đo theo ngày và **chưa tham gia kết luận**. Bảng nguồn cung cấp link trực tiếp Atlanta Fed MPT và LBMA Gold Price với mô tả đúng kỳ/độ trễ. Không thêm JSON data, proxy vàng, xác suất Fed hoặc thay `macro-cross-v1.0.1`.

## Điều kiện mở numeric integration

1. Xác minh bằng văn bản quyền ECO hiển thị/tái phân phối chính các giá trị dẫn xuất MPT và LBMA, hoặc chọn một nguồn khác có quyền rõ ràng; ghi điều kiện attribution và licence vào manifest. Quyền đọc website không tự cấp quyền sao chép vào JSON public.
2. Chốt metric semantics: MPT SOFR theo quý khác xác suất FOMC; USD broad ngày khác DXY; LBMA fixing khác spot intraday. Ghi `observation_date`, `source_available_at`, `retrieved_at`, `first_seen_at` riêng.
3. Thiết kế version mới cho ghép các kênh: cùng cutoff, max age, ngưỡng vật chất, nguồn hash, xử lý ngày lệch và mâu thuẫn; giá vàng/real yield/USD cần cửa sổ trước/sau tin nếu muốn nói phản ứng. Không đổi nhãn Gold đã phát hành ở v1.

Quyết định này giữ lịch sử điểm và assessment bất biến. Lựa chọn thêm ngay số từ chart công khai bị loại vì quyền và timing chưa đủ; dùng vàng token/ETF/futures thay spot cũng bị loại vì khác đại lượng.
