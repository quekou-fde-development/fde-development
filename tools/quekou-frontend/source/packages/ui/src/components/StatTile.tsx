import {forwardRef,type HTMLAttributes} from 'react';
import {cx,useThemeAttributes,type ThemeOverrides} from '../internal/foundation';
export interface StatTileProps extends HTMLAttributes<HTMLDivElement>,ThemeOverrides {label:string;value:string|number;hint?:string}
export const StatTile=forwardRef<HTMLDivElement,StatTileProps>(function StatTile({label,value,hint,density,surfaceMode,className,...rest},ref){const attrs=useThemeAttributes({density,surfaceMode});return <div {...rest} {...attrs} ref={ref} className={cx('qk-stat',className)}><span className="qk-muted">{label}</span><strong>{value}</strong>{hint&&<small className="qk-muted">{hint}</small>}</div>;});
