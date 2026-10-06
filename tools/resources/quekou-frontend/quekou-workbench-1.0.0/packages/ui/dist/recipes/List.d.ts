import { type RefAttributes, type ReactElement } from 'react';
import { type PageHeaderProps } from '../components/PageHeader';
import { type QueryBarProps } from '../blocks/QueryBar';
import { type RecordTableProps } from '../blocks/RecordTable';
import { type PaginationBarProps } from '../blocks/PaginationBar';
import { type ThemeOverrides } from '../internal/foundation';
export interface ListProps<T> extends ThemeOverrides {
    header: PageHeaderProps;
    query: QueryBarProps;
    records: RecordTableProps<T>;
    pagination: PaginationBarProps;
}
export declare const List: <T>(props: ListProps<T> & RefAttributes<HTMLDivElement>) => ReactElement;
