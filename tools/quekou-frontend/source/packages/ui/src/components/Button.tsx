import {forwardRef,type ButtonHTMLAttributes} from 'react';
import {LoaderCircle} from 'lucide-react';
import {cx,useThemeAttributes,type ThemeOverrides} from '../internal/foundation';
export interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement>,ThemeOverrides {variant?:'primary'|'secondary'|'ghost';size?:'sm'|'md'|'lg';loading?:boolean}
export const Button=forwardRef<HTMLButtonElement,ButtonProps>(function Button({variant='secondary',size='md',loading=false,disabled,density,surfaceMode,className,children,type='button',...rest},ref){const attrs=useThemeAttributes({density,surfaceMode});return <button {...rest} {...attrs} ref={ref} type={type} disabled={disabled||loading} aria-busy={loading||undefined} className={cx('qk-button',className)} data-variant={variant} data-size={size}>{loading&&<LoaderCircle aria-hidden="true" className="qk-icon"/>}{children}</button>;});
