import {forwardRef,type HTMLAttributes} from 'react';
import {ArrowDownRight,ArrowUpRight,Minus} from 'lucide-react';
import {cx,useThemeAttributes,type ThemeOverrides} from '../internal/foundation';
import {Sparkline} from './Sparkline';
export interface KpiCardProps extends HTMLAttributes<HTMLElement>,ThemeOverrides {label:string;value:string|number;unit?:string;change:string;trend?:readonly number[];direction?:'up'|'down'|'flat';emphasis?:boolean}
export const KpiCard=forwardRef<HTMLElement,KpiCardProps>(function KpiCard({label,value,unit,change,trend,direction='up',emphasis=false,density,surfaceMode,className,...rest},ref){const attrs=useThemeAttributes({density,surfaceMode}),Icon=direction==='up'?ArrowUpRight:direction==='down'?ArrowDownRight:Minus;return <article {...rest} {...attrs} ref={ref} className={cx('qk-kpi qk-panel',className)} data-emphasis={emphasis}><p className="qk-muted">{label}</p><div className="qk-kpi-value"><strong>{value}</strong><span>{unit}</span></div><div className="qk-kpi-bottom"><span><Icon aria-hidden="true" className="qk-icon"/>{change}</span>{trend&&<Sparkline values={trend} label={`${label}趋势`}/>}</div></article>;});
