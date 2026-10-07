import { type HTMLAttributes, type ReactNode } from 'react';
import { type ThemeOverrides } from '../internal/foundation';
export interface AppShellProps extends HTMLAttributes<HTMLDivElement>, ThemeOverrides {
    brand: ReactNode;
    sidebar: ReactNode;
    header?: ReactNode;
    collapsed?: boolean;
    defaultCollapsed?: boolean;
    onCollapsedChange?: (collapsed: boolean) => void;
}
export declare const AppShell: import("react").ForwardRefExoticComponent<AppShellProps & import("react").RefAttributes<HTMLDivElement>>;
