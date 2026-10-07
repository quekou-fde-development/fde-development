import type { ThemeOverrides } from '../internal/foundation';
export interface TrendPoint {
    label: string;
    value: number;
    target?: number;
}
export interface TrendPanelProps extends ThemeOverrides {
    title: string;
    description: string;
    unit: string;
    points: readonly TrendPoint[];
    loading?: boolean;
}
export declare const TrendPanel: import("react").ForwardRefExoticComponent<TrendPanelProps & import("react").RefAttributes<HTMLElement>>;
