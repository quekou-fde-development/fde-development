import { type HTMLAttributes } from 'react';
import { type ThemeOverrides } from '../internal/foundation';
export interface SkeletonProps extends HTMLAttributes<HTMLDivElement>, ThemeOverrides {
    lines?: 1 | 2 | 3;
    label?: string;
}
export declare const Skeleton: import("react").ForwardRefExoticComponent<SkeletonProps & import("react").RefAttributes<HTMLDivElement>>;
