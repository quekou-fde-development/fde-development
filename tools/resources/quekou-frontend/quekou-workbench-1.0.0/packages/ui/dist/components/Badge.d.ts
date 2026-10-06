import { type HTMLAttributes } from 'react';
import { type ThemeOverrides } from '../internal/foundation';
export type StatusKind = 'success' | 'warning' | 'danger' | 'info';
export interface BadgeProps extends HTMLAttributes<HTMLSpanElement>, ThemeOverrides {
    status?: StatusKind;
}
export declare const statusIcons: {
    success: import("react").ForwardRefExoticComponent<Omit<import("lucide-react").LucideProps, "ref"> & import("react").RefAttributes<SVGSVGElement>>;
    warning: import("react").ForwardRefExoticComponent<Omit<import("lucide-react").LucideProps, "ref"> & import("react").RefAttributes<SVGSVGElement>>;
    danger: import("react").ForwardRefExoticComponent<Omit<import("lucide-react").LucideProps, "ref"> & import("react").RefAttributes<SVGSVGElement>>;
    info: import("react").ForwardRefExoticComponent<Omit<import("lucide-react").LucideProps, "ref"> & import("react").RefAttributes<SVGSVGElement>>;
};
export declare const Badge: import("react").ForwardRefExoticComponent<BadgeProps & import("react").RefAttributes<HTMLSpanElement>>;
