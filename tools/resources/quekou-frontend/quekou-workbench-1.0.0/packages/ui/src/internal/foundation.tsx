import {createContext,useContext,useState,useRef,useCallback,type Ref,type MutableRefObject} from 'react';
import {tokens,type ThemeName,type Density,type SurfaceMode,type RadiusScale} from '@quekou/theme';
export type {ThemeName,Density,SurfaceMode,RadiusScale};
export interface ThemeOverrides {density?:Density;surfaceMode?:SurfaceMode}
export interface ThemeOptions extends ThemeOverrides {theme?:ThemeName;accentHue?:number|'brand';radiusScale?:RadiusScale}
export interface ThemeSettings {theme:ThemeName;density:Density;surfaceMode:SurfaceMode;accentHue:number|'brand';radiusScale:RadiusScale}
export function normalizeTheme(options:ThemeOptions):ThemeSettings {
 const theme=options.theme&&Object.hasOwn(tokens.systems,options.theme)?options.theme:'bento';const defaults=tokens.systems[theme].defaults,p=tokens.parameterPolicy;
 const raw=options.accentHue;const accentHue=raw==='brand'||raw===undefined||!Number.isFinite(raw)||raw===p.accentHue.default?'brand':Math.max(p.accentHue.minimum,Math.min(p.accentHue.maximum,Math.round(raw)));
 return {theme,accentHue,density:options.density&&p.density.values.some(v=>v===options.density)?options.density:defaults.density,surfaceMode:options.surfaceMode&&p.surfaceMode.values.some(v=>v===options.surfaceMode)?options.surfaceMode:defaults.surfaceMode,radiusScale:options.radiusScale&&p.radiusScale.values.some(v=>v===options.radiusScale)?options.radiusScale:p.radiusScale.default};
}
export const ThemeContext=createContext<ThemeSettings>(normalizeTheme({}));
export const themeAttributes=(t:ThemeSettings)=>({'data-theme':t.theme,'data-density':t.density,'data-surface-mode':t.surfaceMode,'data-accent-hue':t.accentHue,'data-radius-scale':t.radiusScale});
export function useThemeAttributes(overrides:ThemeOverrides={}) {const current=useContext(ThemeContext);return {'data-qk':'',...((overrides.density||overrides.surfaceMode)?themeAttributes({...current,...Object.fromEntries(Object.entries(overrides).filter(([,v])=>v!==undefined))}):{})};}
export const cx=(...classes:(string|false|null|undefined)[])=>classes.filter(Boolean).join(' ');
export function useMergedRef<T>(external:Ref<T>,inner:MutableRefObject<T|null>){return useCallback((value:T|null)=>{inner.current=value;if(typeof external==='function')external(value);else if(external)(external as MutableRefObject<T|null>).current=value;},[external,inner]);}
export function useControllable<T>(value:T|undefined,initial:T,onChange?:((next:T)=>void)){const [local,setLocal]=useState(initial);const current=value===undefined?local:value;const ref=useRef(current);ref.current=current;const set=(next:T)=>{if(value===undefined)setLocal(next);onChange?.(next);};return [current,set,ref] as const;}
export const uiTokens=tokens.common;
