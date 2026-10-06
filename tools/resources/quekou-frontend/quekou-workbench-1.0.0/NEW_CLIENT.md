# 新客户短指令

在新客户项目 <客户名> 中：
- 读取 workbench-kit/design/style-spec.md 与 tokens.json；如果当前已是客户目录，读取本目录 design/ 下同名文件
- 风格：<6/7/10>，旋钮 accentHue=<brand 或 210–240> density=<comfortable/compact> radiusScale=<0.5/1/1.5> surfaceMode=<light/dark/auto>
- 需要页面：<Overview/List/Detail/Settings 中选>
- 业务领域：<制造业/HR/销售>，核心实体：<...>，核心指标：<四项指标与口径>
- 用 packages/ui（客户项目为已安装的 @quekou/ui）的组件和四个页面配方拼装，不要自创新布局与颜色
- 交付前自查：无字面量颜色类名 / 正文对比度 ≥4.5:1 / 数字为 tabular-nums / 空态与加载态已实现 / 键盘可达
- 不确定的业务事实列为待确认，演示数据必须标注；真实保存和权限必须单独验收

母版内用 scripts/create-client.mjs 创建独立目录，不覆盖已有项目；客户目录直接迭代。不了解参数时，用 6、brand、comfortable、1、light。

日常自然语言版：

> 用缺口工作台为【客户】做【业务】后台，先用 6 号风格和缺口品牌色。对象是【对象】，使用者每天要【动作】。需要【四类页面中选择】。先询问缺失的口径，再完成页面、检查并打开给我看。把已完成和下一步写入 PROJECT_BRIEF.md。
