"use strict";
var __defProp = Object.defineProperty;
var __getOwnPropDesc = Object.getOwnPropertyDescriptor;
var __getOwnPropNames = Object.getOwnPropertyNames;
var __hasOwnProp = Object.prototype.hasOwnProperty;
var __export = (target, all) => {
  for (var name in all)
    __defProp(target, name, { get: all[name], enumerable: true });
};
var __copyProps = (to, from, except, desc) => {
  if (from && typeof from === "object" || typeof from === "function") {
    for (let key of __getOwnPropNames(from))
      if (!__hasOwnProp.call(to, key) && key !== except)
        __defProp(to, key, { get: () => from[key], enumerable: !(desc = __getOwnPropDesc(from, key)) || desc.enumerable });
  }
  return to;
};
var __toCommonJS = (mod) => __copyProps(__defProp({}, "__esModule", { value: true }), mod);

// packages/ui/src/index.ts
var index_exports = {};
__export(index_exports, {
  ActivityFeed: () => ActivityFeed,
  AppShell: () => AppShell,
  Avatar: () => Avatar,
  Badge: () => Badge,
  BreakdownPanel: () => BreakdownPanel,
  Button: () => Button,
  ChartCard: () => ChartCard,
  Checkbox: () => Checkbox,
  CommandPalette: () => CommandPalette,
  DangerZone: () => DangerZone,
  DataTable: () => DataTable,
  Detail: () => Detail,
  DetailPanel: () => DetailPanel,
  Dialog: () => Dialog,
  Drawer: () => Drawer,
  EmptyState: () => EmptyState,
  EntitySummary: () => EntitySummary,
  FilterBar: () => FilterBar,
  Input: () => Input,
  KpiCard: () => KpiCard,
  KpiRow: () => KpiRow,
  List: () => List,
  NavGroup: () => NavGroup,
  Overview: () => Overview,
  PageHeader: () => PageHeader,
  Pagination: () => Pagination,
  PaginationBar: () => PaginationBar,
  Popover: () => Popover,
  ProgressBar: () => ProgressBar,
  QueryBar: () => QueryBar,
  RecordTable: () => RecordTable,
  RelatedRecords: () => RelatedRecords,
  Select: () => Select,
  Settings: () => Settings,
  SettingsNav: () => SettingsNav,
  SettingsSection: () => SettingsSection,
  Skeleton: () => Skeleton,
  Sparkline: () => Sparkline,
  StatTile: () => StatTile,
  StatusDot: () => StatusDot,
  Tag: () => Tag,
  ThemeProvider: () => ThemeProvider,
  Toast: () => Toast,
  Tooltip: () => Tooltip,
  TrendPanel: () => TrendPanel,
  blockCatalog: () => blockCatalog,
  normalizeTheme: () => normalizeTheme,
  recipeCatalog: () => recipeCatalog,
  statusIcons: () => statusIcons
});
module.exports = __toCommonJS(index_exports);

// packages/ui/src/components/AppShell.tsx
var import_react3 = require("react");
var import_lucide_react2 = require("lucide-react");

// packages/ui/src/internal/foundation.tsx
var import_react = require("react");
var import_theme = require("@quekou/theme");
function normalizeTheme(options) {
  const theme = options.theme && Object.hasOwn(import_theme.tokens.systems, options.theme) ? options.theme : "bento";
  const defaults = import_theme.tokens.systems[theme].defaults, p = import_theme.tokens.parameterPolicy;
  const raw = options.accentHue;
  const accentHue = raw === "brand" || raw === void 0 || !Number.isFinite(raw) || raw === p.accentHue.default ? "brand" : Math.max(p.accentHue.minimum, Math.min(p.accentHue.maximum, Math.round(raw)));
  return { theme, accentHue, density: options.density && p.density.values.some((v) => v === options.density) ? options.density : defaults.density, surfaceMode: options.surfaceMode && p.surfaceMode.values.some((v) => v === options.surfaceMode) ? options.surfaceMode : defaults.surfaceMode, radiusScale: options.radiusScale && p.radiusScale.values.some((v) => v === options.radiusScale) ? options.radiusScale : p.radiusScale.default };
}
var ThemeContext = (0, import_react.createContext)(normalizeTheme({}));
var themeAttributes = (t) => ({ "data-theme": t.theme, "data-density": t.density, "data-surface-mode": t.surfaceMode, "data-accent-hue": t.accentHue, "data-radius-scale": t.radiusScale });
function useThemeAttributes(overrides = {}) {
  const current = (0, import_react.useContext)(ThemeContext);
  return { "data-qk": "", ...overrides.density || overrides.surfaceMode ? themeAttributes({ ...current, ...Object.fromEntries(Object.entries(overrides).filter(([, v]) => v !== void 0)) }) : {} };
}
var cx = (...classes) => classes.filter(Boolean).join(" ");
function useMergedRef(external, inner) {
  return (0, import_react.useCallback)((value) => {
    inner.current = value;
    if (typeof external === "function") external(value);
    else if (external) external.current = value;
  }, [external, inner]);
}
function useControllable(value, initial, onChange) {
  const [local, setLocal] = (0, import_react.useState)(initial);
  const current = value === void 0 ? local : value;
  const ref = (0, import_react.useRef)(current);
  ref.current = current;
  const set = (next) => {
    if (value === void 0) setLocal(next);
    onChange?.(next);
  };
  return [current, set, ref];
}
var uiTokens = import_theme.tokens.common;

// packages/ui/src/components/Button.tsx
var import_react2 = require("react");
var import_lucide_react = require("lucide-react");
var import_jsx_runtime = require("react/jsx-runtime");
var Button = (0, import_react2.forwardRef)(function Button2({ variant = "secondary", size = "md", loading = false, disabled, density, surfaceMode, className, children, type = "button", ...rest }, ref) {
  const attrs = useThemeAttributes({ density, surfaceMode });
  return /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("button", { ...rest, ...attrs, ref, type, disabled: disabled || loading, "aria-busy": loading || void 0, className: cx("qk-button", className), "data-variant": variant, "data-size": size, children: [
    loading && /* @__PURE__ */ (0, import_jsx_runtime.jsx)(import_lucide_react.LoaderCircle, { "aria-hidden": "true", className: "qk-icon" }),
    children
  ] });
});

// packages/ui/src/components/AppShell.tsx
var import_jsx_runtime2 = require("react/jsx-runtime");
var AppShell = (0, import_react3.forwardRef)(function AppShell2({ brand, sidebar, header, collapsed, defaultCollapsed = false, onCollapsedChange, density, surfaceMode, className, children, ...rest }, ref) {
  const attrs = useThemeAttributes({ density, surfaceMode }), id = (0, import_react3.useId)();
  const [closed, setClosed] = useControllable(collapsed, defaultCollapsed, onCollapsedChange);
  const Icon = closed ? import_lucide_react2.PanelLeftOpen : import_lucide_react2.PanelLeftClose;
  return /* @__PURE__ */ (0, import_jsx_runtime2.jsxs)("div", { ...rest, ...attrs, ref, className: cx("qk-shell", className), "data-collapsed": closed, children: [
    /* @__PURE__ */ (0, import_jsx_runtime2.jsxs)("aside", { id, className: "qk-shell-sidebar", children: [
      /* @__PURE__ */ (0, import_jsx_runtime2.jsx)("div", { className: "qk-shell-brand", children: brand }),
      sidebar
    ] }),
    /* @__PURE__ */ (0, import_jsx_runtime2.jsxs)("div", { className: "qk-shell-main", children: [
      /* @__PURE__ */ (0, import_jsx_runtime2.jsxs)("header", { className: "qk-shell-header", children: [
        /* @__PURE__ */ (0, import_jsx_runtime2.jsx)(Button, { size: "sm", variant: "ghost", "aria-label": closed ? "\u5C55\u5F00\u4FA7\u680F" : "\u6536\u8D77\u4FA7\u680F", "aria-expanded": !closed, "aria-controls": id, onClick: () => setClosed(!closed), children: /* @__PURE__ */ (0, import_jsx_runtime2.jsx)(Icon, { className: "qk-icon", "aria-hidden": "true" }) }),
        header
      ] }),
      /* @__PURE__ */ (0, import_jsx_runtime2.jsx)("div", { className: "qk-shell-content", children })
    ] })
  ] });
});

// packages/ui/src/components/Avatar.tsx
var import_react4 = require("react");
var import_jsx_runtime3 = require("react/jsx-runtime");
var Avatar = (0, import_react4.forwardRef)(function Avatar2({ name, src, size = "sm", density, surfaceMode, className, ...rest }, ref) {
  const attrs = useThemeAttributes({ density, surfaceMode });
  const [failed, setFailed] = (0, import_react4.useState)(false);
  (0, import_react4.useEffect)(() => setFailed(false), [src]);
  return /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("span", { ...rest, ...attrs, ref, role: "img", "aria-label": name, className: cx("qk-avatar", className), "data-size": size, children: src && !failed ? /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("img", { src, alt: "", onError: () => setFailed(true) }) : /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("span", { "aria-hidden": "true", children: name.trim().slice(-2) || "?" }) });
});

// packages/ui/src/components/Badge.tsx
var import_react5 = require("react");
var import_lucide_react3 = require("lucide-react");
var import_jsx_runtime4 = require("react/jsx-runtime");
var statusIcons = { success: import_lucide_react3.CheckCircle2, warning: import_lucide_react3.TriangleAlert, danger: import_lucide_react3.OctagonAlert, info: import_lucide_react3.Info };
var Badge = (0, import_react5.forwardRef)(function Badge2({ status = "info", density, surfaceMode, className, children, ...rest }, ref) {
  const attrs = useThemeAttributes({ density, surfaceMode }), Icon = statusIcons[status];
  return /* @__PURE__ */ (0, import_jsx_runtime4.jsxs)("span", { ...rest, ...attrs, ref, className: cx("qk-badge", className), "data-status": status, children: [
    /* @__PURE__ */ (0, import_jsx_runtime4.jsx)(Icon, { "aria-hidden": "true", className: "qk-icon" }),
    children || { success: "\u5DF2\u5B8C\u6210", warning: "\u9700\u590D\u6838", danger: "\u9519\u8BEF", info: "\u4FE1\u606F" }[status]
  ] });
});

// packages/ui/src/components/ChartCard.tsx
var import_react6 = require("react");
var import_jsx_runtime5 = require("react/jsx-runtime");
var ChartCard = (0, import_react6.forwardRef)(function ChartCard2({ title, description, legend, actions, density, surfaceMode, className, children, ...rest }, ref) {
  const attrs = useThemeAttributes({ density, surfaceMode }), id = (0, import_react6.useId)();
  return /* @__PURE__ */ (0, import_jsx_runtime5.jsxs)("figure", { ...rest, ...attrs, ref, "aria-labelledby": id, className: cx("qk-chart-card qk-panel", className), children: [
    /* @__PURE__ */ (0, import_jsx_runtime5.jsxs)("figcaption", { className: "qk-panel-heading", children: [
      /* @__PURE__ */ (0, import_jsx_runtime5.jsxs)("div", { children: [
        /* @__PURE__ */ (0, import_jsx_runtime5.jsx)("h3", { id, children: title }),
        description && /* @__PURE__ */ (0, import_jsx_runtime5.jsx)("p", { className: "qk-muted", children: description })
      ] }),
      actions
    ] }),
    /* @__PURE__ */ (0, import_jsx_runtime5.jsx)("div", { className: "qk-chart-content", children }),
    legend && /* @__PURE__ */ (0, import_jsx_runtime5.jsx)("div", { className: "qk-chart-legend", children: legend })
  ] });
});

// packages/ui/src/components/Checkbox.tsx
var import_react7 = require("react");
var import_jsx_runtime6 = require("react/jsx-runtime");
var Checkbox = (0, import_react7.forwardRef)(function Checkbox2({ label, indeterminate = false, density, surfaceMode, className, ...rest }, ref) {
  const local = (0, import_react7.useRef)(null);
  const merged = useMergedRef(ref, local), attrs = useThemeAttributes({ density, surfaceMode });
  (0, import_react7.useEffect)(() => {
    if (local.current) local.current.indeterminate = indeterminate;
  }, [indeterminate]);
  return /* @__PURE__ */ (0, import_jsx_runtime6.jsxs)("label", { ...attrs, className: cx("qk-checkbox", className), children: [
    /* @__PURE__ */ (0, import_jsx_runtime6.jsx)("input", { ...rest, ref: merged, type: "checkbox", "aria-checked": indeterminate ? "mixed" : rest.checked }),
    /* @__PURE__ */ (0, import_jsx_runtime6.jsx)("span", { children: label })
  ] });
});

// packages/ui/src/components/CommandPalette.tsx
var import_react9 = require("react");

// packages/ui/src/components/Dialog.tsx
var import_react8 = require("react");
var import_lucide_react4 = require("lucide-react");
var import_jsx_runtime7 = require("react/jsx-runtime");
var Dialog = (0, import_react8.forwardRef)(function Dialog2({ open, onOpenChange, title, description, footer, closeOnOutside = true, density, surfaceMode, className, children, onClick, onKeyDown, ...rest }, ref) {
  const attrs = useThemeAttributes({ density, surfaceMode }), id = (0, import_react8.useId)();
  const desired = (0, import_react8.useRef)(open);
  desired.current = open;
  const local = (0, import_react8.useRef)(null), merged = useMergedRef(ref, local);
  (0, import_react8.useEffect)(() => {
    const el = local.current;
    if (open && !el?.open) el?.showModal();
    if (!open && el?.open) el.close();
    return () => {
      if (el?.open) el.close();
    };
  }, [open]);
  return /* @__PURE__ */ (0, import_jsx_runtime7.jsxs)("dialog", { ...rest, ...attrs, ref: merged, className: cx("qk-dialog", className), onKeyDown: (e) => {
    onKeyDown?.(e);
    if (e.defaultPrevented || e.key !== "Tab") return;
    const nodes = [...e.currentTarget.querySelectorAll("button,input,select,textarea,a[href],[tabindex]")].filter((el) => !el.matches(':disabled,[tabindex="-1"]') && el.getClientRects().length > 0 && getComputedStyle(el).visibility !== "hidden");
    const first = nodes[0], last = nodes.at(-1);
    if (!first) {
      e.preventDefault();
      e.currentTarget.focus();
    } else if (e.shiftKey && (document.activeElement === first || document.activeElement === e.currentTarget)) {
      e.preventDefault();
      last?.focus();
    } else if (!e.shiftKey && (document.activeElement === last || document.activeElement === e.currentTarget)) {
      e.preventDefault();
      first.focus();
    }
  }, "aria-labelledby": id, "aria-describedby": description ? id + "-description" : void 0, onCancel: (e) => {
    e.preventDefault();
    onOpenChange(false);
  }, onClose: () => {
    if (desired.current && !local.current?.open) onOpenChange(false);
  }, onClick: (e) => {
    onClick?.(e);
    if (!e.defaultPrevented && closeOnOutside && e.target === e.currentTarget) {
      const r = e.currentTarget.getBoundingClientRect();
      if (e.clientX < r.left || e.clientX > r.right || e.clientY < r.top || e.clientY > r.bottom) onOpenChange(false);
    }
  }, children: [
    /* @__PURE__ */ (0, import_jsx_runtime7.jsxs)("header", { className: "qk-panel-heading", children: [
      /* @__PURE__ */ (0, import_jsx_runtime7.jsx)("h2", { id, children: title }),
      /* @__PURE__ */ (0, import_jsx_runtime7.jsx)(Button, { variant: "ghost", size: "sm", "aria-label": `\u5173\u95ED${title}`, onClick: () => onOpenChange(false), children: /* @__PURE__ */ (0, import_jsx_runtime7.jsx)(import_lucide_react4.X, { "aria-hidden": "true", className: "qk-icon" }) })
    ] }),
    description && /* @__PURE__ */ (0, import_jsx_runtime7.jsx)("p", { id: id + "-description", className: "qk-muted qk-description", children: description }),
    /* @__PURE__ */ (0, import_jsx_runtime7.jsx)("div", { className: "qk-dialog-content", children }),
    footer && /* @__PURE__ */ (0, import_jsx_runtime7.jsx)("footer", { className: "qk-dialog-footer", children: footer })
  ] });
});

// packages/ui/src/components/CommandPalette.tsx
var import_jsx_runtime8 = require("react/jsx-runtime");
var CommandPalette = (0, import_react9.forwardRef)(function CommandPalette2({ items, open, defaultOpen = false, onOpenChange, shortcut = true, title = "\u5FEB\u6377\u547D\u4EE4", ...rest }, ref) {
  const [shown, setShown, current] = useControllable(open, defaultOpen, onOpenChange), [query, setQuery] = (0, import_react9.useState)(""), [active, setActive] = (0, import_react9.useState)(0), id = (0, import_react9.useId)();
  const setter = (0, import_react9.useRef)(setShown);
  setter.current = setShown;
  (0, import_react9.useEffect)(() => {
    if (!shortcut) return;
    const handler = (e) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k" && !e.isComposing) {
        e.preventDefault();
        setter.current(!current.current);
      }
    };
    document.addEventListener("keydown", handler);
    return () => document.removeEventListener("keydown", handler);
  }, [shortcut, current]);
  (0, import_react9.useEffect)(() => {
    if (shown) {
      setQuery("");
      setActive(0);
    }
  }, [shown]);
  const results = items.filter((x) => (x.label + " " + (x.keywords || "")).toLocaleLowerCase().includes(query.toLocaleLowerCase()));
  const index = Math.min(active, Math.max(0, results.length - 1));
  (0, import_react9.useEffect)(() => {
    if (shown && results[index]) document.getElementById(`${id}-${results[index].id}`)?.scrollIntoView({ block: "nearest" });
  }, [shown, index, id, query]);
  const select = (item) => {
    setShown(false);
    item.onSelect();
  };
  return /* @__PURE__ */ (0, import_jsx_runtime8.jsxs)(Dialog, { ...rest, ref, title, open: shown, onOpenChange: setShown, children: [
    /* @__PURE__ */ (0, import_jsx_runtime8.jsx)("input", { className: "qk-input", autoFocus: true, role: "combobox", "aria-label": "\u641C\u7D22\u5FEB\u6377\u547D\u4EE4", "aria-expanded": shown, "aria-controls": id, "aria-autocomplete": "list", "aria-activedescendant": results[index] ? `${id}-${results[index].id}` : void 0, value: query, onChange: (e) => {
      setQuery(e.target.value);
      setActive(0);
    }, onKeyDown: (e) => {
      if (e.nativeEvent.isComposing) return;
      if (e.key === "ArrowDown" || e.key === "ArrowUp") {
        e.preventDefault();
        setActive((n) => results.length ? (n + (e.key === "ArrowDown" ? 1 : -1) + results.length) % results.length : 0);
      }
      if (e.key === "Enter" && results[index]) {
        e.preventDefault();
        select(results[index]);
      }
    } }),
    /* @__PURE__ */ (0, import_jsx_runtime8.jsx)("div", { id, role: "listbox", "aria-label": "\u53EF\u7528\u547D\u4EE4", className: "qk-command-list", children: results.map((item, i) => /* @__PURE__ */ (0, import_jsx_runtime8.jsx)("div", { id: `${id}-${item.id}`, role: "option", "aria-selected": i === index, className: "qk-command-item", onMouseDown: (e) => e.preventDefault(), onMouseEnter: () => setActive(i), onClick: () => select(item), children: item.label }, item.id)) }),
    !results.length && /* @__PURE__ */ (0, import_jsx_runtime8.jsx)("p", { className: "qk-muted", role: "status", children: "\u6CA1\u6709\u5339\u914D\u7684\u547D\u4EE4" })
  ] });
});

// packages/ui/src/components/DataTable.tsx
var import_react12 = require("react");
var import_lucide_react6 = require("lucide-react");

// packages/ui/src/components/Input.tsx
var import_react10 = require("react");
var import_jsx_runtime9 = require("react/jsx-runtime");
var Input = (0, import_react10.forwardRef)(function Input2({ label, hint, error, id, density, surfaceMode, className, ...rest }, ref) {
  const generated = (0, import_react10.useId)(), fieldId = id || generated, descId = fieldId + "-description";
  const attrs = useThemeAttributes({ density, surfaceMode });
  return /* @__PURE__ */ (0, import_jsx_runtime9.jsxs)("div", { ...attrs, className: cx("qk-field", className), children: [
    /* @__PURE__ */ (0, import_jsx_runtime9.jsx)("label", { htmlFor: fieldId, className: "qk-label", children: label }),
    /* @__PURE__ */ (0, import_jsx_runtime9.jsx)("input", { ...rest, ref, id: fieldId, className: "qk-input", "aria-invalid": error ? true : rest["aria-invalid"], "aria-describedby": [rest["aria-describedby"], error || hint ? descId : void 0].filter(Boolean).join(" ") || void 0 }),
    (error || hint) && /* @__PURE__ */ (0, import_jsx_runtime9.jsx)("span", { id: descId, className: cx("qk-field-note", error && "qk-error"), role: error ? "alert" : void 0, children: error || hint })
  ] });
});

// packages/ui/src/components/EmptyState.tsx
var import_react11 = require("react");
var import_lucide_react5 = require("lucide-react");
var import_jsx_runtime10 = require("react/jsx-runtime");
var EmptyState = (0, import_react11.forwardRef)(function EmptyState2({ title, description, action, density, surfaceMode, className, ...rest }, ref) {
  const attrs = useThemeAttributes({ density, surfaceMode });
  return /* @__PURE__ */ (0, import_jsx_runtime10.jsxs)("div", { ...rest, ...attrs, ref, className: cx("qk-empty", className), children: [
    /* @__PURE__ */ (0, import_jsx_runtime10.jsx)(import_lucide_react5.Inbox, { "aria-hidden": "true", className: "qk-empty-icon" }),
    /* @__PURE__ */ (0, import_jsx_runtime10.jsx)("strong", { children: title }),
    description && /* @__PURE__ */ (0, import_jsx_runtime10.jsx)("p", { className: "qk-muted", children: description }),
    action
  ] });
});

// packages/ui/src/components/DataTable.tsx
var import_jsx_runtime11 = require("react/jsx-runtime");
function DataTableInner({ rows, columns, getRowId, label, showToolbar = true, showFooter = true, selectionLabel = "\u9009\u62E9\u7B5B\u9009\u540E\u7684\u5168\u90E8\u884C", selectable = false, selectedIds, onSelectionChange, sort: sortProp, onSortChange, search: searchProp, onSearchChange, pinFirstColumn = true, virtual = true, loading = false, density, surfaceMode, className, ...rest }, ref) {
  const attrs = useThemeAttributes({ density, surfaceMode }), theme = (0, import_react12.useContext)(ThemeContext);
  const outer = (0, import_react12.useRef)(null), scroll = (0, import_react12.useRef)(null), merged = useMergedRef(ref, outer);
  const [search, setSearch] = useControllable(searchProp, "", onSearchChange);
  const [sort, setSort] = useControllable(sortProp, null, (s) => {
    if (s) onSortChange?.(s);
  });
  const [selection, setSelection] = useControllable(selectedIds, [], (ids) => onSelectionChange?.([...ids]));
  const [allRows, setAllRows] = (0, import_react12.useState)(false), [offset, setOffset] = (0, import_react12.useState)(0), [dimensions, setDimensions] = (0, import_react12.useState)({ row: parseFloat(uiTokens["row-height"]), viewport: 0, header: 0 });
  (0, import_react12.useLayoutEffect)(() => {
    const el = scroll.current;
    if (!el) return;
    const measure = () => {
      const cs = getComputedStyle(el);
      setDimensions({ row: parseFloat(cs.getPropertyValue("--row-height")), viewport: el.clientHeight, header: parseFloat(cs.getPropertyValue("--table-header-height")) });
    };
    measure();
    const observer = new ResizeObserver(measure);
    observer.observe(el);
    return () => observer.disconnect();
  }, [density, theme.density, allRows, virtual]);
  const filtered = (0, import_react12.useMemo)(() => {
    const needle = search.trim().toLocaleLowerCase();
    const result = rows.filter((row) => !needle || columns.some((c) => String(c.value(row) ?? "").toLocaleLowerCase().includes(needle)));
    const col = columns.find((c) => c.id === sort?.column);
    if (col && sort) result.sort((a, b) => {
      const x = col.value(a) ?? "", y = col.value(b) ?? "";
      const n = typeof x === "number" && typeof y === "number" ? x - y : String(x).localeCompare(String(y), "zh-CN", { numeric: true });
      return n * (sort.direction === "asc" ? 1 : -1);
    });
    return result;
  }, [rows, columns, search, sort]);
  (0, import_react12.useLayoutEffect)(() => {
    if (scroll.current) scroll.current.scrollTop = 0;
    setOffset(0);
  }, [search, sort, rows]);
  const isVirtual = virtual && !allRows, overscan = Number(uiTokens["virtual-overscan"]), rowHeight = dimensions.row || parseFloat(uiTokens["row-height"]);
  const first = isVirtual ? Math.max(0, Math.min(Math.max(0, filtered.length - 1), Math.floor(Math.max(0, offset - dimensions.header) / rowHeight) - overscan)) : 0;
  const end = isVirtual ? Math.min(filtered.length, first + Math.ceil(dimensions.viewport / rowHeight) + overscan * 2) : filtered.length;
  const visible = filtered.slice(first, end), colSpan = columns.length + (selectable ? 1 : 0), selectedSet = new Set(selection), every = filtered.length > 0 && filtered.every((r) => selectedSet.has(getRowId(r))), some = filtered.some((r) => selectedSet.has(getRowId(r)));
  const selectAll = (checked) => {
    const ids = new Set(selection);
    for (const row of filtered) {
      if (checked) ids.add(getRowId(row));
      else ids.delete(getRowId(row));
    }
    setSelection([...ids]);
  };
  const spacer = (height, key) => /* @__PURE__ */ (0, import_jsx_runtime11.jsx)("tr", { "aria-hidden": "true", className: "qk-table-spacer", children: /* @__PURE__ */ (0, import_jsx_runtime11.jsx)("td", { colSpan, children: /* @__PURE__ */ (0, import_jsx_runtime11.jsx)("svg", { height, width: "1", "aria-hidden": "true" }) }) }, key);
  return /* @__PURE__ */ (0, import_jsx_runtime11.jsxs)("div", { ...rest, ...attrs, ref: merged, className: cx("qk-data-table qk-panel", className), "data-virtual": isVirtual, "data-selectable": selectable, "aria-busy": loading || void 0, children: [
    showToolbar && /* @__PURE__ */ (0, import_jsx_runtime11.jsxs)("div", { className: "qk-table-toolbar", children: [
      /* @__PURE__ */ (0, import_jsx_runtime11.jsx)(Input, { label: "\u641C\u7D22\u8868\u683C", "aria-label": `${label}\u641C\u7D22`, type: "search", value: search, onChange: (e) => setSearch(e.target.value), placeholder: "\u641C\u7D22\u4EFB\u610F\u5217" }),
      /* @__PURE__ */ (0, import_jsx_runtime11.jsxs)("span", { className: "qk-muted", "aria-live": "polite", children: [
        filtered.length,
        " \u884C \xB7 \u5DF2\u9009\u62E9 ",
        selection.length,
        " \u884C"
      ] }),
      virtual && /* @__PURE__ */ (0, import_jsx_runtime11.jsx)(Button, { size: "sm", onClick: () => setAllRows(!allRows), "aria-pressed": allRows, children: allRows ? "\u542F\u7528\u865A\u62DF\u6EDA\u52A8" : "\u663E\u793A\u5168\u90E8\u884C" })
    ] }),
    /* @__PURE__ */ (0, import_jsx_runtime11.jsxs)("div", { ref: scroll, className: "qk-table-scroll", role: "region", "aria-label": `${label}\u53EF\u6EDA\u52A8\u8868\u683C`, tabIndex: 0, onScroll: (e) => setOffset(e.currentTarget.scrollTop), onKeyDown: (e) => {
      if (e.target !== e.currentTarget) return;
      const el = e.currentTarget;
      const jumps = { ArrowDown: el.scrollTop + rowHeight, ArrowUp: el.scrollTop - rowHeight, PageDown: el.scrollTop + el.clientHeight, PageUp: el.scrollTop - el.clientHeight, Home: 0, End: el.scrollHeight };
      if (e.key in jumps) {
        e.preventDefault();
        el.scrollTop = jumps[e.key];
      }
    }, children: [
      /* @__PURE__ */ (0, import_jsx_runtime11.jsxs)("table", { className: "qk-table", "aria-rowcount": filtered.length + 1, children: [
        /* @__PURE__ */ (0, import_jsx_runtime11.jsxs)("caption", { className: "qk-sr-only", children: [
          label,
          "\uFF0C",
          isVirtual ? "\u865A\u62DF\u6EDA\u52A8\uFF1B\u53EF\u7528\u65B9\u5411\u952E\u3001PageDown\u3001Home\u3001End\uFF0C\u6216\u663E\u793A\u5168\u90E8\u884C" : "\u5B8C\u6574\u5217\u8868"
        ] }),
        /* @__PURE__ */ (0, import_jsx_runtime11.jsx)("thead", { children: /* @__PURE__ */ (0, import_jsx_runtime11.jsxs)("tr", { children: [
          selectable && /* @__PURE__ */ (0, import_jsx_runtime11.jsx)("th", { className: "qk-select-col", children: /* @__PURE__ */ (0, import_jsx_runtime11.jsx)(Checkbox, { label: selectionLabel, className: "qk-checkbox-icon", checked: every, indeterminate: some && !every, disabled: !filtered.length || loading, onChange: (e) => selectAll(e.target.checked) }) }),
          columns.map((col, i) => /* @__PURE__ */ (0, import_jsx_runtime11.jsx)("th", { scope: "col", "data-pinned": pinFirstColumn && i === 0, "data-numeric": col.numeric, "aria-sort": sort?.column === col.id ? sort.direction === "asc" ? "ascending" : "descending" : "none", children: col.sortable !== false ? /* @__PURE__ */ (0, import_jsx_runtime11.jsxs)("button", { type: "button", onClick: () => setSort({ column: col.id, direction: sort?.column === col.id && sort.direction === "asc" ? "desc" : "asc" }), children: [
            col.label,
            /* @__PURE__ */ (0, import_jsx_runtime11.jsx)(import_lucide_react6.ArrowDownUp, { className: "qk-icon", "aria-hidden": "true" })
          ] }) : col.label }, col.id))
        ] }) }),
        /* @__PURE__ */ (0, import_jsx_runtime11.jsxs)("tbody", { children: [
          isVirtual && first > 0 && spacer(first * rowHeight, "top"),
          visible.map((row, index) => {
            const id = getRowId(row);
            return /* @__PURE__ */ (0, import_jsx_runtime11.jsxs)("tr", { "aria-rowindex": first + index + 2, "aria-selected": selectable ? selectedSet.has(id) : void 0, "data-selected": selectedSet.has(id), children: [
              selectable && /* @__PURE__ */ (0, import_jsx_runtime11.jsx)("td", { className: "qk-select-col", children: /* @__PURE__ */ (0, import_jsx_runtime11.jsx)(Checkbox, { label: `\u9009\u62E9\u884C ${id}`, className: "qk-checkbox-icon", checked: selectedSet.has(id), disabled: loading, onChange: (e) => {
                const ids = new Set(selection);
                if (e.target.checked) ids.add(id);
                else ids.delete(id);
                setSelection([...ids]);
              } }) }),
              columns.map((col, i) => /* @__PURE__ */ (0, import_jsx_runtime11.jsx)("td", { "data-pinned": pinFirstColumn && i === 0, "data-numeric": col.numeric, children: /* @__PURE__ */ (0, import_jsx_runtime11.jsx)("div", { className: "qk-cell", children: col.render ? col.render(row) : col.value(row) ?? "\u2014" }) }, col.id))
            ] }, id);
          }),
          isVirtual && end < filtered.length && spacer((filtered.length - end) * rowHeight, "bottom")
        ] })
      ] }),
      !filtered.length && /* @__PURE__ */ (0, import_jsx_runtime11.jsx)(EmptyState, { title: loading ? "\u6B63\u5728\u8F7D\u5165\u6570\u636E" : "\u6CA1\u6709\u5339\u914D\u7684\u8BB0\u5F55", description: loading ? "\u8BF7\u7A0D\u5019\u3002" : "\u8C03\u6574\u5173\u952E\u8BCD\u540E\u91CD\u8BD5\u3002" })
    ] }),
    showFooter && /* @__PURE__ */ (0, import_jsx_runtime11.jsxs)("div", { className: "qk-table-footer", children: [
      loading ? "\u6B63\u5728\u66F4\u65B0\u6570\u636E" : `\u663E\u793A ${filtered.length ? first + 1 : 0}\u2013${end} / ${filtered.length} \u884C`,
      isVirtual && /* @__PURE__ */ (0, import_jsx_runtime11.jsx)("span", { children: "\u865A\u62DF\u6EDA\u52A8\u5DF2\u542F\u7528 \xB7 \u9996\u5217\u53EF\u56FA\u5B9A" })
    ] })
  ] });
}
var DataTable = (0, import_react12.forwardRef)(DataTableInner);

// packages/ui/src/components/DetailPanel.tsx
var import_react13 = require("react");
var import_lucide_react7 = require("lucide-react");
var import_jsx_runtime12 = require("react/jsx-runtime");
var DetailPanel = (0, import_react13.forwardRef)(function DetailPanel2({ title, description, onClose, actions, density, surfaceMode, className, children, ...rest }, ref) {
  const attrs = useThemeAttributes({ density, surfaceMode }), id = (0, import_react13.useId)();
  return /* @__PURE__ */ (0, import_jsx_runtime12.jsxs)("aside", { ...rest, ...attrs, ref, className: cx("qk-detail qk-panel", className), "aria-labelledby": id, children: [
    /* @__PURE__ */ (0, import_jsx_runtime12.jsxs)("div", { className: "qk-panel-heading", children: [
      /* @__PURE__ */ (0, import_jsx_runtime12.jsx)("h2", { id, children: title }),
      onClose && /* @__PURE__ */ (0, import_jsx_runtime12.jsx)(Button, { size: "sm", variant: "ghost", "aria-label": `\u5173\u95ED${title}`, onClick: onClose, children: /* @__PURE__ */ (0, import_jsx_runtime12.jsx)(import_lucide_react7.X, { "aria-hidden": "true", className: "qk-icon" }) })
    ] }),
    description && /* @__PURE__ */ (0, import_jsx_runtime12.jsx)("p", { className: "qk-muted qk-description", children: description }),
    /* @__PURE__ */ (0, import_jsx_runtime12.jsx)("div", { children }),
    actions && /* @__PURE__ */ (0, import_jsx_runtime12.jsx)("footer", { className: "qk-dialog-footer", children: actions })
  ] });
});

// packages/ui/src/components/Drawer.tsx
var import_react14 = require("react");
var import_jsx_runtime13 = require("react/jsx-runtime");
var Drawer = (0, import_react14.forwardRef)(function Drawer2({ className, ...props }, ref) {
  return /* @__PURE__ */ (0, import_jsx_runtime13.jsx)(Dialog, { ...props, ref, className: cx("qk-drawer", className) });
});

// packages/ui/src/components/FilterBar.tsx
var import_react16 = require("react");

// packages/ui/src/components/Select.tsx
var import_react15 = require("react");
var import_jsx_runtime14 = require("react/jsx-runtime");
var Select = (0, import_react15.forwardRef)(function Select2({ label, options, hint, error, id, density, surfaceMode, className, ...rest }, ref) {
  const generated = (0, import_react15.useId)(), fieldId = id || generated, desc = fieldId + "-description";
  const attrs = useThemeAttributes({ density, surfaceMode });
  return /* @__PURE__ */ (0, import_jsx_runtime14.jsxs)("div", { ...attrs, className: cx("qk-field", className), children: [
    /* @__PURE__ */ (0, import_jsx_runtime14.jsx)("label", { htmlFor: fieldId, className: "qk-label", children: label }),
    /* @__PURE__ */ (0, import_jsx_runtime14.jsx)("select", { ...rest, ref, id: fieldId, className: "qk-input", "aria-invalid": error ? true : rest["aria-invalid"], "aria-describedby": [rest["aria-describedby"], error || hint ? desc : void 0].filter(Boolean).join(" ") || void 0, children: options.map((o) => /* @__PURE__ */ (0, import_jsx_runtime14.jsx)("option", { value: o.value, disabled: o.disabled, children: o.label }, o.value)) }),
    (error || hint) && /* @__PURE__ */ (0, import_jsx_runtime14.jsx)("span", { id: desc, className: cx("qk-field-note", error && "qk-error"), role: error ? "alert" : void 0, children: error || hint })
  ] });
});

// packages/ui/src/components/FilterBar.tsx
var import_jsx_runtime15 = require("react/jsx-runtime");
var FilterBar = (0, import_react16.forwardRef)(function FilterBar2({ filters, search, onSearchChange, from, to, onDateChange, onReset, density, surfaceMode, className, ...rest }, ref) {
  const attrs = useThemeAttributes({ density, surfaceMode });
  return /* @__PURE__ */ (0, import_jsx_runtime15.jsxs)("div", { ...rest, ...attrs, ref, className: cx("qk-filter-bar", className), "aria-label": "\u7B5B\u9009\u6761\u4EF6", children: [
    filters.map((f) => /* @__PURE__ */ (0, import_jsx_runtime15.jsx)(Select, { label: f.label, value: f.value, options: f.options, onChange: (e) => f.onChange(e.target.value) }, f.id)),
    /* @__PURE__ */ (0, import_jsx_runtime15.jsx)(Input, { label: "\u5F00\u59CB\u65E5\u671F", type: "date", value: from, max: to || void 0, onChange: (e) => onDateChange({ from: e.target.value, to }) }),
    /* @__PURE__ */ (0, import_jsx_runtime15.jsx)(Input, { label: "\u7ED3\u675F\u65E5\u671F", type: "date", value: to, min: from || void 0, onChange: (e) => onDateChange({ from, to: e.target.value }) }),
    /* @__PURE__ */ (0, import_jsx_runtime15.jsx)(Input, { label: "\u641C\u7D22", type: "search", value: search, onChange: (e) => onSearchChange(e.target.value) }),
    /* @__PURE__ */ (0, import_jsx_runtime15.jsx)(Button, { onClick: onReset, children: "\u91CD\u7F6E\u7B5B\u9009" }),
    from && to && from > to && /* @__PURE__ */ (0, import_jsx_runtime15.jsx)("p", { className: "qk-error", role: "alert", children: "\u5F00\u59CB\u65E5\u671F\u665A\u4E8E\u7ED3\u675F\u65E5\u671F" })
  ] });
});

// packages/ui/src/components/KpiCard.tsx
var import_react18 = require("react");
var import_lucide_react8 = require("lucide-react");

// packages/ui/src/components/Sparkline.tsx
var import_react17 = require("react");
var import_jsx_runtime16 = require("react/jsx-runtime");
var Sparkline = (0, import_react17.forwardRef)(function Sparkline2({ values, label, large = false, density, surfaceMode, className, ...rest }, ref) {
  const attrs = useThemeAttributes({ density, surfaceMode }), id = (0, import_react17.useId)(), safe = values.filter(Number.isFinite);
  const min = Math.min(...safe), max = Math.max(...safe), range = max - min || 1;
  const points = safe.map((v, i) => `${8 + i * 184 / Math.max(1, safe.length - 1)},${max === min ? 32 : 56 - (v - min) * 48 / range}`).join(" ");
  return /* @__PURE__ */ (0, import_jsx_runtime16.jsxs)("svg", { ...rest, ...attrs, ref, viewBox: "0 0 200 64", role: "img", "aria-labelledby": id, preserveAspectRatio: "none", className: cx("qk-sparkline", large && "qk-sparkline-large", className), children: [
    /* @__PURE__ */ (0, import_jsx_runtime16.jsxs)("title", { id, children: [
      label,
      safe.length ? `\uFF0C\u8D77\u70B9 ${safe[0]}\uFF0C\u7EC8\u70B9 ${safe.at(-1)}` : "\uFF0C\u6682\u65E0\u6570\u636E"
    ] }),
    safe.length > 1 ? /* @__PURE__ */ (0, import_jsx_runtime16.jsx)("polyline", { points, fill: "none", vectorEffect: "non-scaling-stroke" }) : safe.length === 1 ? /* @__PURE__ */ (0, import_jsx_runtime16.jsx)("circle", { cx: "100", cy: "32", r: "3" }) : null
  ] });
});

// packages/ui/src/components/KpiCard.tsx
var import_jsx_runtime17 = require("react/jsx-runtime");
var KpiCard = (0, import_react18.forwardRef)(function KpiCard2({ label, value, unit, change, trend, direction = "up", emphasis = false, density, surfaceMode, className, ...rest }, ref) {
  const attrs = useThemeAttributes({ density, surfaceMode }), Icon = direction === "up" ? import_lucide_react8.ArrowUpRight : direction === "down" ? import_lucide_react8.ArrowDownRight : import_lucide_react8.Minus;
  return /* @__PURE__ */ (0, import_jsx_runtime17.jsxs)("article", { ...rest, ...attrs, ref, className: cx("qk-kpi qk-panel", className), "data-emphasis": emphasis, children: [
    /* @__PURE__ */ (0, import_jsx_runtime17.jsx)("p", { className: "qk-muted", children: label }),
    /* @__PURE__ */ (0, import_jsx_runtime17.jsxs)("div", { className: "qk-kpi-value", children: [
      /* @__PURE__ */ (0, import_jsx_runtime17.jsx)("strong", { children: value }),
      /* @__PURE__ */ (0, import_jsx_runtime17.jsx)("span", { children: unit })
    ] }),
    /* @__PURE__ */ (0, import_jsx_runtime17.jsxs)("div", { className: "qk-kpi-bottom", children: [
      /* @__PURE__ */ (0, import_jsx_runtime17.jsxs)("span", { children: [
        /* @__PURE__ */ (0, import_jsx_runtime17.jsx)(Icon, { "aria-hidden": "true", className: "qk-icon" }),
        change
      ] }),
      trend && /* @__PURE__ */ (0, import_jsx_runtime17.jsx)(Sparkline, { values: trend, label: `${label}\u8D8B\u52BF` })
    ] })
  ] });
});

// packages/ui/src/components/NavGroup.tsx
var import_react19 = require("react");
var import_jsx_runtime18 = require("react/jsx-runtime");
var NavGroup = (0, import_react19.forwardRef)(function NavGroup2({ label, items, activeId, onNavigate, density, surfaceMode, className, ...rest }, ref) {
  const attrs = useThemeAttributes({ density, surfaceMode });
  return /* @__PURE__ */ (0, import_jsx_runtime18.jsxs)("nav", { ...rest, ...attrs, ref, "aria-label": label, className: cx("qk-nav-group", className), children: [
    /* @__PURE__ */ (0, import_jsx_runtime18.jsx)("p", { className: "qk-nav-label qk-muted", children: label }),
    items.map((item) => /* @__PURE__ */ (0, import_jsx_runtime18.jsxs)("a", { href: item.href, "aria-label": item.label, "aria-current": activeId === item.id ? "page" : void 0, className: "qk-nav-link", onClick: () => onNavigate?.(item.id), children: [
      item.icon && /* @__PURE__ */ (0, import_jsx_runtime18.jsx)("span", { "aria-hidden": "true", children: item.icon }),
      /* @__PURE__ */ (0, import_jsx_runtime18.jsx)("span", { className: "qk-nav-label", children: item.label }),
      item.count !== void 0 && /* @__PURE__ */ (0, import_jsx_runtime18.jsx)("span", { className: "qk-nav-count", children: item.count })
    ] }, item.id))
  ] });
});

// packages/ui/src/components/PageHeader.tsx
var import_react20 = require("react");
var import_jsx_runtime19 = require("react/jsx-runtime");
var PageHeader = (0, import_react20.forwardRef)(function PageHeader2({ title, description, eyebrow, actions, density, surfaceMode, className, ...rest }, ref) {
  const attrs = useThemeAttributes({ density, surfaceMode });
  return /* @__PURE__ */ (0, import_jsx_runtime19.jsxs)("header", { ...rest, ...attrs, ref, className: cx("qk-page-header", className), children: [
    /* @__PURE__ */ (0, import_jsx_runtime19.jsxs)("div", { children: [
      eyebrow && /* @__PURE__ */ (0, import_jsx_runtime19.jsx)("p", { className: "qk-eyebrow", children: eyebrow }),
      /* @__PURE__ */ (0, import_jsx_runtime19.jsx)("h1", { children: title }),
      description && /* @__PURE__ */ (0, import_jsx_runtime19.jsx)("p", { className: "qk-muted", children: description })
    ] }),
    actions && /* @__PURE__ */ (0, import_jsx_runtime19.jsx)("div", { className: "qk-actions", children: actions })
  ] });
});

// packages/ui/src/components/Pagination.tsx
var import_react21 = require("react");
var import_jsx_runtime20 = require("react/jsx-runtime");
var Pagination = (0, import_react21.forwardRef)(function Pagination2({ page, pageCount, onPageChange, density, surfaceMode, className, ...rest }, ref) {
  const attrs = useThemeAttributes({ density, surfaceMode }), count = Math.max(0, Math.floor(pageCount) || 0), current = count ? Math.max(1, Math.min(count, Math.floor(page) || 1)) : 0;
  return /* @__PURE__ */ (0, import_jsx_runtime20.jsxs)("nav", { ...rest, ...attrs, ref, "aria-label": "\u5206\u9875", className: cx("qk-pagination", className), children: [
    /* @__PURE__ */ (0, import_jsx_runtime20.jsx)(Button, { size: "sm", disabled: current <= 1, onClick: () => onPageChange(1), children: "\u9996\u9875" }),
    /* @__PURE__ */ (0, import_jsx_runtime20.jsx)(Button, { size: "sm", disabled: current <= 1, onClick: () => onPageChange(current - 1), children: "\u4E0A\u4E00\u9875" }),
    /* @__PURE__ */ (0, import_jsx_runtime20.jsx)("span", { "aria-live": "polite", children: count ? `\u7B2C ${current} / ${count} \u9875` : "\u6682\u65E0\u5206\u9875" }),
    /* @__PURE__ */ (0, import_jsx_runtime20.jsx)(Button, { size: "sm", disabled: current >= count, onClick: () => onPageChange(current + 1), children: "\u4E0B\u4E00\u9875" }),
    /* @__PURE__ */ (0, import_jsx_runtime20.jsx)(Button, { size: "sm", disabled: current >= count, onClick: () => onPageChange(count), children: "\u672B\u9875" })
  ] });
});

// packages/ui/src/components/Popover.tsx
var import_react22 = require("react");
var import_jsx_runtime21 = require("react/jsx-runtime");
var Popover = (0, import_react22.forwardRef)(function Popover2({ label, trigger, open, defaultOpen = false, onOpenChange, density, surfaceMode, className, children, ...rest }, ref) {
  const attrs = useThemeAttributes({ density, surfaceMode }), id = (0, import_react22.useId)();
  const root = (0, import_react22.useRef)(null), button = (0, import_react22.useRef)(null), content = (0, import_react22.useRef)(null), merged = useMergedRef(ref, root);
  const [shown, setShown] = useControllable(open, defaultOpen, onOpenChange);
  const setter = (0, import_react22.useRef)(setShown);
  setter.current = setShown;
  (0, import_react22.useEffect)(() => {
    if (!shown) return;
    content.current?.querySelector('input,select,button,a[href],[tabindex="0"]')?.focus();
    const close = (e) => {
      if (e.target instanceof Node && !root.current?.contains(e.target)) setter.current(false);
    };
    document.addEventListener("pointerdown", close);
    return () => document.removeEventListener("pointerdown", close);
  }, [shown]);
  return /* @__PURE__ */ (0, import_jsx_runtime21.jsxs)("div", { ...rest, ...attrs, ref: merged, className: cx("qk-popover-root", className), onBlur: (e) => {
    if (e.relatedTarget && !e.currentTarget.contains(e.relatedTarget)) setShown(false);
  }, onKeyDown: (e) => {
    if (e.key === "Escape" && shown) {
      e.stopPropagation();
      setShown(false);
      button.current?.focus();
    }
  }, children: [
    /* @__PURE__ */ (0, import_jsx_runtime21.jsx)(Button, { ref: button, "aria-expanded": shown, "aria-controls": id, onClick: () => setShown(!shown), children: trigger }),
    shown && /* @__PURE__ */ (0, import_jsx_runtime21.jsx)("div", { ref: content, id, role: "region", "aria-label": label, className: "qk-popover", children })
  ] });
});

// packages/ui/src/components/ProgressBar.tsx
var import_react23 = require("react");
var import_jsx_runtime22 = require("react/jsx-runtime");
var ProgressBar = (0, import_react23.forwardRef)(function ProgressBar2({ value, label, showValue = true, density, surfaceMode, className, ...rest }, ref) {
  const attrs = useThemeAttributes({ density, surfaceMode }), n = Number.isFinite(value) ? Math.max(0, Math.min(100, value)) : 0;
  return /* @__PURE__ */ (0, import_jsx_runtime22.jsxs)("span", { ...attrs, className: cx("qk-progress", className), children: [
    /* @__PURE__ */ (0, import_jsx_runtime22.jsx)("progress", { ...rest, ref, max: 100, value: n, "aria-label": label }),
    showValue && /* @__PURE__ */ (0, import_jsx_runtime22.jsxs)("span", { "aria-hidden": "true", children: [
      n,
      "%"
    ] })
  ] });
});

// packages/ui/src/components/Skeleton.tsx
var import_react24 = require("react");
var import_jsx_runtime23 = require("react/jsx-runtime");
var Skeleton = (0, import_react24.forwardRef)(function Skeleton2({ lines = 3, label = "\u6B63\u5728\u52A0\u8F7D", density, surfaceMode, className, ...rest }, ref) {
  const attrs = useThemeAttributes({ density, surfaceMode });
  return /* @__PURE__ */ (0, import_jsx_runtime23.jsxs)("div", { ...rest, ...attrs, ref, className: cx("qk-skeleton", className), role: "status", "aria-label": label, children: [
    /* @__PURE__ */ (0, import_jsx_runtime23.jsx)("span", { className: "qk-sr-only", children: label }),
    Array.from({ length: lines }, (_, i) => /* @__PURE__ */ (0, import_jsx_runtime23.jsx)("span", { "aria-hidden": "true" }, i))
  ] });
});

// packages/ui/src/components/StatTile.tsx
var import_react25 = require("react");
var import_jsx_runtime24 = require("react/jsx-runtime");
var StatTile = (0, import_react25.forwardRef)(function StatTile2({ label, value, hint, density, surfaceMode, className, ...rest }, ref) {
  const attrs = useThemeAttributes({ density, surfaceMode });
  return /* @__PURE__ */ (0, import_jsx_runtime24.jsxs)("div", { ...rest, ...attrs, ref, className: cx("qk-stat", className), children: [
    /* @__PURE__ */ (0, import_jsx_runtime24.jsx)("span", { className: "qk-muted", children: label }),
    /* @__PURE__ */ (0, import_jsx_runtime24.jsx)("strong", { children: value }),
    hint && /* @__PURE__ */ (0, import_jsx_runtime24.jsx)("small", { className: "qk-muted", children: hint })
  ] });
});

// packages/ui/src/components/StatusDot.tsx
var import_react26 = require("react");
var import_jsx_runtime25 = require("react/jsx-runtime");
var StatusDot = (0, import_react26.forwardRef)(function StatusDot2({ status, label, density, surfaceMode, className, ...rest }, ref) {
  const attrs = useThemeAttributes({ density, surfaceMode }), Icon = statusIcons[status];
  return /* @__PURE__ */ (0, import_jsx_runtime25.jsxs)("span", { ...rest, ...attrs, ref, className: cx("qk-status-dot", className), children: [
    /* @__PURE__ */ (0, import_jsx_runtime25.jsx)(Icon, { "aria-hidden": "true", className: "qk-icon" }),
    label
  ] });
});

// packages/ui/src/components/Tag.tsx
var import_react27 = require("react");
var import_lucide_react9 = require("lucide-react");
var import_jsx_runtime26 = require("react/jsx-runtime");
var Tag = (0, import_react27.forwardRef)(function Tag2({ label, onRemove, density, surfaceMode, className, ...rest }, ref) {
  const attrs = useThemeAttributes({ density, surfaceMode });
  return /* @__PURE__ */ (0, import_jsx_runtime26.jsxs)("span", { ...rest, ...attrs, ref, className: cx("qk-tag", className), children: [
    label,
    onRemove && /* @__PURE__ */ (0, import_jsx_runtime26.jsx)("button", { type: "button", className: "qk-icon-button", "aria-label": `\u79FB\u9664${label}`, onClick: onRemove, children: /* @__PURE__ */ (0, import_jsx_runtime26.jsx)(import_lucide_react9.X, { "aria-hidden": "true", className: "qk-icon" }) })
  ] });
});

// packages/ui/src/components/ThemeProvider.tsx
var import_react28 = require("react");
var import_jsx_runtime27 = require("react/jsx-runtime");
var ThemeProvider = (0, import_react28.forwardRef)(function ThemeProvider2({ theme, density, surfaceMode, accentHue, radiusScale, className, children, ...rest }, ref) {
  const settings = normalizeTheme({ theme, density, surfaceMode, accentHue, radiusScale });
  return /* @__PURE__ */ (0, import_jsx_runtime27.jsx)(ThemeContext.Provider, { value: settings, children: /* @__PURE__ */ (0, import_jsx_runtime27.jsx)("div", { ...rest, ...themeAttributes(settings), ref, className: cx("qk-theme", className), children }) });
});

// packages/ui/src/components/Toast.tsx
var import_react29 = require("react");
var import_lucide_react10 = require("lucide-react");
var import_jsx_runtime28 = require("react/jsx-runtime");
var Toast = (0, import_react29.forwardRef)(function Toast2({ open, onDismiss, status = "info", duration = parseFloat(uiTokens["feedback-duration"]), title, density, surfaceMode, className, children, ...rest }, ref) {
  const attrs = useThemeAttributes({ density, surfaceMode }), Icon = statusIcons[status];
  const [hovered, setHovered] = (0, import_react29.useState)(false), [focused, setFocused] = (0, import_react29.useState)(false);
  const paused = hovered || focused;
  const dismiss = (0, import_react29.useRef)(onDismiss);
  dismiss.current = onDismiss;
  (0, import_react29.useEffect)(() => {
    if (!open || paused || duration <= 0) return;
    const t = window.setTimeout(() => dismiss.current(), duration);
    return () => window.clearTimeout(t);
  }, [open, paused, duration]);
  if (!open) return null;
  return /* @__PURE__ */ (0, import_jsx_runtime28.jsxs)("div", { ...rest, ...attrs, ref, className: cx("qk-toast", className), role: status === "danger" ? "alert" : "status", "aria-atomic": "true", onMouseEnter: () => setHovered(true), onMouseLeave: () => setHovered(false), onFocus: () => setFocused(true), onBlur: (e) => {
    if (!e.currentTarget.contains(e.relatedTarget)) setFocused(false);
  }, children: [
    /* @__PURE__ */ (0, import_jsx_runtime28.jsx)(Icon, { className: "qk-icon", "aria-hidden": "true" }),
    /* @__PURE__ */ (0, import_jsx_runtime28.jsxs)("div", { children: [
      /* @__PURE__ */ (0, import_jsx_runtime28.jsx)("strong", { children: title }),
      children && /* @__PURE__ */ (0, import_jsx_runtime28.jsx)("div", { className: "qk-muted", children })
    ] }),
    /* @__PURE__ */ (0, import_jsx_runtime28.jsx)(Button, { variant: "ghost", size: "sm", "aria-label": "\u5173\u95ED\u901A\u77E5", onClick: onDismiss, children: /* @__PURE__ */ (0, import_jsx_runtime28.jsx)(import_lucide_react10.X, { "aria-hidden": "true", className: "qk-icon" }) })
  ] });
});

// packages/ui/src/components/Tooltip.tsx
var import_react30 = require("react");
var import_jsx_runtime29 = require("react/jsx-runtime");
var Tooltip = (0, import_react30.forwardRef)(function Tooltip2({ content, children, density, surfaceMode, className, onMouseEnter, onMouseLeave, onFocus, onBlur, onKeyDown, ...rest }, ref) {
  const attrs = useThemeAttributes({ density, surfaceMode }), id = (0, import_react30.useId)();
  const [hovered, setHovered] = (0, import_react30.useState)(false), [focused, setFocused] = (0, import_react30.useState)(false), [dismissed, setDismissed] = (0, import_react30.useState)(false);
  const open = (hovered || focused) && !dismissed;
  return /* @__PURE__ */ (0, import_jsx_runtime29.jsxs)("span", { ...rest, ...attrs, ref, className: cx("qk-tooltip-root", className), onMouseEnter: (e) => {
    setHovered(true);
    setDismissed(false);
    onMouseEnter?.(e);
  }, onMouseLeave: (e) => {
    setHovered(false);
    onMouseLeave?.(e);
  }, onFocus: (e) => {
    setFocused(true);
    setDismissed(false);
    onFocus?.(e);
  }, onBlur: (e) => {
    if (!e.currentTarget.contains(e.relatedTarget)) setFocused(false);
    onBlur?.(e);
  }, onKeyDown: (e) => {
    onKeyDown?.(e);
    if (!e.defaultPrevented && e.key === "Escape" && open) {
      setDismissed(true);
      e.stopPropagation();
    }
  }, children: [
    (0, import_react30.cloneElement)(children, { "aria-describedby": [children.props["aria-describedby"], open ? id : void 0].filter(Boolean).join(" ") || void 0 }),
    open && /* @__PURE__ */ (0, import_jsx_runtime29.jsx)("span", { id, role: "tooltip", className: "qk-tooltip", children: content })
  ] });
});

// packages/ui/src/blocks/ActivityFeed.tsx
var import_react31 = require("react");
var import_jsx_runtime30 = require("react/jsx-runtime");
var ActivityFeed = (0, import_react31.forwardRef)(function ActivityFeed2({ title, description, items, variant = "feed", loading = false, density, surfaceMode }, ref) {
  const attrs = useThemeAttributes({ density, surfaceMode }), id = (0, import_react31.useId)();
  return /* @__PURE__ */ (0, import_jsx_runtime30.jsxs)("section", { ...attrs, ref, "data-block": "ActivityFeed", className: "qk-panel qk-activity", "aria-labelledby": id, children: [
    /* @__PURE__ */ (0, import_jsx_runtime30.jsxs)("header", { className: "qk-panel-heading", children: [
      /* @__PURE__ */ (0, import_jsx_runtime30.jsxs)("div", { children: [
        /* @__PURE__ */ (0, import_jsx_runtime30.jsx)("h2", { id, children: title }),
        description && /* @__PURE__ */ (0, import_jsx_runtime30.jsx)("p", { className: "qk-muted qk-description", children: description })
      ] }),
      /* @__PURE__ */ (0, import_jsx_runtime30.jsxs)("span", { className: "qk-muted", children: [
        items.length,
        " \u6761"
      ] })
    ] }),
    loading ? /* @__PURE__ */ (0, import_jsx_runtime30.jsx)(Skeleton, { label: "\u6B63\u5728\u52A0\u8F7D\u52A8\u6001" }) : !items.length ? /* @__PURE__ */ (0, import_jsx_runtime30.jsx)(EmptyState, { title: "\u6682\u65E0\u8BB0\u5F55", description: "\u540E\u7EED\u8FDB\u5C55\u4F1A\u663E\u793A\u5728\u8FD9\u91CC\u3002" }) : /* @__PURE__ */ (0, import_jsx_runtime30.jsx)("ol", { className: cx("qk-activity-list", variant === "timeline" && "qk-timeline"), children: items.map((item) => /* @__PURE__ */ (0, import_jsx_runtime30.jsxs)("li", { children: [
      /* @__PURE__ */ (0, import_jsx_runtime30.jsx)("div", { className: "qk-activity-marker", "aria-hidden": "true" }),
      /* @__PURE__ */ (0, import_jsx_runtime30.jsxs)("div", { className: "qk-activity-copy", children: [
        /* @__PURE__ */ (0, import_jsx_runtime30.jsxs)("div", { children: [
          /* @__PURE__ */ (0, import_jsx_runtime30.jsx)("strong", { children: item.title }),
          /* @__PURE__ */ (0, import_jsx_runtime30.jsx)(Badge, { status: item.status, children: item.statusLabel })
        ] }),
        /* @__PURE__ */ (0, import_jsx_runtime30.jsx)("p", { children: item.detail }),
        /* @__PURE__ */ (0, import_jsx_runtime30.jsxs)("small", { children: [
          item.actor,
          " \xB7 ",
          /* @__PURE__ */ (0, import_jsx_runtime30.jsx)("time", { children: item.time })
        ] })
      ] }),
      item.onOpen && /* @__PURE__ */ (0, import_jsx_runtime30.jsx)(Button, { size: "sm", variant: "ghost", onClick: item.onOpen, children: "\u67E5\u770B\u8BE6\u60C5" })
    ] }, item.id)) })
  ] });
});

// packages/ui/src/blocks/BreakdownPanel.tsx
var import_react32 = require("react");
var import_jsx_runtime31 = require("react/jsx-runtime");
var BreakdownPanel = (0, import_react32.forwardRef)(function BreakdownPanel2({ title, description, unit, items, onSelect, loading = false, ...theme }, ref) {
  const total = items.reduce((s, x) => s + Math.max(0, x.value), 0);
  return /* @__PURE__ */ (0, import_jsx_runtime31.jsx)(ChartCard, { ...theme, ref, "data-block": "BreakdownPanel", title, description, children: loading ? /* @__PURE__ */ (0, import_jsx_runtime31.jsx)(Skeleton, { label: "\u6B63\u5728\u52A0\u8F7D\u5206\u5E03" }) : !items.length ? /* @__PURE__ */ (0, import_jsx_runtime31.jsx)(EmptyState, { title: "\u6682\u65E0\u5206\u7C7B\u6570\u636E" }) : /* @__PURE__ */ (0, import_jsx_runtime31.jsxs)("div", { className: "qk-breakdown", children: [
    items.map((item) => /* @__PURE__ */ (0, import_jsx_runtime31.jsxs)("div", { className: "qk-breakdown-row", children: [
      /* @__PURE__ */ (0, import_jsx_runtime31.jsxs)("div", { children: [
        onSelect ? /* @__PURE__ */ (0, import_jsx_runtime31.jsx)(Button, { variant: "ghost", size: "sm", onClick: () => onSelect(item.id), children: item.label }) : /* @__PURE__ */ (0, import_jsx_runtime31.jsx)("span", { children: item.label }),
        /* @__PURE__ */ (0, import_jsx_runtime31.jsxs)("strong", { children: [
          item.value,
          /* @__PURE__ */ (0, import_jsx_runtime31.jsx)("small", { children: unit })
        ] })
      ] }),
      /* @__PURE__ */ (0, import_jsx_runtime31.jsx)(ProgressBar, { label: `${item.label}\u5360\u6BD4`, value: total ? Math.round(Math.max(0, item.value) / total * 100) : 0, showValue: false })
    ] }, item.id)),
    /* @__PURE__ */ (0, import_jsx_runtime31.jsxs)("p", { className: "qk-muted", children: [
      "\u5408\u8BA1 ",
      total,
      " ",
      unit,
      onSelect ? " \xB7 \u70B9\u51FB\u5206\u7C7B\u67E5\u770B\u9879\u76EE" : ""
    ] })
  ] }) });
});

// packages/ui/src/blocks/DangerZone.tsx
var import_react33 = require("react");
var import_lucide_react11 = require("lucide-react");
var import_jsx_runtime32 = require("react/jsx-runtime");
var DangerZone = (0, import_react33.forwardRef)(function DangerZone2({ title, description, actionLabel, confirmText, confirmDescription, onConfirm, disabled = false, density, surfaceMode }, ref) {
  const attrs = useThemeAttributes({ density, surfaceMode }), [open, setOpen] = (0, import_react33.useState)(false), [value, setValue] = (0, import_react33.useState)(""), [pending, setPending] = (0, import_react33.useState)(false), [error, setError] = (0, import_react33.useState)("");
  const running = (0, import_react33.useRef)(false);
  const confirm = async () => {
    if (running.current || disabled || value !== confirmText || !confirmText.trim()) return;
    running.current = true;
    setPending(true);
    setError("");
    try {
      await onConfirm();
      setOpen(false);
    } catch {
      setError("\u64CD\u4F5C\u672A\u5B8C\u6210\uFF0C\u8BF7\u6838\u5BF9\u7ED3\u679C\u540E\u91CD\u8BD5\u3002");
    } finally {
      running.current = false;
      setPending(false);
    }
  };
  return /* @__PURE__ */ (0, import_jsx_runtime32.jsxs)("section", { ...attrs, ref, "data-block": "DangerZone", className: "qk-danger-zone", children: [
    /* @__PURE__ */ (0, import_jsx_runtime32.jsxs)("div", { children: [
      /* @__PURE__ */ (0, import_jsx_runtime32.jsxs)("h2", { children: [
        /* @__PURE__ */ (0, import_jsx_runtime32.jsx)(import_lucide_react11.TriangleAlert, { className: "qk-icon", "aria-hidden": "true" }),
        title
      ] }),
      /* @__PURE__ */ (0, import_jsx_runtime32.jsx)("p", { children: description })
    ] }),
    /* @__PURE__ */ (0, import_jsx_runtime32.jsx)(Button, { className: "qk-danger-button", disabled: disabled || !confirmText.trim(), onClick: () => {
      setValue("");
      setError("");
      setOpen(true);
    }, children: actionLabel }),
    /* @__PURE__ */ (0, import_jsx_runtime32.jsxs)(Dialog, { title: actionLabel, description: confirmDescription, open, onOpenChange: (next) => {
      if (!running.current) setOpen(next);
    }, footer: /* @__PURE__ */ (0, import_jsx_runtime32.jsxs)(import_jsx_runtime32.Fragment, { children: [
      /* @__PURE__ */ (0, import_jsx_runtime32.jsx)(Button, { disabled: pending, onClick: () => setOpen(false), children: "\u53D6\u6D88" }),
      /* @__PURE__ */ (0, import_jsx_runtime32.jsxs)(Button, { className: "qk-danger-button", loading: pending, disabled: value !== confirmText || disabled || !confirmText.trim(), onClick: confirm, children: [
        "\u786E\u8BA4",
        actionLabel
      ] })
    ] }), children: [
      /* @__PURE__ */ (0, import_jsx_runtime32.jsx)(Input, { label: `\u8BF7\u8F93\u5165\u201C${confirmText}\u201D\u4EE5\u786E\u8BA4`, disabled: pending, value, onChange: (e) => setValue(e.target.value), autoComplete: "off" }),
      error && /* @__PURE__ */ (0, import_jsx_runtime32.jsx)("p", { className: "qk-error qk-description", role: "alert", children: error })
    ] })
  ] });
});

// packages/ui/src/blocks/EntitySummary.tsx
var import_react36 = require("react");

// packages/ui/src/blocks/KpiRow.tsx
var import_react34 = require("react");
var import_lucide_react12 = require("lucide-react");
var import_jsx_runtime33 = require("react/jsx-runtime");
var import_react35 = require("react");
function InsightNote({ insight }) {
  return /* @__PURE__ */ (0, import_jsx_runtime33.jsxs)("div", { className: "qk-insight", children: [
    /* @__PURE__ */ (0, import_jsx_runtime33.jsx)(import_lucide_react12.Sparkles, { className: "qk-icon", "aria-hidden": "true" }),
    /* @__PURE__ */ (0, import_jsx_runtime33.jsxs)("div", { children: [
      /* @__PURE__ */ (0, import_jsx_runtime33.jsxs)("strong", { children: [
        "AI \u6458\u8981\u793A\u4F8B ",
        /* @__PURE__ */ (0, import_jsx_runtime33.jsx)("span", { children: "\u9700\u8D1F\u8D23\u4EBA\u786E\u8BA4" })
      ] }),
      /* @__PURE__ */ (0, import_jsx_runtime33.jsx)("p", { children: insight.text }),
      /* @__PURE__ */ (0, import_jsx_runtime33.jsx)("small", { children: insight.source })
    ] }),
    insight.onReview && /* @__PURE__ */ (0, import_jsx_runtime33.jsxs)(Button, { size: "sm", variant: "ghost", onClick: insight.onReview, children: [
      insight.actionLabel || "\u67E5\u770B\u4F9D\u636E",
      /* @__PURE__ */ (0, import_jsx_runtime33.jsx)(import_lucide_react12.ArrowUpRight, { className: "qk-icon", "aria-hidden": "true" })
    ] })
  ] });
}
var KpiRow = (0, import_react34.forwardRef)(function KpiRow2({ items, theme, insight, loading = false, density, surfaceMode }, ref) {
  const attrs = useThemeAttributes({ density, surfaceMode });
  return /* @__PURE__ */ (0, import_jsx_runtime33.jsxs)("section", { ...attrs, ref, "data-block": "KpiRow", "aria-label": "\u56DB\u9879\u6838\u5FC3\u6307\u6807", className: "qk-kpi-block", children: [
    /* @__PURE__ */ (0, import_jsx_runtime33.jsx)("div", { className: "qk-kpi-row", "data-layout": theme, children: items.map((item, i) => loading ? /* @__PURE__ */ (0, import_jsx_runtime33.jsx)("div", { className: "qk-panel", children: /* @__PURE__ */ (0, import_jsx_runtime33.jsx)(Skeleton, { label: `${item.label}\u6B63\u5728\u52A0\u8F7D` }) }, item.label) : /* @__PURE__ */ (0, import_react35.createElement)(KpiCard, { ...item, key: item.label, emphasis: theme === "bento" && i === 0 })) }),
    insight && !loading && /* @__PURE__ */ (0, import_jsx_runtime33.jsx)(InsightNote, { insight })
  ] });
});

// packages/ui/src/blocks/EntitySummary.tsx
var import_jsx_runtime34 = require("react/jsx-runtime");
var EntitySummary = (0, import_react36.forwardRef)(function EntitySummary2({ title, description, status, statusLabel, fields, progress, insight, loading = false, density, surfaceMode }, ref) {
  const attrs = useThemeAttributes({ density, surfaceMode }), id = (0, import_react36.useId)();
  return /* @__PURE__ */ (0, import_jsx_runtime34.jsxs)("section", { ...attrs, ref, "data-block": "EntitySummary", className: "qk-panel qk-entity-summary", "aria-labelledby": id, children: [
    /* @__PURE__ */ (0, import_jsx_runtime34.jsxs)("header", { className: "qk-panel-heading", children: [
      /* @__PURE__ */ (0, import_jsx_runtime34.jsxs)("div", { children: [
        /* @__PURE__ */ (0, import_jsx_runtime34.jsx)("h2", { id, children: title }),
        /* @__PURE__ */ (0, import_jsx_runtime34.jsx)("p", { className: "qk-muted qk-description", children: description })
      ] }),
      /* @__PURE__ */ (0, import_jsx_runtime34.jsx)(Badge, { status, children: statusLabel })
    ] }),
    loading ? /* @__PURE__ */ (0, import_jsx_runtime34.jsx)(Skeleton, { label: "\u6B63\u5728\u52A0\u8F7D\u9879\u76EE\u6982\u51B5" }) : /* @__PURE__ */ (0, import_jsx_runtime34.jsx)("dl", { children: fields.map((f) => /* @__PURE__ */ (0, import_jsx_runtime34.jsxs)("div", { children: [
      /* @__PURE__ */ (0, import_jsx_runtime34.jsx)("dt", { children: f.label }),
      /* @__PURE__ */ (0, import_jsx_runtime34.jsx)("dd", { children: f.value })
    ] }, f.label)) }),
    !loading && progress !== void 0 && /* @__PURE__ */ (0, import_jsx_runtime34.jsxs)("div", { className: "qk-summary-progress", children: [
      /* @__PURE__ */ (0, import_jsx_runtime34.jsx)("span", { children: "\u4EA4\u4ED8\u8FDB\u5EA6" }),
      /* @__PURE__ */ (0, import_jsx_runtime34.jsx)(ProgressBar, { label: "\u4EA4\u4ED8\u8FDB\u5EA6", value: progress })
    ] }),
    !loading && insight && /* @__PURE__ */ (0, import_jsx_runtime34.jsx)(InsightNote, { insight })
  ] });
});

// packages/ui/src/blocks/PaginationBar.tsx
var import_react37 = require("react");
var import_jsx_runtime35 = require("react/jsx-runtime");
var PaginationBar = (0, import_react37.forwardRef)(function PaginationBar2({ page, pageSize, total, selectedCount = 0, onPageChange, onPageSizeChange, density, surfaceMode }, ref) {
  const attrs = useThemeAttributes({ density, surfaceMode }), count = Math.ceil(total / pageSize);
  return /* @__PURE__ */ (0, import_jsx_runtime35.jsxs)("div", { ...attrs, ref, "data-block": "PaginationBar", className: "qk-pagination-bar", children: [
    /* @__PURE__ */ (0, import_jsx_runtime35.jsxs)("p", { className: "qk-muted", "aria-live": "polite", children: [
      "\u5171 ",
      total,
      " \u6761 \xB7 \u5DF2\u9009\u62E9 ",
      selectedCount,
      " \u6761"
    ] }),
    /* @__PURE__ */ (0, import_jsx_runtime35.jsx)(Select, { label: "\u6BCF\u9875\u6761\u6570", value: pageSize, onChange: (e) => onPageSizeChange(Number(e.target.value)), options: [{ value: "5", label: "5 \u6761 / \u9875" }, { value: "10", label: "10 \u6761 / \u9875" }, { value: "20", label: "20 \u6761 / \u9875" }] }),
    /* @__PURE__ */ (0, import_jsx_runtime35.jsx)(Pagination, { page, pageCount: count, onPageChange })
  ] });
});

// packages/ui/src/blocks/QueryBar.tsx
var import_react38 = require("react");
var import_jsx_runtime36 = require("react/jsx-runtime");
var QueryBar = (0, import_react38.forwardRef)(function QueryBar2(props, ref) {
  return /* @__PURE__ */ (0, import_jsx_runtime36.jsx)(FilterBar, { ...props, ref, "data-block": "QueryBar", className: "qk-panel qk-query-block" });
});

// packages/ui/src/blocks/RecordTable.tsx
var import_react39 = require("react");
var import_jsx_runtime37 = require("react/jsx-runtime");
function RecordTableInner({ onClearSelection, total, ...props }, ref) {
  const attrs = useThemeAttributes({ density: props.density, surfaceMode: props.surfaceMode });
  return /* @__PURE__ */ (0, import_jsx_runtime37.jsxs)("div", { ...attrs, "data-block": "RecordTable", className: "qk-record-block", ref, children: [
    /* @__PURE__ */ (0, import_jsx_runtime37.jsxs)("div", { className: "qk-record-heading", children: [
      /* @__PURE__ */ (0, import_jsx_runtime37.jsx)("h2", { children: props.label }),
      /* @__PURE__ */ (0, import_jsx_runtime37.jsxs)("span", { className: "qk-muted", children: [
        "\u5171 ",
        total,
        " \u6761\u8BB0\u5F55"
      ] }),
      !!props.selectedIds?.length && /* @__PURE__ */ (0, import_jsx_runtime37.jsxs)(Button, { size: "sm", variant: "ghost", onClick: onClearSelection, children: [
        "\u6E05\u9664\u9009\u62E9\uFF08",
        props.selectedIds.length,
        "\uFF09"
      ] })
    ] }),
    /* @__PURE__ */ (0, import_jsx_runtime37.jsx)(DataTable, { ...props, showToolbar: false, showFooter: false, selectionLabel: "\u9009\u62E9\u5F53\u524D\u9875\u5168\u90E8\u884C", selectable: !!props.onSelectionChange, virtual: false }),
    /* @__PURE__ */ (0, import_jsx_runtime37.jsx)("p", { className: "qk-scroll-hint", children: "\u5DE6\u53F3\u6ED1\u52A8\u67E5\u770B\u5168\u90E8\u5B57\u6BB5" })
  ] });
}
var RecordTable = (0, import_react39.forwardRef)(RecordTableInner);

// packages/ui/src/blocks/RelatedRecords.tsx
var import_react40 = require("react");
var import_jsx_runtime38 = require("react/jsx-runtime");
function RelatedRecordsInner({ title, description, ...props }, ref) {
  const attrs = useThemeAttributes({ density: props.density, surfaceMode: props.surfaceMode });
  return /* @__PURE__ */ (0, import_jsx_runtime38.jsxs)("div", { ...attrs, ref, "data-block": "RelatedRecords", className: "qk-related-block", children: [
    /* @__PURE__ */ (0, import_jsx_runtime38.jsxs)("header", { children: [
      /* @__PURE__ */ (0, import_jsx_runtime38.jsx)("h2", { children: title }),
      /* @__PURE__ */ (0, import_jsx_runtime38.jsx)("p", { className: "qk-muted", children: description })
    ] }),
    /* @__PURE__ */ (0, import_jsx_runtime38.jsx)(DataTable, { ...props, label: title, showToolbar: false, showFooter: false, virtual: false })
  ] });
}
var RelatedRecords = (0, import_react40.forwardRef)(RelatedRecordsInner);

// packages/ui/src/blocks/SettingsNav.tsx
var import_react41 = require("react");
var import_lucide_react13 = require("lucide-react");
var import_jsx_runtime39 = require("react/jsx-runtime");
var SettingsNav = (0, import_react41.forwardRef)(function SettingsNav2({ items, activeId, onSelect, density, surfaceMode }, ref) {
  const attrs = useThemeAttributes({ density, surfaceMode });
  return /* @__PURE__ */ (0, import_jsx_runtime39.jsx)("nav", { ...attrs, ref, "data-block": "SettingsNav", className: "qk-settings-nav", "aria-label": "\u8BBE\u7F6E\u5206\u7EC4", children: items.map((item) => /* @__PURE__ */ (0, import_jsx_runtime39.jsxs)("a", { href: "#" + item.id, "aria-current": item.id === activeId ? "location" : void 0, onClick: (e) => {
    e.preventDefault();
    onSelect(item.id);
    document.getElementById(item.id)?.scrollIntoView({ block: "start", behavior: "auto" });
  }, children: [
    /* @__PURE__ */ (0, import_jsx_runtime39.jsxs)("span", { children: [
      /* @__PURE__ */ (0, import_jsx_runtime39.jsx)("strong", { children: item.label }),
      /* @__PURE__ */ (0, import_jsx_runtime39.jsx)("small", { children: item.description })
    ] }),
    /* @__PURE__ */ (0, import_jsx_runtime39.jsx)(import_lucide_react13.ChevronRight, { className: "qk-icon", "aria-hidden": "true" })
  ] }, item.id)) });
});

// packages/ui/src/blocks/SettingsSection.tsx
var import_react42 = require("react");
var import_jsx_runtime40 = require("react/jsx-runtime");
var SettingsSection = (0, import_react42.forwardRef)(function SettingsSection2({ id, title, description, fields, density, surfaceMode }, ref) {
  const attrs = useThemeAttributes({ density, surfaceMode });
  return /* @__PURE__ */ (0, import_jsx_runtime40.jsxs)("section", { ...attrs, ref, id, "data-block": "SettingsSection", className: "qk-panel qk-settings-section", "aria-labelledby": id + "-title", children: [
    /* @__PURE__ */ (0, import_jsx_runtime40.jsxs)("header", { children: [
      /* @__PURE__ */ (0, import_jsx_runtime40.jsx)("h2", { id: id + "-title", children: title }),
      /* @__PURE__ */ (0, import_jsx_runtime40.jsx)("p", { className: "qk-muted", children: description })
    ] }),
    /* @__PURE__ */ (0, import_jsx_runtime40.jsx)("div", { className: "qk-settings-fields", children: fields.map((f) => f.kind === "checkbox" ? /* @__PURE__ */ (0, import_jsx_runtime40.jsxs)("div", { className: "qk-settings-toggle", children: [
      /* @__PURE__ */ (0, import_jsx_runtime40.jsx)(Checkbox, { id: f.id, label: f.label, checked: f.value, disabled: f.disabled, onChange: (e) => f.onChange(e.target.checked), "aria-describedby": f.hint ? f.id + "-hint" : void 0 }),
      f.hint && /* @__PURE__ */ (0, import_jsx_runtime40.jsx)("p", { id: f.id + "-hint", className: "qk-muted", children: f.hint })
    ] }, f.id) : f.kind === "select" ? /* @__PURE__ */ (0, import_jsx_runtime40.jsx)(Select, { id: f.id, label: f.label, value: f.value, options: f.options, hint: f.hint, error: f.error, disabled: f.disabled, onChange: (e) => f.onChange(e.target.value) }, f.id) : /* @__PURE__ */ (0, import_jsx_runtime40.jsx)(Input, { id: f.id, label: f.label, type: f.type || "text", value: f.value, hint: f.hint, error: f.error, disabled: f.disabled, required: f.required, maxLength: f.maxLength, onChange: (e) => f.onChange(e.target.value) }, f.id)) })
  ] });
});

// packages/ui/src/blocks/TrendPanel.tsx
var import_react43 = require("react");
var import_jsx_runtime41 = require("react/jsx-runtime");
var TrendPanel = (0, import_react43.forwardRef)(function TrendPanel2({ title, description, unit, points, loading = false, ...theme }, ref) {
  const id = (0, import_react43.useId)();
  const invalid = points.some((p) => !Number.isFinite(p.value) || p.target !== void 0 && !Number.isFinite(p.target));
  const values = points.flatMap((p) => [p.value, ...p.target === void 0 ? [] : [p.target]]);
  const min = invalid ? 0 : Math.floor(Math.min(0, ...values) / 10) * 10;
  const max = invalid ? 10 : Math.ceil(Math.max(1, ...values) / 10) * 10;
  const xy = (v, i) => [52 + i * 624 / Math.max(1, points.length - 1), 192 - (v - min) / (max - min) * 152];
  const line = points.map((p, i) => xy(p.value, i).join(",")).join(" ");
  const hasTarget = points.length > 0 && points.every((p) => p.target !== void 0);
  const target = points.map((p, i) => xy(p.target ?? 0, i).join(",")).join(" ");
  return /* @__PURE__ */ (0, import_jsx_runtime41.jsx)(ChartCard, { ...theme, ref, "data-block": "TrendPanel", title, description, legend: /* @__PURE__ */ (0, import_jsx_runtime41.jsxs)(import_jsx_runtime41.Fragment, { children: [
    /* @__PURE__ */ (0, import_jsx_runtime41.jsxs)("span", { children: [
      /* @__PURE__ */ (0, import_jsx_runtime41.jsx)("i", { className: "qk-line-key" }),
      "\u5B9E\u9645 \xB7 \u5B9E\u7EBF"
    ] }),
    hasTarget && /* @__PURE__ */ (0, import_jsx_runtime41.jsxs)("span", { children: [
      /* @__PURE__ */ (0, import_jsx_runtime41.jsx)("i", { className: "qk-line-key qk-line-target" }),
      "\u8BA1\u5212 \xB7 \u865A\u7EBF"
    ] }),
    /* @__PURE__ */ (0, import_jsx_runtime41.jsxs)("span", { children: [
      "\u5355\u4F4D\uFF1A",
      unit
    ] })
  ] }), children: loading ? /* @__PURE__ */ (0, import_jsx_runtime41.jsx)(Skeleton, { label: "\u6B63\u5728\u52A0\u8F7D\u8D8B\u52BF" }) : invalid ? /* @__PURE__ */ (0, import_jsx_runtime41.jsx)(EmptyState, { title: "\u8D8B\u52BF\u6570\u636E\u683C\u5F0F\u6709\u8BEF", description: "\u5B58\u5728\u65E0\u6548\u6570\u503C\uFF0C\u8BF7\u6838\u5BF9\u6570\u636E\u6765\u6E90\u540E\u91CD\u8BD5\u3002" }) : !points.length ? /* @__PURE__ */ (0, import_jsx_runtime41.jsx)(EmptyState, { title: "\u6682\u65E0\u8D8B\u52BF\u6570\u636E" }) : /* @__PURE__ */ (0, import_jsx_runtime41.jsxs)(import_jsx_runtime41.Fragment, { children: [
    /* @__PURE__ */ (0, import_jsx_runtime41.jsx)("div", { className: "qk-trend-scroll", children: /* @__PURE__ */ (0, import_jsx_runtime41.jsxs)("svg", { className: "qk-trend-chart", viewBox: "0 0 720 228", role: "img", "aria-labelledby": id, children: [
      /* @__PURE__ */ (0, import_jsx_runtime41.jsxs)("title", { id, children: [
        title,
        "\uFF0C",
        points[0].label,
        "\u4E3A",
        points[0].value,
        unit,
        "\uFF0C",
        points.at(-1).label,
        "\u4E3A",
        points.at(-1).value,
        unit,
        "\uFF1B\u7CBE\u786E\u503C\u89C1\u4E0B\u65B9\u6570\u636E\u8868\u3002"
      ] }),
      [0, 0.5, 1].map((r) => /* @__PURE__ */ (0, import_jsx_runtime41.jsxs)("g", { children: [
        /* @__PURE__ */ (0, import_jsx_runtime41.jsx)("line", { x1: "52", x2: "690", y1: 192 - r * 152, y2: 192 - r * 152, className: "qk-chart-grid" }),
        /* @__PURE__ */ (0, import_jsx_runtime41.jsx)("text", { x: "40", y: 196 - r * 152, textAnchor: "end", children: +(min + r * (max - min)).toFixed(1) })
      ] }, r)),
      hasTarget && /* @__PURE__ */ (0, import_jsx_runtime41.jsx)("polyline", { points: target, className: "qk-trend-target" }),
      /* @__PURE__ */ (0, import_jsx_runtime41.jsx)("polyline", { points: line, className: "qk-trend-line" }),
      points.map((p, i) => {
        const [x, y] = xy(p.value, i);
        return /* @__PURE__ */ (0, import_jsx_runtime41.jsxs)("g", { children: [
          /* @__PURE__ */ (0, import_jsx_runtime41.jsx)("circle", { cx: x, cy: y, r: "3", className: "qk-trend-dot" }),
          /* @__PURE__ */ (0, import_jsx_runtime41.jsx)("text", { x, y: "218", textAnchor: "middle", children: p.label })
        ] }, i);
      })
    ] }) }),
    /* @__PURE__ */ (0, import_jsx_runtime41.jsx)("p", { className: "qk-scroll-hint", children: "\u5DE6\u53F3\u6ED1\u52A8\u67E5\u770B\u5B8C\u6574\u8D8B\u52BF" }),
    /* @__PURE__ */ (0, import_jsx_runtime41.jsxs)("details", { className: "qk-chart-values", children: [
      /* @__PURE__ */ (0, import_jsx_runtime41.jsx)("summary", { children: "\u67E5\u770B\u56FE\u8868\u6570\u636E" }),
      /* @__PURE__ */ (0, import_jsx_runtime41.jsx)("div", { children: /* @__PURE__ */ (0, import_jsx_runtime41.jsxs)("table", { children: [
        /* @__PURE__ */ (0, import_jsx_runtime41.jsxs)("caption", { className: "qk-sr-only", children: [
          title,
          "\u7CBE\u786E\u503C\uFF0C\u5355\u4F4D",
          unit
        ] }),
        /* @__PURE__ */ (0, import_jsx_runtime41.jsx)("thead", { children: /* @__PURE__ */ (0, import_jsx_runtime41.jsxs)("tr", { children: [
          /* @__PURE__ */ (0, import_jsx_runtime41.jsx)("th", { scope: "col", children: "\u671F\u95F4" }),
          /* @__PURE__ */ (0, import_jsx_runtime41.jsx)("th", { scope: "col", children: "\u5B9E\u9645" }),
          hasTarget && /* @__PURE__ */ (0, import_jsx_runtime41.jsx)("th", { scope: "col", children: "\u8BA1\u5212" })
        ] }) }),
        /* @__PURE__ */ (0, import_jsx_runtime41.jsx)("tbody", { children: points.map((p, i) => /* @__PURE__ */ (0, import_jsx_runtime41.jsxs)("tr", { children: [
          /* @__PURE__ */ (0, import_jsx_runtime41.jsx)("th", { scope: "row", children: p.label }),
          /* @__PURE__ */ (0, import_jsx_runtime41.jsx)("td", { children: p.value }),
          hasTarget && /* @__PURE__ */ (0, import_jsx_runtime41.jsx)("td", { children: p.target })
        ] }, i)) })
      ] }) })
    ] })
  ] }) });
});

// packages/ui/src/recipes/Overview.tsx
var import_react44 = require("react");
var import_jsx_runtime42 = require("react/jsx-runtime");
var Overview = (0, import_react44.forwardRef)(function Overview2({ header, kpis, trend, breakdown, activity, density, surfaceMode }, ref) {
  const attrs = useThemeAttributes({ density, surfaceMode });
  return /* @__PURE__ */ (0, import_jsx_runtime42.jsxs)("div", { ...attrs, ref, "data-recipe": "Overview", className: "qk-recipe", children: [
    /* @__PURE__ */ (0, import_jsx_runtime42.jsx)(PageHeader, { ...header }),
    /* @__PURE__ */ (0, import_jsx_runtime42.jsx)(KpiRow, { ...kpis }),
    /* @__PURE__ */ (0, import_jsx_runtime42.jsxs)("div", { className: "qk-overview-charts", children: [
      /* @__PURE__ */ (0, import_jsx_runtime42.jsx)(TrendPanel, { ...trend }),
      /* @__PURE__ */ (0, import_jsx_runtime42.jsx)(BreakdownPanel, { ...breakdown })
    ] }),
    /* @__PURE__ */ (0, import_jsx_runtime42.jsx)(ActivityFeed, { ...activity })
  ] });
});

// packages/ui/src/recipes/List.tsx
var import_react45 = require("react");
var import_jsx_runtime43 = require("react/jsx-runtime");
function ListInner({ header, query, records, pagination, density, surfaceMode }, ref) {
  const attrs = useThemeAttributes({ density, surfaceMode });
  return /* @__PURE__ */ (0, import_jsx_runtime43.jsxs)("div", { ...attrs, ref, "data-recipe": "List", className: "qk-recipe", children: [
    /* @__PURE__ */ (0, import_jsx_runtime43.jsx)(PageHeader, { ...header }),
    /* @__PURE__ */ (0, import_jsx_runtime43.jsx)(QueryBar, { ...query }),
    /* @__PURE__ */ (0, import_jsx_runtime43.jsx)(RecordTable, { ...records }),
    /* @__PURE__ */ (0, import_jsx_runtime43.jsx)(PaginationBar, { ...pagination })
  ] });
}
var List = (0, import_react45.forwardRef)(ListInner);

// packages/ui/src/recipes/Detail.tsx
var import_react46 = require("react");
var import_jsx_runtime44 = require("react/jsx-runtime");
function DetailInner({ header, summary, activity, related, activeTab, onTabChange, density, surfaceMode }, ref) {
  const attrs = useThemeAttributes({ density, surfaceMode }), id = (0, import_react46.useId)();
  const tabs = [["timeline", "\u8FDB\u5C55\u65F6\u95F4\u7EBF"], ["related", "\u5173\u8054\u8BB0\u5F55"]];
  return /* @__PURE__ */ (0, import_jsx_runtime44.jsxs)("div", { ...attrs, ref, "data-recipe": "Detail", className: "qk-recipe", children: [
    /* @__PURE__ */ (0, import_jsx_runtime44.jsx)(PageHeader, { ...header }),
    /* @__PURE__ */ (0, import_jsx_runtime44.jsx)(EntitySummary, { ...summary }),
    /* @__PURE__ */ (0, import_jsx_runtime44.jsxs)("div", { className: "qk-detail-tabs", children: [
      /* @__PURE__ */ (0, import_jsx_runtime44.jsx)("div", { role: "tablist", "aria-label": "\u9879\u76EE\u8BE6\u60C5\u89C6\u56FE", className: "qk-tab-list", onKeyDown: (e) => {
        if (!["ArrowLeft", "ArrowRight", "Home", "End"].includes(e.key)) return;
        e.preventDefault();
        const next = e.key === "Home" ? "timeline" : e.key === "End" ? "related" : activeTab === "timeline" ? "related" : "timeline";
        onTabChange(next);
        document.getElementById(id + "-" + next)?.focus();
      }, children: tabs.map(([key, label]) => /* @__PURE__ */ (0, import_jsx_runtime44.jsxs)("button", { id: id + "-" + key, role: "tab", type: "button", "aria-selected": activeTab === key, "aria-controls": id + "-panel-" + key, tabIndex: activeTab === key ? 0 : -1, onClick: () => onTabChange(key), children: [
        label,
        key === "related" && /* @__PURE__ */ (0, import_jsx_runtime44.jsx)("span", { children: related.rows.length })
      ] }, key)) }),
      /* @__PURE__ */ (0, import_jsx_runtime44.jsx)("div", { id: id + "-panel-timeline", role: "tabpanel", "aria-labelledby": id + "-timeline", tabIndex: 0, hidden: activeTab !== "timeline", children: /* @__PURE__ */ (0, import_jsx_runtime44.jsx)(ActivityFeed, { ...activity, variant: "timeline" }) }),
      /* @__PURE__ */ (0, import_jsx_runtime44.jsx)("div", { id: id + "-panel-related", role: "tabpanel", "aria-labelledby": id + "-related", tabIndex: 0, hidden: activeTab !== "related", children: /* @__PURE__ */ (0, import_jsx_runtime44.jsx)(RelatedRecords, { ...related }) })
    ] })
  ] });
}
var Detail = (0, import_react46.forwardRef)(DetailInner);

// packages/ui/src/recipes/Settings.tsx
var import_react47 = require("react");
var import_jsx_runtime45 = require("react/jsx-runtime");
var import_react48 = require("react");
var Settings = (0, import_react47.forwardRef)(function Settings2({ header, navigation, sections, danger, dirty, savedMessage, onSave, onCancel, density, surfaceMode }, ref) {
  const attrs = useThemeAttributes({ density, surfaceMode });
  return /* @__PURE__ */ (0, import_jsx_runtime45.jsxs)("div", { ...attrs, ref, "data-recipe": "Settings", className: "qk-recipe", children: [
    /* @__PURE__ */ (0, import_jsx_runtime45.jsx)(PageHeader, { ...header }),
    /* @__PURE__ */ (0, import_jsx_runtime45.jsxs)("div", { className: "qk-settings-layout", children: [
      /* @__PURE__ */ (0, import_jsx_runtime45.jsx)(SettingsNav, { ...navigation }),
      /* @__PURE__ */ (0, import_jsx_runtime45.jsxs)("div", { className: "qk-settings-main", children: [
        /* @__PURE__ */ (0, import_jsx_runtime45.jsxs)("form", { onSubmit: (e) => {
          e.preventDefault();
          onSave();
        }, className: "qk-settings-form", children: [
          sections.map((section) => /* @__PURE__ */ (0, import_react48.createElement)(SettingsSection, { ...section, key: section.id })),
          /* @__PURE__ */ (0, import_jsx_runtime45.jsxs)("div", { className: "qk-settings-save", children: [
            /* @__PURE__ */ (0, import_jsx_runtime45.jsx)("p", { role: "status", children: dirty ? "\u6709\u5C1A\u672A\u4FDD\u5B58\u7684\u66F4\u6539" : savedMessage || "\u8BBE\u7F6E\u5DF2\u4FDD\u5B58" }),
            /* @__PURE__ */ (0, import_jsx_runtime45.jsxs)("div", { className: "qk-actions", children: [
              /* @__PURE__ */ (0, import_jsx_runtime45.jsx)(Button, { disabled: !dirty, onClick: onCancel, children: "\u53D6\u6D88\u66F4\u6539" }),
              /* @__PURE__ */ (0, import_jsx_runtime45.jsx)(Button, { type: "submit", variant: "primary", disabled: !dirty, children: "\u4FDD\u5B58\u8BBE\u7F6E" })
            ] })
          ] })
        ] }),
        /* @__PURE__ */ (0, import_jsx_runtime45.jsx)(DangerZone, { ...danger })
      ] })
    ] })
  ] });
});

// packages/ui/src/recipes/catalog.ts
var recipeCatalog = [
  { id: "overview", name: "Overview", label: "\u7ECF\u8425\u603B\u89C8", sequence: ["PageHeader", "KpiRow", "TrendPanel + BreakdownPanel", "ActivityFeed"] },
  { id: "list", name: "List", label: "\u9879\u76EE\u5217\u8868", sequence: ["PageHeader", "QueryBar", "RecordTable", "PaginationBar"] },
  { id: "detail", name: "Detail", label: "\u9879\u76EE\u8BE6\u60C5", sequence: ["PageHeader", "EntitySummary", "Tabs", "ActivityFeed / RelatedRecords"] },
  { id: "settings", name: "Settings", label: "\u5DE5\u4F5C\u533A\u8BBE\u7F6E", sequence: ["PageHeader", "SettingsNav + SettingsSection", "DangerZone"] }
];
var blockCatalog = ["KpiRow", "TrendPanel", "BreakdownPanel", "ActivityFeed", "QueryBar", "RecordTable", "PaginationBar", "EntitySummary", "RelatedRecords", "SettingsNav", "SettingsSection", "DangerZone"];
