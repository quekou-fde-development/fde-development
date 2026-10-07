import {forwardRef,type HTMLAttributes} from 'react';
import {CheckCircle2,TriangleAlert,Info,OctagonAlert} from 'lucide-react';
import {cx,useThemeAttributes,type ThemeOverrides} from '../internal/foundation';
export type StatusKind='success'|'warning'|'danger'|'info';
export interface BadgeProps extends HTMLAttributes<HTMLSpanElement>,ThemeOverrides {status?:StatusKind}
export const statusIcons={success:CheckCircle2,warning:TriangleAlert,danger:OctagonAlert,info:Info};
export const Badge=forwardRef<HTMLSpanElement,BadgeProps>(function Badge({status='info',density,surfaceMode,className,children,...rest},ref){const attrs=useThemeAttributes({density,surfaceMode}),Icon=statusIcons[status];return <span {...rest} {...attrs} ref={ref} className={cx('qk-badge',className)} data-status={status}><Icon aria-hidden="true" className="qk-icon"/>{children||{success:'已完成',warning:'需复核',danger:'错误',info:'信息'}[status]}</span>;});
