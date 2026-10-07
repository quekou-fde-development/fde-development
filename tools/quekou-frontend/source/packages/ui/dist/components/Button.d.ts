import { type ButtonHTMLAttributes } from 'react';
import { type ThemeOverrides } from '../internal/foundation';
export interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement>, ThemeOverrides {
    variant?: 'primary' | 'secondary' | 'ghost';
    size?: 'sm' | 'md' | 'lg';
    loading?: boolean;
}
export declare const Button: import("react").ForwardRefExoticComponent<ButtonProps & import("react").RefAttributes<HTMLButtonElement>>;
