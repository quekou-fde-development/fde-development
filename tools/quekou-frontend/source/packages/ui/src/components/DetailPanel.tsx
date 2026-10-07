import {forwardRef,useId,type HTMLAttributes,type ReactNode} from 'react';
import {X} from 'lucide-react';
import {cx,useThemeAttributes,type ThemeOverrides} from '../internal/foundation';
import {Button} from './Button';
export interface DetailPanelProps extends HTMLAttributes<HTMLElement>,ThemeOverrides {title:string;description?:string;onClose?:()=>void;actions?:ReactNode}
export const DetailPanel=forwardRef<HTMLElement,DetailPanelProps>(function DetailPanel({title,description,onClose,actions,density,surfaceMode,className,children,...rest},ref){const attrs=useThemeAttributes({density,surfaceMode}),id=useId();return <aside {...rest} {...attrs} ref={ref} className={cx('qk-detail qk-panel',className)} aria-labelledby={id}><div className="qk-panel-heading"><h2 id={id}>{title}</h2>{onClose&&<Button size="sm" variant="ghost" aria-label={`关闭${title}`} onClick={onClose}><X aria-hidden="true" className="qk-icon"/></Button>}</div>{description&&<p className="qk-muted qk-description">{description}</p>}<div>{children}</div>{actions&&<footer className="qk-dialog-footer">{actions}</footer>}</aside>;});
