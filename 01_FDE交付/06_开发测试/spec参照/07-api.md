# 06 - API 体系设计

本文档定义 Ticket 当前上线 API 的唯一契约。Go controller 注解通过 `swag init` 生成 OpenAPI，再由 OpenAPI 生成 TS SDK；前端只能调用生成 SDK，不允许手写平行 API 客户端。

## 1. API 分组

| 分组 | 前缀 | 使用方 | 鉴权 |
| --- | --- | --- | --- |
| 平台认证 | `/platform-auth/v1` | 平台管理员登录 | 手机号 OTP，管理员手机号来自 `SECURITY_PLATFORM_ADMIN_PHONES`。 |
| 租户认证 | `/tenant-auth/v1` | 租户管理员登录 | 手机号 OTP；进入租户 API 时校验租户管理员手机号授权。 |
| 合作伙伴认证 | `/partner-auth/v1` | 合作伙伴登录 | 手机号 OTP；进入 partner API 时校验手机号命中的 PartnerMember。 |
| 平台 API | `/api/platform/v1` | 平台管理端 | platform bearer token + 平台管理员 allowlist。 |
| 租户 API | `/api/tenant/v1` | 租户管理端 | tenant bearer token + `X-Ticket-Tenant-ID`。 |
| 合作伙伴 API | `/api/partner/v1` | 合作伙伴端 | partner bearer token。 |
| 业务 API | `/api/biz/v1` | 接入方业务系统 | 项目级 AccessKey/Secret HMAC。 |

## 2. 通用响应

- 所有 controller 返回 `pin.Response`。
- 系统错误直接返回 error。
- 业务错误定义在 `host/src/myerrors`。
- 业务错误必须 fastfail，不允许静默吞错或 fallback。

## 3. 平台 API

平台 API 只管理 Ticket 租户与租户管理员手机号。

| Method | Path | 说明 |
| --- | --- | --- |
| GET | `/api/platform/v1/tenants` | 租户列表。 |
| POST | `/api/platform/v1/tenants` | 创建租户。 |
| GET | `/api/platform/v1/tenants/{tenantId}` | 租户详情。 |
| PATCH | `/api/platform/v1/tenants/{tenantId}` | 更新租户基础信息。 |
| GET | `/api/platform/v1/tenants/{tenantId}/admins` | 租户管理员手机号授权列表。 |
| POST | `/api/platform/v1/tenants/{tenantId}/admins` | 创建租户管理员手机号授权。 |
| POST | `/api/platform/v1/tenant-admins/{memberId}/disable` | 禁用租户管理员授权。 |
| GET | `/api/platform/v1/reports/summary` | 平台汇总报表。 |

平台 API 明确不暴露项目、项目密钥、产品、券码或合作伙伴管理。

## 4. 租户 API

租户 API 由 `X-Ticket-Tenant-ID` 确定租户上下文，URL 中不出现 tenantId。

| Method | Path | 说明 |
| --- | --- | --- |
| GET | `/api/tenant/v1/me` | 当前租户管理员身份。 |
| GET | `/api/tenant/v1/members` | 租户成员列表。 |
| POST | `/api/tenant/v1/members` | 通过手机号邀请租户成员。 |
| POST | `/api/tenant/v1/members/{memberId}/disable` | 禁用租户成员。 |
| GET | `/api/tenant/v1/projects` | 项目列表。 |
| POST | `/api/tenant/v1/projects` | 创建项目。 |
| GET | `/api/tenant/v1/projects/{projectId}` | 项目详情。 |
| POST | `/api/tenant/v1/projects/{projectId}/service-credentials` | 创建项目密钥。 |
| GET | `/api/tenant/v1/projects/{projectId}/service-credentials` | 项目密钥列表。 |
| POST | `/api/tenant/v1/projects/{projectId}/service-credentials/{credentialId}/rotate` | 轮换项目密钥。 |
| POST | `/api/tenant/v1/projects/{projectId}/service-credentials/{credentialId}/disable` | 禁用项目密钥。 |
| GET | `/api/tenant/v1/projects/{projectId}/products` | 产品列表。 |
| POST | `/api/tenant/v1/projects/{projectId}/products` | 创建产品。 |
| GET | `/api/tenant/v1/projects/{projectId}/products/{productId}` | 产品详情。 |
| PATCH | `/api/tenant/v1/projects/{projectId}/products/{productId}` | 更新产品。 |
| GET | `/api/tenant/v1/projects/{projectId}/products/{productId}/asset-summary` | 产品维度资产聚合，展示项目库存、Partner 库存、Partner 配额和最近划拨。 |
| POST | `/api/tenant/v1/projects/{projectId}/codes/generate` | 按产品生成券码。 |
| GET | `/api/tenant/v1/projects/{projectId}/codes` | 券码列表，支持 `productId` 和 `tags` 查询；`tags` 为逗号分隔，匹配任一标签。 |
| GET | `/api/tenant/v1/projects/{projectId}/code-tags` | 项目级券码标签列表和使用量。 |
| POST | `/api/tenant/v1/projects/{projectId}/codes/tags/add` | 为选中券码追加项目级后台标签，并写入券码生命周期。 |
| PUT | `/api/tenant/v1/projects/{projectId}/codes/{codeId}/tags` | 在券码详情中整体替换单个券码标签，并写入券码生命周期。 |
| GET | `/api/tenant/v1/projects/{projectId}/partners` | 合作伙伴列表。 |
| POST | `/api/tenant/v1/projects/{projectId}/partners` | 通过手机号邀请合作伙伴；自动创建未激活 Partner。 |
| GET | `/api/tenant/v1/projects/{projectId}/partners/{partnerId}` | 合作伙伴详情。 |
| POST | `/api/tenant/v1/projects/{projectId}/partners/{partnerId}/disable` | 禁用合作伙伴。 |
| GET | `/api/tenant/v1/projects/{projectId}/quotas` | 配额列表。 |
| POST | `/api/tenant/v1/projects/{projectId}/quotas` | 给 Partner 发放产品配额。 |
| GET | `/api/tenant/v1/projects/{projectId}/purchase-links` | 购买链接列表。 |
| POST | `/api/tenant/v1/projects/{projectId}/purchase-links` | 创建购买链接。 |
| GET | `/api/tenant/v1/projects/{projectId}/orders` | 订单列表。 |
| POST | `/api/tenant/v1/projects/{projectId}/orders` | 创建订单。 |
| GET | `/api/tenant/v1/projects/{projectId}/allocations` | 划拨列表。 |
| POST | `/api/tenant/v1/projects/{projectId}/allocations` | 创建券码库存划拨。 |
| POST | `/api/tenant/v1/projects/{projectId}/allocations/quota` | 创建配额划拨。 |
| GET | `/api/tenant/v1/projects/{projectId}/shares` | 分享列表。 |
| POST | `/api/tenant/v1/projects/{projectId}/shares` | 创建分享。 |
| GET | `/api/tenant/v1/projects/{projectId}/exports` | 导出批次列表。 |
| POST | `/api/tenant/v1/projects/{projectId}/exports` | 创建导出批次。 |

## 5. 合作伙伴 API

合作伙伴 API 不暴露 tenantId/projectId。合作伙伴身份由手机号登录后的 token 与 partnerId 路径共同校验。

| Method | Path | 说明 |
| --- | --- | --- |
| GET | `/api/partner/v1/me` | 当前手机号可访问的合作伙伴身份列表。 |
| POST | `/api/partner/v1/partners/{partnerId}/activate` | 激活被邀请的合作伙伴身份。 |
| GET | `/api/partner/v1/partners/{partnerId}/products` | 产品列表。 |
| GET | `/api/partner/v1/partners/{partnerId}/products/{productId}/asset-summary` | 当前 Partner 在该产品下的资产聚合。 |
| GET | `/api/partner/v1/partners/{partnerId}/codes` | 券码列表，支持 `productId` 查询；响应只读包含券码标签。 |
| POST | `/api/partner/v1/partners/{partnerId}/codes/generate-from-quota` | Partner 消耗自己的产品配额生成归属自己的券码。 |
| GET | `/api/partner/v1/partners/{partnerId}/quotas` | 配额列表。 |
| GET | `/api/partner/v1/partners/{partnerId}/purchase-links` | 购买链接列表。 |
| POST | `/api/partner/v1/partners/{partnerId}/purchase-links` | 创建购买链接。 |
| GET | `/api/partner/v1/partners/{partnerId}/orders` | 订单列表。 |
| POST | `/api/partner/v1/partners/{partnerId}/orders` | 创建订单。 |
| GET | `/api/partner/v1/partners/{partnerId}/allocations` | 划拨列表。 |
| POST | `/api/partner/v1/partners/{partnerId}/allocations` | 创建券码库存划拨。 |
| POST | `/api/partner/v1/partners/{partnerId}/allocations/quota` | 将自己的可用配额划拨给其他 Partner。 |
| GET | `/api/partner/v1/partners/{partnerId}/shares` | 分享列表。 |
| POST | `/api/partner/v1/partners/{partnerId}/shares` | 创建分享。 |
| GET | `/api/partner/v1/partners/{partnerId}/exports` | 导出批次列表。 |
| POST | `/api/partner/v1/partners/{partnerId}/exports` | 创建导出批次。 |

## 6. 业务 API

业务 API 使用项目级密钥做 HMAC。项目密钥由租户管理员在租户端项目密钥页面创建和轮换。

| Method | Path | 说明 |
| --- | --- | --- |
| POST | `/api/biz/v1/codes` | 创建本项目券码，可设置券码级 `meta` 和 `tags`。 |
| GET | `/api/biz/v1/codes/{codeId}` | 获取本项目券码详情、`meta` 和 `tags`。 |
| PUT | `/api/biz/v1/codes/{codeId}/meta` | 整体替换本项目券码 `meta`。 |
| PUT | `/api/biz/v1/codes/{codeId}/tags` | 整体替换本项目券码 `tags`。 |
| POST | `/api/biz/v1/redemptions/reserve` | 预留核销，可传 `remark` 备注。 |
| POST | `/api/biz/v1/redemptions/{redemptionId}/confirm` | 确认核销。 |
| POST | `/api/biz/v1/redemptions/{redemptionId}/cancel` | 取消核销预留。 |

核销响应和 webhook 中的 `fulfillmentPayload` / `fulfillment_payload` 是产品固定履约 JSON 原样输出；`codeMeta` / `code_meta` 是核销预留时的券码级 `meta` 快照；`remark` 是 reserve 时业务系统传入的核销备注。

## 7. 禁止项

- 不允许平台 API 管理项目、项目密钥、产品或合作伙伴。
- 不允许租户 API 暴露旧产品路径业务入口。
- 不允许 partner 端使用伙伴编号/密码登录。
- 不允许 Biz API 追加或删除券码标签；Biz 只允许创建时设置标签和整体替换单个券码标签。
- 不允许前端调用未由 controller 注解生成到 OpenAPI 的接口。
- 不允许保留旧 API fallback、旧路径兼容或静默降级。
- 不允许暴露独立资产 API；资产只能通过产品维度 `asset-summary` 聚合接口读取。
- 配额消耗和划拨必须事务化并使用行锁；余额不足、归属不匹配或跨项目操作必须 fastfail。
