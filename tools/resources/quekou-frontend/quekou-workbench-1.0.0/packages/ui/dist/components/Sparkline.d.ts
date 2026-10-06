import { type SVGAttributes } from 'react';
import { type ThemeOverrides } from '../internal/foundation';
export interface SparklineProps extends Omit<SVGAttributes<SVGSVGElement>, 'values'>, ThemeOverrides {
    values: readonly number[];
    label: string;
    large?: boolean;
}
export declare const Sparkline: import("react").ForwardRefExoticComponent<SparklineProps & import("react").RefAttributes<SVGSVGElement>>;
