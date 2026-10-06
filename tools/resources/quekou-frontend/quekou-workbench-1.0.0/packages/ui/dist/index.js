// packages/ui/src/components/AppShell.tsx
import { forwardRef as forwardRef2, useId } from "react";
import { PanelLeftClose, PanelLeftOpen } from "lucide-react";

// packages/ui/src/internal/foundation.tsx
import { createContext, useContext, useState, useRef, useCallback } from "react";
import { tokens } from "@quekou/theme";
function normalizeTheme(options) {
  const theme = options.theme && Object.hasOwn(tokens.systems, options.theme) ? options.theme : "bento";
  const defaults = tokens.systems[theme].defaults, p = tokens.parameterPolicy;
  const raw = options.accentHue;
  const accentHue = raw === "brand" || raw === void 0 || !Number.isFinite(raw) || raw === p.accentHue.default ? "brand" : Math.max(p.accentHue.minimum, Math.min(p.accentHue.maximum, Math.round(raw)));
  return { theme, accentHue, density: options.density && p.density.values.some((v) => v === options.density) ? options.density : defaults.density, surfaceMode: options.surfaceMode && p.surfaceMode.values.some((v) => v === options.surfaceMode) ? options.surfaceMode : defaults.surfaceMode, radiusScale: options.radiusScale && p.radiusScale.values.some((v) => v === options.radiusScale) ? options.radiusScale : p.radiusScale.default };
}
var ThemeContext = createContext(normalizeTheme({}));
var themeAttributes = (t) => ({ "data-theme": t.theme, "data-density": t.density, "data-surface-mode": t.surfaceMode, "data-accent-hue": t.accentHue, "data-radius-scale": t.radiusScale });
function useThemeAttributes(overrides = {}) {
  const current = useContext(ThemeContext);
  return { "data-qk": "", ...overrides.density || overrides.surfaceMode ? themeAttributes({ ...current, ...Object.fromEntries(Object.entries(overrides).filter(([, v]) => v !== void 0)) }) : {} };
}
var cx = (...classes) => classes.filter(Boolean).join(" ");
function useMergedRef(external, inner) {
  return useCallback((value) => {
    inner.current = value;
    if (typeof external === "function") external(value);
    else if (external) external.current = value;
  }, [external, inner]);
}
function useControllable(value, initial, onChange) {
  const [local, setLocal] = useState(initial);
  const current = value === void 0 ? local : value;
  const ref = useRef(current);
  ref.current = current;
  const set = (next) => {
    if (value === void 0) setLocal(next);
    onChange?.(next);
  };
  return [current, set, ref];
}
var uiTokens = tokens.common;

// packages/ui/src/components/Button.tsx
import { forwardRef } from "react";
import { LoaderCircle } from "lucide-react";
import { jsx, jsxs } from "react/jsx-runtime";
var Button = forwardRef(function Button2({ variant = "secondary", size = "md", loading = false, disabled, density, surfaceMode, className, children, type = "button", ...rest }, ref) {
  const attrs = useThemeAttributes({ density, surfaceMode });
  return /* @__PURE__ */ jsxs("button", { ...rest, ...attrs, ref, type, disabled: disabled || loading, "aria-busy": loading || void 0, className: cx("qk-button", className), "data-variant": variant, "data-size": size, children: [
    loading && /* @__PURE__ */ jsx(LoaderCircle, { "aria-hidden": "true", className: "qk-icon" }),
    children
  ] });
});

// packages/ui/src/components/AppShell.tsx
import { jsx as jsx2, jsxs as jsxs2 } from "react/jsx-runtime";
var AppShell = forwardRef2(function AppShell2({ brand, sidebar, header, collapsed, defaultCollapsed = false, onCollapsedChange, density, surfaceMode, className, children, ...rest }, ref) {
  const attrs = useThemeAttributes({ density, surfaceMode }), id = useId();
  const [closed, setClosed] = useControllable(collapsed, defaultCollapsed, onCollapsedChange);
  const Icon = closed ? PanelLeftOpen : PanelLeftClose;
  return /* @__PURE__ */ jsxs2("div", { ...rest, ...attrs, ref, className: cx("qk-shell", className), "data-collapsed": closed, children: [
    /* @__PURE__ */ jsxs2("aside", { id, className: "qk-shell-sidebar", children: [
      /* @__PURE__ */ jsx2("div", { className: "qk-shell-brand", children: brand }),
      sidebar
    ] }),
    /* @__PURE__ */ jsxs2("div", { className: "qk-shell-main", children: [
      /* @__PURE__ */ jsxs2("header", { className: "qk-shell-header", children: [
        /* @__PURE__ */ jsx2(Button, { size: "sm", variant: "ghost", "aria-label": closed ? "\u5C55\u5F00\u4FA7\u680F" : "\u6536\u8D77\u4FA7\u680F", "aria-expanded": !closed, "aria-controls": id, onClick: () => setClosed(!closed), children: /* @__PURE__ */ jsx2(Icon, { className: "qk-icon", "aria-hidden": "true" }) }),
        header
      ] }),
      /* @__PURE__ */ jsx2("div", { className: "qk-shell-content", children })
    ] })
  ] });
});

// packages/ui/src/components/Avatar.tsx
import { forwardRef as forwardRef3, useEffect, useState as useState2 } from "react";
import { jsx as jsx3 } from "react/jsx-runtime";
var Avatar = forwardRef3(function Avatar2({ name, src, size = "sm", density, surfaceMode, className, ...rest }, ref) {
  const attrs = useThemeAttributes({ density, surfaceMode });
  const [failed, setFailed] = useState2(false);
  useEffect(() => setFailed(false), [src]);
  return /* @__PURE__ */ jsx3("span", { ...rest, ...attrs, ref, role: "img", "aria-label": name, className: cx("qk-avatar", className), "data-size": size, children: src && !failed ? /* @__PURE__ */ jsx3("img", { src, alt: "", onError: () => setFailed(true) }) : /* @__PURE__ */ jsx3("span", { "aria-hidden": "true", children: name.trim().slice(-2) || "?" }) });
});

// packages/ui/src/components/Badge.tsx
import { forwardRef as forwardRef4 } from "react";
import { CheckCircle2, TriangleAlert, Info, OctagonAlert } from "lucide-react";
import { jsx as jsx4, jsxs as jsxs3 } from "react/jsx-runtime";
var statusIcons = { success: CheckCircle2, warning: TriangleAlert, danger: OctagonAlert, info: Info };
var Badge = forwardRef4(function Badge2({ status = "info", density, surfaceMode, className, children, ...rest }, ref) {
  const attrs = useThemeAttributes({ density, surfaceMode }), Icon = statusIcons[status];
  return /* @__PURE__ */ jsxs3("span", { ...rest, ...attrs, ref, className: cx("qk-badge", className), "data-status": status, children: [
    /* @__PURE__ */ jsx4(Icon, { "aria-hidden": "true", className: "qk-icon" }),
    children || { success: "\u5DF2\u5B8C\u6210", warning: "\u9700\u590D\u6838", danger: "\u9519\u8BEF", info: "\u4FE1\u606F" }[status]
  ] });
});

// packages/ui/src/components/ChartCard.tsx
import { forwardRef as forwardRef5, useId as useId2 } from "react";
import { jsx as jsx5, jsxs as jsxs4 } from "react/jsx-runtime";
var ChartCard = forwardRef5(function ChartCard2({ title, description, legend, actions, density, surfaceMode, className, children, ...rest }, ref) {
  const attrs = useThemeAttributes({ density, surfaceMode }), id = useId2();
  return /* @__PURE__ */ jsxs4("figure", { ...rest, ...attrs, ref, "aria-labelledby": id, className: cx("qk-chart-card qk-panel", className), children: [
    /* @__PURE__ */ jsxs4("figcaption", { className: "qk-panel-heading", children: [
      /* @__PURE__ */ jsxs4("div", { children: [
        /* @__PURE__ */ jsx5("h3", { id, children: title }),
        description && /* @__PURE__ */ jsx5("p", { className: "qk-muted", children: description })
      ] }),
      actions
    ] }),
    /* @__PURE__ */ jsx5("div", { className: "qk-chart-content", children }),
    legend && /* @__PURE__ */ jsx5("div", { className: "qk-chart-legend", children: legend })
  ] });
});

// packages/ui/src/components/Checkbox.tsx
import { forwardRef as forwardRef6, useRef as useRef2, useEffect as useEffect2 } from "react";
import { jsx as jsx6, jsxs as jsxs5 } from "react/jsx-runtime";
var Checkbox = forwardRef6(function Checkbox2({ label, indeterminate = false, density, surfaceMode, className, ...rest }, ref) {
  const local = useRef2(null);
  const merged = useMergedRef(ref, local), attrs = useThemeAttributes({ density, surfaceMode });
  useEffect2(() => {
    if (local.current) local.current.indeterminate = indeterminate;
  }, [indeterminate]);
  return /* @__PURE__ */ jsxs5("label", { ...attrs, className: cx("qk-checkbox", className), children: [
    /* @__PURE__ */ jsx6("input", { ...rest, ref: merged, type: "checkbox", "aria-checked": indeterminate ? "mixed" : rest.checked }),
    /* @__PURE__ */ jsx6("span", { children: label })
  ] });
});

// packages/ui/src/components/CommandPalette.tsx
import { forwardRef as forwardRef8, useState as useState3, useEffect as useEffect4, useId as useId4, useRef as useRef4 } from "react";

// packages/ui/src/components/Dialog.tsx
import { forwardRef as forwardRef7, useRef as useRef3, useEffect as useEffect3, useId as useId3 } from "react";
import { X } from "lucide-react";
import { jsx as jsx7, jsxs as jsxs6 } from "react/jsx-runtime";
var Dialog = forwardRef7(function Dialog2({ open, onOpenChange, title, description, footer, closeOnOutside = true, density, surfaceMode, className, children, onClick, onKeyDown, ...rest }, ref) {
  const attrs = useThemeAttributes({ density, surfaceMode }), id = useId3();
  const desired = useRef3(open);
  desired.current = open;
  const local = useRef3(null), merged = useMergedRef(ref, local);
  useEffect3(() => {
    const el = local.current;
    if (open && !el?.open) el?.showModal();
    if (!open && el?.open) el.close();
    return () => {
      if (el?.open) el.close();
    };
  }, [open]);
  return /* @__PURE__ */ jsxs6("dialog", { ...rest, ...attrs, ref: merged, className: cx("qk-dialog", className), onKeyDown: (e) => {
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
    /* @__PURE__ */ jsxs6("header", { className: "qk-panel-heading", children: [
      /* @__PURE__ */ jsx7("h2", { id, children: title }),
      /* @__PURE__ */ jsx7(Button, { variant: "ghost", size: "sm", "aria-label": `\u5173\u95ED${title}`, onClick: () => onOpenChange(false), children: /* @__PURE__ */ jsx7(X, { "aria-hidden": "true", className: "qk-icon" }) })
    ] }),
    description && /* @__PURE__ */ jsx7("p", { id: id + "-description", className: "qk-muted qk-description", children: description }),
    /* @__PURE__ */ jsx7("div", { className: "qk-dialog-content", children }),
    footer && /* @__PURE__ */ jsx7("footer", { className: "qk-dialog-footer", children: footer })
  ] });
});

// packages/ui/src/components/CommandPalette.tsx
import { jsx as jsx8, jsxs as jsxs7 } from "react/jsx-runtime";
var CommandPalette = forwardRef8(function CommandPalette2({ items, open, defaultOpen = false, onOpenChange, shortcut = true, title = "\u5FEB\u6377\u547D\u4EE4", ...rest }, ref) {
  const [shown, setShown, current] = useControllable(open, defaultOpen, onOpenChange), [query, setQuery] = useState3(""), [active, setActive] = useState3(0), id = useId4();
  const setter = useRef4(setShown);
  setter.current = setShown;
  useEffect4(() => {
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
  useEffect4(() => {
    if (shown) {
      setQuery("");
      setActive(0);
    }
  }, [shown]);
  const results = items.filter((x) => (x.label + " " + (x.keywords || "")).toLocaleLowerCase().includes(query.toLocaleLowerCase()));
  const index = Math.min(active, Math.max(0, results.length - 1));
  useEffect4(() => {
    if (shown && results[index]) document.getElementById(`${id}-${results[index].id}`)?.scrollIntoView({ block: "nearest" });
  }, [shown, index, id, query]);
  const select = (item) => {
    setShown(false);
    item.onSelect();
  };
  return /* @__PURE__ */ jsxs7(Dialog, { ...rest, ref, title, open: shown, onOpenChange: setShown, children: [
    /* @__PURE__ */ jsx8("input", { className: "qk-input", autoFocus: true, role: "combobox", "aria-label": "\u641C\u7D22\u5FEB\u6377\u547D\u4EE4", "aria-expanded": shown, "aria-controls": id, "aria-autocomplete": "list", "aria-activedescendant": results[index] ? `${id}-${results[index].id}` : void 0, value: query, onChange: (e) => {
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
    /* @__PURE__ */ jsx8("div", { id, role: "listbox", "aria-label": "\u53EF\u7528\u547D\u4EE4", className: "qk-command-list", children: results.map((item, i) => /* @__PURE__ */ jsx8("div", { id: `${id}-${item.id}`, role: "option", "aria-selected": i === index, className: "qk-command-item", onMouseDown: (e) => e.preventDefault(), onMouseEnter: () => setActive(i), onClick: () => select(item), children: item.label }, item.id)) }),
    !results.length && /* @__PURE__ */ jsx8("p", { className: "qk-muted", role: "status", children: "\u6CA1\u6709\u5339\u914D\u7684\u547D\u4EE4" })
  ] });
});

// packages/ui/src/components/DataTable.tsx
import { forwardRef as forwardRef11, useRef as useRef5, useState as useState4, useMemo, useLayoutEffect, useContext as useContext2 } from "react";
import { ArrowDownUp } from "lucide-react";

// packages/ui/src/components/Input.tsx
import { forwardRef as forwardRef9, useId as useId5 } from "react";
import { jsx as jsx9, jsxs as jsxs8 } from "react/jsx-runtime";
var Input = forwardRef9(function Input2({ label, hint, error, id, density, surfaceMode, className, ...rest }, ref) {
  const generated = useId5(), fieldId = id || generated, descId = fieldId + "-description";
  const attrs = useThemeAttributes({ density, surfaceMode });
  return /* @__PURE__ */ jsxs8("div", { ...attrs, className: cx("qk-field", className), children: [
    /* @__PURE__ */ jsx9("label", { htmlFor: fieldId, className: "qk-label", children: label }),
    /* @__PURE__ */ jsx9("input", { ...rest, ref, id: fieldId, className: "qk-input", "aria-invalid": error ? true : rest["aria-invalid"], "aria-describedby": [rest["aria-describedby"], error || hint ? descId : void 0].filter(Boolean).join(" ") || void 0 }),
    (error || hint) && /* @__PURE__ */ jsx9("span", { id: descId, className: cx("qk-field-note", error && "qk-error"), role: error ? "alert" : void 0, children: error || hint })
  ] });
});

// packages/ui/src/components/EmptyState.tsx
import { forwardRef as forwardRef10 } from "react";
import { Inbox } from "lucide-react";
import { jsx as jsx10, jsxs as jsxs9 } from "react/jsx-runtime";
var EmptyState = forwardRef10(function EmptyState2({ title, description, action, density, surfaceMode, className, ...rest }, ref) {
  const attrs = useThemeAttributes({ density, surfaceMode });
  return /* @__PURE__ */ jsxs9("div", { ...rest, ...attrs, ref, className: cx("qk-empty", className), children: [
    /* @__PURE__ */ jsx10(Inbox, { "aria-hidden": "true", className: "qk-empty-icon" }),
    /* @__PURE__ */ jsx10("strong", { children: title }),
    description && /* @__PURE__ */ jsx10("p", { className: "qk-muted", children: description }),
    action
  ] });
});

// packages/ui/src/components/DataTable.tsx
import { jsx as jsx11, jsxs as jsxs10 } from "react/jsx-runtime";
function DataTableInner({ rows, columns, getRowId, label, showToolbar = true, showFooter = true, selectionLabel = "\u9009\u62E9\u7B5B\u9009\u540E\u7684\u5168\u90E8\u884C", selectable = false, selectedIds, onSelectionChange, sort: sortProp, onSortChange, search: searchProp, onSearchChange, pinFirstColumn = true, virtual = true, loading = false, density, surfaceMode, className, ...rest }, ref) {
  const attrs = useThemeAttributes({ density, surfaceMode }), theme = useContext2(ThemeContext);
  const outer = useRef5(null), scroll = useRef5(null), merged = useMergedRef(ref, outer);
  const [search, setSearch] = useControllable(searchProp, "", onSearchChange);
  const [sort, setSort] = useControllable(sortProp, null, (s) => {
    if (s) onSortChange?.(s);
  });
  const [selection, setSelection] = useControllable(selectedIds, [], (ids) => onSelectionChange?.([...ids]));
  const [allRows, setAllRows] = useState4(false), [offset, setOffset] = useState4(0), [dimensions, setDimensions] = useState4({ row: parseFloat(uiTokens["row-height"]), viewport: 0, header: 0 });
  useLayoutEffect(() => {
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
  const filtered = useMemo(() => {
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
  useLayoutEffect(() => {
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
  const spacer = (height, key) => /* @__PURE__ */ jsx11("tr", { "aria-hidden": "true", className: "qk-table-spacer", children: /* @__PURE__ */ jsx11("td", { colSpan, children: /* @__PURE__ */ jsx11("svg", { height, width: "1", "aria-hidden": "true" }) }) }, key);
  return /* @__PURE__ */ jsxs10("div", { ...rest, ...attrs, ref: merged, className: cx("qk-data-table qk-panel", className), "data-virtual": isVirtual, "data-selectable": selectable, "aria-busy": loading || void 0, children: [
    showToolbar && /* @__PURE__ */ jsxs10("div", { className: "qk-table-toolbar", children: [
      /* @__PURE__ */ jsx11(Input, { label: "\u641C\u7D22\u8868\u683C", "aria-label": `${label}\u641C\u7D22`, type: "search", value: search, onChange: (e) => setSearch(e.target.value), placeholder: "\u641C\u7D22\u4EFB\u610F\u5217" }),
      /* @__PURE__ */ jsxs10("span", { className: "qk-muted", "aria-live": "polite", children: [
        filtered.length,
        " \u884C \xB7 \u5DF2\u9009\u62E9 ",
        selection.length,
        " \u884C"
      ] }),
      virtual && /* @__PURE__ */ jsx11(Button, { size: "sm", onClick: () => setAllRows(!allRows), "aria-pressed": allRows, children: allRows ? "\u542F\u7528\u865A\u62DF\u6EDA\u52A8" : "\u663E\u793A\u5168\u90E8\u884C" })
    ] }),
    /* @__PURE__ */ jsxs10("div", { ref: scroll, className: "qk-table-scroll", role: "region", "aria-label": `${label}\u53EF\u6EDA\u52A8\u8868\u683C`, tabIndex: 0, onScroll: (e) => setOffset(e.currentTarget.scrollTop), onKeyDown: (e) => {
      if (e.target !== e.currentTarget) return;
      const el = e.currentTarget;
      const jumps = { ArrowDown: el.scrollTop + rowHeight, ArrowUp: el.scrollTop - rowHeight, PageDown: el.scrollTop + el.clientHeight, PageUp: el.scrollTop - el.clientHeight, Home: 0, End: el.scrollHeight };
      if (e.key in jumps) {
        e.preventDefault();
        el.scrollTop = jumps[e.key];
      }
    }, children: [
      /* @__PURE__ */ jsxs10("table", { className: "qk-table", "aria-rowcount": filtered.length + 1, children: [
        /* @__PURE__ */ jsxs10("caption", { className: "qk-sr-only", children: [
          label,
          "\uFF0C",
          isVirtual ? "\u865A\u62DF\u6EDA\u52A8\uFF1B\u53EF\u7528\u65B9\u5411\u952E\u3001PageDown\u3001Home\u3001End\uFF0C\u6216\u663E\u793A\u5168\u90E8\u884C" : "\u5B8C\u6574\u5217\u8868"
        ] }),
        /* @__PURE__ */ jsx11("thead", { children: /* @__PURE__ */ jsxs10("tr", { children: [
          selectable && /* @__PURE__ */ jsx11("th", { className: "qk-select-col", children: /* @__PURE__ */ jsx11(Checkbox, { label: selectionLabel, className: "qk-checkbox-icon", checked: every, indeterminate: some && !every, disabled: !filtered.length || loading, onChange: (e) => selectAll(e.target.checked) }) }),
          columns.map((col, i) => /* @__PURE__ */ jsx11("th", { scope: "col", "data-pinned": pinFirstColumn && i === 0, "data-numeric": col.numeric, "aria-sort": sort?.column === col.id ? sort.direction === "asc" ? "ascending" : "descending" : "none", children: col.sortable !== false ? /* @__PURE__ */ jsxs10("button", { type: "button", onClick: () => setSort({ column: col.id, direction: sort?.column === col.id && sort.direction === "asc" ? "desc" : "asc" }), children: [
            col.label,
            /* @__PURE__ */ jsx11(ArrowDownUp, { className: "qk-icon", "aria-hidden": "true" })
          ] }) : col.label }, col.id))
        ] }) }),
        /* @__PURE__ */ jsxs10("tbody", { children: [
          isVirtual && first > 0 && spacer(first * rowHeight, "top"),
          visible.map((row, index) => {
            const id = getRowId(row);
            return /* @__PURE__ */ jsxs10("tr", { "aria-rowindex": first + index + 2, "aria-selected": selectable ? selectedSet.has(id) : void 0, "data-selected": selectedSet.has(id), children: [
              selectable && /* @__PURE__ */ jsx11("td", { className: "qk-select-col", children: /* @__PURE__ */ jsx11(Checkbox, { label: `\u9009\u62E9\u884C ${id}`, className: "qk-checkbox-icon", checked: selectedSet.has(id), disabled: loading, onChange: (e) => {
                const ids = new Set(selection);
                if (e.target.checked) ids.add(id);
                else ids.delete(id);
                setSelection([...ids]);
              } }) }),
              columns.map((col, i) => /* @__PURE__ */ jsx11("td", { "data-pinned": pinFirstColumn && i === 0, "data-numeric": col.numeric, children: /* @__PURE__ */ jsx11("div", { className: "qk-cell", children: col.render ? col.render(row) : col.value(row) ?? "\u2014" }) }, col.id))
            ] }, id);
          }),
          isVirtual && end < filtered.length && spacer((filtered.length - end) * rowHeight, "bottom")
        ] })
      ] }),
      !filtered.length && /* @__PURE__ */ jsx11(EmptyState, { title: loading ? "\u6B63\u5728\u8F7D\u5165\u6570\u636E" : "\u6CA1\u6709\u5339\u914D\u7684\u8BB0\u5F55", description: loading ? "\u8BF7\u7A0D\u5019\u3002" : "\u8C03\u6574\u5173\u952E\u8BCD\u540E\u91CD\u8BD5\u3002" })
    ] }),
    showFooter && /* @__PURE__ */ jsxs10("div", { className: "qk-table-footer", children: [
      loading ? "\u6B63\u5728\u66F4\u65B0\u6570\u636E" : `\u663E\u793A ${filtered.length ? first + 1 : 0}\u2013${end} / ${filtered.length} \u884C`,
      isVirtual && /* @__PURE__ */ jsx11("span", { children: "\u865A\u62DF\u6EDA\u52A8\u5DF2\u542F\u7528 \xB7 \u9996\u5217\u53EF\u56FA\u5B9A" })
    ] })
  ] });
}
var DataTable = forwardRef11(DataTableInner);

// packages/ui/src/components/DetailPanel.tsx
import { forwardRef as forwardRef12, useId as useId6 } from "react";
import { X as X2 } from "lucide-react";
import { jsx as jsx12, jsxs as jsxs11 } from "react/jsx-runtime";
var DetailPanel = forwardRef12(function DetailPanel2({ title, description, onClose, actions, density, surfaceMode, className, children, ...rest }, ref) {
  const attrs = useThemeAttributes({ density, surfaceMode }), id = useId6();
  return /* @__PURE__ */ jsxs11("aside", { ...rest, ...attrs, ref, className: cx("qk-detail qk-panel", className), "aria-labelledby": id, children: [
    /* @__PURE__ */ jsxs11("div", { className: "qk-panel-heading", children: [
      /* @__PURE__ */ jsx12("h2", { id, children: title }),
      onClose && /* @__PURE__ */ jsx12(Button, { size: "sm", variant: "ghost", "aria-label": `\u5173\u95ED${title}`, onClick: onClose, children: /* @__PURE__ */ jsx12(X2, { "aria-hidden": "true", className: "qk-icon" }) })
    ] }),
    description && /* @__PURE__ */ jsx12("p", { className: "qk-muted qk-description", children: description }),
    /* @__PURE__ */ jsx12("div", { children }),
    actions && /* @__PURE__ */ jsx12("footer", { className: "qk-dialog-footer", children: actions })
  ] });
});

// packages/ui/src/components/Drawer.tsx
import { forwardRef as forwardRef13 } from "react";
import { jsx as jsx13 } from "react/jsx-runtime";
var Drawer = forwardRef13(function Drawer2({ className, ...props }, ref) {
  return /* @__PURE__ */ jsx13(Dialog, { ...props, ref, className: cx("qk-drawer", className) });
});

// packages/ui/src/components/FilterBar.tsx
import { forwardRef as forwardRef15 } from "react";

// packages/ui/src/components/Select.tsx
import { forwardRef as forwardRef14, useId as useId7 } from "react";
import { jsx as jsx14, jsxs as jsxs12 } from "react/jsx-runtime";
var Select = forwardRef14(function Select2({ label, options, hint, error, id, density, surfaceMode, className, ...rest }, ref) {
  const generated = useId7(), fieldId = id || generated, desc = fieldId + "-description";
  const attrs = useThemeAttributes({ density, surfaceMode });
  return /* @__PURE__ */ jsxs12("div", { ...attrs, className: cx("qk-field", className), children: [
    /* @__PURE__ */ jsx14("label", { htmlFor: fieldId, className: "qk-label", children: label }),
    /* @__PURE__ */ jsx14("select", { ...rest, ref, id: fieldId, className: "qk-input", "aria-invalid": error ? true : rest["aria-invalid"], "aria-describedby": [rest["aria-describedby"], error || hint ? desc : void 0].filter(Boolean).join(" ") || void 0, children: options.map((o) => /* @__PURE__ */ jsx14("option", { value: o.value, disabled: o.disabled, children: o.label }, o.value)) }),
    (error || hint) && /* @__PURE__ */ jsx14("span", { id: desc, className: cx("qk-field-note", error && "qk-error"), role: error ? "alert" : void 0, children: error || hint })
  ] });
});

// packages/ui/src/components/FilterBar.tsx
import { jsx as jsx15, jsxs as jsxs13 } from "react/jsx-runtime";
var FilterBar = forwardRef15(function FilterBar2({ filters, search, onSearchChange, from, to, onDateChange, onReset, density, surfaceMode, className, ...rest }, ref) {
  const attrs = useThemeAttributes({ density, surfaceMode });
  return /* @__PURE__ */ jsxs13("div", { ...rest, ...attrs, ref, className: cx("qk-filter-bar", className), "aria-label": "\u7B5B\u9009\u6761\u4EF6", children: [
    filters.map((f) => /* @__PURE__ */ jsx15(Select, { label: f.label, value: f.value, options: f.options, onChange: (e) => f.onChange(e.target.value) }, f.id)),
    /* @__PURE__ */ jsx15(Input, { label: "\u5F00\u59CB\u65E5\u671F", type: "date", value: from, max: to || void 0, onChange: (e) => onDateChange({ from: e.target.value, to }) }),
    /* @__PURE__ */ jsx15(Input, { label: "\u7ED3\u675F\u65E5\u671F", type: "date", value: to, min: from || void 0, onChange: (e) => onDateChange({ from, to: e.target.value }) }),
    /* @__PURE__ */ jsx15(Input, { label: "\u641C\u7D22", type: "search", value: search, onChange: (e) => onSearchChange(e.target.value) }),
    /* @__PURE__ */ jsx15(Button, { onClick: onReset, children: "\u91CD\u7F6E\u7B5B\u9009" }),
    from && to && from > to && /* @__PURE__ */ jsx15("p", { className: "qk-error", role: "alert", children: "\u5F00\u59CB\u65E5\u671F\u665A\u4E8E\u7ED3\u675F\u65E5\u671F" })
  ] });
});

// packages/ui/src/components/KpiCard.tsx
import { forwardRef as forwardRef17 } from "react";
import { ArrowDownRight, ArrowUpRight, Minus } from "lucide-react";

// packages/ui/src/components/Sparkline.tsx
import { forwardRef as forwardRef16, useId as useId8 } from "react";
import { jsx as jsx16, jsxs as jsxs14 } from "react/jsx-runtime";
var Sparkline = forwardRef16(function Sparkline2({ values, label, large = false, density, surfaceMode, className, ...rest }, ref) {
  const attrs = useThemeAttributes({ density, surfaceMode }), id = useId8(), safe = values.filter(Number.isFinite);
  const min = Math.min(...safe), max = Math.max(...safe), range = max - min || 1;
  const points = safe.map((v, i) => `${8 + i * 184 / Math.max(1, safe.length - 1)},${max === min ? 32 : 56 - (v - min) * 48 / range}`).join(" ");
  return /* @__PURE__ */ jsxs14("svg", { ...rest, ...attrs, ref, viewBox: "0 0 200 64", role: "img", "aria-labelledby": id, preserveAspectRatio: "none", className: cx("qk-sparkline", large && "qk-sparkline-large", className), children: [
    /* @__PURE__ */ jsxs14("title", { id, children: [
      label,
      safe.length ? `\uFF0C\u8D77\u70B9 ${safe[0]}\uFF0C\u7EC8\u70B9 ${safe.at(-1)}` : "\uFF0C\u6682\u65E0\u6570\u636E"
    ] }),
    safe.length > 1 ? /* @__PURE__ */ jsx16("polyline", { points, fill: "none", vectorEffect: "non-scaling-stroke" }) : safe.length === 1 ? /* @__PURE__ */ jsx16("circle", { cx: "100", cy: "32", r: "3" }) : null
  ] });
});

// packages/ui/src/components/KpiCard.tsx
import { jsx as jsx17, jsxs as jsxs15 } from "react/jsx-runtime";
var KpiCard = forwardRef17(function KpiCard2({ label, value, unit, change, trend, direction = "up", emphasis = false, density, surfaceMode, className, ...rest }, ref) {
  const attrs = useThemeAttributes({ density, surfaceMode }), Icon = direction === "up" ? ArrowUpRight : direction === "down" ? ArrowDownRight : Minus;
  return /* @__PURE__ */ jsxs15("article", { ...rest, ...attrs, ref, className: cx("qk-kpi qk-panel", className), "data-emphasis": emphasis, children: [
    /* @__PURE__ */ jsx17("p", { className: "qk-muted", children: label }),
    /* @__PURE__ */ jsxs15("div", { className: "qk-kpi-value", children: [
      /* @__PURE__ */ jsx17("strong", { children: value }),
      /* @__PURE__ */ jsx17("span", { children: unit })
    ] }),
    /* @__PURE__ */ jsxs15("div", { className: "qk-kpi-bottom", children: [
      /* @__PURE__ */ jsxs15("span", { children: [
        /* @__PURE__ */ jsx17(Icon, { "aria-hidden": "true", className: "qk-icon" }),
        change
      ] }),
      trend && /* @__PURE__ */ jsx17(Sparkline, { values: trend, label: `${label}\u8D8B\u52BF` })
    ] })
  ] });
});

// packages/ui/src/components/NavGroup.tsx
import { forwardRef as forwardRef18 } from "react";
import { jsx as jsx18, jsxs as jsxs16 } from "react/jsx-runtime";
var NavGroup = forwardRef18(function NavGroup2({ label, items, activeId, onNavigate, density, surfaceMode, className, ...rest }, ref) {
  const attrs = useThemeAttributes({ density, surfaceMode });
  return /* @__PURE__ */ jsxs16("nav", { ...rest, ...attrs, ref, "aria-label": label, className: cx("qk-nav-group", className), children: [
    /* @__PURE__ */ jsx18("p", { className: "qk-nav-label qk-muted", children: label }),
    items.map((item) => /* @__PURE__ */ jsxs16("a", { href: item.href, "aria-label": item.label, "aria-current": activeId === item.id ? "page" : void 0, className: "qk-nav-link", onClick: () => onNavigate?.(item.id), children: [
      item.icon && /* @__PURE__ */ jsx18("span", { "aria-hidden": "true", children: item.icon }),
      /* @__PURE__ */ jsx18("span", { className: "qk-nav-label", children: item.label }),
      item.count !== void 0 && /* @__PURE__ */ jsx18("span", { className: "qk-nav-count", children: item.count })
    ] }, item.id))
  ] });
});

// packages/ui/src/components/PageHeader.tsx
import { forwardRef as forwardRef19 } from "react";
import { jsx as jsx19, jsxs as jsxs17 } from "react/jsx-runtime";
var PageHeader = forwardRef19(function PageHeader2({ title, description, eyebrow, actions, density, surfaceMode, className, ...rest }, ref) {
  const attrs = useThemeAttributes({ density, surfaceMode });
  return /* @__PURE__ */ jsxs17("header", { ...rest, ...attrs, ref, className: cx("qk-page-header", className), children: [
    /* @__PURE__ */ jsxs17("div", { children: [
      eyebrow && /* @__PURE__ */ jsx19("p", { className: "qk-eyebrow", children: eyebrow }),
      /* @__PURE__ */ jsx19("h1", { children: title }),
      description && /* @__PURE__ */ jsx19("p", { className: "qk-muted", children: description })
    ] }),
    actions && /* @__PURE__ */ jsx19("div", { className: "qk-actions", children: actions })
  ] });
});

// packages/ui/src/components/Pagination.tsx
import { forwardRef as forwardRef20 } from "react";
import { jsx as jsx20, jsxs as jsxs18 } from "react/jsx-runtime";
var Pagination = forwardRef20(function Pagination2({ page, pageCount, onPageChange, density, surfaceMode, className, ...rest }, ref) {
  const attrs = useThemeAttributes({ density, surfaceMode }), count = Math.max(0, Math.floor(pageCount) || 0), current = count ? Math.max(1, Math.min(count, Math.floor(page) || 1)) : 0;
  return /* @__PURE__ */ jsxs18("nav", { ...rest, ...attrs, ref, "aria-label": "\u5206\u9875", className: cx("qk-pagination", className), children: [
    /* @__PURE__ */ jsx20(Button, { size: "sm", disabled: current <= 1, onClick: () => onPageChange(1), children: "\u9996\u9875" }),
    /* @__PURE__ */ jsx20(Button, { size: "sm", disabled: current <= 1, onClick: () => onPageChange(current - 1), children: "\u4E0A\u4E00\u9875" }),
    /* @__PURE__ */ jsx20("span", { "aria-live": "polite", children: count ? `\u7B2C ${current} / ${count} \u9875` : "\u6682\u65E0\u5206\u9875" }),
    /* @__PURE__ */ jsx20(Button, { size: "sm", disabled: current >= count, onClick: () => onPageChange(current + 1), children: "\u4E0B\u4E00\u9875" }),
    /* @__PURE__ */ jsx20(Button, { size: "sm", disabled: current >= count, onClick: () => onPageChange(count), children: "\u672B\u9875" })
  ] });
});

// packages/ui/src/components/Popover.tsx
import { forwardRef as forwardRef21, useRef as useRef6, useEffect as useEffect5, useId as useId9 } from "react";
import { jsx as jsx21, jsxs as jsxs19 } from "react/jsx-runtime";
var Popover = forwardRef21(function Popover2({ label, trigger, open, defaultOpen = false, onOpenChange, density, surfaceMode, className, children, ...rest }, ref) {
  const attrs = useThemeAttributes({ density, surfaceMode }), id = useId9();
  const root = useRef6(null), button = useRef6(null), content = useRef6(null), merged = useMergedRef(ref, root);
  const [shown, setShown] = useControllable(open, defaultOpen, onOpenChange);
  const setter = useRef6(setShown);
  setter.current = setShown;
  useEffect5(() => {
    if (!shown) return;
    content.current?.querySelector('input,select,button,a[href],[tabindex="0"]')?.focus();
    const close = (e) => {
      if (e.target instanceof Node && !root.current?.contains(e.target)) setter.current(false);
    };
    document.addEventListener("pointerdown", close);
    return () => document.removeEventListener("pointerdown", close);
  }, [shown]);
  return /* @__PURE__ */ jsxs19("div", { ...rest, ...attrs, ref: merged, className: cx("qk-popover-root", className), onBlur: (e) => {
    if (e.relatedTarget && !e.currentTarget.contains(e.relatedTarget)) setShown(false);
  }, onKeyDown: (e) => {
    if (e.key === "Escape" && shown) {
      e.stopPropagation();
      setShown(false);
      button.current?.focus();
    }
  }, children: [
    /* @__PURE__ */ jsx21(Button, { ref: button, "aria-expanded": shown, "aria-controls": id, onClick: () => setShown(!shown), children: trigger }),
    shown && /* @__PURE__ */ jsx21("div", { ref: content, id, role: "region", "aria-label": label, className: "qk-popover", children })
  ] });
});

// packages/ui/src/components/ProgressBar.tsx
import { forwardRef as forwardRef22 } from "react";
import { jsx as jsx22, jsxs as jsxs20 } from "react/jsx-runtime";
var ProgressBar = forwardRef22(function ProgressBar2({ value, label, showValue = true, density, surfaceMode, className, ...rest }, ref) {
  const attrs = useThemeAttributes({ density, surfaceMode }), n = Number.isFinite(value) ? Math.max(0, Math.min(100, value)) : 0;
  return /* @__PURE__ */ jsxs20("span", { ...attrs, className: cx("qk-progress", className), children: [
    /* @__PURE__ */ jsx22("progress", { ...rest, ref, max: 100, value: n, "aria-label": label }),
    showValue && /* @__PURE__ */ jsxs20("span", { "aria-hidden": "true", children: [
      n,
      "%"
    ] })
  ] });
});

// packages/ui/src/components/Skeleton.tsx
import { forwardRef as forwardRef23 } from "react";
import { jsx as jsx23, jsxs as jsxs21 } from "react/jsx-runtime";
var Skeleton = forwardRef23(function Skeleton2({ lines = 3, label = "\u6B63\u5728\u52A0\u8F7D", density, surfaceMode, className, ...rest }, ref) {
  const attrs = useThemeAttributes({ density, surfaceMode });
  return /* @__PURE__ */ jsxs21("div", { ...rest, ...attrs, ref, className: cx("qk-skeleton", className), role: "status", "aria-label": label, children: [
    /* @__PURE__ */ jsx23("span", { className: "qk-sr-only", children: label }),
    Array.from({ length: lines }, (_, i) => /* @__PURE__ */ jsx23("span", { "aria-hidden": "true" }, i))
  ] });
});

// packages/ui/src/components/StatTile.tsx
import { forwardRef as forwardRef24 } from "react";
import { jsx as jsx24, jsxs as jsxs22 } from "react/jsx-runtime";
var StatTile = forwardRef24(function StatTile2({ label, value, hint, density, surfaceMode, className, ...rest }, ref) {
  const attrs = useThemeAttributes({ density, surfaceMode });
  return /* @__PURE__ */ jsxs22("div", { ...rest, ...attrs, ref, className: cx("qk-stat", className), children: [
    /* @__PURE__ */ jsx24("span", { className: "qk-muted", children: label }),
    /* @__PURE__ */ jsx24("strong", { children: value }),
    hint && /* @__PURE__ */ jsx24("small", { className: "qk-muted", children: hint })
  ] });
});

// packages/ui/src/components/StatusDot.tsx
import { forwardRef as forwardRef25 } from "react";
import { jsx as jsx25, jsxs as jsxs23 } from "react/jsx-runtime";
var StatusDot = forwardRef25(function StatusDot2({ status, label, density, surfaceMode, className, ...rest }, ref) {
  const attrs = useThemeAttributes({ density, surfaceMode }), Icon = statusIcons[status];
  return /* @__PURE__ */ jsxs23("span", { ...rest, ...attrs, ref, className: cx("qk-status-dot", className), children: [
    /* @__PURE__ */ jsx25(Icon, { "aria-hidden": "true", className: "qk-icon" }),
    label
  ] });
});

// packages/ui/src/components/Tag.tsx
import { forwardRef as forwardRef26 } from "react";
import { X as X3 } from "lucide-react";
import { jsx as jsx26, jsxs as jsxs24 } from "react/jsx-runtime";
var Tag = forwardRef26(function Tag2({ label, onRemove, density, surfaceMode, className, ...rest }, ref) {
  const attrs = useThemeAttributes({ density, surfaceMode });
  return /* @__PURE__ */ jsxs24("span", { ...rest, ...attrs, ref, className: cx("qk-tag", className), children: [
    label,
    onRemove && /* @__PURE__ */ jsx26("button", { type: "button", className: "qk-icon-button", "aria-label": `\u79FB\u9664${label}`, onClick: onRemove, children: /* @__PURE__ */ jsx26(X3, { "aria-hidden": "true", className: "qk-icon" }) })
  ] });
});

// packages/ui/src/components/ThemeProvider.tsx
import { forwardRef as forwardRef27 } from "react";
import { jsx as jsx27 } from "react/jsx-runtime";
var ThemeProvider = forwardRef27(function ThemeProvider2({ theme, density, surfaceMode, accentHue, radiusScale, className, children, ...rest }, ref) {
  const settings = normalizeTheme({ theme, density, surfaceMode, accentHue, radiusScale });
  return /* @__PURE__ */ jsx27(ThemeContext.Provider, { value: settings, children: /* @__PURE__ */ jsx27("div", { ...rest, ...themeAttributes(settings), ref, className: cx("qk-theme", className), children }) });
});

// packages/ui/src/components/Toast.tsx
import { forwardRef as forwardRef28, useState as useState5, useEffect as useEffect6, useRef as useRef7 } from "react";
import { X as X4 } from "lucide-react";
import { jsx as jsx28, jsxs as jsxs25 } from "react/jsx-runtime";
var Toast = forwardRef28(function Toast2({ open, onDismiss, status = "info", duration = parseFloat(uiTokens["feedback-duration"]), title, density, surfaceMode, className, children, ...rest }, ref) {
  const attrs = useThemeAttributes({ density, surfaceMode }), Icon = statusIcons[status];
  const [hovered, setHovered] = useState5(false), [focused, setFocused] = useState5(false);
  const paused = hovered || focused;
  const dismiss = useRef7(onDismiss);
  dismiss.current = onDismiss;
  useEffect6(() => {
    if (!open || paused || duration <= 0) return;
    const t = window.setTimeout(() => dismiss.current(), duration);
    return () => window.clearTimeout(t);
  }, [open, paused, duration]);
  if (!open) return null;
  return /* @__PURE__ */ jsxs25("div", { ...rest, ...attrs, ref, className: cx("qk-toast", className), role: status === "danger" ? "alert" : "status", "aria-atomic": "true", onMouseEnter: () => setHovered(true), onMouseLeave: () => setHovered(false), onFocus: () => setFocused(true), onBlur: (e) => {
    if (!e.currentTarget.contains(e.relatedTarget)) setFocused(false);
  }, children: [
    /* @__PURE__ */ jsx28(Icon, { className: "qk-icon", "aria-hidden": "true" }),
    /* @__PURE__ */ jsxs25("div", { children: [
      /* @__PURE__ */ jsx28("strong", { children: title }),
      children && /* @__PURE__ */ jsx28("div", { className: "qk-muted", children })
    ] }),
    /* @__PURE__ */ jsx28(Button, { variant: "ghost", size: "sm", "aria-label": "\u5173\u95ED\u901A\u77E5", onClick: onDismiss, children: /* @__PURE__ */ jsx28(X4, { "aria-hidden": "true", className: "qk-icon" }) })
  ] });
});

// packages/ui/src/components/Tooltip.tsx
import { forwardRef as forwardRef29, useState as useState6, useId as useId10, cloneElement } from "react";
import { jsx as jsx29, jsxs as jsxs26 } from "react/jsx-runtime";
var Tooltip = forwardRef29(function Tooltip2({ content, children, density, surfaceMode, className, onMouseEnter, onMouseLeave, onFocus, onBlur, onKeyDown, ...rest }, ref) {
  const attrs = useThemeAttributes({ density, surfaceMode }), id = useId10();
  const [hovered, setHovered] = useState6(false), [focused, setFocused] = useState6(false), [dismissed, setDismissed] = useState6(false);
  const open = (hovered || focused) && !dismissed;
  return /* @__PURE__ */ jsxs26("span", { ...rest, ...attrs, ref, className: cx("qk-tooltip-root", className), onMouseEnter: (e) => {
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
    cloneElement(children, { "aria-describedby": [children.props["aria-describedby"], open ? id : void 0].filter(Boolean).join(" ") || void 0 }),
    open && /* @__PURE__ */ jsx29("span", { id, role: "tooltip", className: "qk-tooltip", children: content })
  ] });
});

// packages/ui/src/blocks/ActivityFeed.tsx
import { forwardRef as forwardRef30, useId as useId11 } from "react";
import { jsx as jsx30, jsxs as jsxs27 } from "react/jsx-runtime";
var ActivityFeed = forwardRef30(function ActivityFeed2({ title, description, items, variant = "feed", loading = false, density, surfaceMode }, ref) {
  const attrs = useThemeAttributes({ density, surfaceMode }), id = useId11();
  return /* @__PURE__ */ jsxs27("section", { ...attrs, ref, "data-block": "ActivityFeed", className: "qk-panel qk-activity", "aria-labelledby": id, children: [
    /* @__PURE__ */ jsxs27("header", { className: "qk-panel-heading", children: [
      /* @__PURE__ */ jsxs27("div", { children: [
        /* @__PURE__ */ jsx30("h2", { id, children: title }),
        description && /* @__PURE__ */ jsx30("p", { className: "qk-muted qk-description", children: description })
      ] }),
      /* @__PURE__ */ jsxs27("span", { className: "qk-muted", children: [
        items.length,
        " \u6761"
      ] })
    ] }),
    loading ? /* @__PURE__ */ jsx30(Skeleton, { label: "\u6B63\u5728\u52A0\u8F7D\u52A8\u6001" }) : !items.length ? /* @__PURE__ */ jsx30(EmptyState, { title: "\u6682\u65E0\u8BB0\u5F55", description: "\u540E\u7EED\u8FDB\u5C55\u4F1A\u663E\u793A\u5728\u8FD9\u91CC\u3002" }) : /* @__PURE__ */ jsx30("ol", { className: cx("qk-activity-list", variant === "timeline" && "qk-timeline"), children: items.map((item) => /* @__PURE__ */ jsxs27("li", { children: [
      /* @__PURE__ */ jsx30("div", { className: "qk-activity-marker", "aria-hidden": "true" }),
      /* @__PURE__ */ jsxs27("div", { className: "qk-activity-copy", children: [
        /* @__PURE__ */ jsxs27("div", { children: [
          /* @__PURE__ */ jsx30("strong", { children: item.title }),
          /* @__PURE__ */ jsx30(Badge, { status: item.status, children: item.statusLabel })
        ] }),
        /* @__PURE__ */ jsx30("p", { children: item.detail }),
        /* @__PURE__ */ jsxs27("small", { children: [
          item.actor,
          " \xB7 ",
          /* @__PURE__ */ jsx30("time", { children: item.time })
        ] })
      ] }),
      item.onOpen && /* @__PURE__ */ jsx30(Button, { size: "sm", variant: "ghost", onClick: item.onOpen, children: "\u67E5\u770B\u8BE6\u60C5" })
    ] }, item.id)) })
  ] });
});

// packages/ui/src/blocks/BreakdownPanel.tsx
import { forwardRef as forwardRef31 } from "react";
import { jsx as jsx31, jsxs as jsxs28 } from "react/jsx-runtime";
var BreakdownPanel = forwardRef31(function BreakdownPanel2({ title, description, unit, items, onSelect, loading = false, ...theme }, ref) {
  const total = items.reduce((s, x) => s + Math.max(0, x.value), 0);
  return /* @__PURE__ */ jsx31(ChartCard, { ...theme, ref, "data-block": "BreakdownPanel", title, description, children: loading ? /* @__PURE__ */ jsx31(Skeleton, { label: "\u6B63\u5728\u52A0\u8F7D\u5206\u5E03" }) : !items.length ? /* @__PURE__ */ jsx31(EmptyState, { title: "\u6682\u65E0\u5206\u7C7B\u6570\u636E" }) : /* @__PURE__ */ jsxs28("div", { className: "qk-breakdown", children: [
    items.map((item) => /* @__PURE__ */ jsxs28("div", { className: "qk-breakdown-row", children: [
      /* @__PURE__ */ jsxs28("div", { children: [
        onSelect ? /* @__PURE__ */ jsx31(Button, { variant: "ghost", size: "sm", onClick: () => onSelect(item.id), children: item.label }) : /* @__PURE__ */ jsx31("span", { children: item.label }),
        /* @__PURE__ */ jsxs28("strong", { children: [
          item.value,
          /* @__PURE__ */ jsx31("small", { children: unit })
        ] })
      ] }),
      /* @__PURE__ */ jsx31(ProgressBar, { label: `${item.label}\u5360\u6BD4`, value: total ? Math.round(Math.max(0, item.value) / total * 100) : 0, showValue: false })
    ] }, item.id)),
    /* @__PURE__ */ jsxs28("p", { className: "qk-muted", children: [
      "\u5408\u8BA1 ",
      total,
      " ",
      unit,
      onSelect ? " \xB7 \u70B9\u51FB\u5206\u7C7B\u67E5\u770B\u9879\u76EE" : ""
    ] })
  ] }) });
});

// packages/ui/src/blocks/DangerZone.tsx
import { forwardRef as forwardRef32, useRef as useRef8, useState as useState7 } from "react";
import { TriangleAlert as TriangleAlert2 } from "lucide-react";
import { Fragment, jsx as jsx32, jsxs as jsxs29 } from "react/jsx-runtime";
var DangerZone = forwardRef32(function DangerZone2({ title, description, actionLabel, confirmText, confirmDescription, onConfirm, disabled = false, density, surfaceMode }, ref) {
  const attrs = useThemeAttributes({ density, surfaceMode }), [open, setOpen] = useState7(false), [value, setValue] = useState7(""), [pending, setPending] = useState7(false), [error, setError] = useState7("");
  const running = useRef8(false);
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
  return /* @__PURE__ */ jsxs29("section", { ...attrs, ref, "data-block": "DangerZone", className: "qk-danger-zone", children: [
    /* @__PURE__ */ jsxs29("div", { children: [
      /* @__PURE__ */ jsxs29("h2", { children: [
        /* @__PURE__ */ jsx32(TriangleAlert2, { className: "qk-icon", "aria-hidden": "true" }),
        title
      ] }),
      /* @__PURE__ */ jsx32("p", { children: description })
    ] }),
    /* @__PURE__ */ jsx32(Button, { className: "qk-danger-button", disabled: disabled || !confirmText.trim(), onClick: () => {
      setValue("");
      setError("");
      setOpen(true);
    }, children: actionLabel }),
    /* @__PURE__ */ jsxs29(Dialog, { title: actionLabel, description: confirmDescription, open, onOpenChange: (next) => {
      if (!running.current) setOpen(next);
    }, footer: /* @__PURE__ */ jsxs29(Fragment, { children: [
      /* @__PURE__ */ jsx32(Button, { disabled: pending, onClick: () => setOpen(false), children: "\u53D6\u6D88" }),
      /* @__PURE__ */ jsxs29(Button, { className: "qk-danger-button", loading: pending, disabled: value !== confirmText || disabled || !confirmText.trim(), onClick: confirm, children: [
        "\u786E\u8BA4",
        actionLabel
      ] })
    ] }), children: [
      /* @__PURE__ */ jsx32(Input, { label: `\u8BF7\u8F93\u5165\u201C${confirmText}\u201D\u4EE5\u786E\u8BA4`, disabled: pending, value, onChange: (e) => setValue(e.target.value), autoComplete: "off" }),
      error && /* @__PURE__ */ jsx32("p", { className: "qk-error qk-description", role: "alert", children: error })
    ] })
  ] });
});

// packages/ui/src/blocks/EntitySummary.tsx
import { forwardRef as forwardRef34, useId as useId12 } from "react";

// packages/ui/src/blocks/KpiRow.tsx
import { forwardRef as forwardRef33 } from "react";
import { Sparkles, ArrowUpRight as ArrowUpRight2 } from "lucide-react";
import { jsx as jsx33, jsxs as jsxs30 } from "react/jsx-runtime";
import { createElement } from "react";
function InsightNote({ insight }) {
  return /* @__PURE__ */ jsxs30("div", { className: "qk-insight", children: [
    /* @__PURE__ */ jsx33(Sparkles, { className: "qk-icon", "aria-hidden": "true" }),
    /* @__PURE__ */ jsxs30("div", { children: [
      /* @__PURE__ */ jsxs30("strong", { children: [
        "AI \u6458\u8981\u793A\u4F8B ",
        /* @__PURE__ */ jsx33("span", { children: "\u9700\u8D1F\u8D23\u4EBA\u786E\u8BA4" })
      ] }),
      /* @__PURE__ */ jsx33("p", { children: insight.text }),
      /* @__PURE__ */ jsx33("small", { children: insight.source })
    ] }),
    insight.onReview && /* @__PURE__ */ jsxs30(Button, { size: "sm", variant: "ghost", onClick: insight.onReview, children: [
      insight.actionLabel || "\u67E5\u770B\u4F9D\u636E",
      /* @__PURE__ */ jsx33(ArrowUpRight2, { className: "qk-icon", "aria-hidden": "true" })
    ] })
  ] });
}
var KpiRow = forwardRef33(function KpiRow2({ items, theme, insight, loading = false, density, surfaceMode }, ref) {
  const attrs = useThemeAttributes({ density, surfaceMode });
  return /* @__PURE__ */ jsxs30("section", { ...attrs, ref, "data-block": "KpiRow", "aria-label": "\u56DB\u9879\u6838\u5FC3\u6307\u6807", className: "qk-kpi-block", children: [
    /* @__PURE__ */ jsx33("div", { className: "qk-kpi-row", "data-layout": theme, children: items.map((item, i) => loading ? /* @__PURE__ */ jsx33("div", { className: "qk-panel", children: /* @__PURE__ */ jsx33(Skeleton, { label: `${item.label}\u6B63\u5728\u52A0\u8F7D` }) }, item.label) : /* @__PURE__ */ createElement(KpiCard, { ...item, key: item.label, emphasis: theme === "bento" && i === 0 })) }),
    insight && !loading && /* @__PURE__ */ jsx33(InsightNote, { insight })
  ] });
});

// packages/ui/src/blocks/EntitySummary.tsx
import { jsx as jsx34, jsxs as jsxs31 } from "react/jsx-runtime";
var EntitySummary = forwardRef34(function EntitySummary2({ title, description, status, statusLabel, fields, progress, insight, loading = false, density, surfaceMode }, ref) {
  const attrs = useThemeAttributes({ density, surfaceMode }), id = useId12();
  return /* @__PURE__ */ jsxs31("section", { ...attrs, ref, "data-block": "EntitySummary", className: "qk-panel qk-entity-summary", "aria-labelledby": id, children: [
    /* @__PURE__ */ jsxs31("header", { className: "qk-panel-heading", children: [
      /* @__PURE__ */ jsxs31("div", { children: [
        /* @__PURE__ */ jsx34("h2", { id, children: title }),
        /* @__PURE__ */ jsx34("p", { className: "qk-muted qk-description", children: description })
      ] }),
      /* @__PURE__ */ jsx34(Badge, { status, children: statusLabel })
    ] }),
    loading ? /* @__PURE__ */ jsx34(Skeleton, { label: "\u6B63\u5728\u52A0\u8F7D\u9879\u76EE\u6982\u51B5" }) : /* @__PURE__ */ jsx34("dl", { children: fields.map((f) => /* @__PURE__ */ jsxs31("div", { children: [
      /* @__PURE__ */ jsx34("dt", { children: f.label }),
      /* @__PURE__ */ jsx34("dd", { children: f.value })
    ] }, f.label)) }),
    !loading && progress !== void 0 && /* @__PURE__ */ jsxs31("div", { className: "qk-summary-progress", children: [
      /* @__PURE__ */ jsx34("span", { children: "\u4EA4\u4ED8\u8FDB\u5EA6" }),
      /* @__PURE__ */ jsx34(ProgressBar, { label: "\u4EA4\u4ED8\u8FDB\u5EA6", value: progress })
    ] }),
    !loading && insight && /* @__PURE__ */ jsx34(InsightNote, { insight })
  ] });
});

// packages/ui/src/blocks/PaginationBar.tsx
import { forwardRef as forwardRef35 } from "react";
import { jsx as jsx35, jsxs as jsxs32 } from "react/jsx-runtime";
var PaginationBar = forwardRef35(function PaginationBar2({ page, pageSize, total, selectedCount = 0, onPageChange, onPageSizeChange, density, surfaceMode }, ref) {
  const attrs = useThemeAttributes({ density, surfaceMode }), count = Math.ceil(total / pageSize);
  return /* @__PURE__ */ jsxs32("div", { ...attrs, ref, "data-block": "PaginationBar", className: "qk-pagination-bar", children: [
    /* @__PURE__ */ jsxs32("p", { className: "qk-muted", "aria-live": "polite", children: [
      "\u5171 ",
      total,
      " \u6761 \xB7 \u5DF2\u9009\u62E9 ",
      selectedCount,
      " \u6761"
    ] }),
    /* @__PURE__ */ jsx35(Select, { label: "\u6BCF\u9875\u6761\u6570", value: pageSize, onChange: (e) => onPageSizeChange(Number(e.target.value)), options: [{ value: "5", label: "5 \u6761 / \u9875" }, { value: "10", label: "10 \u6761 / \u9875" }, { value: "20", label: "20 \u6761 / \u9875" }] }),
    /* @__PURE__ */ jsx35(Pagination, { page, pageCount: count, onPageChange })
  ] });
});

// packages/ui/src/blocks/QueryBar.tsx
import { forwardRef as forwardRef36 } from "react";
import { jsx as jsx36 } from "react/jsx-runtime";
var QueryBar = forwardRef36(function QueryBar2(props, ref) {
  return /* @__PURE__ */ jsx36(FilterBar, { ...props, ref, "data-block": "QueryBar", className: "qk-panel qk-query-block" });
});

// packages/ui/src/blocks/RecordTable.tsx
import { forwardRef as forwardRef37 } from "react";
import { jsx as jsx37, jsxs as jsxs33 } from "react/jsx-runtime";
function RecordTableInner({ onClearSelection, total, ...props }, ref) {
  const attrs = useThemeAttributes({ density: props.density, surfaceMode: props.surfaceMode });
  return /* @__PURE__ */ jsxs33("div", { ...attrs, "data-block": "RecordTable", className: "qk-record-block", ref, children: [
    /* @__PURE__ */ jsxs33("div", { className: "qk-record-heading", children: [
      /* @__PURE__ */ jsx37("h2", { children: props.label }),
      /* @__PURE__ */ jsxs33("span", { className: "qk-muted", children: [
        "\u5171 ",
        total,
        " \u6761\u8BB0\u5F55"
      ] }),
      !!props.selectedIds?.length && /* @__PURE__ */ jsxs33(Button, { size: "sm", variant: "ghost", onClick: onClearSelection, children: [
        "\u6E05\u9664\u9009\u62E9\uFF08",
        props.selectedIds.length,
        "\uFF09"
      ] })
    ] }),
    /* @__PURE__ */ jsx37(DataTable, { ...props, showToolbar: false, showFooter: false, selectionLabel: "\u9009\u62E9\u5F53\u524D\u9875\u5168\u90E8\u884C", selectable: !!props.onSelectionChange, virtual: false }),
    /* @__PURE__ */ jsx37("p", { className: "qk-scroll-hint", children: "\u5DE6\u53F3\u6ED1\u52A8\u67E5\u770B\u5168\u90E8\u5B57\u6BB5" })
  ] });
}
var RecordTable = forwardRef37(RecordTableInner);

// packages/ui/src/blocks/RelatedRecords.tsx
import { forwardRef as forwardRef38 } from "react";
import { jsx as jsx38, jsxs as jsxs34 } from "react/jsx-runtime";
function RelatedRecordsInner({ title, description, ...props }, ref) {
  const attrs = useThemeAttributes({ density: props.density, surfaceMode: props.surfaceMode });
  return /* @__PURE__ */ jsxs34("div", { ...attrs, ref, "data-block": "RelatedRecords", className: "qk-related-block", children: [
    /* @__PURE__ */ jsxs34("header", { children: [
      /* @__PURE__ */ jsx38("h2", { children: title }),
      /* @__PURE__ */ jsx38("p", { className: "qk-muted", children: description })
    ] }),
    /* @__PURE__ */ jsx38(DataTable, { ...props, label: title, showToolbar: false, showFooter: false, virtual: false })
  ] });
}
var RelatedRecords = forwardRef38(RelatedRecordsInner);

// packages/ui/src/blocks/SettingsNav.tsx
import { forwardRef as forwardRef39 } from "react";
import { ChevronRight } from "lucide-react";
import { jsx as jsx39, jsxs as jsxs35 } from "react/jsx-runtime";
var SettingsNav = forwardRef39(function SettingsNav2({ items, activeId, onSelect, density, surfaceMode }, ref) {
  const attrs = useThemeAttributes({ density, surfaceMode });
  return /* @__PURE__ */ jsx39("nav", { ...attrs, ref, "data-block": "SettingsNav", className: "qk-settings-nav", "aria-label": "\u8BBE\u7F6E\u5206\u7EC4", children: items.map((item) => /* @__PURE__ */ jsxs35("a", { href: "#" + item.id, "aria-current": item.id === activeId ? "location" : void 0, onClick: (e) => {
    e.preventDefault();
    onSelect(item.id);
    document.getElementById(item.id)?.scrollIntoView({ block: "start", behavior: "auto" });
  }, children: [
    /* @__PURE__ */ jsxs35("span", { children: [
      /* @__PURE__ */ jsx39("strong", { children: item.label }),
      /* @__PURE__ */ jsx39("small", { children: item.description })
    ] }),
    /* @__PURE__ */ jsx39(ChevronRight, { className: "qk-icon", "aria-hidden": "true" })
  ] }, item.id)) });
});

// packages/ui/src/blocks/SettingsSection.tsx
import { forwardRef as forwardRef40 } from "react";
import { jsx as jsx40, jsxs as jsxs36 } from "react/jsx-runtime";
var SettingsSection = forwardRef40(function SettingsSection2({ id, title, description, fields, density, surfaceMode }, ref) {
  const attrs = useThemeAttributes({ density, surfaceMode });
  return /* @__PURE__ */ jsxs36("section", { ...attrs, ref, id, "data-block": "SettingsSection", className: "qk-panel qk-settings-section", "aria-labelledby": id + "-title", children: [
    /* @__PURE__ */ jsxs36("header", { children: [
      /* @__PURE__ */ jsx40("h2", { id: id + "-title", children: title }),
      /* @__PURE__ */ jsx40("p", { className: "qk-muted", children: description })
    ] }),
    /* @__PURE__ */ jsx40("div", { className: "qk-settings-fields", children: fields.map((f) => f.kind === "checkbox" ? /* @__PURE__ */ jsxs36("div", { className: "qk-settings-toggle", children: [
      /* @__PURE__ */ jsx40(Checkbox, { id: f.id, label: f.label, checked: f.value, disabled: f.disabled, onChange: (e) => f.onChange(e.target.checked), "aria-describedby": f.hint ? f.id + "-hint" : void 0 }),
      f.hint && /* @__PURE__ */ jsx40("p", { id: f.id + "-hint", className: "qk-muted", children: f.hint })
    ] }, f.id) : f.kind === "select" ? /* @__PURE__ */ jsx40(Select, { id: f.id, label: f.label, value: f.value, options: f.options, hint: f.hint, error: f.error, disabled: f.disabled, onChange: (e) => f.onChange(e.target.value) }, f.id) : /* @__PURE__ */ jsx40(Input, { id: f.id, label: f.label, type: f.type || "text", value: f.value, hint: f.hint, error: f.error, disabled: f.disabled, required: f.required, maxLength: f.maxLength, onChange: (e) => f.onChange(e.target.value) }, f.id)) })
  ] });
});

// packages/ui/src/blocks/TrendPanel.tsx
import { forwardRef as forwardRef41, useId as useId13 } from "react";
import { Fragment as Fragment2, jsx as jsx41, jsxs as jsxs37 } from "react/jsx-runtime";
var TrendPanel = forwardRef41(function TrendPanel2({ title, description, unit, points, loading = false, ...theme }, ref) {
  const id = useId13();
  const invalid = points.some((p) => !Number.isFinite(p.value) || p.target !== void 0 && !Number.isFinite(p.target));
  const values = points.flatMap((p) => [p.value, ...p.target === void 0 ? [] : [p.target]]);
  const min = invalid ? 0 : Math.floor(Math.min(0, ...values) / 10) * 10;
  const max = invalid ? 10 : Math.ceil(Math.max(1, ...values) / 10) * 10;
  const xy = (v, i) => [52 + i * 624 / Math.max(1, points.length - 1), 192 - (v - min) / (max - min) * 152];
  const line = points.map((p, i) => xy(p.value, i).join(",")).join(" ");
  const hasTarget = points.length > 0 && points.every((p) => p.target !== void 0);
  const target = points.map((p, i) => xy(p.target ?? 0, i).join(",")).join(" ");
  return /* @__PURE__ */ jsx41(ChartCard, { ...theme, ref, "data-block": "TrendPanel", title, description, legend: /* @__PURE__ */ jsxs37(Fragment2, { children: [
    /* @__PURE__ */ jsxs37("span", { children: [
      /* @__PURE__ */ jsx41("i", { className: "qk-line-key" }),
      "\u5B9E\u9645 \xB7 \u5B9E\u7EBF"
    ] }),
    hasTarget && /* @__PURE__ */ jsxs37("span", { children: [
      /* @__PURE__ */ jsx41("i", { className: "qk-line-key qk-line-target" }),
      "\u8BA1\u5212 \xB7 \u865A\u7EBF"
    ] }),
    /* @__PURE__ */ jsxs37("span", { children: [
      "\u5355\u4F4D\uFF1A",
      unit
    ] })
  ] }), children: loading ? /* @__PURE__ */ jsx41(Skeleton, { label: "\u6B63\u5728\u52A0\u8F7D\u8D8B\u52BF" }) : invalid ? /* @__PURE__ */ jsx41(EmptyState, { title: "\u8D8B\u52BF\u6570\u636E\u683C\u5F0F\u6709\u8BEF", description: "\u5B58\u5728\u65E0\u6548\u6570\u503C\uFF0C\u8BF7\u6838\u5BF9\u6570\u636E\u6765\u6E90\u540E\u91CD\u8BD5\u3002" }) : !points.length ? /* @__PURE__ */ jsx41(EmptyState, { title: "\u6682\u65E0\u8D8B\u52BF\u6570\u636E" }) : /* @__PURE__ */ jsxs37(Fragment2, { children: [
    /* @__PURE__ */ jsx41("div", { className: "qk-trend-scroll", children: /* @__PURE__ */ jsxs37("svg", { className: "qk-trend-chart", viewBox: "0 0 720 228", role: "img", "aria-labelledby": id, children: [
      /* @__PURE__ */ jsxs37("title", { id, children: [
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
      [0, 0.5, 1].map((r) => /* @__PURE__ */ jsxs37("g", { children: [
        /* @__PURE__ */ jsx41("line", { x1: "52", x2: "690", y1: 192 - r * 152, y2: 192 - r * 152, className: "qk-chart-grid" }),
        /* @__PURE__ */ jsx41("text", { x: "40", y: 196 - r * 152, textAnchor: "end", children: +(min + r * (max - min)).toFixed(1) })
      ] }, r)),
      hasTarget && /* @__PURE__ */ jsx41("polyline", { points: target, className: "qk-trend-target" }),
      /* @__PURE__ */ jsx41("polyline", { points: line, className: "qk-trend-line" }),
      points.map((p, i) => {
        const [x, y] = xy(p.value, i);
        return /* @__PURE__ */ jsxs37("g", { children: [
          /* @__PURE__ */ jsx41("circle", { cx: x, cy: y, r: "3", className: "qk-trend-dot" }),
          /* @__PURE__ */ jsx41("text", { x, y: "218", textAnchor: "middle", children: p.label })
        ] }, i);
      })
    ] }) }),
    /* @__PURE__ */ jsx41("p", { className: "qk-scroll-hint", children: "\u5DE6\u53F3\u6ED1\u52A8\u67E5\u770B\u5B8C\u6574\u8D8B\u52BF" }),
    /* @__PURE__ */ jsxs37("details", { className: "qk-chart-values", children: [
      /* @__PURE__ */ jsx41("summary", { children: "\u67E5\u770B\u56FE\u8868\u6570\u636E" }),
      /* @__PURE__ */ jsx41("div", { children: /* @__PURE__ */ jsxs37("table", { children: [
        /* @__PURE__ */ jsxs37("caption", { className: "qk-sr-only", children: [
          title,
          "\u7CBE\u786E\u503C\uFF0C\u5355\u4F4D",
          unit
        ] }),
        /* @__PURE__ */ jsx41("thead", { children: /* @__PURE__ */ jsxs37("tr", { children: [
          /* @__PURE__ */ jsx41("th", { scope: "col", children: "\u671F\u95F4" }),
          /* @__PURE__ */ jsx41("th", { scope: "col", children: "\u5B9E\u9645" }),
          hasTarget && /* @__PURE__ */ jsx41("th", { scope: "col", children: "\u8BA1\u5212" })
        ] }) }),
        /* @__PURE__ */ jsx41("tbody", { children: points.map((p, i) => /* @__PURE__ */ jsxs37("tr", { children: [
          /* @__PURE__ */ jsx41("th", { scope: "row", children: p.label }),
          /* @__PURE__ */ jsx41("td", { children: p.value }),
          hasTarget && /* @__PURE__ */ jsx41("td", { children: p.target })
        ] }, i)) })
      ] }) })
    ] })
  ] }) });
});

// packages/ui/src/recipes/Overview.tsx
import { forwardRef as forwardRef42 } from "react";
import { jsx as jsx42, jsxs as jsxs38 } from "react/jsx-runtime";
var Overview = forwardRef42(function Overview2({ header, kpis, trend, breakdown, activity, density, surfaceMode }, ref) {
  const attrs = useThemeAttributes({ density, surfaceMode });
  return /* @__PURE__ */ jsxs38("div", { ...attrs, ref, "data-recipe": "Overview", className: "qk-recipe", children: [
    /* @__PURE__ */ jsx42(PageHeader, { ...header }),
    /* @__PURE__ */ jsx42(KpiRow, { ...kpis }),
    /* @__PURE__ */ jsxs38("div", { className: "qk-overview-charts", children: [
      /* @__PURE__ */ jsx42(TrendPanel, { ...trend }),
      /* @__PURE__ */ jsx42(BreakdownPanel, { ...breakdown })
    ] }),
    /* @__PURE__ */ jsx42(ActivityFeed, { ...activity })
  ] });
});

// packages/ui/src/recipes/List.tsx
import { forwardRef as forwardRef43 } from "react";
import { jsx as jsx43, jsxs as jsxs39 } from "react/jsx-runtime";
function ListInner({ header, query, records, pagination, density, surfaceMode }, ref) {
  const attrs = useThemeAttributes({ density, surfaceMode });
  return /* @__PURE__ */ jsxs39("div", { ...attrs, ref, "data-recipe": "List", className: "qk-recipe", children: [
    /* @__PURE__ */ jsx43(PageHeader, { ...header }),
    /* @__PURE__ */ jsx43(QueryBar, { ...query }),
    /* @__PURE__ */ jsx43(RecordTable, { ...records }),
    /* @__PURE__ */ jsx43(PaginationBar, { ...pagination })
  ] });
}
var List = forwardRef43(ListInner);

// packages/ui/src/recipes/Detail.tsx
import { forwardRef as forwardRef44, useId as useId14 } from "react";
import { jsx as jsx44, jsxs as jsxs40 } from "react/jsx-runtime";
function DetailInner({ header, summary, activity, related, activeTab, onTabChange, density, surfaceMode }, ref) {
  const attrs = useThemeAttributes({ density, surfaceMode }), id = useId14();
  const tabs = [["timeline", "\u8FDB\u5C55\u65F6\u95F4\u7EBF"], ["related", "\u5173\u8054\u8BB0\u5F55"]];
  return /* @__PURE__ */ jsxs40("div", { ...attrs, ref, "data-recipe": "Detail", className: "qk-recipe", children: [
    /* @__PURE__ */ jsx44(PageHeader, { ...header }),
    /* @__PURE__ */ jsx44(EntitySummary, { ...summary }),
    /* @__PURE__ */ jsxs40("div", { className: "qk-detail-tabs", children: [
      /* @__PURE__ */ jsx44("div", { role: "tablist", "aria-label": "\u9879\u76EE\u8BE6\u60C5\u89C6\u56FE", className: "qk-tab-list", onKeyDown: (e) => {
        if (!["ArrowLeft", "ArrowRight", "Home", "End"].includes(e.key)) return;
        e.preventDefault();
        const next = e.key === "Home" ? "timeline" : e.key === "End" ? "related" : activeTab === "timeline" ? "related" : "timeline";
        onTabChange(next);
        document.getElementById(id + "-" + next)?.focus();
      }, children: tabs.map(([key, label]) => /* @__PURE__ */ jsxs40("button", { id: id + "-" + key, role: "tab", type: "button", "aria-selected": activeTab === key, "aria-controls": id + "-panel-" + key, tabIndex: activeTab === key ? 0 : -1, onClick: () => onTabChange(key), children: [
        label,
        key === "related" && /* @__PURE__ */ jsx44("span", { children: related.rows.length })
      ] }, key)) }),
      /* @__PURE__ */ jsx44("div", { id: id + "-panel-timeline", role: "tabpanel", "aria-labelledby": id + "-timeline", tabIndex: 0, hidden: activeTab !== "timeline", children: /* @__PURE__ */ jsx44(ActivityFeed, { ...activity, variant: "timeline" }) }),
      /* @__PURE__ */ jsx44("div", { id: id + "-panel-related", role: "tabpanel", "aria-labelledby": id + "-related", tabIndex: 0, hidden: activeTab !== "related", children: /* @__PURE__ */ jsx44(RelatedRecords, { ...related }) })
    ] })
  ] });
}
var Detail = forwardRef44(DetailInner);

// packages/ui/src/recipes/Settings.tsx
import { forwardRef as forwardRef45 } from "react";
import { jsx as jsx45, jsxs as jsxs41 } from "react/jsx-runtime";
import { createElement as createElement2 } from "react";
var Settings = forwardRef45(function Settings2({ header, navigation, sections, danger, dirty, savedMessage, onSave, onCancel, density, surfaceMode }, ref) {
  const attrs = useThemeAttributes({ density, surfaceMode });
  return /* @__PURE__ */ jsxs41("div", { ...attrs, ref, "data-recipe": "Settings", className: "qk-recipe", children: [
    /* @__PURE__ */ jsx45(PageHeader, { ...header }),
    /* @__PURE__ */ jsxs41("div", { className: "qk-settings-layout", children: [
      /* @__PURE__ */ jsx45(SettingsNav, { ...navigation }),
      /* @__PURE__ */ jsxs41("div", { className: "qk-settings-main", children: [
        /* @__PURE__ */ jsxs41("form", { onSubmit: (e) => {
          e.preventDefault();
          onSave();
        }, className: "qk-settings-form", children: [
          sections.map((section) => /* @__PURE__ */ createElement2(SettingsSection, { ...section, key: section.id })),
          /* @__PURE__ */ jsxs41("div", { className: "qk-settings-save", children: [
            /* @__PURE__ */ jsx45("p", { role: "status", children: dirty ? "\u6709\u5C1A\u672A\u4FDD\u5B58\u7684\u66F4\u6539" : savedMessage || "\u8BBE\u7F6E\u5DF2\u4FDD\u5B58" }),
            /* @__PURE__ */ jsxs41("div", { className: "qk-actions", children: [
              /* @__PURE__ */ jsx45(Button, { disabled: !dirty, onClick: onCancel, children: "\u53D6\u6D88\u66F4\u6539" }),
              /* @__PURE__ */ jsx45(Button, { type: "submit", variant: "primary", disabled: !dirty, children: "\u4FDD\u5B58\u8BBE\u7F6E" })
            ] })
          ] })
        ] }),
        /* @__PURE__ */ jsx45(DangerZone, { ...danger })
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
export {
  ActivityFeed,
  AppShell,
  Avatar,
  Badge,
  BreakdownPanel,
  Button,
  ChartCard,
  Checkbox,
  CommandPalette,
  DangerZone,
  DataTable,
  Detail,
  DetailPanel,
  Dialog,
  Drawer,
  EmptyState,
  EntitySummary,
  FilterBar,
  Input,
  KpiCard,
  KpiRow,
  List,
  NavGroup,
  Overview,
  PageHeader,
  Pagination,
  PaginationBar,
  Popover,
  ProgressBar,
  QueryBar,
  RecordTable,
  RelatedRecords,
  Select,
  Settings,
  SettingsNav,
  SettingsSection,
  Skeleton,
  Sparkline,
  StatTile,
  StatusDot,
  Tag,
  ThemeProvider,
  Toast,
  Tooltip,
  TrendPanel,
  blockCatalog,
  normalizeTheme,
  recipeCatalog,
  statusIcons
};
