import { type SelectHTMLAttributes } from 'react';
import { type ThemeOverrides } from '../internal/foundation';
export interface SelectOption {
    value: string;
    label: string;
    disabled?: boolean;
}
export interface SelectProps extends SelectHTMLAttributes<HTMLSelectElement>, ThemeOverrides {
    label: string;
    options: readonly SelectOption[];
    hint?: string;
    error?: string;
}
export declare const Select: import("react").ForwardRefExoticComponent<SelectProps & import("react").RefAttributes<HTMLSelectElement>>;
