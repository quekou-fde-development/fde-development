# @quekou/theme

缺口工作台主题，版本 1.0.0。唯一可编辑数值来源是工作区 `design/tokens.json`；`src/tokens.css`、`src/tokens.ts`、`src/tailwind.preset.ts` 和 `dist/` 都由构建生成。

## 安装与使用

本地压缩包可通过 `npm install /path/quekou-theme-1.0.0.tgz` 安装。没有向公共 registry 发布。

```tsx
import '@quekou/theme/tokens.css';
import { tokens, tokenVar, type ThemeName } from '@quekou/theme';
// 与 @quekou/ui 的 ThemeProvider 配套使用，统一设置三种主题和四项参数。
```

无 React 场景可直接设置容器属性：

```html
<div data-theme="bento" data-surface-mode="light" data-density="comfortable"
     data-accent-hue="brand" data-radius-scale="1">...</div>
```

- 三套主题：`bento`（06）、`glass`（07）、`ambient`（10）。
- 明暗：`light / dark / auto`。`auto` 响应操作系统实时切换。
- 密度：`comfortable / compact`，保持字号，调整留白与行高。
- 圆角：`0.5 / 1 / 1.5`。
- 色相：`brand` 为缺口原色，或 210–240 的整数。可读性衍生色自动配套。
- `:root` 默认 Bento 浅色。`.dark` 提供默认深色；`data-theme` 根节点自身加 `.dark` 也支持。显式 `data-surface-mode` 优先于同节点 `.dark`。嵌套主题使用自身的模式。
- CSS 自定义属性包括 `--surface-base`、`--fg-primary`、`--accent-solid`、状态色、间距、圆角、字号、阴影等；`tokenVar()` 限定合法名称。
- 品牌颜色来源：用户提供《缺口公司 VI 系统》第 6 页，来源记录在工作区 `design/references.md`。避免手工改写输出或另设客户色常量。

## 可选 Tailwind 3.4 preset

```ts
import preset from '@quekou/theme/tailwind.preset';
export default { presets: [preset], content: ['./src/**/*.{ts,tsx}'] };
```

使用如 `bg-surface-raised text-fg-primary rounded-card shadow-panel p-4`。颜色全部为语义变量，间距、字号、圆角和阴影也通过 token。预设替换对应默认 theme 字段，防止任意用色；需要额外数值时先修改唯一来源。纯 CSS 消费不需要安装 Tailwind。

1.0.0 新增页面配方需要的内容宽度、设置导航、趋势图高度与列表宽度 token；原三主题配色、密度和参数范围保持已认可值。
