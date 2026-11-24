# 网站架构图（菜单与路由）

本文档定义 Ticket 当前上线的唯一 Web 信息架构。未在本文档出现的页面不属于当前可达功能，不允许在前端菜单、路由、文案或 API SDK 包装中暴露。

## 角色边界

| 端 | 域名 | 用户 | 职责边界 |
| --- | --- | --- | --- |
| 平台管理端 | `https://ticket-admin.autostaff.cn` | 平台管理员 | 只管理 Ticket 租户与租户管理员手机号。 |
| 租户管理端 | `https://ticket-tenant.autostaff.cn` | 租户管理员 | 管理本租户项目、项目密钥、产品、券码、合作伙伴、配额和运营记录；资产聚合在产品详情页查看。 |
| 合作伙伴端 | `https://ticket-portal.autostaff.cn` | 合作伙伴 | 手机号登录，管理自己可访问的产品、券码、配额和运营记录；资产聚合在产品上下文查看。 |

## 通用路由约束

- 平台端允许出现 `tenantId`，但不出现项目运营能力。
- 租户端允许出现 `projectId`，不允许出现 `tenantId`。
- 合作伙伴端允许出现 `partnerId`，不允许出现 `tenantId` 或 `projectId`。
- 项目密钥只能在租户端项目上下文内创建、查看、轮换、禁用。
- 合作伙伴使用手机号登录；被邀请手机号第一次登录后可激活对应合作伙伴身份。

## 平台管理端

```text
Platform Console
├─ /login
├─ /dashboard
├─ /tenants
│  ├─ /tenants/new
│  └─ /tenants/:tenantId/overview
└─ /reports
```

## 租户管理端

```text
Tenant Console
├─ /login
├─ /members
├─ /projects
│  └─ /projects/:projectId
│     ├─ /projects/:projectId/overview
│     ├─ /projects/:projectId/service-credentials
│     ├─ /projects/:projectId/products
│     │  ├─ /projects/:projectId/products/new
│     │  └─ /projects/:projectId/products/:productId
│     ├─ /projects/:projectId/inventory
│     ├─ /projects/:projectId/quotas
│     ├─ /projects/:projectId/purchase-links
│     ├─ /projects/:projectId/orders
│     ├─ /projects/:projectId/allocations
│     ├─ /projects/:projectId/shares
│     ├─ /projects/:projectId/exports
│     └─ /projects/:projectId/partners
│        └─ /projects/:projectId/partners/:partnerId
└─ /profile
```

| 菜单 | 页面 | 路由 | 说明 |
| --- | --- | --- | --- |
| 成员 | 成员列表 | `/members` | 租户管理员通过手机号邀请/禁用租户成员。 |
| 项目管理 | 项目列表 | `/projects` | 创建和选择项目。 |
| 项目管理 | 项目总览 | `/projects/:projectId/overview` | 查看项目基本信息与快捷入口。 |
| 项目密钥 | 密钥列表 | `/projects/:projectId/service-credentials` | 创建、复制、轮换、禁用项目密钥；支持多个密钥并行轮替。 |
| 产品 | 产品列表 | `/projects/:projectId/products` | 管理产品。 |
| 产品 | 新建产品 | `/projects/:projectId/products/new` | 创建产品并填写固定履约 JSON。 |
| 产品 | 产品详情 | `/projects/:projectId/products/:productId` | 唯一产品详情入口；查看/编辑产品、固定履约 JSON、库存、配额和资产聚合。 |
| 券码 | 券码生成与列表 | `/projects/:projectId/inventory` | 按产品生成券码。 |
| 配额 | 配额列表 | `/projects/:projectId/quotas` | 管理产品配额。 |
| 购买链接 | 购买链接列表 | `/projects/:projectId/purchase-links` | 管理购买链接。 |
| 订单 | 订单列表 | `/projects/:projectId/orders` | 查看订单。 |
| 划拨 | 划拨列表 | `/projects/:projectId/allocations` | 管理划拨。 |
| 分享 | 分享列表 | `/projects/:projectId/shares` | 管理分享。 |
| 导出 | 导出中心 | `/projects/:projectId/exports` | 导出券码和运营数据。 |
| 合作伙伴 | 合作伙伴列表 | `/projects/:projectId/partners` | 通过手机号邀请合作伙伴；自动创建未激活 Partner。 |
| 合作伙伴 | 合作伙伴详情 | `/projects/:projectId/partners/:partnerId` | 查看合作伙伴与成员状态，可禁用合作伙伴。 |

## 合作伙伴端

```text
Partner Portal
├─ /login
└─ /partners/:partnerId
   ├─ /partners/:partnerId/overview
   ├─ /partners/:partnerId/products
   ├─ /partners/:partnerId/codes
   ├─ /partners/:partnerId/quotas
   ├─ /partners/:partnerId/purchase-links
   ├─ /partners/:partnerId/orders
   ├─ /partners/:partnerId/allocations
   ├─ /partners/:partnerId/shares
   ├─ /partners/:partnerId/exports
   └─ /partners/:partnerId/profile
```

合作伙伴端所有数据必须按当前手机号和 `partnerId` 授权过滤，不暴露 tenantId/projectId。

资产(Asset Summary)不是独立页面或独立资源模型。资产只作为产品详情页中的聚合视图存在，展示该产品维度下的项目库存、Partner 库存、Partner 配额和最近划拨。

## 禁止项

- 平台端项目管理、平台端项目密钥管理、平台端产品管理。
- 租户端旧产品路径业务入口。
- 伙伴编号/密码登录。
- 未由后端 OpenAPI 支撑的占位页面。
