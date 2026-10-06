import { type ReactNode } from 'react';
import { type StatusKind } from '../components/Badge';
import { type Insight } from './KpiRow';
import { type ThemeOverrides } from '../internal/foundation';
export interface SummaryField {
    label: string;
    value: ReactNode;
}
export interface EntitySummaryProps extends ThemeOverrides {
    title: string;
    description: string;
    status: StatusKind;
    statusLabel: string;
    fields: readonly SummaryField[];
    progress?: number;
    insight?: Insight;
    loading?: boolean;
}
export declare const EntitySummary: import("react").ForwardRefExoticComponent<EntitySummaryProps & import("react").RefAttributes<HTMLElement>>;
