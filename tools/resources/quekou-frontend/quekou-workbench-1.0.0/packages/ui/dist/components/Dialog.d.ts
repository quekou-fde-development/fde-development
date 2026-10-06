import { type DialogHTMLAttributes, type ReactNode } from 'react';
import { type ThemeOverrides } from '../internal/foundation';
export interface DialogProps extends Omit<DialogHTMLAttributes<HTMLDialogElement>, 'open' | 'title' | 'onClose' | 'onCancel'>, ThemeOverrides {
    open: boolean;
    onOpenChange: (open: boolean) => void;
    title: string;
    description?: string;
    footer?: ReactNode;
    closeOnOutside?: boolean;
}
export declare const Dialog: import("react").ForwardRefExoticComponent<DialogProps & import("react").RefAttributes<HTMLDialogElement>>;
