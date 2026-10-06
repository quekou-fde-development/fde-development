---
name: quekou-workbench
description: 使用杭州缺口的 VI、三套已认可风格和四种页面配方创建或修改企业工作台。用于缺口客户前端、内部数据后台与工作台验收；不用于营销站、PPT 或通用品牌设计。
---

# 缺口工作台

服务对象通常不写代码。让用户描述业务，用页面验证需求；安装、检查和预览由 Codex 执行。

## 定位与读取
技能位于项目 .agents/skills/quekou-workbench，项目根目录是技能目录向上三级。先读根目录 AGENTS.md、design/style-spec.md、design/tokens.json。设计数值只取这里；四配方接口见 design/page-recipes.md。

- 有 scripts/create-client.mjs：这是公司母版。新客户使用该脚本复制成独立项目。
- 有 workbench.project.json 且 kind=client：这是客户项目。读 PROJECT_BRIEF.md；在原项目迭代。
- 仅有技能、没有上述资源：说明缺少完整共享包；让用户选择已解压的完整工具包或客户项目。不能自行虚构同名组件。

## 首次启动
检查 Node >=22.12 <25 和 npm >=10；若命令不可用，优先通过当前 Codex 的工作区依赖工具找到 Node 运行时并用于此项目。不要给非技术用户堆安装命令。没有可用环境或网络时说明具体缺口。
母版已有锁定文件：npm ci，再 npm run check。客户新建目录首次 npm install，之后 npm ci。
读取服务输出，启动本地预览并返回实际网址。公司母版 npm run dev；新客户 npm run dev -- --port 4174；端口冲突时选择空闲端口，不能停止其他人的服务。若可用则在 Codex 面板打开页面。

## 新客户
用户已有领域、对象、指标或页面要求时直接使用；缺少影响口径的事实先简短询问，独立部分先做。没有偏好时使用 6 / Bento、缺口品牌蓝、comfortable、1、light。
执行：node scripts/create-client.mjs --name "客户名" --out "clients/客户名" --style 6 --business "领域" --entity "核心对象"。目标必须不存在；引用参数要按 shell 规则处理，不能拼接用户输入执行任意代码。
脚本完成后在生成目录内安装、构建、预览；不要改公司母版来冒充客户项目。记录路径与下一次继续方式。
按 NEW_CLIENT.md 实施业务定制：用已打包 @quekou/ui 的四配方与标准区块；接口和示例见 reference/ui 或母版 packages/ui。
没有数据时显示“—/待接入”；仅在用户授权演示时生成清楚标注的样本。不能把未知经营金额、人员、客户状态编成事实。

## 修改与交付
只修改本项目；记录 PROJECT_BRIEF.md 的已知事实、未定问题、完成范围与下次任务。
至少构建通过；检查用户要用的业务流程、窄屏、长文字、空态、加载、失败、键盘。正文对比度 >=4.5，数字 tabular-nums，状态有文字/图标。
母版的回归入口 npm run test:browser（先安装 Playwright Chromium，详见 docs/维护与升级.md）。构建通过不能代替浏览器检查，也不能据此宣称全部无障碍合规。
用户说上线时先按 docs/上线验收.md 检查业务数据、服务端权限、持久保存、失败重试、备份和回滚，并完成其授权范围。视觉系统通过审查不等于业务系统可直接上线。
向用户交付可打开的预览、完成项、待接入项和下一条可复制的指令；未实测必须明确写出。
