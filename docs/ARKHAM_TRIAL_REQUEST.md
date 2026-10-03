# Hồ sơ xin Arkham API trial — ECO

Đã chuẩn bị theo yêu cầu của người dùng ngày 2026-10-03. **Chưa gửi, chưa đăng ký account hoặc chấp nhận API Terms.** Hồ sơ dùng để xin trial phi thương mại và làm rõ quyền; không cam kết subscription, auto-renewal hoặc chi phí.

## Thông tin điền biểu mẫu

| Trường | Nội dung đã chuẩn bị |
|---|---|
| Full Name | **Còn thiếu tên thật người đứng tên đăng ký**; không tự dùng email hoặc tên dự án thay tên cá nhân |
| Email | `tnmjsc@gmail.com` |
| Use case | Researcher nếu có lựa chọn; nếu biểu mẫu chỉ Individual thì dùng mục đó và mô tả nghiên cứu bên dưới |
| Project | ECO — Ethereum cycle research dashboard |
| Website | https://eco.tnmp.cloud/ |
| Source repository | https://github.com/tnmjsc-hue/eco |
| Access requested | Free, time-limited API trial; ETH native on Ethereum L1; tối đa 5 entity CEX trong đợt đầu |
| Chi phí được phép | 0 USD; chưa cho phép mua plan hoặc phát sinh overage/x402 |
| Terms checkbox | Chưa chấp thuận; cần làm rõ các quyền dưới đây trước khi xác nhận |

Form chính thức: https://arkm.com/api . Hướng dẫn truy cập: https://arkm.com/docs#getting-started/access . Account/login là dependency của form hiện tại. Tên người đăng ký và bước chấp thuận hợp đồng là hai phần còn cần người dùng cung cấp/xác nhận trước submission. Không gửi email tự động từ tài liệu này.

## Nội dung yêu cầu sẵn để gửi

**Subject: Free ETH research API trial and derived-publication permission — ECO**

Hello Arkham API team,

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

**[Tên người đăng ký — người dùng cần điền]**

ECO research project

tnmjsc@gmail.com

## Nghiệm thu trial sau khi được cấp

Thử tối đa 10 request như hồ sơ, lưu raw/manifest private và kiểm chain/token/unit/UTC/earliest/latest/gaps/status/label vintage. Credential phải được lưu trong DPAPI/secret backend; không đưa trong URL, frontend hoặc chat. R2 readback hash phải đạt trước backfill dài. Quyền chưa được trả lời vẫn là unknown và không cho phép publish dữ liệu Arkham vào ECO 7.

Hồ sơ này không đổi nguồn hay trọng số `extended-v0.1.0`. Khi sample/rights/coverage đạt, khóa candidate Arkham dưới version mới rồi kiểm định theo [kế hoạch nguồn](ARKHAM_SOURCE.md).
