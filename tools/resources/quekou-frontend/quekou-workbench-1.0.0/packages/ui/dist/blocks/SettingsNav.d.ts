import { type ThemeOverrides } from '../internal/foundation';
export interface SettingsNavItem {
    id: string;
    label: string;
    description: string;
}
export interface SettingsNavProps extends ThemeOverrides {
    items: readonly SettingsNavItem[];
    activeId: string;
    onSelect: (id: string) => void;
}
export declare const SettingsNav: import("react").ForwardRefExoticComponent<SettingsNavProps & import("react").RefAttributes<HTMLElement>>;
