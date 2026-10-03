# Core 10 Experimental

Protocol `core-v0.2.0` khóa trước code/tính/đánh giá, [ADR-008](ADR-008-core-ten-experimental.md), SHA `43fc1f29c02868f4d1f5b02ed0f121fc15d9e79e5f886dbaf2061e8b8837d404`. Trạng thái nghiệm thu thực tế trong [HANDOFF](HANDOFF.md). ETH native L1, phi thương mại theo CC BY-NC, reconstructed, availability lịch sử chưa biết.

## Điều kiện tích hợp

Core 4 + ba proxy giữ nguyên điểm cha. E2/C1/C2 đã qua ETH/schema/unit/coverage/licence, replay đúng cha và R2 readback 7/7 + 8/8 file. Core 10 pin bốn release Core/proxy/ECO 7/diagnostic bằng SHA; lineage của ECO 7 và diagnostic phải đúng Core/proxy đang dùng. “Hợp lệ” là dữ liệu/phương pháp nghiên cứu, chưa xác nhận giá trị dự báo.

| Metric thêm | Raw trước normalizer | Ngày score hợp lệ đến 02/10/2026 | Trọng số |
|---|---|---:|---:|
| E2 | NUPL = 1−1/MVRV, ratio | 3.709, từ 07/08/2016 | 18,75% |
| C1 supply_scarcity | Âm của % thay đổi nguồn cung 30 ngày | 3.688, từ 28/08/2016 | 6,25% |
| C2 exchange_balance_pressure | Số dư ETH sàn t trừ t−30 | 3.688, từ 28/08/2016 | 3,125% |

Giữ ngân sách giá 37,5%, định giá 37,5%, mạng 25% của ECO 7. E2/E7 chia nhóm định giá; các phép đo sàn chia họ sàn 6,25%. Mạng chia đều bốn họ sàn/nguồn cung/địa chỉ/transfer. Không tăng ngân sách từ các thông tin phụ thuộc MVRV/sàn. Chiều C1 là giả thuyết khan hiếm tương đối khi tăng cung ròng giảm; C2 là giả thuyết số dư sàn tăng làm tăng lượng có thể giao dịch. Không suy ra giá sẽ giảm, gross inflow hoặc hành vi bán. London/Merge/Dencun và thay đổi nhãn sàn ảnh hưởng diễn giải.

Ba feature mới dùng q05/q95 tuyến tính trên tối đa 1.460 ngày lịch **trước t**, tối thiểu 365 raw hợp lệ; clip 0–100; biên suy biến → null. Fit lịch diagnostic đầy đủ từ 30/07/2015 rồi join Core từ 01/08/2015. Signed/zero/null/reason/flash giữ trong history/CSV; không fill hoặc gán thiếu thành 0/50. Thiếu bất kỳ thành phần bắt buộc → composite null. E4 giữ R&D; E3/E8/E9 original vẫn chờ entitlement, proxy giữ công thức riêng.

## Kết quả snapshot 03/10/2026

4.081 ngày lịch, 2.979 ngày có Core 10 từ 07/08/2018 đến 02/10/2026. Ngày cuối **37.71262149722105**, UI **38**, đủ 10/10. Cùng ngày Core 4 **40.009962172523664**, ECO 7 **31.979753577249287**. Mọi điểm lịch sử cha giữ nguyên.

2.102 ngày đánh giá 01/01/2020–02/10/2025, nhãn future drawdown −50%/365 ngày hoàn tất. Bootstrap ghép cặp 90 ngày ×10.000, seed 20261003; holdout đã dùng lại nên chỉ thăm dò.

| Mô hình | Average Precision | Δ AP Core 10 − baseline | CI 95% |
|---|---:|---:|---|
| Core 10 | 0,522631 | — | — |
| Core 4 | 0,554702 | −0,032071 | [−0,071774; −0,005058] |
| ECO 7 | 0,533890 | −0,011259 | [−0,029043; 0,005326] |
| E7 riêng | 0,554274 | −0,031643 | [−0,107040; 0,021122] |
| Nhóm giá | 0,545849 | −0,023218 | [−0,111727; 0,034344] |

Core 10 thấp hơn Core 4 trong CI này. Không retune để ép cải thiện; giữ nhãn Experimental và kết quả thực tế trong Kiểm định. Dashboard chỉ hiện Core 10 (hoặc một đường tùy chỉnh khi người dùng chọn); bỏ chế độ/đường điểm Core 4 và ECO 7, bỏ hai cột composite cũ khỏi CSV chính. Baseline nằm trong chi tiết kiểm định thu gọn; lịch sử cha và bốn cổng lineage giữ nguyên. JSON có correlation, 10 ablation, regime và coverage. Không gọi score là xác suất hoặc 10 thành phần là bản đủ chín metric gốc.

## Vận hành và kiểm thử

```text
python -m eco.core_ten
python -m unittest discover -s tests -v
node --test tests/*.test.mjs
node scripts/validate-research-artifacts.mjs
node scripts/check-dashboard.mjs http://127.0.0.1:8876/
node scripts/check-proxies.mjs http://127.0.0.1:8876/
node scripts/check-diagnostics.mjs http://127.0.0.1:8876/
```

`eco/core_ten.py`: private candidate → replay parent/normalization/evaluation → publication gate → immutable releases/revision/ledger → atomic pointer/status. Public `/data/core-v2/` chỉ history/research/manifest cùng metadata. Raw ở R2 private, không cần token mới. Engine hash chuẩn LF cho Windows/Linux cùng identity.

Hai workflows gọi Core 10 sau cả ECO 7 và diagnostics thành công. Sai hash/lineage, lost coverage hoặc forged report → giữ pointer cũ và failed. Parent/engine revision tạo release mới, giữ bản trước; first-publication chỉ ghi ngày mới nhất có điểm, không giả ledger cho toàn backfill. `recorded_at` là lúc batch chuẩn bị record; `public_available_at` và `source_available_at` null, không giả thời điểm HTTP hoặc provider công bố.

Frontend kiểm checksum/version/weights/groups/normalizer, raw có chiều/unit/reason/flags và bốn parent manifest cùng lineage. CSV có 10 score, ba input theo đơn vị gốc, oriented raw, versions và release cha. Cùng release đổi SHA bị từ chối; lỗi tải giữ dữ liệu đã xác minh. Auto-refresh 15 phút giữ ngày lịch sử đã chọn hoặc theo ngày có điểm gần nhất.

**Đã nghiệm thu local, production và hosted:** 102 Python, 30 Node PASS; frozen validator PASS; ba UI qua viewport 1440/768/390/360, CSV/calendar/keyboard/null/flash/error retention. Tests bao gồm past-only/current exclusion/window expiry/prefix shock, signed/zero/degenerate, family budgets, all-parent point equality, licence/hash/lineage, forged candidate/research, immutable revision/ledger, lost coverage/fail-safe. Auto-refresh dùng fixture tổng hợp, không là dữ liệu tương lai thật. Code `43629af` CI/Pages success, hai domain xác minh 38 file/năm chain/cache và UI. Hosted Core `37134104578` và network `37134106123` success cả Core 10 `unchanged`, tests, bot commit và production verifier. [Evidence](evidence/core-ten-publication-2026-10-03.json).
