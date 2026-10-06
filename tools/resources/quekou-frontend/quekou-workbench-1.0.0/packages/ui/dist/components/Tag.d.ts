import { type HTMLAttributes } from 'react';
import { type ThemeOverrides } from '../internal/foundation';
export interface TagProps extends HTMLAttributes<HTMLSpanElement>, ThemeOverrides {
    label: string;
    onRemove?: () => void;
}
export declare const Tag: import("react").ForwardRefExoticComponent<TagProps & import("react").RefAttributes<HTMLSpanElement>>;
