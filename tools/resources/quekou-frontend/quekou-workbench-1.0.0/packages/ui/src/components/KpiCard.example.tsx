import {KpiCard} from '@quekou/ui';
export function KpiCardExample(){return <div className="qk-example-grid"><KpiCard label="本月已验收收入" value="128.6" unit="万元" change="较上月 +12.8%" trend={[12,15,14,18,17,22,25]} emphasis/><KpiCard label="待复核项目" value={8} unit="项" direction="down" change="较上周减少 3 项" trend={[16,15,18,14,11,10,8]}/></div>}
