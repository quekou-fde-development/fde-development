import { type ProgressHTMLAttributes } from 'react';
import { type ThemeOverrides } from '../internal/foundation';
export interface ProgressBarProps extends Omit<ProgressHTMLAttributes<HTMLProgressElement>, 'value' | 'max'>, ThemeOverrides {
    value: number;
    label: string;
    showValue?: boolean;
}
export declare const ProgressBar: import("react").ForwardRefExoticComponent<ProgressBarProps & import("react").RefAttributes<HTMLProgressElement>>;
