# 页面元素与布局

本文档只描述 Ticket 当前上线页面。所有页面必须以真实后端 API 和 swagger 生成的 TS SDK 为数据来源；没有后端契约的页面不允许以占位 API、mock 数据或 `unsupportedApi` 形式出现在生产前端。

## 通用交互规范

- 列表页使用搜索、刷新、空状态、错误状态和明确的主操作按钮。
- 所有前端统一使用 shadcn/ui `new-york-v4` 组件配置；用户可见的下拉选择使用 shadcn/ui `Select` 或 `Combobox`，不再使用原生 `<select>`。
- 四个前端都提供全局主题切换：`浅色`、`深色`、`跟随系统`；主题状态保存在 `ticket-theme`。
- 创建、编辑、轮换密钥等短上下文操作优先使用 shadcn/ui `Sheet`；不可逆或敏感动作使用 shadcn/ui `AlertDialog`。产品主详情不使用 Sheet，必须使用唯一详情页。
- 表单只展示用户能理解和负责的字段：租户管理员只填手机号，不出现 slauth user id；合作伙伴登录只填手机号和验证码。
- 错误必须 fastfail，直接展示可执行错误信息，不做静默降级。

## 平台管理端

- `/login`: 平台管理员手机号登录。
- `/dashboard`: 展示平台只读统计，不提供项目运营入口。
- `/tenants`: 展示租户名称、租户 ID、状态；新建租户使用 Sheet 或 Modal。
- `/tenants/:tenantId/overview`: 只展示租户基础信息和租户管理员手机号授权；不显示项目、项目密钥、产品或合作伙伴。

## 租户管理端

- `/login`: 租户管理员手机号登录。
- `/members`: 通过手机号邀请/禁用租户成员。
- `/projects`: 展示当前租户下项目列表；点击项目行进入项目总览。
- `/projects/:projectId/...`: 进入项目后左侧切换为项目工作台导航，顶部提供 shadcn/ui `Combobox`（`Popover` + `Command`）项目切换器。
- `/projects/:projectId/overview`: 展示项目基础信息和少量常用操作；完整入口由左侧项目工作台导航承载。
- `/projects/:projectId/service-credentials`: 展示多个项目密钥，支持创建、轮换、禁用；创建/轮换后一次性展示 `Ticket Project ID`、`Access Key ID`、`Secret Key`。
- `/projects/:projectId/products`: 产品列表，支持创建产品、进入产品详情；不提供产品快速查看 Sheet。
- `/projects/:projectId/products/new`: 创建产品，必须填写固定履约 JSON。
- `/projects/:projectId/products/:productId`: 唯一产品详情页，展示并编辑产品基础信息和固定履约 JSON，并展示产品维度资产聚合：项目库存、Partner 库存、Partner 配额和最近划拨。
- `/projects/:projectId/inventory`: 按产品生成券码；输入 JSON 必须能直接粘贴从 BotWorks 套餐详情复制出的 payload。
- `/projects/:projectId/quotas`: 配额列表，支持租户管理员给 Partner 发放产品配额；配额可被 Partner 用于生成 Code，也可被继续划拨。
- `/projects/:projectId/purchase-links`: 购买链接列表。
- `/projects/:projectId/orders`: 订单列表。
- `/projects/:projectId/allocations`: 划拨列表。
- `/projects/:projectId/shares`: 分享列表。
- `/projects/:projectId/exports`: 导出列表与导出动作。
- `/projects/:projectId/partners`: 通过手机号邀请合作伙伴；提交后自动创建未激活 Partner 与成员邀请。
- `/projects/:projectId/partners/:partnerId`: 展示合作伙伴基础信息、成员手机号、状态，并支持禁用。

## 合作伙伴端

- `/login`: 合作伙伴手机号验证码登录；不允许伙伴编号/密码登录。
- `/partners/:partnerId/overview`: 展示当前合作伙伴基础信息和运营入口。
- `/partners/:partnerId/products`: 产品列表。
- `/partners/:partnerId/codes`: 券码列表。
- `/partners/:partnerId/quotas`: 配额列表，支持查看可用配额、基于配额生成 Code、将可用配额划拨给其他 Partner。
- `/partners/:partnerId/purchase-links`: 购买链接列表。
- `/partners/:partnerId/orders`: 订单列表。
- `/partners/:partnerId/allocations`: 划拨列表。
- `/partners/:partnerId/shares`: 分享列表。
- `/partners/:partnerId/exports`: 导出列表。
- `/partners/:partnerId/profile`: 展示当前手机号和合作伙伴身份。

## 禁止项

- 平台端项目管理、平台端项目密钥管理、平台端产品管理。
- 租户端以 slauth user id 管理成员。
- 合作伙伴端伙伴编号/密码登录。
- 任何没有后端 API 的前端占位页面。
- 任何前端绕过 swagger TS SDK 的直接请求封装。
- 独立资产页。资产聚合只能出现在产品详情页内。
