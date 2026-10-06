import {forwardRef,type HTMLAttributes} from 'react';
import {cx,useThemeAttributes,type ThemeOverrides} from '../internal/foundation';
import {statusIcons,type StatusKind} from './Badge';
export interface StatusDotProps extends HTMLAttributes<HTMLSpanElement>,ThemeOverrides {status:StatusKind;label:string}
export const StatusDot=forwardRef<HTMLSpanElement,StatusDotProps>(function StatusDot({status,label,density,surfaceMode,className,...rest},ref){const attrs=useThemeAttributes({density,surfaceMode}),Icon=statusIcons[status];return <span {...rest} {...attrs} ref={ref} className={cx('qk-status-dot',className)}><Icon aria-hidden="true" className="qk-icon"/>{label}</span>;});
