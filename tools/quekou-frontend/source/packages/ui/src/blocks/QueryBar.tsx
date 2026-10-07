import {forwardRef} from 'react';import {FilterBar,type FilterBarProps} from '../components/FilterBar';
export type QueryBarProps=Omit<FilterBarProps,'children'|'className'>;
export const QueryBar=forwardRef<HTMLDivElement,QueryBarProps>(function QueryBar(props,ref){return <FilterBar {...props} ref={ref} data-block="QueryBar" className="qk-panel qk-query-block"/>});
