export declare const tokens: {
    readonly common: {
        readonly "font-body": "Inter, -apple-system, BlinkMacSystemFont, \"Segoe UI\", \"PingFang SC\", \"Microsoft YaHei\", sans-serif";
        readonly "font-display": "Inter, -apple-system, BlinkMacSystemFont, \"Segoe UI\", \"PingFang SC\", sans-serif";
        readonly "font-numeric": "ui-monospace, \"SFMono-Regular\", Menlo, Monaco, Consolas, \"Liberation Mono\", \"Noto Sans Mono CJK SC\", monospace";
        readonly "font-size-micro": "11px";
        readonly "font-size-caption": "12px";
        readonly "font-size-body": "13px";
        readonly "font-size-label": "14px";
        readonly "font-size-section": "16px";
        readonly "font-size-title": "26px";
        readonly "font-size-display": "34px";
        readonly "font-size-kpi": "30px";
        readonly "line-body": "1.55";
        readonly "line-tight": "1.2";
        readonly "line-display": "1.05";
        readonly "weight-regular": "400";
        readonly "weight-medium": "500";
        readonly "weight-semibold": "600";
        readonly "weight-bold": "700";
        readonly "tracking-tight": "-0.035em";
        readonly "tracking-label": "0.1em";
        readonly "tracking-normal": "0em";
        readonly "radius-control": "6px";
        readonly "radius-card": "6px";
        readonly "radius-pill": "999px";
        readonly "radius-none": "0px";
        readonly "border-width": "1px";
        readonly "border-emphasis": "2px";
        readonly "stroke-chart": "2.5px";
        readonly "stroke-icon": "1.6px";
        readonly "shadow-panel": "none";
        readonly "shadow-overlay": "0 12px 36px hsl(220 20% 10% / 0.14)";
        readonly "space-0": "0px";
        readonly "space-0_5": "2px";
        readonly "space-1": "4px";
        readonly "space-1_5": "6px";
        readonly "space-2": "8px";
        readonly "space-3": "12px";
        readonly "space-4": "16px";
        readonly "space-5": "20px";
        readonly "space-6": "24px";
        readonly "space-8": "32px";
        readonly "space-10": "40px";
        readonly "space-12": "48px";
        readonly "space-16": "64px";
        readonly "panel-padding": "20px";
        readonly "page-padding": "32px";
        readonly "grid-gap": "16px";
        readonly "row-height": "45px";
        readonly "control-height": "34px";
        readonly "sidebar-width": "192px";
        readonly "topbar-height": "56px";
        readonly "motion-duration": "160ms";
        readonly "motion-easing": "cubic-bezier(0.2, 0, 0, 1)";
        readonly "blur-panel": "0px";
        readonly "panel-alpha": "1";
        readonly "ambient-background": "none";
        readonly "ai-border": "linear-gradient(115deg, hsl(255 68% 60%), hsl(203 80% 46%), hsl(284 64% 58%))";
        readonly "chart-height": "176px";
        readonly "chart-min-width": "460px";
        readonly "table-min-width": "800px";
        readonly "max-frame-width": "1800px";
        readonly "icon-size": "16px";
        readonly "icon-size-small": "13px";
        readonly "icon-size-large": "22px";
        readonly "spark-width": "88px";
        readonly "spark-height": "32px";
        readonly "progress-width": "76px";
        readonly "progress-height": "4px";
        readonly "sidebar-logo-size": "30px";
        readonly "avatar-size": "28px";
        readonly "empty-symbol-size": "44px";
        readonly "tracking-terminal": "0.035em";
        readonly "layer-sticky": "30";
        readonly "layer-overlay": "50";
        readonly "opacity-fill": "0.07";
        readonly "opacity-muted": "0.6";
        readonly "opacity-disabled": "0.4";
        readonly "shadow-selection": "inset 0 0 0 var(--border-width) var(--fg-primary)";
        readonly "category-manufacturing": "hsl(223 64% 41%)";
        readonly "category-retail": "hsl(280 44% 42%)";
        readonly "category-tech": "hsl(175 60% 29%)";
        readonly "category-services": "hsl(25 65% 40%)";
        readonly "category-logistics": "hsl(150 35% 32%)";
        readonly "feedback-duration": "3600ms";
        readonly "brand-ink": "hsl(213.3333 72.0000% 9.8039%)";
        readonly "brand-blue": "hsl(220.3687 98.1900% 56.6667%)";
        readonly "brand-light-blue": "hsl(220.7812 100.0000% 74.9020%)";
        readonly "brand-orange": "hsl(16.0396 100.0000% 60.3922%)";
        readonly "brand-steel": "hsl(211.5789 31.1475% 88.0392%)";
        readonly "brand-cold-white": "hsl(210.0000 37.5000% 96.8627%)";
        readonly "brand-muted": "hsl(211.0345 29.5918% 38.4314%)";
        readonly "accent-solid": "var(--accent-default)";
        readonly "brand-paper": "hsl(0 0% 100%)";
        readonly "brand-action-text": "color-mix(in srgb, var(--brand-blue) 88%, var(--brand-ink))";
        readonly "status-warning-indicator": "var(--status-warning)";
        readonly "client-blue": "var(--brand-blue)";
        readonly "client-light-blue": "var(--brand-light-blue)";
        readonly "client-action-text": "var(--brand-action-text)";
        readonly "table-cell-padding-y": "var(--space-1)";
        readonly "table-line-height": "var(--line-body)";
        readonly "motion-fast": "100ms";
        readonly "motion-slow": "240ms";
        readonly "motion-easing-exit": "cubic-bezier(0.4, 0, 1, 1)";
        readonly "shadow-none": "none";
        readonly "shadow-raised": "var(--shadow-panel)";
        readonly "shadow-floating": "var(--shadow-overlay)";
        readonly "layer-base": "0";
        readonly "layer-panel": "1";
        readonly "layer-popover": "40";
        readonly "layer-toast": "60";
        readonly "focus-offset": "2px";
        readonly "parameter-panel-width": "1800px";
        readonly "control-height-sm": "calc(var(--control-height) - var(--space-1))";
        readonly "control-height-lg": "calc(var(--control-height) + var(--space-1))";
        readonly "dialog-width": "calc(var(--space-16) * 9)";
        readonly "drawer-width": "calc(var(--space-16) * 7)";
        readonly "tooltip-width": "calc(var(--space-16) * 4)";
        readonly "table-viewport-height": "calc(var(--space-16) * 6)";
        readonly "table-primary-width": "calc(var(--space-16) * 3)";
        readonly "table-select-width": "var(--space-10)";
        readonly "table-header-height": "var(--space-10)";
        readonly "virtual-overscan": "4";
        readonly "toast-width": "calc(var(--space-16) * 6)";
        readonly "shell-collapsed-width": "var(--space-16)";
        readonly "skeleton-height": "var(--space-4)";
        readonly "avatar-size-lg": "var(--space-10)";
        readonly "chart-height-small": "var(--space-12)";
        readonly "recipe-content-width": "calc(var(--space-16) * 24)";
        readonly "settings-nav-width": "calc(var(--space-16) * 3)";
        readonly "recipe-chart-height": "calc(var(--space-16) * 4)";
        readonly "recipe-chart-tick": "var(--font-size-body)";
        readonly "recipe-chart-min-width": "720px";
        readonly "recipe-table-width": "calc(var(--space-16) * 17)";
    };
    readonly systems: {
        readonly bento: {
            readonly id: 6;
            readonly intent: "大指标与趋势并置，小模块组成经营总览。";
            readonly structure: {
                readonly "radius-card": "var(--radius-card-base)";
                readonly "radius-control": "var(--radius-control-base)";
                readonly "font-size-kpi": "36px";
                readonly "ai-border": "linear-gradient(115deg, var(--client-blue), var(--client-light-blue), var(--client-blue))";
                readonly "font-size-kpi-hero": "64px";
                readonly "font-size-kpi-hero-small": "48px";
                readonly "hero-spark-height": "72px";
                readonly "radius-card-base": "20px";
                readonly "radius-control-base": "10px";
            };
            readonly colors: {
                readonly light: {
                    readonly surface: {
                        readonly base: "var(--brand-cold-white)";
                        readonly raised: "var(--brand-paper)";
                        readonly overlay: "color-mix(in srgb, var(--brand-steel) 42%, var(--brand-paper))";
                        readonly hover: "color-mix(in srgb, var(--brand-steel) 58%, var(--brand-paper))";
                    };
                    readonly fg: {
                        readonly primary: "var(--brand-ink)";
                        readonly muted: "var(--brand-muted)";
                        readonly subtle: "var(--brand-muted)";
                        readonly inverse: "var(--brand-paper)";
                    };
                    readonly border: {
                        readonly subtle: "color-mix(in srgb, var(--brand-steel) 60%, var(--brand-paper))";
                        readonly default: "var(--brand-steel)";
                        readonly strong: "color-mix(in srgb, var(--brand-muted) 58%, var(--brand-steel))";
                    };
                    readonly accent: {
                        readonly default: "var(--client-action-text)";
                        readonly soft: "color-mix(in srgb, var(--client-blue) 7%, var(--brand-paper))";
                        readonly fg: "var(--brand-paper)";
                        readonly solid: "var(--client-blue)";
                        readonly hover: "color-mix(in srgb, var(--client-blue) 88%, var(--brand-ink))";
                    };
                    readonly status: {
                        readonly success: {
                            readonly fg: "var(--brand-muted)";
                            readonly bg: "var(--brand-cold-white)";
                        };
                        readonly warning: {
                            readonly fg: "var(--brand-ink)";
                            readonly bg: "var(--brand-orange)";
                        };
                        readonly danger: {
                            readonly fg: "hsl(0 63% 39%)";
                            readonly bg: "hsl(0 80% 97%)";
                        };
                        readonly info: {
                            readonly fg: "var(--client-action-text)";
                            readonly bg: "color-mix(in srgb, var(--client-blue) 7%, var(--brand-paper))";
                        };
                    };
                    readonly chart: {
                        readonly primary: "var(--client-action-text)";
                        readonly secondary: "var(--brand-muted)";
                    };
                    readonly hero: {
                        readonly bg: "var(--brand-ink)";
                        readonly fg: "var(--brand-cold-white)";
                        readonly muted: "var(--brand-steel)";
                    };
                    readonly focus: {
                        readonly ring: "var(--client-action-text)";
                    };
                };
                readonly dark: {
                    readonly surface: {
                        readonly base: "var(--brand-ink)";
                        readonly raised: "color-mix(in srgb, var(--brand-ink) 91%, var(--brand-muted))";
                        readonly overlay: "color-mix(in srgb, var(--brand-ink) 78%, var(--brand-muted))";
                        readonly hover: "color-mix(in srgb, var(--brand-ink) 65%, var(--brand-muted))";
                    };
                    readonly fg: {
                        readonly primary: "var(--brand-cold-white)";
                        readonly muted: "var(--brand-steel)";
                        readonly subtle: "color-mix(in srgb, var(--brand-steel) 86%, var(--brand-ink))";
                        readonly inverse: "var(--brand-ink)";
                    };
                    readonly border: {
                        readonly subtle: "color-mix(in srgb, var(--brand-muted) 60%, var(--brand-ink))";
                        readonly default: "color-mix(in srgb, var(--brand-muted) 80%, var(--brand-ink))";
                        readonly strong: "var(--brand-muted)";
                    };
                    readonly accent: {
                        readonly default: "var(--client-light-blue)";
                        readonly soft: "color-mix(in srgb, var(--client-blue) 14%, var(--brand-ink))";
                        readonly fg: "var(--brand-paper)";
                        readonly solid: "var(--client-blue)";
                        readonly hover: "color-mix(in srgb, var(--client-blue) 88%, var(--brand-ink))";
                    };
                    readonly status: {
                        readonly success: {
                            readonly fg: "var(--brand-steel)";
                            readonly bg: "color-mix(in srgb, var(--brand-muted) 18%, var(--brand-ink))";
                        };
                        readonly warning: {
                            readonly fg: "var(--brand-ink)";
                            readonly bg: "var(--brand-orange)";
                        };
                        readonly danger: {
                            readonly fg: "hsl(0 82% 76%)";
                            readonly bg: "hsl(0 32% 14%)";
                        };
                        readonly info: {
                            readonly fg: "var(--client-light-blue)";
                            readonly bg: "color-mix(in srgb, var(--client-blue) 14%, var(--brand-ink))";
                        };
                    };
                    readonly chart: {
                        readonly primary: "var(--client-light-blue)";
                        readonly secondary: "var(--brand-steel)";
                    };
                    readonly hero: {
                        readonly bg: "var(--brand-ink)";
                        readonly fg: "var(--brand-cold-white)";
                        readonly muted: "var(--brand-steel)";
                    };
                    readonly focus: {
                        readonly ring: "var(--client-light-blue)";
                    };
                };
            };
            readonly effects: {
                readonly light: {
                    readonly "ambient-background": "none";
                    readonly "shadow-panel": "0 2px 4px hsl(213.3333 72% 9.8039% / 0.035)";
                    readonly "shadow-overlay": "0 12px 36px hsl(213.3333 72% 9.8039% / 0.16)";
                    readonly "status-warning-indicator": "var(--brand-ink)";
                };
                readonly dark: {
                    readonly "ambient-background": "none";
                    readonly "shadow-panel": "0 2px 4px hsl(213.3333 72% 2% / 0.2)";
                    readonly "shadow-overlay": "0 12px 36px hsl(213.3333 72% 9.8039% / 0.4)";
                    readonly "status-warning-indicator": "var(--brand-orange)";
                };
            };
            readonly density: {
                readonly comfortable: {
                    readonly "page-padding": "32px";
                    readonly "panel-padding": "24px";
                    readonly "grid-gap": "16px";
                    readonly "row-height": "48px";
                    readonly "control-height": "36px";
                    readonly "table-cell-padding-y": "4px";
                    readonly "table-line-height": "1.5";
                };
                readonly compact: {
                    readonly "page-padding": "24px";
                    readonly "panel-padding": "16px";
                    readonly "grid-gap": "12px";
                    readonly "row-height": "40px";
                    readonly "control-height": "32px";
                    readonly "table-cell-padding-y": "2px";
                    readonly "table-line-height": "1.35";
                };
            };
            readonly parameters: {
                readonly accentHue: {
                    readonly $ref: "parameterPolicy.accentHue";
                };
                readonly density: {
                    readonly $ref: "parameterPolicy.density";
                };
                readonly radiusScale: {
                    readonly $ref: "parameterPolicy.radiusScale";
                };
                readonly surfaceMode: {
                    readonly $ref: "parameterPolicy.surfaceMode";
                };
            };
            readonly defaults: {
                readonly accentHue: "brand";
                readonly density: "comfortable";
                readonly radiusScale: 1;
                readonly surfaceMode: "light";
            };
        };
        readonly glass: {
            readonly id: 7;
            readonly intent: "以玻璃层次营造空间，用稳定底色守住可读性。";
            readonly structure: {
                readonly "radius-card": "var(--radius-card-base)";
                readonly "radius-control": "var(--radius-control-base)";
                readonly "panel-alpha": "0.90";
                readonly "blur-panel": "24px";
                readonly "ai-border": "linear-gradient(115deg, var(--client-blue), var(--client-light-blue), var(--client-blue))";
                readonly "radius-card-base": "14px";
                readonly "radius-control-base": "8px";
            };
            readonly colors: {
                readonly light: {
                    readonly surface: {
                        readonly base: "var(--brand-cold-white)";
                        readonly raised: "var(--brand-paper)";
                        readonly overlay: "color-mix(in srgb, var(--brand-steel) 42%, var(--brand-paper))";
                        readonly hover: "color-mix(in srgb, var(--brand-steel) 58%, var(--brand-paper))";
                    };
                    readonly fg: {
                        readonly primary: "var(--brand-ink)";
                        readonly muted: "color-mix(in srgb, var(--brand-muted) 80%, var(--brand-ink))";
                        readonly subtle: "color-mix(in srgb, var(--brand-muted) 80%, var(--brand-ink))";
                        readonly inverse: "var(--brand-paper)";
                    };
                    readonly border: {
                        readonly subtle: "color-mix(in srgb, var(--brand-steel) 60%, var(--brand-paper))";
                        readonly default: "var(--brand-steel)";
                        readonly strong: "color-mix(in srgb, var(--brand-muted) 58%, var(--brand-steel))";
                    };
                    readonly accent: {
                        readonly default: "var(--client-action-text)";
                        readonly soft: "color-mix(in srgb, var(--client-blue) 7%, var(--brand-paper))";
                        readonly fg: "var(--brand-paper)";
                        readonly solid: "var(--client-blue)";
                        readonly hover: "color-mix(in srgb, var(--client-blue) 88%, var(--brand-ink))";
                    };
                    readonly status: {
                        readonly success: {
                            readonly fg: "var(--brand-muted)";
                            readonly bg: "var(--brand-cold-white)";
                        };
                        readonly warning: {
                            readonly fg: "var(--brand-ink)";
                            readonly bg: "var(--brand-orange)";
                        };
                        readonly danger: {
                            readonly fg: "hsl(0 63% 39%)";
                            readonly bg: "hsl(0 80% 97%)";
                        };
                        readonly info: {
                            readonly fg: "var(--client-action-text)";
                            readonly bg: "color-mix(in srgb, var(--client-blue) 7%, var(--brand-paper))";
                        };
                    };
                    readonly chart: {
                        readonly primary: "var(--client-action-text)";
                        readonly secondary: "var(--brand-muted)";
                    };
                    readonly hero: {
                        readonly bg: "var(--brand-ink)";
                        readonly fg: "var(--brand-cold-white)";
                        readonly muted: "var(--brand-steel)";
                    };
                    readonly focus: {
                        readonly ring: "var(--client-action-text)";
                    };
                };
                readonly dark: {
                    readonly surface: {
                        readonly base: "var(--brand-ink)";
                        readonly raised: "color-mix(in srgb, var(--brand-ink) 91%, var(--brand-muted))";
                        readonly overlay: "color-mix(in srgb, var(--brand-ink) 78%, var(--brand-muted))";
                        readonly hover: "color-mix(in srgb, var(--brand-ink) 65%, var(--brand-muted))";
                    };
                    readonly fg: {
                        readonly primary: "var(--brand-cold-white)";
                        readonly muted: "var(--brand-steel)";
                        readonly subtle: "color-mix(in srgb, var(--brand-steel) 86%, var(--brand-ink))";
                        readonly inverse: "var(--brand-ink)";
                    };
                    readonly border: {
                        readonly subtle: "color-mix(in srgb, var(--brand-muted) 60%, var(--brand-ink))";
                        readonly default: "color-mix(in srgb, var(--brand-muted) 80%, var(--brand-ink))";
                        readonly strong: "var(--brand-muted)";
                    };
                    readonly accent: {
                        readonly default: "var(--client-light-blue)";
                        readonly soft: "color-mix(in srgb, var(--client-blue) 14%, var(--brand-ink))";
                        readonly fg: "var(--brand-paper)";
                        readonly solid: "var(--client-blue)";
                        readonly hover: "color-mix(in srgb, var(--client-blue) 88%, var(--brand-ink))";
                    };
                    readonly status: {
                        readonly success: {
                            readonly fg: "var(--brand-steel)";
                            readonly bg: "color-mix(in srgb, var(--brand-muted) 18%, var(--brand-ink))";
                        };
                        readonly warning: {
                            readonly fg: "var(--brand-ink)";
                            readonly bg: "var(--brand-orange)";
                        };
                        readonly danger: {
                            readonly fg: "hsl(0 82% 76%)";
                            readonly bg: "hsl(0 32% 14%)";
                        };
                        readonly info: {
                            readonly fg: "var(--client-light-blue)";
                            readonly bg: "color-mix(in srgb, var(--client-blue) 14%, var(--brand-ink))";
                        };
                    };
                    readonly chart: {
                        readonly primary: "var(--client-light-blue)";
                        readonly secondary: "var(--brand-steel)";
                    };
                    readonly hero: {
                        readonly bg: "var(--brand-ink)";
                        readonly fg: "var(--brand-cold-white)";
                        readonly muted: "var(--brand-steel)";
                    };
                    readonly focus: {
                        readonly ring: "var(--client-light-blue)";
                    };
                };
            };
            readonly effects: {
                readonly light: {
                    readonly "ambient-background": "radial-gradient(ellipse at 10% 2%, color-mix(in srgb, var(--client-blue) 4%, transparent), transparent 48%), radial-gradient(ellipse at 96% 38%, color-mix(in srgb, var(--client-light-blue) 6%, transparent), transparent 48%)";
                    readonly "shadow-panel": "0 8px 32px hsl(213.3333 72% 9.8039% / 0.08), inset 0 1px 0 hsl(0 0% 100% / 0.8)";
                    readonly "shadow-overlay": "0 12px 36px hsl(213.3333 72% 9.8039% / 0.16)";
                    readonly "status-warning-indicator": "var(--brand-ink)";
                };
                readonly dark: {
                    readonly "ambient-background": "radial-gradient(ellipse at 10% 2%, color-mix(in srgb, var(--client-blue) 24%, transparent), transparent 48%), radial-gradient(ellipse at 96% 38%, color-mix(in srgb, var(--client-light-blue) 9%, transparent), transparent 48%)";
                    readonly "shadow-panel": "0 8px 32px hsl(213.3333 72% 9.8039% / 0.22), inset 0 1px 0 hsl(220.7812 100% 74.9020% / 0.14)";
                    readonly "shadow-overlay": "0 12px 36px hsl(213.3333 72% 9.8039% / 0.4)";
                    readonly "status-warning-indicator": "var(--brand-orange)";
                };
            };
            readonly density: {
                readonly comfortable: {
                    readonly "page-padding": "32px";
                    readonly "panel-padding": "20px";
                    readonly "grid-gap": "16px";
                    readonly "row-height": "48px";
                    readonly "control-height": "36px";
                    readonly "table-cell-padding-y": "4px";
                    readonly "table-line-height": "1.5";
                };
                readonly compact: {
                    readonly "page-padding": "24px";
                    readonly "panel-padding": "16px";
                    readonly "grid-gap": "12px";
                    readonly "row-height": "40px";
                    readonly "control-height": "32px";
                    readonly "table-cell-padding-y": "2px";
                    readonly "table-line-height": "1.35";
                };
            };
            readonly parameters: {
                readonly accentHue: {
                    readonly $ref: "parameterPolicy.accentHue";
                };
                readonly density: {
                    readonly $ref: "parameterPolicy.density";
                };
                readonly radiusScale: {
                    readonly $ref: "parameterPolicy.radiusScale";
                };
                readonly surfaceMode: {
                    readonly $ref: "parameterPolicy.surfaceMode";
                };
            };
            readonly defaults: {
                readonly accentHue: "brand";
                readonly density: "comfortable";
                readonly radiusScale: 1;
                readonly surfaceMode: "dark";
            };
        };
        readonly ambient: {
            readonly id: 10;
            readonly intent: "指标轻量呈现，AI 建议紧贴项目操作区。";
            readonly structure: {
                readonly "radius-card": "var(--radius-card-base)";
                readonly "radius-control": "var(--radius-control-base)";
                readonly "ai-border": "linear-gradient(115deg, var(--client-blue), var(--client-light-blue), var(--client-blue))";
                readonly "font-size-kpi": "26px";
                readonly "radius-card-base": "10px";
                readonly "radius-control-base": "7px";
                readonly "panel-alpha": "1";
                readonly "blur-panel": "0px";
            };
            readonly colors: {
                readonly light: {
                    readonly surface: {
                        readonly base: "var(--brand-paper)";
                        readonly raised: "var(--brand-paper)";
                        readonly overlay: "color-mix(in srgb, var(--brand-steel) 42%, var(--brand-paper))";
                        readonly hover: "color-mix(in srgb, var(--brand-steel) 58%, var(--brand-paper))";
                    };
                    readonly fg: {
                        readonly primary: "var(--brand-ink)";
                        readonly muted: "var(--brand-muted)";
                        readonly subtle: "var(--brand-muted)";
                        readonly inverse: "var(--brand-paper)";
                    };
                    readonly border: {
                        readonly subtle: "color-mix(in srgb, var(--brand-steel) 60%, var(--brand-paper))";
                        readonly default: "var(--brand-steel)";
                        readonly strong: "color-mix(in srgb, var(--brand-muted) 58%, var(--brand-steel))";
                    };
                    readonly accent: {
                        readonly default: "var(--client-action-text)";
                        readonly soft: "color-mix(in srgb, var(--client-blue) 7%, var(--brand-paper))";
                        readonly fg: "var(--brand-paper)";
                        readonly solid: "var(--client-blue)";
                        readonly hover: "color-mix(in srgb, var(--client-blue) 88%, var(--brand-ink))";
                    };
                    readonly status: {
                        readonly success: {
                            readonly fg: "var(--brand-muted)";
                            readonly bg: "var(--brand-cold-white)";
                        };
                        readonly warning: {
                            readonly fg: "var(--brand-ink)";
                            readonly bg: "var(--brand-orange)";
                        };
                        readonly danger: {
                            readonly fg: "hsl(0 63% 39%)";
                            readonly bg: "hsl(0 80% 97%)";
                        };
                        readonly info: {
                            readonly fg: "var(--client-action-text)";
                            readonly bg: "color-mix(in srgb, var(--client-blue) 7%, var(--brand-paper))";
                        };
                    };
                    readonly chart: {
                        readonly primary: "var(--client-action-text)";
                        readonly secondary: "var(--brand-muted)";
                    };
                    readonly hero: {
                        readonly bg: "var(--brand-ink)";
                        readonly fg: "var(--brand-cold-white)";
                        readonly muted: "var(--brand-steel)";
                    };
                    readonly focus: {
                        readonly ring: "var(--client-action-text)";
                    };
                };
                readonly dark: {
                    readonly surface: {
                        readonly base: "var(--brand-ink)";
                        readonly raised: "color-mix(in srgb, var(--brand-ink) 91%, var(--brand-muted))";
                        readonly overlay: "color-mix(in srgb, var(--brand-ink) 78%, var(--brand-muted))";
                        readonly hover: "color-mix(in srgb, var(--brand-ink) 65%, var(--brand-muted))";
                    };
                    readonly fg: {
                        readonly primary: "var(--brand-cold-white)";
                        readonly muted: "var(--brand-steel)";
                        readonly subtle: "color-mix(in srgb, var(--brand-steel) 86%, var(--brand-ink))";
                        readonly inverse: "var(--brand-ink)";
                    };
                    readonly border: {
                        readonly subtle: "color-mix(in srgb, var(--brand-muted) 60%, var(--brand-ink))";
                        readonly default: "color-mix(in srgb, var(--brand-muted) 80%, var(--brand-ink))";
                        readonly strong: "var(--brand-muted)";
                    };
                    readonly accent: {
                        readonly default: "var(--client-light-blue)";
                        readonly soft: "color-mix(in srgb, var(--client-blue) 14%, var(--brand-ink))";
                        readonly fg: "var(--brand-paper)";
                        readonly solid: "var(--client-blue)";
                        readonly hover: "color-mix(in srgb, var(--client-blue) 88%, var(--brand-ink))";
                    };
                    readonly status: {
                        readonly success: {
                            readonly fg: "var(--brand-steel)";
                            readonly bg: "color-mix(in srgb, var(--brand-muted) 18%, var(--brand-ink))";
                        };
                        readonly warning: {
                            readonly fg: "var(--brand-ink)";
                            readonly bg: "var(--brand-orange)";
                        };
                        readonly danger: {
                            readonly fg: "hsl(0 82% 76%)";
                            readonly bg: "hsl(0 32% 14%)";
                        };
                        readonly info: {
                            readonly fg: "var(--client-light-blue)";
                            readonly bg: "color-mix(in srgb, var(--client-blue) 14%, var(--brand-ink))";
                        };
                    };
                    readonly chart: {
                        readonly primary: "var(--client-light-blue)";
                        readonly secondary: "var(--brand-steel)";
                    };
                    readonly hero: {
                        readonly bg: "var(--brand-ink)";
                        readonly fg: "var(--brand-cold-white)";
                        readonly muted: "var(--brand-steel)";
                    };
                    readonly focus: {
                        readonly ring: "var(--client-light-blue)";
                    };
                };
            };
            readonly effects: {
                readonly light: {
                    readonly "ambient-background": "none";
                    readonly "shadow-panel": "none";
                    readonly "shadow-overlay": "0 12px 36px hsl(213.3333 72% 9.8039% / 0.16)";
                    readonly "status-warning-indicator": "var(--brand-ink)";
                };
                readonly dark: {
                    readonly "ambient-background": "none";
                    readonly "shadow-panel": "none";
                    readonly "shadow-overlay": "0 12px 36px hsl(213.3333 72% 9.8039% / 0.4)";
                    readonly "status-warning-indicator": "var(--brand-orange)";
                };
            };
            readonly density: {
                readonly comfortable: {
                    readonly "page-padding": "32px";
                    readonly "panel-padding": "20px";
                    readonly "grid-gap": "16px";
                    readonly "row-height": "48px";
                    readonly "control-height": "36px";
                    readonly "table-cell-padding-y": "4px";
                    readonly "table-line-height": "1.5";
                };
                readonly compact: {
                    readonly "page-padding": "24px";
                    readonly "panel-padding": "16px";
                    readonly "grid-gap": "12px";
                    readonly "row-height": "40px";
                    readonly "control-height": "32px";
                    readonly "table-cell-padding-y": "2px";
                    readonly "table-line-height": "1.35";
                };
            };
            readonly parameters: {
                readonly accentHue: {
                    readonly $ref: "parameterPolicy.accentHue";
                };
                readonly density: {
                    readonly $ref: "parameterPolicy.density";
                };
                readonly radiusScale: {
                    readonly $ref: "parameterPolicy.radiusScale";
                };
                readonly surfaceMode: {
                    readonly $ref: "parameterPolicy.surfaceMode";
                };
            };
            readonly defaults: {
                readonly accentHue: "brand";
                readonly density: "compact";
                readonly radiusScale: 1;
                readonly surfaceMode: "light";
            };
        };
    };
    readonly parameterPolicy: {
        readonly accentHue: {
            readonly default: 220.3687;
            readonly minimum: 210;
            readonly maximum: 240;
            readonly step: 1;
            readonly recommended: readonly [215, 230];
            readonly brandAlias: "brand";
            readonly brandSaturation: 98.19;
            readonly brandLightness: 56.6667;
            readonly lightSaturation: 100;
            readonly lightLightness: 74.902;
            readonly textInkMix: 0.12;
            readonly lightnessAdjustmentStep: 0.05;
            readonly minimumButtonContrast: 4.55;
            readonly invalid: "越界钳制到 210–240；区间内四舍五入到整数；缺口标准值或 brand 保留原色；非数值回到标准蓝。";
            readonly minimumLightTextContrast: 4.65;
            readonly lightContrastAgainst: "所有 systems.<style>.colors.dark.surface.hover";
        };
        readonly density: {
            readonly values: readonly ["comfortable", "compact"];
            readonly invalid: "回到该风格默认密度";
        };
        readonly radiusScale: {
            readonly values: readonly [0.5, 1, 1.5];
            readonly default: 1;
            readonly invalid: "不支持的值回到 1；不缩放描边、焦点环、pill 与圆形头像";
        };
        readonly surfaceMode: {
            readonly values: readonly ["light", "dark", "auto"];
            readonly invalid: "回到该风格默认模式";
            readonly auto: "跟随 prefers-color-scheme 并实时响应系统变化；浏览器不提供偏好时使用浅色";
        };
    };
};
export type ThemeName = keyof typeof tokens.systems;
export type Density = typeof tokens.parameterPolicy.density.values[number];
export type SurfaceMode = typeof tokens.parameterPolicy.surfaceMode.values[number];
export type RadiusScale = typeof tokens.parameterPolicy.radiusScale.values[number];
export type TokenName = "font-body" | "font-display" | "font-numeric" | "font-size-micro" | "font-size-caption" | "font-size-body" | "font-size-label" | "font-size-section" | "font-size-title" | "font-size-display" | "font-size-kpi" | "line-body" | "line-tight" | "line-display" | "weight-regular" | "weight-medium" | "weight-semibold" | "weight-bold" | "tracking-tight" | "tracking-label" | "tracking-normal" | "radius-control" | "radius-card" | "radius-pill" | "radius-none" | "border-width" | "border-emphasis" | "stroke-chart" | "stroke-icon" | "shadow-panel" | "shadow-overlay" | "space-0" | "space-0_5" | "space-1" | "space-1_5" | "space-2" | "space-3" | "space-4" | "space-5" | "space-6" | "space-8" | "space-10" | "space-12" | "space-16" | "panel-padding" | "page-padding" | "grid-gap" | "row-height" | "control-height" | "sidebar-width" | "topbar-height" | "motion-duration" | "motion-easing" | "blur-panel" | "panel-alpha" | "ambient-background" | "ai-border" | "chart-height" | "chart-min-width" | "table-min-width" | "max-frame-width" | "icon-size" | "icon-size-small" | "icon-size-large" | "spark-width" | "spark-height" | "progress-width" | "progress-height" | "sidebar-logo-size" | "avatar-size" | "empty-symbol-size" | "tracking-terminal" | "layer-sticky" | "layer-overlay" | "opacity-fill" | "opacity-muted" | "opacity-disabled" | "shadow-selection" | "category-manufacturing" | "category-retail" | "category-tech" | "category-services" | "category-logistics" | "feedback-duration" | "brand-ink" | "brand-blue" | "brand-light-blue" | "brand-orange" | "brand-steel" | "brand-cold-white" | "brand-muted" | "accent-solid" | "brand-paper" | "brand-action-text" | "status-warning-indicator" | "client-blue" | "client-light-blue" | "client-action-text" | "table-cell-padding-y" | "table-line-height" | "motion-fast" | "motion-slow" | "motion-easing-exit" | "shadow-none" | "shadow-raised" | "shadow-floating" | "layer-base" | "layer-panel" | "layer-popover" | "layer-toast" | "focus-offset" | "parameter-panel-width" | "control-height-sm" | "control-height-lg" | "dialog-width" | "drawer-width" | "tooltip-width" | "table-viewport-height" | "table-primary-width" | "table-select-width" | "table-header-height" | "virtual-overscan" | "toast-width" | "shell-collapsed-width" | "skeleton-height" | "avatar-size-lg" | "chart-height-small" | "recipe-content-width" | "settings-nav-width" | "recipe-chart-height" | "recipe-chart-tick" | "recipe-chart-min-width" | "recipe-table-width" | "font-size-kpi-hero" | "font-size-kpi-hero-small" | "hero-spark-height" | "radius-card-base" | "radius-control-base" | "surface-base" | "surface-raised" | "surface-overlay" | "surface-hover" | "fg-primary" | "fg-muted" | "fg-subtle" | "fg-inverse" | "border-subtle" | "border-default" | "border-strong" | "accent-default" | "accent-soft" | "accent-fg" | "accent-hover" | "status-success" | "status-success-bg" | "status-warning" | "status-warning-bg" | "status-danger" | "status-danger-bg" | "status-info" | "status-info-bg" | "chart-primary" | "chart-secondary" | "hero-bg" | "hero-fg" | "hero-muted" | "focus-ring";
export declare function tokenVar(name: TokenName): string;
