import { type HTMLAttributes } from 'react';
import { type ThemeOverrides } from '../internal/foundation';
import { type SelectOption } from './Select';
export interface FilterDefinition {
    id: string;
    label: string;
    value: string;
    options: readonly SelectOption[];
    onChange: (value: string) => void;
}
export interface FilterBarProps extends HTMLAttributes<HTMLDivElement>, ThemeOverrides {
    filters: readonly FilterDefinition[];
    search: string;
    onSearchChange: (value: string) => void;
    from: string;
    to: string;
    onDateChange: (range: {
        from: string;
        to: string;
    }) => void;
    onReset: () => void;
}
export declare const FilterBar: import("react").ForwardRefExoticComponent<FilterBarProps & import("react").RefAttributes<HTMLDivElement>>;
