import {forwardRef} from 'react';
import {Sparkles,ArrowUpRight} from 'lucide-react';
import {KpiCard,type KpiCardProps} from '../components/KpiCard';
import {Button} from '../components/Button';
import {Skeleton} from '../components/Skeleton';
import {useThemeAttributes,type ThemeName,type ThemeOverrides} from '../internal/foundation';
export interface Insight {text:string;source:string;actionLabel?:string;onReview?:()=>void}
export interface KpiRowProps extends ThemeOverrides {items:readonly [KpiCardProps,KpiCardProps,KpiCardProps,KpiCardProps];theme:ThemeName;insight?:Insight;loading?:boolean}
export function InsightNote({insight}:{insight:Insight}){return <div className="qk-insight"><Sparkles className="qk-icon" aria-hidden="true"/><div><strong>AI 摘要示例 <span>需负责人确认</span></strong><p>{insight.text}</p><small>{insight.source}</small></div>{insight.onReview&&<Button size="sm" variant="ghost" onClick={insight.onReview}>{insight.actionLabel||'查看依据'}<ArrowUpRight className="qk-icon" aria-hidden="true"/></Button>}</div>}
export const KpiRow=forwardRef<HTMLElement,KpiRowProps>(function KpiRow({items,theme,insight,loading=false,density,surfaceMode},ref){const attrs=useThemeAttributes({density,surfaceMode});return <section {...attrs} ref={ref} data-block="KpiRow" aria-label="四项核心指标" className="qk-kpi-block"><div className="qk-kpi-row" data-layout={theme}>{items.map((item,i)=>loading?<div className="qk-panel" key={item.label}><Skeleton label={`${item.label}正在加载`}/></div>:<KpiCard {...item} key={item.label} emphasis={theme==='bento'&&i===0}/>)}</div>{insight&&!loading&&<InsightNote insight={insight}/>}</section>});
