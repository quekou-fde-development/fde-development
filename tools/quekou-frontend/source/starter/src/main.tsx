import React,{useEffect,useMemo,useState} from 'react';
import {createRoot} from 'react-dom/client';
import {ThemeProvider,AppShell,NavGroup,Overview,List,Detail,Settings,Button,EmptyState,type DataColumn,type KpiRowProps,type DetailTab,type TableSort} from '@quekou/ui';
import {LayoutDashboard,Rows3,FileText,Settings2} from 'lucide-react';
import {client} from './client.config';
import '@quekou/theme/tokens.css';
import '@quekou/ui/styles.css';
import './styles.css';

type Page='overview'|'list'|'detail'|'settings';
type Row={id:string;name:string;owner:string;due:string};
const pageNames:Record<Page,string>={overview:'经营总览',list:'业务列表',detail:'对象详情',settings:'工作区设置'};
const pageIcons={overview:LayoutDashboard,list:Rows3,detail:FileText,settings:Settings2};
const readPage=():Page=>Object.hasOwn(pageNames,location.hash.slice(1))?location.hash.slice(1) as Page:'overview';
const rows:Row[]=[]; // No customer records have been provided. Do not invent them.
function App(){
 const [page,setPage]=useState<Page>(readPage),[query,setQuery]=useState(''),[from,setFrom]=useState(''),[to,setTo]=useState(''),[tab,setTab]=useState<DetailTab>('timeline'),[listPage,setListPage]=useState(1),[pageSize,setPageSize]=useState(5),[sort,setSort]=useState<TableSort|null>(null);
 const [saved,setSaved]=useState(client.name),[draft,setDraft]=useState(client.name),[message,setMessage]=useState('仅本次预览有效');
 useEffect(()=>{const update=()=>setPage(readPage());addEventListener('hashchange',update);return()=>removeEventListener('hashchange',update);},[]);
 const filtered=useMemo(()=>{const result=rows.filter(r=>(!query||[r.name,r.owner,r.id].some(s=>s.includes(query)))&&(!from||r.due>=from)&&(!to||r.due<=to));if(sort)result.sort((a,b)=>String(a[sort.column as keyof Row]??'').localeCompare(String(b[sort.column as keyof Row]??''),'zh-CN',{numeric:true})*(sort.direction==='asc'?1:-1));return result;},[query,from,to,sort]);
 const columns:DataColumn<Row>[]=[{id:'name',label:client.entity,value:r=>r.name,render:r=><Button variant="ghost" onClick={()=>{location.hash='detail';}}>{r.name}</Button>},{id:'owner',label:'负责人',value:r=>r.owner},{id:'due',label:'计划日期',value:r=>r.due}];
 const metrics=client.metrics.map(label=>({label,value:'—',direction:'flat' as const,change:'尚未接入数据'})) as unknown as KpiRowProps['items'];
 const changeSearch=(v:string)=>{setQuery(v);setListPage(1);};
 const navItems=(Object.keys(pageNames) as Page[]).map(id=>{const Icon=pageIcons[id];return {id,label:pageNames[id],href:'#'+id,icon:<Icon className="qk-icon"/>};});
 const selectPage=Math.min(listPage,Math.max(1,Math.ceil(filtered.length/pageSize)));
 return <ThemeProvider {...client.theme} className="client-root gallery-workspace">
  <AppShell brand={<strong title={saved}>{saved}</strong>} sidebar={<NavGroup label="工作台" items={navItems} activeId={page}/>} header={<span className="qk-muted">待接入业务数据 · 前端骨架</span>}>
   <main className="client-main">
    <p className="client-notice">尚未接入账号、权限与业务保存服务。空白指标表示没有数据；本页设置只在当前预览中生效。</p>
    {page==='overview'&&<Overview header={{title:pageNames.overview,description:client.business+' · '+client.entity}} kpis={{theme:client.theme.theme,items:metrics}} trend={{title:'业务趋势',description:'接入数据后显示',unit:'项',points:[]}} breakdown={{title:'分类分布',description:'分类口径待确认',unit:'项',items:[]}} activity={{title:'最近动态',items:[]}}/>}
    {page==='list'&&<List<Row> header={{title:pageNames.list,description:client.entity+'明细'}} query={{filters:[],search:query,onSearchChange:changeSearch,from,to,onDateChange:({from:a,to:b})=>{setFrom(a);setTo(b);setListPage(1);},onReset:()=>{setQuery('');setFrom('');setTo('');setListPage(1);}}} records={{label:client.entity+'列表',rows:filtered.slice((selectPage-1)*pageSize,selectPage*pageSize),columns,getRowId:r=>r.id,total:filtered.length,sort,onSortChange:s=>{setSort(s);setListPage(1);}}} pagination={{page:selectPage,pageSize,total:filtered.length,onPageChange:setListPage,onPageSizeChange:s=>{setPageSize(s);setListPage(1);}}}/>}
    {page==='detail'&&<Detail<Row> header={{title:pageNames.detail,description:'接入数据后，从业务列表选择一个对象'}} summary={{title:'尚未选择业务对象',description:'负责人、状态与时间均待业务数据提供',status:'info',statusLabel:'待接入',fields:[{label:'对象类型',value:client.entity},{label:'数据来源',value:'待确认'}]}} activeTab={tab} onTabChange={setTab} activity={{title:'进展时间线',items:[]}} related={{title:'关联记录',description:'尚未接入',rows:[],columns,getRowId:r=>r.id}}/>}
    {page==='settings'&&<Settings header={{title:pageNames.settings,description:'仅供预览；刷新恢复项目配置'}} navigation={{items:[{id:'workspace',label:'工作区',description:'显示名称'}],activeId:'workspace',onSelect:()=>document.getElementById('workspace')?.scrollIntoView()}} sections={[{id:'workspace',title:'工作区资料',description:'此处不连接真实业务系统',fields:[{kind:'text',id:'workspace-name',label:'工作区名称',value:draft,onChange:setDraft,required:true}]}]} dirty={draft!==saved} savedMessage={message} onSave={()=>{if(!draft.trim()){setMessage('请输入有效名称');return;}setSaved(draft.trim());setDraft(draft.trim());setMessage('已用于本次预览，刷新恢复项目配置');}} onCancel={()=>setDraft(saved)} danger={{title:'恢复预览名称',description:'仅恢复当前页面的演示名称',actionLabel:'恢复名称',confirmText:'恢复',confirmDescription:'不会修改任何真实客户数据',onConfirm:()=>{setSaved(client.name);setDraft(client.name);setMessage('已恢复项目配置名称');}}}/>}
   </main>
  </AppShell>
 </ThemeProvider>;
}
createRoot(document.getElementById('root')!).render(<React.StrictMode><App/></React.StrictMode>);
