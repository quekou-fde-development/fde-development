import { type HTMLAttributes } from 'react';
import { type ThemeOverrides } from '../internal/foundation';
export interface StatTileProps extends HTMLAttributes<HTMLDivElement>, ThemeOverrides {
    label: string;
    value: string | number;
    hint?: string;
}
export declare const StatTile: import("react").ForwardRefExoticComponent<StatTileProps & import("react").RefAttributes<HTMLDivElement>>;
