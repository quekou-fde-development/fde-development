import { type HTMLAttributes, type ReactNode } from 'react';
import { type ThemeOverrides } from '../internal/foundation';
export interface PopoverProps extends HTMLAttributes<HTMLDivElement>, ThemeOverrides {
    label: string;
    trigger: ReactNode;
    open?: boolean;
    defaultOpen?: boolean;
    onOpenChange?: (open: boolean) => void;
}
export declare const Popover: import("react").ForwardRefExoticComponent<PopoverProps & import("react").RefAttributes<HTMLDivElement>>;
