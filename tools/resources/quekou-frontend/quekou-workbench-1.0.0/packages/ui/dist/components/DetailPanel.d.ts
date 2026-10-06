import { type HTMLAttributes, type ReactNode } from 'react';
import { type ThemeOverrides } from '../internal/foundation';
export interface DetailPanelProps extends HTMLAttributes<HTMLElement>, ThemeOverrides {
    title: string;
    description?: string;
    onClose?: () => void;
    actions?: ReactNode;
}
export declare const DetailPanel: import("react").ForwardRefExoticComponent<DetailPanelProps & import("react").RefAttributes<HTMLElement>>;
