import { type HTMLAttributes } from 'react';
import { type ThemeOptions } from '../internal/foundation';
export interface ThemeProviderProps extends HTMLAttributes<HTMLDivElement>, ThemeOptions {
}
export declare const ThemeProvider: import("react").ForwardRefExoticComponent<ThemeProviderProps & import("react").RefAttributes<HTMLDivElement>>;
