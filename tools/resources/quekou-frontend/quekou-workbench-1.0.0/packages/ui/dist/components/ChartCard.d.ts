import { type HTMLAttributes, type ReactNode } from 'react';
import { type ThemeOverrides } from '../internal/foundation';
export interface ChartCardProps extends HTMLAttributes<HTMLElement>, ThemeOverrides {
    title: string;
    description?: string;
    legend?: ReactNode;
    actions?: ReactNode;
}
export declare const ChartCard: import("react").ForwardRefExoticComponent<ChartCardProps & import("react").RefAttributes<HTMLElement>>;
