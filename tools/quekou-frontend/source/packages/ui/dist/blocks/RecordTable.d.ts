import { type RefAttributes, type ReactElement } from 'react';
import { type DataTableProps } from '../components/DataTable';
export interface RecordTableProps<T> extends Pick<DataTableProps<T>, 'rows' | 'columns' | 'getRowId' | 'label' | 'selectedIds' | 'onSelectionChange' | 'sort' | 'onSortChange' | 'loading' | 'density' | 'surfaceMode'> {
    onClearSelection?: () => void;
    total: number;
}
export declare const RecordTable: <T>(props: RecordTableProps<T> & RefAttributes<HTMLDivElement>) => ReactElement;
