import {forwardRef,type ProgressHTMLAttributes} from 'react';
import {cx,useThemeAttributes,type ThemeOverrides} from '../internal/foundation';
export interface ProgressBarProps extends Omit<ProgressHTMLAttributes<HTMLProgressElement>,'value'|'max'>,ThemeOverrides {value:number;label:string;showValue?:boolean}
export const ProgressBar=forwardRef<HTMLProgressElement,ProgressBarProps>(function ProgressBar({value,label,showValue=true,density,surfaceMode,className,...rest},ref){const attrs=useThemeAttributes({density,surfaceMode}),n=Number.isFinite(value)?Math.max(0,Math.min(100,value)):0;return <span {...attrs} className={cx('qk-progress',className)}><progress {...rest} ref={ref} max={100} value={n} aria-label={label}/>{showValue&&<span aria-hidden="true">{n}%</span>}</span>;});
