import {forwardRef,type HTMLAttributes} from 'react';
import {ThemeContext,normalizeTheme,themeAttributes,cx,type ThemeOptions} from '../internal/foundation';
export interface ThemeProviderProps extends HTMLAttributes<HTMLDivElement>,ThemeOptions {}
export const ThemeProvider=forwardRef<HTMLDivElement,ThemeProviderProps>(function ThemeProvider({theme,density,surfaceMode,accentHue,radiusScale,className,children,...rest},ref){const settings=normalizeTheme({theme,density,surfaceMode,accentHue,radiusScale});return <ThemeContext.Provider value={settings}><div {...rest} {...themeAttributes(settings)} ref={ref} className={cx('qk-theme',className)}>{children}</div></ThemeContext.Provider>;});
