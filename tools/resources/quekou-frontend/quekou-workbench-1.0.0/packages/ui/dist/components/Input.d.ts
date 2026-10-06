import { type InputHTMLAttributes } from 'react';
import { type ThemeOverrides } from '../internal/foundation';
export interface InputProps extends InputHTMLAttributes<HTMLInputElement>, ThemeOverrides {
    label: string;
    hint?: string;
    error?: string;
}
export declare const Input: import("react").ForwardRefExoticComponent<InputProps & import("react").RefAttributes<HTMLInputElement>>;
