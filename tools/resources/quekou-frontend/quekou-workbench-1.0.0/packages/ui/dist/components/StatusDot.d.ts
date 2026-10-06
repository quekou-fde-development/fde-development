import { type HTMLAttributes } from 'react';
import { type ThemeOverrides } from '../internal/foundation';
import { type StatusKind } from './Badge';
export interface StatusDotProps extends HTMLAttributes<HTMLSpanElement>, ThemeOverrides {
    status: StatusKind;
    label: string;
}
export declare const StatusDot: import("react").ForwardRefExoticComponent<StatusDotProps & import("react").RefAttributes<HTMLSpanElement>>;
