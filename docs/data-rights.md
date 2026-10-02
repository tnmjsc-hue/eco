# Quyền sử dụng dữ liệu Coin Metrics

**Trạng thái: D02 đã ghi nhận ranh giới; quyền phát hành vẫn cần xác nhận.** Đây là ghi nhận tài liệu công khai, không phải tư vấn pháp lý hay xác nhận quyền thương mại.

## Bằng chứng đã đọc

- Tài liệu API v4 nói Community HTTP API không cần API key và dành cho cộng đồng theo Creative Commons.
- Tài liệu truy cập dữ liệu mô tả Community là miễn phí cho mục đích phi thương mại theo Creative Commons và dẫn chiếu điều khoản sử dụng.
- Kho archive `coinmetrics/data` ghi rõ dữ liệu CSV được cung cấp theo **CC BY-NC 4.0**. License này giới hạn sử dụng phi thương mại và yêu cầu ghi công; lưu bản sao raw không tạo quyền tái phân phối thương mại.
- API v4 có thể trả dữ liệu phụ thuộc quyền/licensing riêng của upstream; việc một trường trả HTTP 200 không tự xác nhận quyền xuất dữ liệu thô, cache dài hạn, chart công khai hay phân phối dẫn xuất.

## Cách xử lý trong dự án

- Tiếp tục audit local như nghiên cứu phi thương mại theo điều khoản áp dụng; lưu request, response hash và provenance riêng tư. Đây không phải kết luận pháp lý hay quyền tái phân phối.
- Không đưa raw response, CSV archive hoặc snapshot chưa rõ quyền lên repo public, Pages hay bucket public.
- Chưa xác nhận mục đích thương mại của sản phẩm. Vì vậy quyền hiển thị dashboard công khai, tải CSV, cache, phân phối derived score và sử dụng thương mại vẫn **chưa được giải quyết**.
- Trước khi công bố, kiểm tra điều khoản Community hiện hành và xin Coin Metrics xác nhận bằng văn bản về từng mục: derived scores, chart, public display, redistribution/download, retention/cache và commercial use. Nếu quyền không đủ, cần nguồn/licence khác được nghiên cứu và version hóa; không đổi provider ngầm.
- Không dùng CapRealUSD hoặc FeeTotUSD khi Community probe trả 403. `CapMrktCurUSD / CapMVRVCur` là giá trị dẫn xuất đại số với cùng provider/ngày; quyền sử dụng đầu vào và dẫn xuất vẫn cần được xác nhận cho kiểu phát hành đã chọn.

## Nguồn và lần xem

Đã xem ngày 2026-10-03:

- [Coin Metrics API v4: Community API](https://docs.coinmetrics.io/api/v4/)
- [Coin Metrics: Access Our Data / API Access](https://gitbook-docs.coinmetrics.io/access-our-data/api)
- [Coin Metrics Community Data](https://gitbook-docs.coinmetrics.io/packages/coin-metrics-community-data)
- [Kho archive và ghi chú CC BY-NC 4.0](https://github.com/coinmetrics/data/blob/master/README.md)
- [Creative Commons BY-NC 4.0](https://creativecommons.org/licenses/by-nc/4.0/)

## Chưa xác minh

- Bản điều khoản pháp lý hiện hành áp dụng trực tiếp cho API Community và việc lưu snapshot.
- Quyền commercial/publication đối với số liệu và derived outputs cụ thể của ECO.
- Chính sách revision/backfill và thời điểm availability lịch sử theo từng metric.
- Attribution format mà Coin Metrics yêu cầu cho hình thức hiển thị dự kiến.
- Điều khoản Community hiện hành có cho phép snapshot lưu riêng tư dài hạn theo nhu cầu dự án hay không; review lại trước khi đưa pipeline vào vận hành liên tục.
