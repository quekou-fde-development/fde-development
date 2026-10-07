import { type InputHTMLAttributes } from 'react';
import { type ThemeOverrides } from '../internal/foundation';
export interface CheckboxProps extends Omit<InputHTMLAttributes<HTMLInputElement>, 'type'>, ThemeOverrides {
    label: string;
    indeterminate?: boolean;
}
export declare const Checkbox: import("react").ForwardRefExoticComponent<CheckboxProps & import("react").RefAttributes<HTMLInputElement>>;
