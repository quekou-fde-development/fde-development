import { type RefAttributes, type ReactElement, type ReactNode, type HTMLAttributes } from 'react';
import { type ThemeOverrides } from '../internal/foundation';
export interface DataColumn<T> {
    id: string;
    label: string;
    value: (row: T) => string | number | null | undefined;
    render?: (row: T) => ReactNode;
    sortable?: boolean;
    numeric?: boolean;
}
export interface TableSort {
    column: string;
    direction: 'asc' | 'desc';
}
export interface DataTableProps<T> extends Omit<HTMLAttributes<HTMLDivElement>, 'onSelect'>, ThemeOverrides {
    rows: readonly T[];
    columns: readonly DataColumn<T>[];
    getRowId: (row: T) => string;
    label: string;
    showToolbar?: boolean;
    showFooter?: boolean;
    selectionLabel?: string;
    selectable?: boolean;
    selectedIds?: readonly string[];
    onSelectionChange?: (ids: string[]) => void;
    sort?: TableSort | null;
    onSortChange?: (sort: TableSort) => void;
    search?: string;
    onSearchChange?: (search: string) => void;
    pinFirstColumn?: boolean;
    virtual?: boolean;
    loading?: boolean;
}
export declare const DataTable: <T>(props: DataTableProps<T> & RefAttributes<HTMLDivElement>) => ReactElement;
