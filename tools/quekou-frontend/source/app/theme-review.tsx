import { RotateCcw } from 'lucide-react';
import tokens from '../design/tokens.json';
export type SystemKey = keyof typeof tokens.systems;
export interface ThemeParameters { accentHue:'brand'|number; density:'comfortable'|'compact'; radiusScale:0.5|1|1.5; surfaceMode:'light'|'dark'|'auto' }
export const isSystemKey = (key:string):key is SystemKey => key in tokens.systems;
export function normalizeParameters(key:SystemKey,raw:Record<string,unknown>):ThemeParameters {
  const defaults=tokens.systems[key].defaults;
  const policy=tokens.parameterPolicy;
  const h=(typeof raw.accentHue==='number'||typeof raw.accentHue==='string'&&raw.accentHue.trim()!=='')?Number(raw.accentHue):NaN;
  return {
    accentHue:raw.accentHue==='brand'||h===policy.accentHue.default||!Number.isFinite(h)?'brand':Math.max(policy.accentHue.minimum,Math.min(policy.accentHue.maximum,Math.round(h))),
    density:policy.density.values.includes(String(raw.density))?raw.density as ThemeParameters['density']:defaults.density as ThemeParameters['density'],
    radiusScale:policy.radiusScale.values.includes(Number(raw.radiusScale))?Number(raw.radiusScale) as ThemeParameters['radiusScale']:policy.radiusScale.default as ThemeParameters['radiusScale'],
    surfaceMode:policy.surfaceMode.values.includes(String(raw.surfaceMode))?raw.surfaceMode as ThemeParameters['surfaceMode']:defaults.surfaceMode as ThemeParameters['surfaceMode'],
  };
}
export const defaultParameters=(key:SystemKey)=>normalizeParameters(key,tokens.systems[key].defaults);
export function ThemeReview({systemKey,value,onChange}:{systemKey:SystemKey;value:ThemeParameters;onChange:(next:ThemeParameters)=>void}) {
  const system=tokens.systems[systemKey];
  const hue=tokens.parameterPolicy.accentHue;
  const density=system.density[value.density];
  const patch=(next:Partial<ThemeParameters>)=>onChange(normalizeParameters(systemKey,{...value,...next}));
  const swatches=[['surface-base','背景'],['surface-raised','面板'],['fg-primary','正文'],['accent-solid','行动'],['status-success','完成'],['status-warning-bg','风险'],['status-danger','危险']];
  return <section className="theme-review" aria-label="第二阶段主题参数">
    <div className="theme-review-heading"><div><p className="eyebrow">THEME SETTINGS / 阶段 02</p><h2>同一种风格，为不同客户微调</h2><p>四项设置会保存在当前预览链接中，刷新后可继续比较。</p></div><button className="button secondary" onClick={()=>onChange(defaultParameters(systemKey))}><RotateCcw/>恢复主题默认值</button></div>
    <div className="theme-controls">
      <label className="hue-control"><span>强调色相 <small>accentHue</small></span><div><input type="range" aria-label="强调色相" min={hue.minimum} max={hue.maximum} step={hue.step} value={value.accentHue==='brand'?Math.round(hue.default):value.accentHue} onChange={e=>patch({accentHue:Number(e.target.value)})}/><output>{value.accentHue==='brand'?'缺口标准蓝':`${value.accentHue}°`}</output></div><button className="text-button" onClick={()=>patch({accentHue:'brand'})}>恢复标准蓝 · {hue.default.toFixed(2)}°</button></label>
      <label><span>信息密度 <small>density</small></span><select aria-label="信息密度" value={value.density} onChange={e=>patch({density:e.target.value as ThemeParameters['density']})}><option value="comfortable">舒适 · 留白更多</option><option value="compact">紧凑 · 同屏更多</option></select><p>保持字号，调整留白与行高</p></label>
      <label><span>圆角程度 <small>radiusScale</small></span><select aria-label="圆角程度" value={value.radiusScale} onChange={e=>patch({radiusScale:Number(e.target.value) as ThemeParameters['radiusScale']})}><option value="0.5">0.5× · 更利落</option><option value="1">1× · 标准</option><option value="1.5">1.5× · 更柔和</option></select><p>只调整容器和控件边角</p></label>
      <label><span>明暗模式 <small>surfaceMode</small></span><select aria-label="明暗模式" value={value.surfaceMode} onChange={e=>patch({surfaceMode:e.target.value as ThemeParameters['surfaceMode']})}><option value="light">浅色</option><option value="dark">深色</option><option value="auto">跟随系统</option></select><p>两套配色，保持相同业务内容</p></label>
    </div>
    <details className="token-review"><summary>查看本次规范数值与用色</summary><div className="token-review-content"><dl><div><dt>表格行高下限</dt><dd>{density['row-height']}</dd></div><div><dt>控件高度</dt><dd>{density['control-height']}</dd></div><div><dt>卡片圆角</dt><dd>{parseFloat(system.structure['radius-card-base'])*value.radiusScale}px</dd></div><div><dt>正文 / 表格字号</dt><dd>{tokens.common['font-size-body']} / {tokens.common['font-size-caption']}</dd></div></dl><div className="token-swatches">{swatches.map(([token,label])=><div key={token}><span className="token-swatch" data-token={token}/><span>{label}<small>{token.replaceAll('-','/')}</small></span></div>)}</div><p>色相推荐 {hue.recommended[0]}–{hue.recommended[1]}°，支持 {hue.minimum}–{hue.maximum}°。风险橙与危险红保持独立含义。</p></div></details>
  </section>;
}
