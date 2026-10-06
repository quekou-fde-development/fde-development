# Workbench Kit

开工先读 `design/style-spec.md`，再读 `design/tokens.json` 与 `design/references.md`。

当前阶段：5 / 公司共享交付。用户已授权审查生产可用性、修复缺口并封装公司复用工具与手把手手册。日常复用入口为 START_HERE.md、NEW_CLIENT.md 和 .agents/skills/quekou-workbench/SKILL.md。
- 读取 design/preferences.json；品牌色以用户提供 VI PDF 第 6 页为准，标准色与可读性衍生色分开记录。
- React 18 + TypeScript + Vite + Tailwind CSS。
- 先规范与 token，后样品；tokens.json 是所有视觉数值唯一真相源。
- 只允许用户列出的无样式 primitives、lucide-react、recharts/visx、clsx/tailwind-merge；当前只使用 lucide-react。禁止 UI 组件库与 CSS-in-JS。
- 颜色、圆角、阴影、字号、间距均通过 token；间距允许 Tailwind scale。
- 所有数字 tabular-nums；状态同时有文字/图标；正文对比度至少 4.5:1。
- 10 种风格共用业务数据与样品结构。可以按风格改变模块比例和密度，不得改变事实。
- app/specimens 保留规范评审；packages/theme 与 packages/ui 为本轮正式产物，组件必须提供严格类型、forwardRef、键盘操作、density/surfaceMode 和同目录示例。
- 原五阶段开发已进入最终封装；新客户需求可在已授权范围内完成。用户明确要求阶段验收时才停在该阶段。
- 给非技术同事用业务语言报告结果、使用入口、验收和未完成项。不得把前端通过检查说成客户业务系统已上线。
- 新项目使用 scripts/create-client.mjs；目标必须是新目录，不覆盖既有项目。客户需求不完整时保留待确认项，不虚构经营事实。

- tokens.json 的 systems 是本轮入选风格规范；themes 仅为阶段 1 参考，不可作为新客户默认。
- 参数范围来自 parameterPolicy；不任意开放玻璃透明度、状态色或文字大小。

- 新页面必须由配方 + 标准区块拼装，不得自创布局与颜色。四个配方固定为 Overview / List / Detail / Settings；接口目录见 design/page-recipes.md。
- 标准区块只从 packages/ui 的基础组件组合，业务数据、路由与保存逻辑留在 app 或客户项目；不得把演示信息当作真实经营事实。
