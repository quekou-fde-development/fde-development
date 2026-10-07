import { type HTMLAttributes } from 'react';
import { type ThemeOverrides } from '../internal/foundation';
import { type StatusKind } from './Badge';
export interface ToastProps extends HTMLAttributes<HTMLDivElement>, ThemeOverrides {
    open: boolean;
    onDismiss: () => void;
    status?: StatusKind;
    duration?: number;
    title: string;
}
export declare const Toast: import("react").ForwardRefExoticComponent<ToastProps & import("react").RefAttributes<HTMLDivElement>>;
