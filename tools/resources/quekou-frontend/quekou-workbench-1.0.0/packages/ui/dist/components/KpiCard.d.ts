import { type HTMLAttributes } from 'react';
import { type ThemeOverrides } from '../internal/foundation';
export interface KpiCardProps extends HTMLAttributes<HTMLElement>, ThemeOverrides {
    label: string;
    value: string | number;
    unit?: string;
    change: string;
    trend?: readonly number[];
    direction?: 'up' | 'down' | 'flat';
    emphasis?: boolean;
}
export declare const KpiCard: import("react").ForwardRefExoticComponent<KpiCardProps & import("react").RefAttributes<HTMLElement>>;
