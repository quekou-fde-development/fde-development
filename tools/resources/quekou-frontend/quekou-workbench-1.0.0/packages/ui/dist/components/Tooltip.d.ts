import { type ReactElement, type AriaAttributes, type HTMLAttributes } from 'react';
import { type ThemeOverrides } from '../internal/foundation';
export interface TooltipProps extends Omit<HTMLAttributes<HTMLSpanElement>, 'children' | 'content'>, ThemeOverrides {
    content: string;
    children: ReactElement<AriaAttributes>;
}
export declare const Tooltip: import("react").ForwardRefExoticComponent<TooltipProps & import("react").RefAttributes<HTMLSpanElement>>;
