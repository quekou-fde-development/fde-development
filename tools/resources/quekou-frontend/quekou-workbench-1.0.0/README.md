# 杭州缺口 · 工作台工具包 1.0.0

给公司同事复用的前端工具箱：三套风格、28 个基础组件、12 个标准区块、四类固定页面、客户项目创建脚本与 Codex 项目技能。

**第一次使用请打开 [START_HERE.md](START_HERE.md)。** 非技术同事直接复制手册指令给 Codex，无需自行操作命令行。带可复制指令和风格截图的浏览版见 START_HERE.html。

| 入口 | 用途 |
|---|---|
| START_HERE.md / START_HERE.html | 手把手：第一次打开、练习、客户项目、修改、继续、分享 |
| NEW_CLIENT.md | 一段可复制的新客户指令 |
| RELEASE_AUDIT.md | 生产适用范围、发现与修复、实测证据及限制 |
| design/ | 缺口 VI 色彩、视觉规范与参数 |
| packages/theme、packages/ui | 可引用主题与组件源码，带构建产物及示例 |
| artifacts/ | 同版本 theme/ui 安装包 |
| starter/、scripts/create-client.mjs | 创建独立客户项目，避免误改母版 |
| .agents/skills/quekou-workbench | Codex 日常复用技能 |
| materials/ | 色板、12 张页面参考及依赖许可资料 |
| docs/上线验收.md | 每个客户业务上线前需要验收什么 |
| docs/维护与升级.md | 维护人发布、检查、回退与多人协作 |

本包适合制作界面、业务原型、客户项目的前端基础。登录、服务端权限、数据库保存、真实 AI 和上线环境需按客户项目接入。预览中的所有业务数据均为演示。

维护人命令：npm ci；npm run check；npx playwright install chromium；npm run test:browser。
日常预览：npm run dev。打开终端实际返回的网址；四页入口为 ?view=recipes&style=6&page=overview。
