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

// packages/theme/src/tailwind.preset.ts
var tailwind_preset_exports = {};
__export(tailwind_preset_exports, {
  default: () => tailwind_preset_default
});
module.exports = __toCommonJS(tailwind_preset_exports);
var preset = {
  "theme": {
    "colors": {
      "surface-base": "var(--surface-base)",
      "surface-raised": "var(--surface-raised)",
      "surface-overlay": "var(--surface-overlay)",
      "surface-hover": "var(--surface-hover)",
      "fg-primary": "var(--fg-primary)",
      "fg-muted": "var(--fg-muted)",
      "fg-subtle": "var(--fg-subtle)",
      "fg-inverse": "var(--fg-inverse)",
      "border-subtle": "var(--border-subtle)",
      "border-default": "var(--border-default)",
      "border-strong": "var(--border-strong)",
      "accent-default": "var(--accent-default)",
      "accent-soft": "var(--accent-soft)",
      "accent-fg": "var(--accent-fg)",
      "accent-solid": "var(--accent-solid)",
      "accent-hover": "var(--accent-hover)",
      "status-success": "var(--status-success)",
      "status-success-bg": "var(--status-success-bg)",
      "status-warning": "var(--status-warning)",
      "status-warning-bg": "var(--status-warning-bg)",
      "status-danger": "var(--status-danger)",
      "status-danger-bg": "var(--status-danger-bg)",
      "status-info": "var(--status-info)",
      "status-info-bg": "var(--status-info-bg)",
      "chart-primary": "var(--chart-primary)",
      "chart-secondary": "var(--chart-secondary)",
      "hero-bg": "var(--hero-bg)",
      "hero-fg": "var(--hero-fg)",
      "hero-muted": "var(--hero-muted)",
      "focus-ring": "var(--focus-ring)"
    },
    "fontFamily": {
      "sans": "var(--font-body)",
      "display": "var(--font-display)",
      "mono": "var(--font-numeric)"
    },
    "fontSize": {
      "micro": "var(--font-size-micro)",
      "caption": "var(--font-size-caption)",
      "body": "var(--font-size-body)",
      "label": "var(--font-size-label)",
      "section": "var(--font-size-section)",
      "title": "var(--font-size-title)",
      "display": "var(--font-size-display)",
      "kpi": "var(--font-size-kpi)"
    },
    "fontWeight": {
      "regular": "var(--weight-regular)",
      "medium": "var(--weight-medium)",
      "semibold": "var(--weight-semibold)",
      "bold": "var(--weight-bold)"
    },
    "lineHeight": {
      "body": "var(--line-body)",
      "tight": "var(--line-tight)",
      "display": "var(--line-display)"
    },
    "borderRadius": {
      "none": "var(--radius-none)",
      "control": "var(--radius-control)",
      "card": "var(--radius-card)",
      "full": "var(--radius-pill)"
    },
    "boxShadow": {
      "panel": "var(--shadow-panel)",
      "overlay": "var(--shadow-overlay)"
    },
    "borderWidth": {
      "DEFAULT": "var(--border-width)",
      "strong": "var(--border-emphasis)"
    },
    "spacing": {
      "0": "var(--space-0)",
      "1": "var(--space-1)",
      "2": "var(--space-2)",
      "3": "var(--space-3)",
      "4": "var(--space-4)",
      "5": "var(--space-5)",
      "6": "var(--space-6)",
      "8": "var(--space-8)",
      "10": "var(--space-10)",
      "12": "var(--space-12)",
      "16": "var(--space-16)",
      "0.5": "var(--space-0_5)",
      "1.5": "var(--space-1_5)"
    }
  }
};
var tailwind_preset_default = preset;
