# 07 - 技术栈与目录规划(Tech Stack & Directory)

本文档给出兑换码系统的推荐技术栈与仓库目录规划.
技术栈参考: `/Users/wanglei/Projects/teamatai/README.md`.

## 1. 技术栈总览

### 1.1 前端
- 所有前端应用统一: `React + Vite + React Router + Pinia + shadcn/ui + Tailwind CSS`
- 包含: `admin`(平台管理端)、`tenant`(租户管理端)、`portal`(合作伙伴端)、`pay`(公共购买页)

### 1.2 后端
- 主服务: `Go`(统一API与业务编排)
- API响应: `pin.Response`(统一200 + error结构, 见 `06-api.md`)
- 认证中心: `slauth`(`https://github.com/thecybersailor/slauth`)
- 认证校验: `JWT ES256(P-256) + JWKS`(由 `slauth` 签发/托管)
- 多认证体系: 统一收敛到 `slauth`(用户认证、第三方登录、机器凭证等), 业务服务只消费标准化身份上下文
- 核心能力: 库存/配额/购买链接/履约/核销/导出

### 1.3 数据与基础设施(推荐)
- 数据库: `PostgreSQL`
- 缓存/幂等: `Redis`
- 对象存储: Excel导出文件存储(`S3/OSS/COS`等)
- 部署: `Kubernetes`
- 自动化: `scripts/` + `Makefile` + CI/CD

## 2. 目录规划(建议 Monorepo)

```text
ticket/
├─ docs/
│  ├─ design/
│  └─ principles/
├─ packages/                  # 公共包
│  ├─ api-contracts/          # OpenAPI/JSON Schema/TS SDK
│  ├─ ui-kit/                 # 跨端UI组件与Design Tokens
│  └─ eslint-config/          # 前端规范
├─ host/                      # Go后端主工程(API + 领域服务)
│  ├─ cmd/
│  │  ├─ api/                 # 对外API入口(platform/tenant/partner/pay/biz)
│  │  └─ worker/              # 异步任务(webhook outbox/履约/导出等)
│  ├─ internal/
│  │  ├─ domain/              # 领域模型与规则
│  │  ├─ app/                 # 用例编排
│  │  ├─ infra/               # db/redis/webhook/storage/jwks
│  │  └─ transport/           # http handlers/middleware
│  ├─ migrations/
│  └─ openapi/
├─ admin/                     # 平台管理端
├─ tenant/                    # 租户管理端(独立前端系统)
├─ portal/                    # 合作伙伴端
├─ pay/                       # 公共购买页
├─ scripts/                   # 本地开发/联调/发布脚本
├─ e2e/                       # 端到端测试
└─ k8s/                       # 部署清单
```

补充说明:
- `slauth` 为独立认证中心仓库, 不放在本 monorepo 内:
  - `https://github.com/thecybersailor/slauth`
- 业务系统通过 `JWKS/Issuer/Audience` 对接 `slauth`, 不在业务代码里重复实现认证体系

## 3. 前后端边界约束(落地到目录)
- `host/openapi` 作为单一契约源, 生成 `packages/api-contracts`.
- `admin/tenant/portal/pay/site/site-dyn` 仅依赖 `packages/api-contracts` 发请求, 禁止手写漂移接口.
- 认证边界:
  - `slauth`: 负责多认证体系与身份签发
  - `host`: 只做 token/claim 校验与业务授权, 不重复实现登录体系
- 安全与透传规则遵循 `03-security-privacy.md`:
  - 租户端URL/API仅暴露 `project_id`
  - 下游端(`partner/pay/biz`)不暴露 `tenant_id/project_id`

## 4. 本地开发与端口建议(沿用16xxx)
- `host-api`: `:7181`
- `admin`: `:7105`
- `tenant`: `:7107`
- `portal`: `:7104`
- `pay`: `:7106`
- 统一入口: 根目录 `make dev`(tmux编排)

## 5. 开发顺序建议
1. 先完成 `host/` 核心领域与API契约(`06-api.md`).
2. 再做 `portal/`(伙伴端高频路径: 卡券 -> 券码列表 -> 详情).
3. 完成 `tenant/`(租户管理能力).
4. 完成 `admin/`(平台管理能力).
5. 最后完善 `pay/`、`site/`、`site-dyn/` 与自动化发布链路.
