# Hồ sơ xin Arkham API trial — ECO

**Đã tạo tài khoản Arkham miễn phí, xác minh email và gửi hồ sơ ngày 2026-10-03.** Người dùng đã cung cấp tên thật và xác nhận đồng ý điều khoản. Thư gửi từ `tnmjsc@gmail.com` đến `support@arkm.com` lúc **18:03 giờ Việt Nam**, đã kiểm Sent/người nhận; Arkham gửi xác nhận **[Request received] lúc 18:06**. Trial/API key và quyền sử dụng còn chờ đội hỗ trợ xét duyệt. Không kích hoạt subscription, auto-renewal hoặc trả phí.

Biểu mẫu trial hiện yêu cầu thẻ, miễn phí 30 ngày rồi tự kích hoạt Starter **1.500 USD/tháng**. Vì ngân sách được phép là 0 USD, đã gửi yêu cầu trial nghiên cứu thủ công **không cần thẻ, không tự gia hạn, không overage** qua kênh support chính thức. [Metadata xác minh](evidence/arkham-registration-2026-10-03.json) không chứa credential hoặc thư nguyên văn. Bản định danh và email gửi thực tế giữ private trong `data/raw/arkham/registration-2026-10-03/`; bản dưới đây là mẫu công khai.

## Thông tin điền biểu mẫu

| Trường | Nội dung đã chuẩn bị |
|---|---|
| Full Name | Đã được người dùng cung cấp và điền; tên trong bản định danh private |
| Email | `tnmjsc@gmail.com` |
| Use case | Individual; mô tả nghiên cứu ETH trong thư (form chỉ có Individual/Business/Government) |
| Project | ECO — Ethereum cycle research dashboard |
| Website | https://eco.tnmp.cloud/ |
| Source repository | https://github.com/tnmjsc-hue/eco |
| Access requested | Free, time-limited API trial; ETH native on Ethereum L1; tối đa 5 entity CEX trong đợt đầu |
| Chi phí được phép | 0 USD; chưa cho phép mua plan hoặc phát sinh overage/x402 |
| Terms checkbox | Người dùng đã xác nhận đồng ý; platform terms đã chấp thuận khi đăng ký. Không submit/kích hoạt trial tự gia hạn; quyền dữ liệu API vẫn cần Arkham cấp riêng |

Form chính thức: https://arkm.com/api . Hướng dẫn truy cập: https://arkm.com/docs#getting-started/access . Account và xác minh email đã đạt; CAPTCHA do người dùng hoàn tất. Mật khẩu ngẫu nhiên lưu DPAPI ngoài repo, không lưu password trong browser hoặc công khai. Chấp thuận của người dùng không thay quyền automation/cache/public derived của Arkham. Không cấu hình tự gửi email từ tài liệu hoặc upstream.

## Mẫu nội dung yêu cầu

**Subject: Free ETH research API trial and derived-publication permission — ECO**

Hello Arkham API team,

I have created and verified my Arkham account with tnmjsc@gmail.com. Your current trial form requires a credit card and automatic activation of a $1,500/month Starter subscription after 30 days. Please advise whether you can offer a manually approved noncommercial research trial with no credit card, no automatic renewal, no paid overages and zero charges. We will not activate the card-based trial.

We are developing ECO, a noncommercial Ethereum research dashboard at https://eco.tnmp.cloud/ with open-source computation code at https://github.com/tnmjsc-hue/eco. Please provision any approved trial to tnmjsc@gmail.com.

We would like a free, time-limited trial to evaluate native ETH data on Ethereum mainnet. Our initial scope is a fixed cohort of up to five centralized-exchange entities, excluding bridges, staking contracts, predicted labels and non-ETH tokens. We aim to compare daily exchange balances and exchange flows with our existing ETH research metrics. We will not market these scores as probabilities or trading recommendations.

Requested endpoints are:

- `/token/holders/ethereum` for a small entity-grouped discovery sample;
- `/portfolio/timeSeries/entity/{entity}` with `pricingId=ethereum` and `chains=ethereum` for daily UTC balances;
- `/transfers/histogram` with an explicit exchange base, `tokens=ethereum`, `chains=ethereum`, and daily UTC buckets, for exchange inflow/outflow diagnostics;
- relevant entity/address intelligence and label-update metadata for coverage and revision audits.

For the initial validation, we propose no more than ten sample requests. Any historical backfill would require your confirmation of endpoint coverage, per-call/per-row credit costs, trial quota, allowed date ranges, rate limits and caching rules. The tentative steady-state budget is five entity-balance queries and two flow queries twice daily (about 14 calls/day). We understand that time-series endpoints may return full history and that actual credits depend on the endpoint and output size; this is an estimate of calls, not a claim about cost.

Please confirm in writing whether the trial permits:

1. API access from a scheduled backend batch and coding/AI assistants acting for our research project;
2. private caching of raw responses and request/hash manifests, with encrypted credentials and a private Cloudflare R2 backup;
3. retaining immutable source vintages, daily derived scores and revisions for reproducibility;
4. displaying derived noncommercial research indicators, attribution and coverage summaries on our public dashboard, with derived CSV export, while keeping raw Arkham data and full address-label lists private.

The API guide describes support for AI agents, whereas API Terms section 1.2 restricts Authorized Users and section 8.2 limits distribution and derived compilations. Please identify the trial/subscription terms or written permission that authorize the requested uses. If public derived indicators or CSV export require a separate agreement, please specify that requirement; we will not treat a trial key as publication permission.

We are requesting a free trial only, with no payment details, automatic renewal, paid overages or x402 payments. Please also confirm whether ETH daily native balances are net balances rather than cumulative deposited amounts, how historical labels change, and whether source/indexing availability timestamps and confidence metadata are supplied.

Thank you,

**[Tên người đăng ký đã xác nhận — xem bản định danh private]**

ECO research project

tnmjsc@gmail.com

## Nghiệm thu trial sau khi được cấp

Thử tối đa 10 request như hồ sơ, lưu raw/manifest private và kiểm chain/token/unit/UTC/earliest/latest/gaps/status/label vintage. Credential phải được lưu trong DPAPI/secret backend; không đưa trong URL, frontend hoặc chat. R2 readback hash phải đạt trước backfill dài. Quyền chưa được trả lời vẫn là unknown và không cho phép publish dữ liệu Arkham vào ECO 7.

Hồ sơ này không đổi nguồn hay trọng số `extended-v0.1.0`. Khi sample/rights/coverage đạt, khóa candidate Arkham dưới version mới rồi kiểm định theo [kế hoạch nguồn](ARKHAM_SOURCE.md).
