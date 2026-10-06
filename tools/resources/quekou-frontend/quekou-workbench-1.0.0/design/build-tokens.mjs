// Generate both the comparison preview and the distributable phase 3 theme from one source.
import { readFile, mkdir, writeFile } from 'node:fs/promises';
import { flattenColors, accentVariants } from './preview-parameters.mjs';
const root = new URL('../', import.meta.url);
const tokens = JSON.parse(await readFile(new URL('design/tokens.json', root), 'utf8'));
const vars = values => Object.entries(values).map(([k,v]) => `  --${k}: ${v};`).join('\n');
const rule = (selector, values, mode) => `${selector} {\n${vars(values)}\n${mode ? `  color-scheme: ${mode};\n` : ''}}\n`;
let css = `/* Generated from design/tokens.json. Preview and phase 3 theme. Do not edit. */\n`;
css += rule(':root', {...tokens.common,...tokens.gallery});
for (const [theme,values] of Object.entries(tokens.themes)) {
  const mode = theme==='editorial-dark'||tokens.styles.find(s=>s.key===theme)?.mode==='dark'?'dark':'light';
  css += rule(`[data-theme="${theme}"]`, {...tokens.common,...values}, mode);
}
let selectedCss='';
for (const [key,system] of Object.entries(tokens.systems)) {
  const start=css.length;
  const selector = `[data-theme="${key}"]`;
  const modeValues = mode => ({...flattenColors(system.colors[mode]),...system.effects[mode]});
  css += rule(selector, {...tokens.common,...system.structure,...modeValues(system.defaults.surfaceMode),...system.density[system.defaults.density]}, system.defaults.surfaceMode);
  css += rule(`${selector}.dark`, modeValues('dark'), 'dark');
  for (const mode of ['light','dark']) css += rule(`${selector}[data-surface-mode="${mode}"]`, modeValues(mode), mode);
  css += rule(`${selector}[data-surface-mode="auto"]`, modeValues('light'), 'light');
  css += `@media (prefers-color-scheme: dark) {\n${rule(`${selector}[data-surface-mode="auto"]`, modeValues('dark'), 'dark')}}\n`;
  for (const [density,values] of Object.entries(system.density)) css += rule(`${selector}[data-density="${density}"]`, values);
  for (const scale of tokens.parameterPolicy.radiusScale.values) css += rule(`${selector}[data-radius-scale="${scale}"]`, {'radius-card':`${parseFloat(system.structure['radius-card-base'])*scale}px`,'radius-control':`${parseFloat(system.structure['radius-control-base'])*scale}px`});
  for (const [hue,values] of Object.entries(accentVariants(tokens))) css += rule(`${selector}[data-accent-hue="${hue}"]`, values);
  selectedCss+=css.slice(start);
}
const colorKeys=Object.keys(tokens.gallery).filter(k=>/^(surface|fg|border-(subtle|default|strong)|accent|status|chart|hero|focus)/.test(k));
for(const key of colorKeys) css+=`.token-swatch[data-token="${key}"] { background:var(--${key}); }\n`;
const preset={theme:{
  colors:Object.fromEntries(colorKeys.map(k=>[k,`var(--${k})`])),
  fontFamily:{sans:'var(--font-body)',display:'var(--font-display)',mono:'var(--font-numeric)'},
  fontSize:Object.fromEntries(['micro','caption','body','label','section','title','display','kpi'].map(k=>[k,`var(--font-size-${k})`])),
  fontWeight:Object.fromEntries(['regular','medium','semibold','bold'].map(k=>[k,`var(--weight-${k})`])),
  lineHeight:{body:'var(--line-body)',tight:'var(--line-tight)',display:'var(--line-display)'},
  borderRadius:{none:'var(--radius-none)',control:'var(--radius-control)',card:'var(--radius-card)',full:'var(--radius-pill)'},
  boxShadow:{panel:'var(--shadow-panel)',overlay:'var(--shadow-overlay)'},
  borderWidth:{DEFAULT:'var(--border-width)',strong:'var(--border-emphasis)'},
  spacing:Object.fromEntries(Object.keys(tokens.common).filter(k=>k.startsWith('space-')).map(k=>[k.slice(6).replace('_','.'),`var(--${k})`])),
}};
await mkdir(new URL('app/generated/',root),{recursive:true});
await writeFile(new URL('app/generated/tokens.css',root),css);
await writeFile(new URL('app/generated/preview-preset.cjs',root),'// Generated preview-only preset\nmodule.exports = '+JSON.stringify(preset,null,2)+';\n');
console.log('Generated 3 selected systems × 2 modes, 4 parameter controls, and 8 reference variants.');

const themeDir=new URL('packages/theme/src/',root);
await mkdir(themeDir,{recursive:true});
const base=tokens.systems.bento;
const rootValues={...tokens.common,...base.structure,...flattenColors(base.colors.light),...base.effects.light,...base.density[base.defaults.density]};
const productionCss='/* Generated; edit design/tokens.json only. */\n'+rule(':root',rootValues,'light')+rule('.dark',{...flattenColors(base.colors.dark),...base.effects.dark},'dark')+selectedCss;
await writeFile(new URL('tokens.css',themeDir),productionCss);
const exported={common:tokens.common,systems:tokens.systems,parameterPolicy:tokens.parameterPolicy};
const tokenNames=[...new Set([...Object.keys(tokens.common),...Object.values(tokens.systems).flatMap(s=>[...Object.keys(s.structure),...Object.keys(flattenColors(s.colors.light)),...Object.keys(s.effects.light)])])];
await writeFile(new URL('tokens.ts',themeDir),'// Generated from design/tokens.json. Do not edit.\nexport const tokens = '+JSON.stringify(exported,null,2)+' as const;\nexport type ThemeName = keyof typeof tokens.systems;\nexport type Density = typeof tokens.parameterPolicy.density.values[number];\nexport type SurfaceMode = typeof tokens.parameterPolicy.surfaceMode.values[number];\nexport type RadiusScale = typeof tokens.parameterPolicy.radiusScale.values[number];\nexport type TokenName = '+tokenNames.map(x=>JSON.stringify(x)).join(' | ')+';\nexport function tokenVar(name: TokenName): string { return \"var(--\"+name+\")\"; }\n');
const productionPreset=structuredClone(preset);productionPreset.theme.colors=Object.fromEntries(Object.keys(flattenColors(base.colors.light)).map(k=>[k,'var(--'+k+')']));
await writeFile(new URL('tailwind.preset.ts',themeDir),'// Generated from design/tokens.json. Do not edit.\nimport type { Config } from \"tailwindcss\";\nconst preset = '+JSON.stringify(productionPreset,null,2)+' satisfies Partial<Config>;\nexport default preset;\n');
