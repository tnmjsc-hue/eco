# E2, nguồn cung và số dư sàn ETH

Ngày thực hiện: 2026-10-03. Protocol [diagnostics-v0.1.0](../configs/research/diagnostics-v0.1.0.json) khóa trước implementation theo [ADR-007](ADR-007-raw-eth-diagnostics.md). Đã hoàn thiện và xác minh production tại [eco.tnmp.cloud/#diagnostics](https://eco.tnmp.cloud/#diagnostics). Commit/CI/Pages/domain/browser và hai hosted workflow đã đạt; bằng chứng ở [HANDOFF](HANDOFF.md) và [audit publication](evidence/diagnostics-publication-2026-10-03.json). Không có điểm tổng hợp, normalizer hoặc tuyên bố hiệu quả dự báo cho ba chỉ số này.

## Định nghĩa và kết quả

| ID | Đại lượng công bố | Đơn vị JSON/CSV | Giá trị 2026-10-02 | Coverage |
|---|---|---|---|---|
| E2 `nupl_diagnostic` | `1 - 1 / CapMVRVCur(t)` | ratio; UI nhân 100% | 0.11931373854117377 (11,931%) | 4.074 ngày, từ 2015-08-08; 9 null |
| C1 `supply_change_30d` | `100 * (SplyCur(t)/SplyCur(t-30) - 1)` | percent, không nhân 100 thêm | 0.07090517490266901% | 4.053 ngày, từ 2015-08-29; 30 null |
| C2 `exchange_balance_change_30d` | `SplyExNtv(t) - SplyExNtv(t-30)` | ETH | -208715.0385640096 ETH | 4.053 ngày, từ 2015-08-29; 30 null |

Calendar đầy đủ: 4.083 ngày UTC 2015-07-30..2026-10-02. E2 âm 1.131 ngày; C1 âm 446 ngày; C2 âm 2.102 ngày. C2 giữ `flash` ở 4.083 dòng, kể cả các cửa sổ chưa đủ. Null có reason; số âm và zero hợp lệ không bị ép vào 0–100. C1/C2 yêu cầu đủ 31 ngày lịch, cả nội bộ cửa sổ; thiếu một ngày thì null cho đến khi cửa sổ hết khoảng thiếu.

E2 là biến đổi đại số của MVRV, khác phép đếm ví/holder đang có lãi. C1 dùng current ledger supply, khác circulating/free-float và không tách gross issuance/burn. C2 là thay đổi ròng của số dư địa chỉ sàn được nhận diện, không đo tổng nạp/rút hoặc chứng minh ý định mua/bán. Nhãn sàn không đầy đủ và có thể sửa hồi cứu. Native ETH L1 không bao quát ERC-20/L2. Nguồn khả dụng trong quá khứ chưa biết; backfill là reconstructed.

## Nguồn, lineage và quyền

E2 đã restore **đúng snapshot Core đang công bố**, không dùng bản local cũ thiếu MVRV ngày cuối:

- Core cha `core-f677f7dd1f1749cc6dce`; canonical SHA `59bda78805616259b93c63cef5aec50a0f33db768fe8e8d7c272e44bab5ccdfb`; retrieved `2026-10-03T09:10:53.030Z`. R2 GET/readback 7/7 object. Replay toàn bộ giá, điểm và bốn thành phần Core khớp cha, tolerance relative `1e-12`/absolute `1e-8` cho khác biệt số thực, không đổi giá trị đã công bố.
- C1/C2 dùng proxy cha `proxy-f9edb79c4231efbbb9fe`; canonical SHA `405c4eaf20e23123643ed08acf00d4ce6df2f0ce41f82c975ebf7d4730628637`; source manifest SHA `bc8ccb903bf57be31fcf9d3dcc2a7cad36010fad55dea77537dd60f62603cac6`; retrieved `2026-10-03T08:46:45.399Z`. R2 GET/readback 8/8 object. Không ghép bản network 09:14 khác vintage.
- Source evidence SHA `5d35aa2fa85e6a8ef7d6e538d8f7fc8ac456f366b3efedac54cd01b07200e72d`, entitlement Community/canonical/raw/metric flags/catalogue và quyền nghiên cứu phi thương mại kiểm trước publish. [Coin Metrics Community](https://docs.coinmetrics.io/packages/coin-metrics-community-data), [CC BY-NC 4.0](https://creativecommons.org/licenses/by-nc/4.0/); có attribution trên UI/CSV/manifest. Không sử dụng Arkham chưa được cấp key/quyền hoặc API trả phí.

Restore dùng script read-only [restore-private-snapshot-r2.mjs](../scripts/restore-private-snapshot-r2.mjs), prefix và canonical hash được pin bởi cha. Script chỉ GET, không PUT/DELETE, không tạo token; không ghi đè file local khác hash. Token bucket cũ qua environment; raw/receipt ở `data/raw`, `data/computed` bị Git ignore. Readback này xác minh hai snapshot, chưa hoàn thành fault/restore drill toàn hệ thống O03.

## Artifact và cổng phát hành

Release đầu: `diagnostic-c005275a913702669d2d`, engine SHA `303bae7015547807a815656fa1d8fcc195ecbe87ede3787a7ab81bdbeea14c9c`.

- Protocol SHA `fb7f5b80ca84ffc4babb8b5ffe823574500f13fed31fc03a3a25922da76afc4a`.
- Manifest public SHA `213bc94cbe3f478be31253c70b4a5e604630d44f8ffa55e109f40113232dc98f`.
- `history.json` SHA `c4a2f0f137dacb9043c72b087ed4e6de7de8ce4be77ea98b5eba6a22782e4c81`.
- `research.json` SHA `243d87d225e03eb16685acdc5701dd049335da2339a9ab3f4c4338648098bc36`.

Publisher riêng `/data/diagnostics/` chỉ copy history/research/manifest đã kiểm; private replay input paths, raw API pages/catalogue và credentials không được copy. History/research/parents/readback phải khớp recompute trước publish. Release cũ bất biến, revision có lý do/changed dates/new dates; record công bố đầu tiên chỉ cho ngày cuối, không gán lịch sử backfill thành as-published. Pointer ghi atomic cuối cùng. Core, network proxy và ECO 7 cũ không đổi bytes/version/trọng số.

Báo cáo research là **mô tả coverage/âm/zero/null và regime London/Merge/Dencun**, không phải AP/bootstrap cho mô hình mới. Normalizer, hướng dự báo, trọng số hoặc promote về composite sẽ cần protocol/version và kiểm định riêng.

## Vận hành và UI

Hai workflow Core/network đã thêm `python -m eco.diagnostic_pipeline daily` sau batch cha thành công, cùng concurrency hiện có. Bước mới restore hai snapshot R2 đúng cha, kiểm/hash/replay, build/publish và status. Lỗi giữ pointer tốt, ghi stage đã làm sạch và làm job báo failure. Bot chỉ stage allowlist diagnostics; verifier kiểm cả bốn chuỗi checksum trên production. Không cần secret, token hoặc job lịch mới.

Lệnh thực tế cho runtime có R2 environment hợp lệ:

```text
python -m eco.diagnostic_pipeline daily
python -m unittest discover -s tests -v
node --test tests/*.test.mjs
node scripts/validate-research-artifacts.mjs
node scripts/check-diagnostics.mjs http://127.0.0.1:8876/
```

Có thể build offline bằng `--core-snapshot`, `--core-receipt`, `--proxies-snapshot`, `--proxies-receipt`; tất cả bắt buộc khớp manifest cha. `build` lưu candidate private; `publish <candidate-folder>` chạy lại gates. Không thay input bằng dữ liệu mới dưới release cũ.

Tab `#diagnostics` có ngày UTC, ba card, chart chọn một metric để không trộn đơn vị, range 1/3 năm/tất cả hoặc ngày tùy chọn, CSV đúng range kể cả null/reason/flags/version/snapshot lineage. E2 CSV giữ ratio, UI hiển thị %. Thử lại khi network/checksum/immutable release lỗi giữ dữ liệu cũ. Refresh 15 phút và visibility refresh giữ ngày lịch sử; theo ngày gần nhất thì nhận ngày mới.

Kiểm local: 88 test Python, 26 test Node, frozen validator, vendor build/syntax/diff đạt. Playwright trên 1440/768/390/360: signed values, warm-up, chart không trắng, keyboard, 366 ngày CSV/5 ngày tùy chọn, range invalid, retry, checksum/immutable retention và future-publication fixture refresh đạt. Fixture refresh chỉ kiểm UI, không là dữ liệu nguồn hoặc bằng chứng shadow. Chạy daily thật R2 lần hai trả `unchanged`, giữ pointer/history/research/ledger. Code `5d8107f` có CI `37127187382`/Pages `b37efb41-6a12-4750-8af4-65649cf5394e` success. Hosted Core run `37127278755`/job `111215047643` success cả diagnostics và deploy verifier; logs xác minh `unchanged`. Bot `deb6e5e` chỉ đổi Core/Extended/diagnostics status, không đổi pointer/release/điểm. Hai hostname mỗi nơi 32 file đúng Git SHA bytes, bốn release chain và cache headers khớp; ba browser QA production đạt bốn viewport. Chi tiết tiếp tại HANDOFF.

Hosted network run `37127520932`/job `111215765840` cũng success nguồn/R2/diagnostics/verify/deploy; bot `a00cd2d` và Pages `f195a79f-8582-46e3-b6de-8ac2be41cf1c` chỉ cập nhật status. Hai đường daily đều giữ release `diagnostic-c005275a913702669d2d`, không đổi các điểm công bố hoặc ledger; hashes/cache headers hai hostname được kiểm lại sau bot cuối.
