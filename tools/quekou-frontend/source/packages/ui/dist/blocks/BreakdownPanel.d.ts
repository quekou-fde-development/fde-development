import type { ThemeOverrides } from '../internal/foundation';
export interface BreakdownItem {
    id: string;
    label: string;
    value: number;
}
export interface BreakdownPanelProps extends ThemeOverrides {
    title: string;
    description: string;
    unit: string;
    items: readonly BreakdownItem[];
    onSelect?: (id: string) => void;
    loading?: boolean;
}
export declare const BreakdownPanel: import("react").ForwardRefExoticComponent<BreakdownPanelProps & import("react").RefAttributes<HTMLElement>>;
