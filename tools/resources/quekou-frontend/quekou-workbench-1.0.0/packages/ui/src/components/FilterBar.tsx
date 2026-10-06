import {forwardRef,type HTMLAttributes} from 'react';
import {cx,useThemeAttributes,type ThemeOverrides} from '../internal/foundation';
import {Input} from './Input';
import {Select,type SelectOption} from './Select';
import {Button} from './Button';
export interface FilterDefinition {id:string;label:string;value:string;options:readonly SelectOption[];onChange:(value:string)=>void}
export interface FilterBarProps extends HTMLAttributes<HTMLDivElement>,ThemeOverrides {filters:readonly FilterDefinition[];search:string;onSearchChange:(value:string)=>void;from:string;to:string;onDateChange:(range:{from:string;to:string})=>void;onReset:()=>void}
export const FilterBar=forwardRef<HTMLDivElement,FilterBarProps>(function FilterBar({filters,search,onSearchChange,from,to,onDateChange,onReset,density,surfaceMode,className,...rest},ref){const attrs=useThemeAttributes({density,surfaceMode});return <div {...rest} {...attrs} ref={ref} className={cx('qk-filter-bar',className)} aria-label="筛选条件">{filters.map(f=><Select key={f.id} label={f.label} value={f.value} options={f.options} onChange={e=>f.onChange(e.target.value)}/>)}<Input label="开始日期" type="date" value={from} max={to||undefined} onChange={e=>onDateChange({from:e.target.value,to})}/><Input label="结束日期" type="date" value={to} min={from||undefined} onChange={e=>onDateChange({from,to:e.target.value})}/><Input label="搜索" type="search" value={search} onChange={e=>onSearchChange(e.target.value)}/><Button onClick={onReset}>重置筛选</Button>{from&&to&&from>to&&<p className="qk-error" role="alert">开始日期晚于结束日期</p>}</div>;});
