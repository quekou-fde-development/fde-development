import { useRef, type Dispatch, type SetStateAction } from 'react';
import { Activity, ArrowDown, ArrowDownUp, ArrowRight, ArrowUpRight, Bell, Check, CheckCircle2, ChevronDown, ChevronRight, Circle, Clock3, Command, Download, FolderKanban, HelpCircle, Inbox, LayoutDashboard, MoreHorizontal, Search, Settings2, SlidersHorizontal, Sparkles, TriangleAlert, Users, X } from 'lucide-react';
import { actual, target, projects, kpis, number, statusKind, type Project } from '../data';

export interface ViewState { search:string; status:string; owner:string; from:string; to:string; sort:keyof Project; direction:1|-1; selected:string[]; edits:Record<string,number> }
export const initialView: ViewState = {search:'',status:'全部状态',owner:'全部负责人',from:'2026-09-01',to:'2026-10-31',sort:'id',direction:1,selected:[],edits:{}};
export interface SampleProps { view:ViewState; setView:Dispatch<SetStateAction<ViewState>> }
interface Props extends SampleProps { theme:string; name:string }
function Sparkline({ values }: { values:number[] }) {
  const points = values.map((v,i)=>`${i*8},${58-v}`).join(' ');
  return <svg className="sparkline" viewBox="0 0 88 48" preserveAspectRatio="none" aria-hidden="true"><polyline points={points} fill="none" /></svg>;
}
function Chart() {
  const line = (values:number[]) => values.map((v,i)=>`${48+i*48},${160-v*1.4}`).join(' ');
  return <svg className="trend-chart" viewBox="0 0 604 184" role="img" aria-label="近 12 周累计交付产出：实际从 38 万元增至 92 万元；计划从 32 万元增至 87 万元。实线为实际，虚线为计划。">
    {[0,30,60,90].map(v=><g key={v}><line className="chart-grid" x1="48" x2="576" y1={160-v*1.4} y2={160-v*1.4}/><text x="0" y={164-v*1.4}>{v}</text></g>)}
    <polygon className="chart-area" points={`48,160 ${line(actual)} 576,160`} />
    <polyline className="chart-target" points={line(target)} fill="none"/>
    <polyline className="chart-actual" points={line(actual)} fill="none"/>
    {actual.map((v,i)=><circle className="chart-point" key={i} cx={48+i*48} cy={160-v*1.4} r="2.5"><title>第 {i+1} 周：{v} 万元</title></circle>)}
    {['07.06','07.20','08.03','08.17','08.31','09.21'].map((v,i)=><text key={v} x={48+i*105.6} y="182" textAnchor={i===5?'end':'start'}>{v}</text>)}
  </svg>;
}
export default function Workbench({theme,name,view,setView}:Props) {
  const dialog = useRef<HTMLDialogElement>(null);
  const detail = useRef<HTMLDialogElement>(null);
  const current = useRef<Project>(projects[0]);
  const patch = (update:Partial<ViewState>) => setView(v=>({...v,...update}));
  const rows = projects.map(p=>({...p,progress:view.edits[p.id]??p.progress})).filter(p =>
    `${p.name} ${p.id} ${p.client} ${p.owner}`.toLowerCase().includes(view.search.toLowerCase()) &&
    (view.status==='全部状态'||p.status===view.status) && (view.owner==='全部负责人'||p.owner===view.owner) &&
    (!view.from||p.due>=view.from) && (!view.to||p.due<=view.to)
  ).sort((a,b) => typeof a[view.sort]==='number' ? (Number(a[view.sort])-Number(b[view.sort]))*view.direction : String(a[view.sort]).localeCompare(String(b[view.sort]),'zh-CN')*view.direction);
  const sort = (key:keyof Project) => patch({sort:key,direction:view.sort===key&&view.direction===1?-1:1});
  const select = (id:string) => patch({selected:view.selected.includes(id)?view.selected.filter(x=>x!==id):[...view.selected,id]});
  const showDetail = (row:Project) => {current.current=row; patch({}); detail.current?.showModal();};
  const exportRows = () => {
    const csv = '\uFEFF项目编号,项目名称,客户,负责人,金额,进度,状态,交付日\n'+rows.map(p=>[p.id,p.name,p.client,p.owner,p.amount,p.progress,p.status,p.due].join(',')).join('\n');
    const url=URL.createObjectURL(new Blob([csv],{type:'text/csv;charset=utf-8;'}));
    const a=document.createElement('a');a.href=url;a.download='项目交付-演示数据.csv';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);
  };
  const nav = [{label:'工作台概览',icon:LayoutDashboard,href:'overview'},{label:'交付项目',icon:FolderKanban,href:'projects'},{label:'经营指标',icon:Activity,href:'metrics'},{label:'交付趋势',icon:ArrowUpRight,href:'trend'},{label:'待办事项',icon:Inbox,href:'inbox'},{label:'工作台设置',icon:Settings2,href:'style-draft'}];
  const header = (key:keyof Project,label:string) => <th scope="col" aria-sort={view.sort===key?(view.direction===1?'ascending':'descending'):'none'}><button onClick={()=>sort(key)}>{label}<ArrowDownUp aria-hidden="true"/></button></th>;
  // Phase 1 layout variants share these exact business-content nodes.
  const metricCards = kpis.map((k,i)=><article className={`panel kpi-card kpi-${i+1}`} key={k.label}><div className="kpi-label"><span>{k.label}</span><span className="kpi-index">0{i+1}</span></div><div className="kpi-value"><strong>{k.value}</strong><span>{k.unit}</span></div><div className="kpi-bottom"><div><span className="kpi-change">{i===3?<ArrowDown/>:<ArrowUpRight/>}{k.change}</span><span className="kpi-note">{k.note}</span></div><Sparkline values={k.trend}/></div></article>);
  const metricStrip = <section className="kpi-grid" id="metrics" aria-label="关键经营指标">{metricCards}</section>;
  const trendPanel = <article className="panel chart-card" id="trend"><div className="panel-heading"><div><p className="section-kicker">DELIVERY TREND</p><h2>交付产出趋势<span className="heading-unit">万元</span></h2></div><span className="text-fg-muted text-caption">近 12 周</span></div><div className="chart-summary"><strong>92.0 <small>万元</small></strong><div className="chart-legend"><span><i className="legend-line actual"/>实际产出</span><span><i className="legend-line target"/>计划产出</span></div></div><div className="chart-scroll"><Chart/></div></article>;
  const inboxPanel = <article className="panel empty-card" id="inbox"><div className="panel-heading"><div><p className="section-kicker">YOUR INBOX</p><h2>待办事项<span className="count-badge">0</span></h2></div><Inbox/></div><div className="empty-content"><div className="empty-symbol"><Inbox/><span><Check/></span></div><h3>一切井然有序</h3><p>当前没有分配给你的待办。<br/>新的协作事项将在这里出现。</p><button className="text-button" onClick={()=>dialog.current?.showModal()}>查看提醒规则<ArrowRight/></button></div><div className="empty-footer"><Clock3/>最近同步于 09:41</div></article>;
  const analysisPanels = <section className="analysis-grid" aria-label="趋势与待办">{trendPanel}{inboxPanel}</section>;
  const insight = <div className="insight-strip"><span className="insight-icon" aria-hidden="true"><Sparkles/></span><div className="insight-copy"><strong>交付摘要</strong><span className="ai-label">AI 演示</span><p>2 个项目存在风险，建议优先复核「智能客服工作台」与「仓储追溯系统」。</p></div><span className="insight-confirm">需负责人确认</span><button className="icon-button insight-action" aria-label="筛选风险项目" onClick={()=>patch({status:'存在风险',search:'',owner:'全部负责人',from:'2026-09-01',to:'2026-10-31'})}><span className="insight-action-label">筛选风险项目</span><ArrowRight/></button></div>;
  const projectTable = <section className="panel table-card" id="projects"><div className="panel-heading table-title"><div className="inline-heading"><h2>项目明细</h2><span className="count-badge">10</span><span className="table-subtitle">从进度到验收，全程可见</span></div><span className="text-fg-muted text-caption">{view.selected.length>0?`已选择 ${view.selected.length} 项`:'2026 年第三季度'}</span></div>
            <div className="filter-bar"><SlidersHorizontal className="filter-icon"/><label className="select-wrap"><span className="sr-only">项目状态</span><select aria-label="项目状态" value={view.status} onChange={e=>patch({status:e.target.value})}>{['全部状态','正常推进','存在风险','待验收','已完成'].map(s=><option key={s}>{s}</option>)}</select><ChevronDown/></label><label className="select-wrap"><span className="sr-only">负责人</span><select aria-label="负责人" value={view.owner} onChange={e=>patch({owner:e.target.value})}>{['全部负责人','林悦','周明','陈曦','许诺'].map(s=><option key={s}>{s}</option>)}</select><ChevronDown/></label><div className="date-range"><input type="date" aria-label="交付日期开始" value={view.from} max={view.to||undefined} onChange={e=>patch({from:e.target.value})}/><span>—</span><input type="date" aria-label="交付日期结束" value={view.to} min={view.from||undefined} onChange={e=>patch({to:e.target.value})}/></div><label className="table-search"><Search/><input aria-label="搜索项目明细" placeholder="搜索项目或客户" value={view.search} onChange={e=>patch({search:e.target.value})}/>{view.search&&<button aria-label="清空搜索" onClick={()=>patch({search:''})}><X/></button>}</label></div>
            {view.from&&view.to&&view.from>view.to&&<p className="filter-error" role="alert">开始日期晚于结束日期，请重新选择。</p>}
            <div className="table-scroll"><table><caption className="sr-only">10 个虚构项目的交付快照；列标题支持排序</caption><thead><tr><th className="check-cell"><input type="checkbox" aria-label="选择当前全部项目" checked={rows.length>0&&rows.every(p=>view.selected.includes(p.id))} onChange={e=>patch({selected:e.target.checked?[...new Set([...view.selected,...rows.map(p=>p.id)])]:view.selected.filter(id=>!rows.some(p=>p.id===id))})}/></th>{header('name','项目名称')}{header('client','客户')}{header('owner','负责人')}{header('amount','项目金额')}{header('progress','交付进度')}{header('status','状态')}{header('due','交付日期')}<th><span className="sr-only">详情</span></th></tr></thead><tbody>{rows.map(p=><tr key={p.id} className={view.selected.includes(p.id)?'selected':''}><td className="check-cell"><input type="checkbox" aria-label={`选择${p.name}`} checked={view.selected.includes(p.id)} onChange={()=>select(p.id)}/></td><td><button className="project-name" onClick={()=>showDetail(p)}>{p.name}<span>{p.id}</span></button></td><td><span className="client-cell"><span className="category-dot" data-industry={p.category} aria-hidden="true"/><span>{p.client}<small className="client-sector">{p.category}</small></span></span></td><td><span className="owner-cell"><span className="owner-avatar">{p.owner.slice(-1)}</span>{p.owner}</span></td><td className="amount-cell">¥{number.format(p.amount)}</td><td><div className="progress-cell"><div className="progress-track" role="progressbar" aria-label={`${p.name}交付进度`} aria-valuenow={p.progress} aria-valuemin={0} aria-valuemax={100}><svg viewBox="0 0 100 4" preserveAspectRatio="none" aria-hidden="true"><line x1="0" x2={p.progress} y1="2" y2="2"/></svg></div>{theme==='grid'?<label className="inline-progress"><input aria-label={`调整${p.name}进度（本地演示）`} type="number" min="0" max="100" value={p.progress} onChange={e=>patch({edits:{...view.edits,[p.id]:Math.max(0,Math.min(100,Number(e.target.value)))}})}/><span>%</span></label>:<span>{p.progress}%</span>}</div></td><td><span className={`status ${statusKind[p.status]}`}>{p.status==='已完成'?<CheckCircle2/>:p.status==='存在风险'?<TriangleAlert/>:p.status==='待验收'?<Clock3/>:<Circle/>}{p.status}</span></td><td className="date-cell">{p.due.slice(5).replace('-',' / ')}</td><td><button className="row-more" aria-label={`查看${p.name}详情`} onClick={()=>showDetail(p)}><MoreHorizontal/></button></td></tr>)}</tbody></table>{rows.length===0&&<div className="table-empty"><Search/><strong>没有符合条件的项目</strong><p>调整筛选条件，或恢复全部演示项目。</p><button className="button secondary" onClick={()=>setView(initialView)}>重置筛选</button></div>}</div>
            <footer className="table-footer"><span>显示 {rows.length} / 10 个项目{Object.keys(view.edits).length>0?' · 含本地试改进度':''}</span><span className="table-hint">{theme==='grid'?'点击列头排序 · 进度可直接试改':'点击列头排序 · 点击项目查看详情'}</span><span className="page-number" aria-label="当前页，第 1 页，共 1 页">01 <span>/ 01</span></span></footer>
          </section>;
  return <section className={`workbench theme-${theme}`} aria-label={`${name} 工作台样品`}>
    <aside className="sidebar">
      <a href="#overview" className="workspace-brand"><span className="q-mark" aria-hidden="true"><span/><span/><span/></span><span>缺口 <span className="brand-suffix">WORKSPACE</span></span></a>
      <button className="workspace-picker" onClick={()=>dialog.current?.showModal()}><span className="workspace-avatar">Q</span><span>项目交付中心<small>Quekou FDE</small></span><ChevronDown/></button>
      <div className="navigation"><p className="nav-group">工作空间</p>{nav.map((n,i)=><div key={n.label}>{i===4&&<p className="nav-group second-group">运营管理</p>}<a className={`nav-link ${i===0?'active':''}`} href={`#${n.href}`}><n.icon/><span>{n.label}</span>{i===1&&<span className="nav-count">10</span>}{i===4&&<span className="nav-count">0</span>}</a></div>)}</div>
      <div className="sidebar-bottom"><div className="system-status"><CheckCircle2/><span>数据快照已就绪</span></div><p>2026.09.28 · 09:41</p><button className="sidebar-help" onClick={()=>dialog.current?.showModal()}><HelpCircle/>样品使用说明<ArrowUpRight/></button></div>
    </aside>
    <div className="workspace-main">
      <header className="topbar"><div className="breadcrumb"><span>工作空间</span><ChevronRight/><strong>工作台概览</strong></div><div className="topbar-actions"><label className="global-search"><Search/><input aria-label="全局搜索项目" placeholder="搜索项目、客户…" value={view.search} onChange={e=>patch({search:e.target.value})}/><Command/></label><button className="icon-button notification" aria-label="查看两项风险提醒" onClick={()=>dialog.current?.showModal()}><Bell/><span>2</span></button><button className="avatar" aria-label="演示账户：林溪" onClick={()=>dialog.current?.showModal()}>林</button></div></header>
      <main className="workspace-content" id="overview">
        <div className="page-heading"><div><p className="eyebrow">DELIVERY OPERATIONS <span>/ 2026 Q3</span></p><h1>每个项目，心中有数<span className="terminal-cursor" aria-hidden="true">_</span></h1><p className="page-description">项目交付总览 <span>·</span> 统一查看进展、风险与团队协作</p></div><button className="button secondary" onClick={exportRows}><Download/>导出视图</button></div>
        <div className="snapshot-label"><span className="demo-dot"/>虚构演示数据 <span>·</span> KPI 与趋势为固定快照，筛选仅作用于项目明细</div>
        <div className="dashboard-grid">
          {theme==='bento' ? <>
            <section className="bento-mosaic" id="metrics" aria-label="经营概况">
              {metricCards[0]}{trendPanel}{metricCards.slice(1)}{inboxPanel}
            </section>
            {insight}{projectTable}
          </> : theme==='ambient' ? <>
            {metricStrip}
            <section className="ambient-execution" aria-label="项目与 AI 交付摘要">{insight}{projectTable}</section>
            {analysisPanels}
          </> : <>{metricStrip}{analysisPanels}{insight}{projectTable}</>}
        </div>
        <footer className="workspace-footer"><span><span className="q-small">Q</span>QUEKOU FDE <span className="footer-divider">/</span> 让交付，清晰发生。</span><span>样品 2026.09 · 所有数据均为虚构</span></footer>
      </main>
    </div>
    <dialog ref={dialog} className="sample-dialog"><div className="dialog-heading"><h2>样品使用说明</h2><button className="icon-button" aria-label="关闭说明" onClick={()=>dialog.current?.close()}><X/></button></div><p>这是同一份虚构项目数据的风格对比。你可以搜索、筛选、排序、选中行、查看项目详情并导出当前明细。</p><div className="dialog-callout"><TriangleAlert/><div><strong>2 个风险项目</strong><p>智能客服工作台、仓储追溯系统。此提醒用于视觉演示，未连接实际业务系统。</p></div></div><p>当前待办为 0；风险提醒与个人待办属于不同维度。通知规则演示：负责人确认后才生成个人协作事项。</p><button className="button primary" onClick={()=>dialog.current?.close()}>知道了</button></dialog>
    <dialog ref={detail} className="sample-dialog"><div className="dialog-heading"><div><p className="eyebrow">{current.current.id}</p><h2>{current.current.name}</h2></div><button className="icon-button" aria-label="关闭项目详情" onClick={()=>detail.current?.close()}><X/></button></div><dl className="detail-grid"><div><dt>客户</dt><dd>{current.current.client}</dd></div><div><dt>负责人</dt><dd>{current.current.owner}</dd></div><div><dt>项目金额</dt><dd>¥{number.format(current.current.amount)}</dd></div><div><dt>交付日期</dt><dd>{current.current.due}</dd></div><div><dt>交付进度</dt><dd>{current.current.progress}%</dd></div><div><dt>当前状态</dt><dd>{current.current.status}</dd></div></dl><p className="text-fg-muted">虚构演示数据，仅用于样品比较。</p></dialog>
  </section>;
}
