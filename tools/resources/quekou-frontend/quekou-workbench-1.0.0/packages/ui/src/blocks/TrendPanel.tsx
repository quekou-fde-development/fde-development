import {forwardRef,useId} from 'react';
import {ChartCard} from '../components/ChartCard';
import {EmptyState} from '../components/EmptyState';
import {Skeleton} from '../components/Skeleton';
import type {ThemeOverrides} from '../internal/foundation';
export interface TrendPoint {label:string;value:number;target?:number}
export interface TrendPanelProps extends ThemeOverrides {title:string;description:string;unit:string;points:readonly TrendPoint[];loading?:boolean}
export const TrendPanel=forwardRef<HTMLElement,TrendPanelProps>(function TrendPanel({title,description,unit,points,loading=false,...theme},ref){
 const id=useId();
 const invalid=points.some(p=>!Number.isFinite(p.value)||(p.target!==undefined&&!Number.isFinite(p.target)));
 const values=points.flatMap(p=>[p.value,...(p.target===undefined?[]:[p.target])]);
 const min=invalid?0:Math.floor(Math.min(0,...values)/10)*10;
 const max=invalid?10:Math.ceil(Math.max(1,...values)/10)*10;
 const xy=(v:number,i:number)=>[52+i*624/Math.max(1,points.length-1),192-(v-min)/(max-min)*152];
 const line=points.map((p,i)=>xy(p.value,i).join(',')).join(' ');
 const hasTarget=points.length>0&&points.every(p=>p.target!==undefined);
 const target=points.map((p,i)=>xy(p.target??0,i).join(',')).join(' ');
 return <ChartCard {...theme} ref={ref} data-block="TrendPanel" title={title} description={description} legend={<><span><i className="qk-line-key"/>实际 · 实线</span>{hasTarget&&<span><i className="qk-line-key qk-line-target"/>计划 · 虚线</span>}<span>单位：{unit}</span></>}>
  {loading?<Skeleton label="正在加载趋势"/>:invalid?<EmptyState title="趋势数据格式有误" description="存在无效数值，请核对数据来源后重试。"/>:!points.length?<EmptyState title="暂无趋势数据"/>:<>
   <div className="qk-trend-scroll"><svg className="qk-trend-chart" viewBox="0 0 720 228" role="img" aria-labelledby={id}>
    <title id={id}>{title}，{points[0].label}为{points[0].value}{unit}，{points.at(-1)!.label}为{points.at(-1)!.value}{unit}；精确值见下方数据表。</title>
    {[0,.5,1].map(r=><g key={r}><line x1="52" x2="690" y1={192-r*152} y2={192-r*152} className="qk-chart-grid"/><text x="40" y={196-r*152} textAnchor="end">{+(min+r*(max-min)).toFixed(1)}</text></g>)}
    {hasTarget&&<polyline points={target} className="qk-trend-target"/>}<polyline points={line} className="qk-trend-line"/>
    {points.map((p,i)=>{const [x,y]=xy(p.value,i);return <g key={i}><circle cx={x} cy={y} r="3" className="qk-trend-dot"/><text x={x} y="218" textAnchor="middle">{p.label}</text></g>})}
   </svg></div><p className="qk-scroll-hint">左右滑动查看完整趋势</p>
   <details className="qk-chart-values"><summary>查看图表数据</summary><div><table><caption className="qk-sr-only">{title}精确值，单位{unit}</caption><thead><tr><th scope="col">期间</th><th scope="col">实际</th>{hasTarget&&<th scope="col">计划</th>}</tr></thead><tbody>{points.map((p,i)=><tr key={i}><th scope="row">{p.label}</th><td>{p.value}</td>{hasTarget&&<td>{p.target}</td>}</tr>)}</tbody></table></div></details>
  </>}
 </ChartCard>;
});
