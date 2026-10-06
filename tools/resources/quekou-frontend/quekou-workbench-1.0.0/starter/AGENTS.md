# 缺口客户工作台
先读 design/style-spec.md、design/tokens.json、PROJECT_BRIEF.md 与 docs/上线验收.md。
日常用法参照 .agents/skills/quekou-workbench/SKILL.md。

- React 18 / TypeScript / Vite / Tailwind；使用本项目 vendor 的缺口 1.0.0 安装包。
- 新页面必须由配方 + 标准区块拼装，不得自创布局与颜色。四配方：Overview / List / Detail / Settings。
- 28 基础组件、12 区块只从 @quekou/ui 公开入口使用；接口与示例见 reference/ui。
- 视觉数值只来自 design/tokens.json 与 @quekou/theme；禁止额外 UI 库、CSS-in-JS、字面量颜色。四参数见 src/client.config.ts。
- 所有数字 tabular-nums；状态有文字/图标；正文对比度至少 4.5。保留键盘、窄屏、空态、加载和失败状态。
- 业务事实以用户提供资料为准；缺少指标口径、对象关系或权限规则时询问，不杜撰。模拟数据必须标注演示。
- 默认生成空数据骨架。现有项目不因“复用”而重建覆盖；先检查保留原有工作。
- 开始工作检查 Node 与 npm；没有运行环境时优先使用 Codex 提供的工作区运行时，再向用户说明缺口。
- npm ci；npm run dev -- --port 4174 预览；npm run check 检查。端口已占用时选空闲端口并返回实际地址。
- 前端完成不等于业务上线；上线前按照 docs/上线验收.md 核对真实数据、服务端权限、保存、失败重试和回滚。
- 把接续位置、待确认信息和通过的检查写回 PROJECT_BRIEF.md；用业务语言告诉用户下一次怎么继续。
