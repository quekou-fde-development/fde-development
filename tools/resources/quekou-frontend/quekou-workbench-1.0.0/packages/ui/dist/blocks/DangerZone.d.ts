import { type ThemeOverrides } from '../internal/foundation';
export interface DangerZoneProps extends ThemeOverrides {
    title: string;
    description: string;
    actionLabel: string;
    confirmText: string;
    confirmDescription: string;
    onConfirm: () => void | Promise<void>;
    disabled?: boolean;
}
export declare const DangerZone: import("react").ForwardRefExoticComponent<DangerZoneProps & import("react").RefAttributes<HTMLElement>>;
