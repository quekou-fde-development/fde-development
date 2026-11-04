# 03 - 安全与隐私要求(Security & Privacy)

本文档定义本系统的安全/隐私硬约束, 并作为 `01~07` 文档的上位规约.

## 1. 目标与边界
- 目标: 在满足多租户隔离的前提下, 最小化URL与API暴露的上下文信息, 降低越权枚举与横向推断风险.
- 边界: 认证与鉴权中心外置; 本系统负责令牌校验、防御性一致性校验、审计留痕与数据最小暴露.

## 2. 信息透明度分级(硬约束)

### 2.1 Web URL 透明度
- 平台管理端(`platform.<domain>`): 可出现 `tenant_id`/`project_id`(平台运营域).
- 租户管理端(`tenant.<domain>`):
  - **允许**出现 `project_id`.
  - **禁止**出现 `tenant_id`.
- 下游端(`partner.<domain>`、`pay.<domain>`、业务系统回调可见URL):
  - **禁止**出现 `tenant_id`、`project_id`.

### 2.2 API Path 透明度
- 与Web保持同级透明度:
  - 平台API: 可带 `tenant_id`/`project_id`.
  - 租户API: 可带 `project_id`, 不带 `tenant_id`.
  - 下游API(`partner/pay/biz`): 不带 `tenant_id`、`project_id`.

## 3. 标识符可见性规则
- `tenant_id`:
  - 仅平台域可见(平台URL/API、平台审计后台).
  - 禁止出现在租户端/下游端URL与公开API路径中.
- `project_id`:
  - 允许出现在租户端URL/API路径.
  - 禁止出现在下游端URL/API路径.
- `partner_id` / `link_id` / `order_id` / `code_id`:
  - 可在下游域使用, 但必须为不可猜测的高熵ID(建议UUIDv7/ULID).
- 对外响应体遵循最小化原则:
  - 下游响应体默认不返回 `tenant_id`、`project_id`.
  - `PurchaseLink`/`Order` 等公共模型不暴露 `project_id`.

## 4. 路由与接口设计约束

### 4.1 允许/禁止示例
- 允许(租户端): `/projects/{project_id}/products`
- 禁止(租户端): `/tenants/{tenant_id}/projects/{project_id}/products`
- 允许(伙伴端): `/partners/{partner_id}/codes`
- 禁止(伙伴端): `/projects/{project_id}/partners/{partner_id}/codes`
- 允许(Biz): `/api/biz/v1/redemptions/reserve`
- 禁止(Biz): `/api/biz/v1/projects/{project_id}/redemptions/reserve`

### 4.2 项目上下文推导
- 下游接口的项目归属通过以下方式推导, 不通过URL暴露:
  - 业务凭证(issuer/audience/scope)绑定项目;
  - 资源反查(`link_id` / `code_value` / `order_id`);
  - 网关注入受信上下文头(内网链路).

## 5. 认证与鉴权要求
- JWT签名算法: `ES256`(ECC P-256), 必须校验 `alg/kid/iss/aud/exp/nbf/iat/sub`.
- 多用户体系支持多`jwks_url`; 通过 `iss` 路由公钥.
- 鉴权外置, 但服务内必须做防御性校验:
  - 路径主体ID与token主体一致(如 `partner_id`);
  - 资源所属关系一致(如 `link_id -> partner_id`).

## 6. 隐私与数据最小化
- 导出能力仅支持Excel; 导出请求可手工追加 `tags[]`.
- 系统自动设置 `exported` 标记与导出批次元数据(时间/批次/操作者).
- `tags[]` 可能包含业务敏感文本(如客户称谓/渠道名), 需:
  - 在权限范围内最小可见;
  - 写审计日志(谁在何时新增/删除哪些标签);
  - 不在公开购买页暴露.

## 7. 审计与追踪
- 关键动作必须审计: 生成库存、划拨、配额分配、创建链接、导出、核销.
- 审计字段至少包含: `trace_id`、`sub`、`iss`、`role/scopes`、资源ID、结果.
- 安全事件(签名失败、aud不匹配、重放嫌疑、越权访问)需单独告警.

## 8. 数据透传原则(固定)
接口落地以 `06-api.md` 的 `2.5.2~2.5.4` 与支付/分享/核销接口明细为准.

### 8.1 白名单透传
- 只允许透传“最小必要字段”:
  - 外部请求: `X-Request-Id`、`Idempotency-Key`、`request_id`、`share_token`
  - 支付场景: `buyer`(业务必需字段)
  - 受信上下文仅由网关注入: `X-Ctx-*`

### 8.2 黑名单透传
- 外部请求禁止携带:
  - 任意 `X-Ctx-*` 头
  - 下游场景中的 `tenant_id/project_id`
  - 客户端自报的资源归属字段(如“我属于某项目”)

### 8.3 透传处理链路
- 网关必须“剥离来路上下文头 + 验证JWT + 重建受信上下文头”.
- 业务服务必须“资源反查归属 + 上下文一致性校验”.
- 不一致直接失败, 不做“将错就错”降级.

### 8.4 令牌化透传
- 分享归因使用短期签名 `share_token`(ES256), 不透传明文归属信息.
- 透传令牌必须校验 `aud/exp/nbf/jti` 与资源绑定关系(如 `link_id`).
- 建议启用 `jti` 去重防重放.

### 8.5 幂等与重放防护
- 所有写接口必须支持 `request_id` 或 `Idempotency-Key`.
- 支付回调必须基于 `provider_txn_id + provider_event_id` 去重.

### 8.6 对外最小暴露
- 下游API响应体默认不返回 `tenant_id/project_id`.
- 仅返回业务必要字段与可审计标识(`trace_id` 等).

## 9. 一致性检查清单(供01~07引用)
- [ ] 租户端URL/API路径不出现 `tenant_id`.
- [ ] 下游URL/API路径不出现 `tenant_id`、`project_id`.
- [ ] 下游响应体默认不包含 `tenant_id`、`project_id`.
- [ ] `PurchaseLink`/`Order` 对外模型不含 `project_id`.
- [ ] 所有业务错误遵循 `pin` 响应格式(HTTP 200 + `error`).
- [ ] 外部来路 `X-Ctx-*` 被网关剥离并重建.
- [ ] 写接口具备 `request_id`/幂等机制, 重放可检测可拒绝.
- [ ] `share_token` 使用短期签名令牌并完成验签、过期、绑定校验.
