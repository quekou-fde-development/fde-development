import { type HTMLAttributes, type ReactNode } from 'react';
import { type ThemeOverrides } from '../internal/foundation';
export interface EmptyStateProps extends HTMLAttributes<HTMLDivElement>, ThemeOverrides {
    title: string;
    description?: string;
    action?: ReactNode;
}
export declare const EmptyState: import("react").ForwardRefExoticComponent<EmptyStateProps & import("react").RefAttributes<HTMLDivElement>>;
