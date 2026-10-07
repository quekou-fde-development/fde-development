import { type RefAttributes, type ReactElement } from 'react';
import { type DataTableProps } from '../components/DataTable';
export interface RelatedRecordsProps<T> extends Pick<DataTableProps<T>, 'rows' | 'columns' | 'getRowId' | 'loading' | 'density' | 'surfaceMode'> {
    title: string;
    description: string;
}
export declare const RelatedRecords: <T>(props: RelatedRecordsProps<T> & RefAttributes<HTMLDivElement>) => ReactElement;
