# Chỉ số có thể triển khai tiếp từ dữ liệu đã lưu

Ngày đánh giá: 2026-10-03. Phạm vi là xác minh mức sẵn sàng, chưa triển khai/phát hành metric mới. Không cần account hoặc API trả phí cho các đầu vào Community đã có; phạm vi nghiên cứu phi thương mại theo [ADR-002](ADR-002-experimental-research-preview.md) và [data-rights](data-rights.md).

## Ưu tiên thực hiện

| Ưu tiên | Chỉ số | Đầu vào và công thức | Phần còn thiếu |
|---|---|---|---|
| 1 | E2 · NUPL dẫn xuất | `1 - 1/CapMVRVCur`; helper và contract đã có | Khóa quyết định xuất raw ratio/%, publisher diagnostic, biểu đồ, CSV, daily/revision và xác minh production |
| 2 | C1 · Thay đổi nguồn cung ETH trong 30 ngày | Đề xuất `100 * (SplyCur(t)/SplyCur(t-30) - 1)` | Contract/phương pháp mới, engine theo ngày lịch, kiểm định và publisher riêng |
| 3 | C2 · Thay đổi số dư ETH trên sàn trong 30 ngày | Đề xuất `SplyExNtv(t) - SplyExNtv(t-30)`, đơn vị ETH | Contract/phương pháp mới, kiểm heuristic/flash/revision, engine/kiểm định/publisher riêng |
| Sau đó | E4 · Fee Activity | Protocol/engine đã khóa `ln(SMA30(FeeTotNtv)/SMA365(FeeTotNtv))` | Giữ R&D; quyết định public metric hiện chưa cho phép promote, cần câu hỏi/protocol mới hoặc prospective |

C1/C2 là đề xuất mới, không phải thay thế tương đương cho RHODL/Dormancy/NVT và chưa có điểm chuẩn hóa hoặc bằng chứng dự báo. Hai công thức 30 ngày chỉ để xác định phạm vi triển khai; chưa frozen hoặc chọn sau backtest. Không thêm các ứng viên này vào `extended-v0.1.0` hoặc sửa lịch sử ECO 7.

E2 nên ưu tiên raw ratio/%, không tạo thêm normalized vote cạnh E7. Đây là biến đổi đại số của MVRV cùng ngày/provider/snapshot, không phải tỷ lệ người đang có lãi hoặc một nguồn xác nhận độc lập. [Contract và kiểm thử hiện có](../eco/core.py), [evidence E2-01](evidence/e2-nupl-diagnostic-2026-10-03.json).

`SplyCur` là current issued supply theo ledger, khác circulating/free-float supply. C1 chỉ mô tả thay đổi nguồn cung provider ghi nhận; không tách được gross issuance và burn chỉ từ hiệu hai giá trị. [Định nghĩa Coin Metrics](https://gitbook-docs.coinmetrics.io/network-data/network-data-overview/supply/current-supply).

C2 mô tả biến động số dư trong các địa chỉ được provider gắn nhãn sàn; không chứng minh tổng nạp/rút, hành vi từng holder hoặc đủ mọi sàn. Nhãn có thể đổi làm số dư bị revision; toàn bộ `SplyExNtv` của snapshot kiểm tra đang có cờ `flash`. [Định nghĩa exchange supply](https://gitbook-docs.coinmetrics.io/network-data/network-data-overview/exchange/exchange-supply).

## Dữ liệu đã kiểm tra

| Snapshot private | SHA-256 canonical | Coverage và giới hạn |
|---|---|---|
| Core tải 02:00:41 UTC | `33264b50fc555e3591cdd61be0301ed84f62505f86a55bd1c3807a9e97d3f976` | 4.081 ngày 2015-08-01–2026-10-02; MVRV có 8 null, 4.073 ngày hợp lệ 2015-08-08–2026-10-01 |
| Network tải 09:14:12 UTC | `ea93bccbcd3b50483b249d4899c5204771b59f13a722003617281300da1c7480` | 4.083 ngày 2015-07-30–2026-10-02; `SplyCur`/`SplyExNtv` không null; exchange flash 4.083 ngày |
| Fee tải 03:12:17 UTC | `c0cd16263f6ebf33ef2c431a057fc827612bdd67b0312927f308e31b8fbe4f8c` | 4.083 ngày cùng range; không null, giữ 8 số 0 đầu kỳ theo policy E4 |

Audit readiness xác nhận C1/C2 có 4.053 cửa sổ 31 ngày lịch hoàn chỉnh, ngày kết thúc đầu tiên 2015-08-29 và cuối cùng 2026-10-02. Đây là coverage đầu vào cho đề xuất 30 ngày, chưa phải chuỗi metric/score đã thực thi hoặc được phát hành.

Các snapshot có manifest/hash; nguồn ETH/1d, không gap/duplicate/invalid trong range đã audit. Đường dẫn cụ thể ở [HANDOFF](HANDOFF.md), [STORAGE](STORAGE.md), [NETWORK_PROXIES](NETWORK_PROXIES.md) và [E4 backfill evidence](evidence/e4-fee-backfill-2026-10-03.json). Raw giữ private. Availability/vintage quá khứ vẫn unknown; chỉ được gọi lịch sử reconstructed.

Core production hiện pin canonical SHA `59bda78805616259b93c63cef5aec50a0f33db768fe8e8d7c272e44bab5ccdfb`, khác snapshot local 02:00. Khi triển khai E2, dùng output private của chính batch Core đang tính hoặc restore đúng snapshot cha đã xác minh; không ghép NUPL local cũ vào release cha mới. Không sửa evidence E2-01 cũ để đổi ngày coverage.

E4 đã có 3.719 ngày raw feature, 3.354 ngày score nghiên cứu. AP thăm dò `0.240946` so với Core `0.554249`; quyết định giữ R&D và không promote public metric còn hiệu lực. [Kết quả E4](evidence/e4-candidate-evaluation-2026-10-03.json). Một series có dữ liệu đầy đủ chưa đủ để trở thành thành phần điểm tổng hợp.

## Trình tự để hoàn thiện

1. Khóa contract/version và vai trò: E2 raw diagnostic; C1/C2 context riêng. Ghi đơn vị, ngày UTC, null/warm-up, chiều tín hiệu nếu có score, các giới hạn nâng cấp và revision.
2. Xác minh snapshot đúng lineage; C1/C2 kiểm 31 ngày lịch liên tục cho chênh lệch 30 ngày. Missing trả null, không forward-fill hoặc thay bằng 0.
3. Engine/fixtures/calendar/prefix/future shock; với ứng viên score, khóa normalizer trước đánh giá và dùng các kiểm định tương quan/regime/baseline/prospective phù hợp.
4. Publisher allowlist JSON/CSV/biểu đồ riêng, attribution/CC BY-NC, manifest/snapshot R2 readback, daily cùng parent và immutable revisions; giữ số ECO 7/Core đã phát hành.
5. Review diff/secret/data gates, CI, main → Pages và kiểm UI/domain. Chỉ đánh metric DONE sau khi đầu ra này thực sự chạy và được xác minh.

Original E3/E8/E9 vẫn thiếu quyền/coverage đúng định nghĩa. Account Arkham và hồ sơ trial đã hoàn tất, nhưng chưa có key/approval/quyền dữ liệu; receipt không mở source gate. [Trạng thái Arkham](ARKHAM_SOURCE.md).
