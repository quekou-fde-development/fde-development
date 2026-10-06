import { type FilterBarProps } from '../components/FilterBar';
export type QueryBarProps = Omit<FilterBarProps, 'children' | 'className'>;
export declare const QueryBar: import("react").ForwardRefExoticComponent<QueryBarProps & import("react").RefAttributes<HTMLDivElement>>;
