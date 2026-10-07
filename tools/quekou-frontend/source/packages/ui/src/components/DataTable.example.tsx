import {DataTable,type DataColumn} from '@quekou/ui';import {Badge} from '@quekou/ui';
type Project={id:string;name:string;owner:string;stage:string;amount:number};
const rows:Project[]=Array.from({length:5000},(_,i)=>({id:String(i+1).padStart(4,'0'),name:'演示项目 '+String(i+1).padStart(4,'0'),owner:['陈明','林悦','王宁'][i%3],stage:['实施中','已完成','需复核'][i%3],amount:12000+i*100}));
const columns:DataColumn<Project>[]=[{id:'name',label:'项目名称',value:r=>r.name},{id:'owner',label:'负责人',value:r=>r.owner},{id:'stage',label:'状态',value:r=>r.stage,render:r=><Badge status={r.stage==='已完成'?'success':r.stage==='需复核'?'warning':'info'}>{r.stage}</Badge>},{id:'amount',label:'合同金额（元）',numeric:true,value:r=>r.amount,render:r=>r.amount.toLocaleString('zh-CN')}];
export function DataTableExample(){return <DataTable label="5000行项目演示" rows={rows} columns={columns} getRowId={r=>r.id} selectable/>}
