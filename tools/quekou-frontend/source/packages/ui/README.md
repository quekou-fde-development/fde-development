# @quekou/ui

缺口工作台组件库，版本 1.0.0。28 个基础组件、12 个标准区块、4 个固定页面配方，加一个主题容器。React 18，无 UI 组件库、无 CSS-in-JS、无内联样式。

## 安装与使用

```sh
npm install /path/quekou-theme-1.0.0.tgz /path/quekou-ui-1.0.0.tgz
```

项目需有 React / React DOM 18。CSS 按下列顺序导入；必须用 ThemeProvider 包裹工作区，以统一字体、数字、焦点和明暗参数。组件样式不依赖 Tailwind 的 reset。

```tsx
import '@quekou/theme/tokens.css';
import '@quekou/ui/styles.css';
import { ThemeProvider, Button, KpiCard } from '@quekou/ui';

export function App() {
  return <ThemeProvider theme="bento" accentHue="brand" density="comfortable"
    radiusScale={1} surfaceMode="light">
    <KpiCard label="已验收收入" value="128.6" unit="万元" change="较上月 +12.8%" />
    <Button variant="primary" onClick={() => { /* 执行业务动作 */ }}>新建项目</Button>
  </ThemeProvider>;
}
```

`ThemeProvider` 支持三套主题与四项参数，具体边界见 `@quekou/theme`。所有组件支持可选 `density`、`surfaceMode` 覆盖（包括嵌套控件）；无覆盖时继承容器。ref 指向组件主节点；Input、Select、Checkbox、ProgressBar 指向原生控件，Dialog/Drawer/CommandPalette 指向 dialog，其他指向最外层语义节点。DataTable 保留泛型行类型。

## 组件清单与主要接口

| 组件 | 主要接口与操作 |
|---|---|
| Button | primary / secondary / ghost × sm / md / lg；disabled、loading；Enter / Space |
| Input | label、hint、error；原生输入类型，错误提示与输入关联 |
| Select | label、options、hint、error；原生方向键选择 |
| Checkbox | label、indeterminate；Space 选择，支持混合状态 |
| Badge | success / warning / danger / info；图标和文字一起表达状态 |
| Tag | label、onRemove；移除按钮具有可读名称 |
| Avatar | name、src、size；图片加载失败退回姓名 |
| Tooltip | 一个可聚焦子元素、content；聚焦或悬停显示，Esc 关闭 |
| Popover | trigger、label、open/onOpenChange；打开聚焦首个控件，Esc 关闭并返回触发按钮，点击外部或移出焦点关闭 |
| Dialog | open/onOpenChange、title、description、footer；原生模态、限制焦点在弹窗、Esc 关闭并返回原焦点 |
| Drawer | 同 Dialog，呈现为右侧抽屉 |
| Toast | open、onDismiss、title、status、duration；默认自动关闭，悬停/聚焦暂停，duration=0 持续显示，关闭按钮可聚焦 |
| DataTable | rows、columns、getRowId、label；排序/搜索/选择/首列固定/虚拟滚动，详情见下文 |
| KpiCard | label、value、unit、change、direction、trend、emphasis |
| StatTile | label、value、hint |
| ChartCard | title、description、legend、actions、children；命名的 figure 容器 |
| Sparkline | values、label、large；SVG 提供可读名称与首尾值，单点及空数据有回退 |
| ProgressBar | value、label；数值限制到 0–100，语义为原生 progress |
| StatusDot | status、label；图形与文字表达状态 |
| EmptyState | title、description、action |
| Skeleton | lines=1/2/3、label；静态占位，避免干扰 |
| Pagination | page、pageCount、onPageChange；边界按钮不可点，页数变化可读 |
| AppShell | brand、sidebar、header、collapsed/onCollapsedChange；可收起导航，窄屏展开时上移导航 |
| NavGroup | label、items、activeId、onNavigate；链接的 href 由消费应用负责，当前项 aria-current |
| CommandPalette | items、open/onOpenChange、shortcut；⌘K / Ctrl+K、上下键、Enter、Esc，默认每页只放一个 |
| FilterBar | filters、search、from/to、变更回调、onReset；原生日期输入与范围校验 |
| PageHeader | title、description、eyebrow、actions |
| DetailPanel | title、description、onClose、actions、children |

## 表格使用边界

`DataColumn<T>` 提供 `id`、`label`、`value(row)` 和可选 `render(row)`。排序与搜索依照 value 的原始值；数值列按数字排序。`numeric` 控制数字对齐，`sortable=false` 关闭列排序。组件默认本地计算，后台分页/授权/提交由业务应用负责。

`selectedIds`、`sort`、`search` 和对应回调可采用受控模式；不传状态时由组件保存。全选针对筛选后的全部记录，也保留筛选外已有选择。getRowId 必须稳定且唯一。行选择支持复选框与混合状态。`pinFirstColumn=false` 取消首列固定。

默认开启固定行高的虚拟滚动，5,000 行演示只挂载可视区和少量缓冲行。表格滚动区可聚焦，方向键、PageUp/Down、Home/End 可滚动。为读屏与浏览器查找提供“显示全部行”；表格带总行数和行位置标记。当前不支持多行展开或不定行高单元格；长内容单行省略，应在详情面板展示。极大列表需服务器分页；本地过滤/排序仍会扫描全部数据。

图表提供可读标题及首尾信息，复杂图表应补充文本总结或数据表，不以迷你图代替精确数据。状态变化需要消费方传入正确文案；组件不推断业务结论。

## 示例与验证

每个组件同目录有 `*.example.tsx`，共 28 份，均通过严格类型检查。示例从公开包入口导入，可复制到消费项目。`styles.css` 包含示例用的轻量 `.qk-example-*` 排版。所有姓名和数据为虚构演示。完整验收页在工作区 `?view=components`。

已有验证覆盖 Chrome 中三主题明暗/密度、键盘与焦点、长列表、窄屏和文字对比度，以及独立 npm 压缩包消费。未声称完成所有浏览器与读屏软件的人工认证；在正式业务中仍需结合实际内容与目标辅助技术验收。


## 阶段 4：固定页面配方与标准区块

从公开入口导出 `Overview`、`List<T>`、`Detail<T>`、`Settings`。四者按固定顺序组合已认可组件；不提供任意重排 slots。`recipeCatalog` 是四配方的顺序清单；`blockCatalog` 是十二区块的固定清单。完整使用示例见工作区 `app/workbench/WorkbenchDemo.tsx`；接口与复用边界见 `design/page-recipes.md`。

- Overview：header、四项 kpis、trend、breakdown、activity。KpiRow 的 theme 与 ThemeProvider 使用同一值。
- List：header、query、records、pagination。调用方先筛选/全量排序，再提供当前页 records；不要只对分页后的记录做跨页排序。选中 id 可跨页保留，表头全选仅选择当前页。
- Detail：header、summary、activeTab/onTabChange、activity、related。Tab 提供方向键与 Home/End；关联记录仍保留行类型 T。
- Settings：header、navigation、sections、danger、dirty、onSave/onCancel、savedMessage。字段是 text/select/checkbox 判别联合；持久保存、验证和授权由业务调用方负责。

十二标准区块是 `KpiRow`、`TrendPanel`、`BreakdownPanel`、`ActivityFeed`、`QueryBar`、`RecordTable<T>`、`PaginationBar`、`EntitySummary`、`RelatedRecords<T>`、`SettingsNav`、`SettingsSection`、`DangerZone`。均有固定 Props、forwardRef、density/surfaceMode 参数。TrendPanel 支持有限正负数，提供精确值数据表；无效值显示错误状态。BreakdownPanel 需要调用方提供经过校验的非负有限指标。KpiRow、TrendPanel、BreakdownPanel、ActivityFeed、EntitySummary 以及记录类区块支持加载状态；无记录时显示明确空态。

`styles.css` 已包含区块与配方样式，仍只需导入主题 CSS 再导入 UI CSS。DataTable `showToolbar`、`showFooter`、`selectionLabel` 都有保持旧行为的默认值，供列表配方避免重复搜索和错误的全选口径。共享包只携带同版本 1.0.0 的安装包。

DangerZone 的 onConfirm 支持同步函数或 Promise；异步操作完成后才关闭，等待期间阻止重复提交，失败时保留弹窗并提示重试。调用方必须把失败抛出，且在服务端另做授权与幂等校验。Settings 的保存状态和业务错误由调用方控制，不能仅凭按钮点击判断保存成功。

新页面必须由配方 + 标准区块拼装，不得自创布局与颜色。示例的设置保存仅限本地浏览器，项目创建只限当前会话，危险操作只重置演示设置。组件包本身不访问浏览器存储、不带客户数据，也不执行网络请求。
