# 兑换码系统概念(Concept)

本文档定义 Ticket 当前唯一名词体系。对外业务、API、前端均使用“产品(Product)”表达卡券/权益的可售卖定义；内部数据库模型可以继续使用 `TicketTemplate` 作为存储实现名，但不得作为用户可见名词或外部契约。

## 概念(Glossary)

- 租户(Tenant): 系统的隔离边界。Ticket 租户之间数据完全隔离。
- 租户管理员(Tenant Admin): 由平台管理员授权手机号形成的租户管理身份。手机号命中授权即可登录管理，不绑定 slauth user id。
- 项目(Project): 租户下的业务隔离单元。项目持有产品、项目密钥、合作伙伴、券码、配额和运营记录。
- 项目密钥(Project Credential): 项目级 Access Key / Secret Key。业务系统使用它调用 `/api/biz/v1/*`，密钥只能由租户管理员在租户端项目上下文创建、轮换、禁用。
- 产品(Product): 一类可发放、可生成券码、可核销、可履约的业务定义。产品包含固定履约 JSON，不支持模板变量。
- 固定履约 JSON(Fixed Fulfillment Payload): 产品创建时保存的 JSON 对象。核销和 webhook 原样返回该 JSON，Ticket 不做变量替换、不猜测字段含义。
- 兑换码(Code): 产品实例化后的具体券码，可被核销。包含 `code_value`、可选 `serial_no`、状态、标签、导出状态和券码级 `meta`。`meta` 是业务系统写入的 JSON object，Ticket 只保存、审计和透传，不解释字段含义。标签按项目隔离，用于批量标记、列表筛选和运营识别，可由 Tenant Console 追加，也可由 Biz API 在创建券码时设置或整体替换。对外展示和用户输入的 `code_value` 必须是 16 位纯数字短码；内部记录 ID 仍是系统 ID，不可作为兑换码展示。
- 合作伙伴(Partner): 项目下的运营主体。由租户管理员通过手机号邀请时自动创建，初始为未激活；该手机号登录后可激活并进入 Partner Portal。
- 资产聚合(Asset Summary): 产品维度下的只读聚合视图，不是独立页面或独立资源模型。资产只在产品详情页展示，包含项目库存、Partner 库存、Partner 配额和最近划拨。
- 配额(Quota): Partner 持有的某产品额度，可用于生成属于自己的券码，也可继续划拨给其他 Partner。
- 购买链接(Purchase Link): 合作伙伴或租户管理员创建的可售卖链接。
- 订单(Order): 购买链接成交后的交易记录。
- 划拨(Allocation): 券码库存或配额在 Partner 之间的转移记录。对外资产类型只允许 `code_inventory` 和 `quota`。
- 分享(Share): 购买链接或产品传播行为的归因记录。
- 导出(Export): 券码或运营数据导出批次。
- 核销(Redemption): 业务系统提交券码后，Ticket 执行 reserve / confirm / cancel 并返回产品的固定履约 JSON、核销预留时的券码级 `meta` 快照，以及可选核销备注 `remark`。

## 角色边界

| 角色 | 端 | 职责 |
| --- | --- | --- |
| 平台管理员 | Platform Console | 只管理 Ticket 租户和租户管理员手机号授权。 |
| 租户管理员 | Tenant Console | 管理项目、项目密钥、产品、券码、合作伙伴、配额、购买链接、订单、划拨、分享、导出；在产品详情页查看资产聚合。 |
| 合作伙伴 | Partner Portal | 手机号登录后管理自己可访问的产品、券码、配额、购买链接、订单、划拨、分享、导出；在产品上下文查看资产聚合。 |
| 业务系统 | Biz API | 使用项目密钥 HMAC 创建券码、设置券码级 `meta` 和标签、调用核销 API，并接收固定履约 JSON、券码级 `meta` 快照与核销备注。 |

## 券码 Meta 与标签

- 券码级 `meta` 属于业务系统数据。Biz API 可以在创建券码时设置 `meta`，也可以整体替换 `meta`；核销响应和 webhook 会携带核销预留时的 `meta` 快照。
- 券码标签属于项目级运营数据。Tenant Console 可以批量选择券码并追加标签，也可以在券码详情中整体替换单个券码标签；Biz API 可以在创建券码时设置标签，也可以整体替换单个券码标签；Partner Portal 只读展示标签。
- 标签按项目隔离，存储为 `ticket_tag_names` 中的项目级标签定义和 `ticket_tags` 中的券码 bit-cell 关系。`TicketCode` 上不保存标签源数据。
- 标签变化必须进入券码生命周期，Tenant 追加事件类型为 `code.tags.added`，Biz 替换事件类型为 `code.tags.replaced`。

## 结构关系树

```text
Ticket
└─ Tenant
   ├─ Tenant Admin Phone Grants
   └─ Project
      ├─ Project Credentials
      ├─ Products
      │  └─ Fixed Fulfillment Payload JSON
      ├─ Codes
      ├─ Partners
      │  ├─ Partner Members
      │  ├─ Quotas
      │  ├─ Purchase Links
      │  ├─ Orders
      │  ├─ Allocations
      │  ├─ Shares
      │  └─ Exports
      └─ Biz Redemptions
         └─ Reserve / Confirm / Cancel
```

## 单一路径约束

- 平台端不管理项目、项目密钥、产品、券码或合作伙伴。
- 租户端是项目运营配置的唯一入口。
- Partner Portal 使用手机号登录，不使用伙伴编号/密码登录。
- 产品履约字段是固定 JSON；不支持模板变量、不支持运行时字符串替换。
- 业务核销只接受项目密钥 HMAC，不接受 bearer token、全局密钥或旧 header fallback。
- 产品详情只保留页面 `/projects/:projectId/products/:productId`。产品列表不提供快速查看 Sheet；Sheet 只能用于轻量表单或确认，不承载产品主详情。
- 不存在独立资产页。资产聚合只能作为产品详情页中的只读视图出现。
- Quota lifecycle:
  1. Tenant Admin grants product quota to Partner.
  2. Partner consumes available quota to generate owned Codes.
  3. Partner allocates available quota to another Partner.
  4. All quota consume/allocate writes are transactional and row-locked.
