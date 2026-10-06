import {forwardRef,type HTMLAttributes,type ReactNode} from 'react';
import {Inbox} from 'lucide-react';
import {cx,useThemeAttributes,type ThemeOverrides} from '../internal/foundation';
export interface EmptyStateProps extends HTMLAttributes<HTMLDivElement>,ThemeOverrides {title:string;description?:string;action?:ReactNode}
export const EmptyState=forwardRef<HTMLDivElement,EmptyStateProps>(function EmptyState({title,description,action,density,surfaceMode,className,...rest},ref){const attrs=useThemeAttributes({density,surfaceMode});return <div {...rest} {...attrs} ref={ref} className={cx('qk-empty',className)}><Inbox aria-hidden="true" className="qk-empty-icon"/><strong>{title}</strong>{description&&<p className="qk-muted">{description}</p>}{action}</div>;});
