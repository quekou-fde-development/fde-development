import {forwardRef,type HTMLAttributes} from 'react';
import {X} from 'lucide-react';
import {cx,useThemeAttributes,type ThemeOverrides} from '../internal/foundation';
export interface TagProps extends HTMLAttributes<HTMLSpanElement>,ThemeOverrides {label:string;onRemove?:()=>void}
export const Tag=forwardRef<HTMLSpanElement,TagProps>(function Tag({label,onRemove,density,surfaceMode,className,...rest},ref){const attrs=useThemeAttributes({density,surfaceMode});return <span {...rest} {...attrs} ref={ref} className={cx('qk-tag',className)}>{label}{onRemove&&<button type="button" className="qk-icon-button" aria-label={`移除${label}`} onClick={onRemove}><X aria-hidden="true" className="qk-icon"/></button>}</span>;});
