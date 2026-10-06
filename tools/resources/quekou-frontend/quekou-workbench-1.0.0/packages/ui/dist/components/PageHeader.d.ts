import { type HTMLAttributes, type ReactNode } from 'react';
import { type ThemeOverrides } from '../internal/foundation';
export interface PageHeaderProps extends HTMLAttributes<HTMLElement>, ThemeOverrides {
    title: string;
    description?: string;
    eyebrow?: string;
    actions?: ReactNode;
}
export declare const PageHeader: import("react").ForwardRefExoticComponent<PageHeaderProps & import("react").RefAttributes<HTMLElement>>;
