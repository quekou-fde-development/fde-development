import {ChartCard} from '@quekou/ui';import {Sparkline} from '@quekou/ui';
export function ChartCardExample(){return <ChartCard title="近七期验收收入" description="演示数据 · 单位：万元" legend={<span>12 → 15 → 14 → 18 → 17 → 22 → 25</span>}><Sparkline values={[12,15,14,18,17,22,25]} label="验收收入由12万元增长至25万元" large/></ChartCard>}
