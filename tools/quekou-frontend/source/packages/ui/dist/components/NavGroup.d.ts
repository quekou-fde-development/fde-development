import { type HTMLAttributes, type ReactNode } from 'react';
import { type ThemeOverrides } from '../internal/foundation';
export interface NavItem {
    id: string;
    label: string;
    href: string;
    icon?: ReactNode;
    count?: number;
}
export interface NavGroupProps extends HTMLAttributes<HTMLElement>, ThemeOverrides {
    label: string;
    items: readonly NavItem[];
    activeId?: string;
    onNavigate?: (id: string) => void;
}
export declare const NavGroup: import("react").ForwardRefExoticComponent<NavGroupProps & import("react").RefAttributes<HTMLElement>>;
