import { type HTMLAttributes } from 'react';
import { type ThemeOverrides } from '../internal/foundation';
export interface AvatarProps extends HTMLAttributes<HTMLSpanElement>, ThemeOverrides {
    name: string;
    src?: string;
    size?: 'sm' | 'lg';
}
export declare const Avatar: import("react").ForwardRefExoticComponent<AvatarProps & import("react").RefAttributes<HTMLSpanElement>>;
