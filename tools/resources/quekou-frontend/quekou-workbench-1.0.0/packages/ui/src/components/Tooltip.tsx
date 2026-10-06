import {forwardRef,useState,useId,cloneElement,type ReactElement,type AriaAttributes,type HTMLAttributes} from 'react';
import {cx,useThemeAttributes,type ThemeOverrides} from '../internal/foundation';
export interface TooltipProps extends Omit<HTMLAttributes<HTMLSpanElement>,'children'|'content'>,ThemeOverrides {content:string;children:ReactElement<AriaAttributes>}
export const Tooltip=forwardRef<HTMLSpanElement,TooltipProps>(function Tooltip({content,children,density,surfaceMode,className,onMouseEnter,onMouseLeave,onFocus,onBlur,onKeyDown,...rest},ref){
 const attrs=useThemeAttributes({density,surfaceMode}),id=useId();
 const [hovered,setHovered]=useState(false),[focused,setFocused]=useState(false),[dismissed,setDismissed]=useState(false);
 const open=(hovered||focused)&&!dismissed;
 return <span {...rest} {...attrs} ref={ref} className={cx('qk-tooltip-root',className)} onMouseEnter={e=>{setHovered(true);setDismissed(false);onMouseEnter?.(e);}} onMouseLeave={e=>{setHovered(false);onMouseLeave?.(e);}} onFocus={e=>{setFocused(true);setDismissed(false);onFocus?.(e);}} onBlur={e=>{if(!e.currentTarget.contains(e.relatedTarget))setFocused(false);onBlur?.(e);}} onKeyDown={e=>{onKeyDown?.(e);if(!e.defaultPrevented&&e.key==='Escape'&&open){setDismissed(true);e.stopPropagation();}}}>{cloneElement(children,{'aria-describedby':[children.props['aria-describedby'],open?id:undefined].filter(Boolean).join(' ')||undefined})}{open&&<span id={id} role="tooltip" className="qk-tooltip">{content}</span>}</span>;
});
