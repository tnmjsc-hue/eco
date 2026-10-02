# Quyền sử dụng dữ liệu Coin Metrics

**Trạng thái: được áp dụng CC BY-NC 4.0 cho preview nghiên cứu phi thương mại sau xác nhận của người dùng ngày 2026-10-03.** Không phải quyền thương mại hay thư chấp thuận riêng của provider. Quyết định mới ở [ADR-002](ADR-002-experimental-research-preview.md); các ghi nhận dưới đây giữ bối cảnh trước xác nhận và được giới hạn bởi quyết định mới.

## Phạm vi đã giải quyết

Tài liệu [Coin Metrics Community Data](https://docs.coinmetrics.io/packages/coin-metrics-community-data) liên kết trực tiếp CC BY-NC 4.0. Người dùng đã xác nhận “Phi thương mại, công bố nghiên cứu”. Section 2/3 của [legal code](https://creativecommons.org/licenses/by-nc/4.0/legalcode.en) cho phép chia sẻ/biến đổi trong phạm vi NonCommercial với attribution, license link, ghi modifications và không endorsement. Áp dụng cho chart giá Community, derived Core/CSV và lưu snapshot nghiên cứu. UI/manifest/CSV đều ghi nguồn/licence/thay đổi/disclaimer. Raw vẫn private, không commit.

Không đòi thư riêng cho phạm vi được giấy phép công khai này cấp. Vẫn phải xin quyền phù hợp nếu thương mại hóa hoặc dùng nguồn/licence khác. Không tự suy diễn API Pro/Glassnode hay candidate chưa truy cập được cũng được cấp quyền. Availability/revision lịch sử vẫn chưa biết.

## Bằng chứng đã đọc

- Tài liệu API v4 nói Community HTTP API không cần API key và dành cho cộng đồng theo Creative Commons.
- Tài liệu truy cập dữ liệu mô tả Community là miễn phí cho mục đích phi thương mại theo Creative Commons và dẫn chiếu điều khoản sử dụng.
- Kho archive `coinmetrics/data` ghi rõ dữ liệu CSV được cung cấp theo **CC BY-NC 4.0**. License này giới hạn sử dụng phi thương mại và yêu cầu ghi công; lưu bản sao raw không tạo quyền tái phân phối thương mại.
- API v4 có thể trả dữ liệu phụ thuộc quyền/licensing riêng của upstream; việc một trường trả HTTP 200 không tự xác nhận quyền xuất dữ liệu thô, cache dài hạn, chart công khai hay phân phối dẫn xuất.

## Cách xử lý trong dự án

- Tiếp tục audit local như nghiên cứu phi thương mại theo điều khoản áp dụng; lưu request, response hash và provenance riêng tư. Đây không phải kết luận pháp lý hay quyền tái phân phối.
- Không đưa raw response, CSV archive hoặc snapshot chưa rõ quyền lên repo public, Pages hay bucket public.
- Mục đích đã xác nhận phi thương mại; quyền preview theo giấy phép nêu trên. Quyền thương mại **chưa được cấp**.
- Trước khi thương mại hóa hoặc thay phạm vi/nguồn, review quyền và xin giấy phép tương ứng. Không đổi provider ngầm dưới cùng version.
- Không dùng CapRealUSD hoặc FeeTotUSD khi Community probe trả 403. `CapMrktCurUSD / CapMVRVCur` là giá trị dẫn xuất đại số với cùng provider/ngày; quyền sử dụng đầu vào và dẫn xuất vẫn cần được xác nhận cho kiểu phát hành đã chọn.

## Nguồn và lần xem

Đã xem ngày 2026-10-03:

- [Coin Metrics API v4: Community API](https://docs.coinmetrics.io/api/v4/)
- [Coin Metrics: Access Our Data / API Access](https://gitbook-docs.coinmetrics.io/access-our-data/api)
- [Coin Metrics Community Data](https://gitbook-docs.coinmetrics.io/packages/coin-metrics-community-data)
- [Kho archive và ghi chú CC BY-NC 4.0](https://github.com/coinmetrics/data/blob/master/README.md)
- [Creative Commons BY-NC 4.0](https://creativecommons.org/licenses/by-nc/4.0/)

## Chưa được cấp hoặc chưa biết

- Quyền sử dụng thương mại hoặc licence ngoài Community; không suy rộng preview thành quyền bán tín hiệu/quảng cáo.
- Chính sách revision/backfill và thời điểm availability lịch sử theo từng metric.
- Điều khoản/entitlement riêng của nguồn mở rộng chưa chọn. Review lại quyền khi đổi mục đích hoặc phạm vi vận hành.
