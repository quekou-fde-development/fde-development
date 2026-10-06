import {forwardRef,type HTMLAttributes} from 'react';
import {cx,useThemeAttributes,type ThemeOverrides} from '../internal/foundation';
export interface SkeletonProps extends HTMLAttributes<HTMLDivElement>,ThemeOverrides {lines?:1|2|3;label?:string}
export const Skeleton=forwardRef<HTMLDivElement,SkeletonProps>(function Skeleton({lines=3,label='正在加载',density,surfaceMode,className,...rest},ref){const attrs=useThemeAttributes({density,surfaceMode});return <div {...rest} {...attrs} ref={ref} className={cx('qk-skeleton',className)} role="status" aria-label={label}><span className="qk-sr-only">{label}</span>{Array.from({length:lines},(_,i)=><span key={i} aria-hidden="true"/>)}</div>;});
