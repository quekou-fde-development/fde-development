import {Sparkline} from '@quekou/ui';
export function SparklineExample(){return <div className="qk-example-stack"><Sparkline values={[10,12,11,15,17,16,22]} label="七期项目趋势"/><p className="qk-muted">也支持仅有一个数据点或暂无数据。</p><Sparkline values={[18]} label="单期数据18"/><Sparkline values={[]} label="空数据趋势"/></div>}
