# 阶段 4 · 页面配方与标准区块

页面配方、标准区块和三套风格演示现已固化。用户随后授权公司共享封装；日常调用入口为根目录 NEW_CLIENT.md，审查记录见 RELEASE_AUDIT.md。

## 四个配方

新页面必须由配方 + 标准区块拼装，不得自创布局与颜色。配方约定结构；调用方只提供类型化数据、状态与动作。

| 配方 | 固定顺序 | 用途 |
|---|---|---|
| Overview | PageHeader → KpiRow（4项）→ TrendPanel + BreakdownPanel → ActivityFeed | 经营概况与需要关注的工作 |
| List | PageHeader → QueryBar（FilterBar）→ RecordTable（DataTable）→ PaginationBar | 查找、排序、选择、进入业务对象 |
| Detail | PageHeader → EntitySummary → Tab → ActivityFeed（时间线）/ RelatedRecords | 理解一个对象及其过程与关联 |
| Settings | PageHeader → 左侧 SettingsNav + 右侧 SettingsSection 分组 → DangerZone | 修改工作区设置、保存与重置 |

Overview 按用户原任务要求统一先四指标、再双图、最后活动流。Bento 在四指标中保留一个更大主指标与三个次指标；Glass 保留等宽玻璃面板；Ambient 保留紧凑指标条与内联摘要。阶段 1 对照页仍保留用户认可的自由拼图布局，不用它改变正式配方的顺序。

## 十二个标准区块（固定接口）

| # | 区块 | 核心输入 | 对外动作 |
|---|---|---|---|
| 01 | KpiRow | 四项 label/value/unit/change/direction/trend，theme，可选 insight | 摘要的 onReview |
| 02 | TrendPanel | title/description/unit + 含 label/value/target 的时间序列 | 由可见数据表提供精确值，无隐式动作 |
| 03 | BreakdownPanel | title/description/unit + 分类 id/label/value | 可选 onSelect(id) |
| 04 | ActivityFeed | title/description + id/title/detail/actor/time/status，variant | 单条可选 onOpen |
| 05 | QueryBar | 搜索、日期区间、枚举筛选与变更回调 | onReset |
| 06 | RecordTable<T> | 标题、已处理的当前页记录、列定义、主键、排序、选择 | onSortChange/onSelectionChange/onClearSelection |
| 07 | PaginationBar | page/pageSize/total/selectedCount | onPageChange/onPageSizeChange |
| 08 | EntitySummary | title/description/status、字段、progress，可选 insight | 摘要的 onReview |
| 09 | RelatedRecords<T> | 关联标题、记录、列定义、主键、loading | 使用列动作进入关联对象 |
| 10 | SettingsNav | id/label/description 导航项 + activeId | onSelect |
| 11 | SettingsSection | id/title/description + text/select/checkbox 类型化字段 | 字段 onChange |
| 12 | DangerZone | 说明、操作文案、要求输入的确认文字 | onConfirm，仅输入匹配后触发 |

接口为导出的 TypeScript Props，见 packages/ui/src/blocks；配方接口见 packages/ui/src/recipes。所有区块基于已认可的 UI 组件组合，不包含客户数据库、授权或网络请求。颜色、字号、留白和新尺寸只取 design/tokens.json。

## 数据与交互规则

- 同一业务对象用稳定 id 贯穿总览、列表和详情；切换主题保留筛选、排序、选中项与当前对象。
- 列表必须先筛选、全量排序，再分页；当前页“全选”不能冒充筛选后全部记录。搜索只有一个入口。
- KPI 和图表的口径写在页面上。演示总额/完成度/状态分布从现有十条项目记录计算；趋势与活动注明模拟。
- 详情 Tab 支持方向键、Home/End、Enter/Space，并使用对应的 tabpanel；时间线与关联记录有加载、空态。
- 设置草稿与已保存值区分，显示未保存状态，取消会恢复已保存值。演示保存到当前浏览器，不声称写入公司系统。
- 危险操作放在右侧表单组之后，要求二次确认。本演示只重置演示配置，不能操作真实公司数据。
- Ambient 摘要标明“AI摘要示例 / 需负责人确认”，只提供进入记录的建议动作，不自动改变业务数据。
- 图表给出文字口径和精确值入口；不以颜色单独区分系列。小屏表格/图表只在自身区域滚动。
