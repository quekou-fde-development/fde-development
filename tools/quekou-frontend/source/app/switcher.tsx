import { useEffect, useState, type ComponentType } from 'react';
import { ArrowLeft, ArrowRight, Check, ChevronDown, Moon, RotateCcw, Sun } from 'lucide-react';
import tokenSource from '../design/tokens.json';
import preferences from '../design/preferences.json';
import { ThemeReview, defaultParameters, normalizeParameters, isSystemKey, type SystemKey, type ThemeParameters } from './theme-review';
import * as samples from './specimens';
import { initialView, type SampleProps } from './specimens/Workbench';

const specimenList:ComponentType<SampleProps>[] = [samples.Sample01,samples.Sample02,samples.Sample03,samples.Sample04,samples.Sample05,samples.Sample06,samples.Sample07,samples.Sample08,samples.Sample09,samples.Sample10];
const shortNames = ['Swiss','Industrial','Editorial','Soft','Grid','Bento','Glass','Terminal','Calm','Ambient'];
const readPicks = ():number[] => {try {if(localStorage.getItem('quekou-style-picks-revision')!==preferences.revision)return [...preferences.styleIds];const a:unknown=JSON.parse(localStorage.getItem('quekou-style-picks')||'[]');return Array.isArray(a)?a.filter((v):v is number=>Number.isInteger(v)&&v>=1&&v<=10).slice(0,3):[...preferences.styleIds];}catch{return [...preferences.styleIds];}};
export default function Switcher() {
  const query = new URLSearchParams(location.search);
  const initial = Number(query.get('style')||'6');
  const [index,setIndex] = useState(Number.isInteger(initial)&&initial>=1&&initial<=10?initial-1:0);
  const [dark,setDark] = useState(query.get('mode')==='dark');
  const [parameters,setParameters] = useState<Record<SystemKey,ThemeParameters>>(()=>{
    const map={bento:defaultParameters('bento'),glass:defaultParameters('glass'),ambient:defaultParameters('ambient')};
    const key=tokenSource.styles.find(s=>s.id===initial)?.key;
    if(key&&isSystemKey(key)) map[key]=normalizeParameters(key,{accentHue:query.get('accentHue')??'brand',density:query.get('density'),radiusScale:query.get('radiusScale'),surfaceMode:query.get('surfaceMode')??query.get('mode')});
    return map;
  });
  const [view,setView] = useState(initialView);
  const [picks,setPicks] = useState<number[]>(readPicks);
  useEffect(()=>{try{if(localStorage.getItem('quekou-style-picks-revision')!==preferences.revision){setPicks([...preferences.styleIds]);localStorage.setItem('quekou-style-picks',JSON.stringify(preferences.styleIds));localStorage.setItem('quekou-style-picks-revision',preferences.revision);}}catch{/* In-memory picks still reflect the user's saved project preference. */}},[]);
  const [announcement,setAnnouncement] = useState('');
  useEffect(()=>{if(!announcement)return;const timer=window.setTimeout(()=>setAnnouncement(''),parseInt(tokenSource.common['feedback-duration'],10));return()=>window.clearTimeout(timer);},[announcement]);
  const [openDraft,setOpenDraft] = useState(true);
  const style = tokenSource.styles[index];
  const theme = style.key==='editorial'&&dark?'editorial-dark':style.key;
  const systemKey=isSystemKey(style.key)?style.key:undefined;
  const params=systemKey?parameters[systemKey]:undefined;
  const Sample=specimenList[index];
  const writeQuery=(n:number,map:Record<SystemKey,ThemeParameters>)=>{const url=new URL(location.href);url.searchParams.set('style',String(n+1));const key=tokenSource.styles[n].key;if(isSystemKey(key)){for(const [name,value]of Object.entries(map[key]))url.searchParams.set(name,String(value));url.searchParams.delete('mode');}else{for(const name of ['accentHue','density','radiusScale','surfaceMode'])url.searchParams.delete(name);url.searchParams.set('mode',dark?'dark':'light');}history.replaceState(null,'',url);};
  const changeParameters=(next:ThemeParameters)=>{if(!systemKey)return;const map={...parameters,[systemKey]:next};setParameters(map);writeQuery(index,map);};
  useEffect(()=>{if(systemKey)writeQuery(index,parameters);},[]);
  const switchTo=(next:number)=>{const n=(next+10)%10;setIndex(n);writeQuery(n,parameters);setAnnouncement(`正在查看 ${tokenSource.styles[n].name}`);};
  const toggleDark=()=>{setDark(!dark);const url=new URL(location.href);url.searchParams.set('mode',dark?'light':'dark');history.replaceState(null,'',url);};
  const choose=()=>{if(!picks.includes(style.id)&&picks.length>=3){setAnnouncement('已选 3 种，请先移除一个候选。');return;}const next=picks.includes(style.id)?picks.filter(id=>id!==style.id):[...picks,style.id];setPicks(next);try{localStorage.setItem('quekou-style-picks',JSON.stringify(next));}catch{setAnnouncement('本机存储不可用，候选只在本次页面内保留。');return;}setAnnouncement(next.length?`候选编号：${next.join('、')}`:'候选已清空');};
  return <>
    <header className="gallery-header"><a className="gallery-brand" href="?style=1"><span className="gallery-symbol">Q<span>↗</span></span><span>QUEKOU <span className="gallery-brand-separator">/</span> <strong>工作台风格实验室</strong><small>WORKBENCH ATELIER</small></span></a><div className="gallery-progress"><span className="stage-badge">阶段 02</span><span>规范已认可</span><span className="gallery-divider"/><span>3 种入选风格 · 4 项可调参数</span></div></header>
    <nav className="style-switcher" aria-label="选择视觉风格">{tokenSource.styles.map((s,i)=><button key={s.id} className={`style-tab ${i===index?'is-active':''}`} aria-pressed={i===index} aria-label={`${String(s.id).padStart(2,'0')} ${s.name}`} onClick={()=>switchTo(i)}><span className={`style-swatch swatch-${s.key}`} data-theme={s.key} aria-hidden="true"><i/><i/><i/></span><span className="style-tab-label"><span>{String(s.id).padStart(2,'0')}</span>{shortNames[i]}</span>{picks.includes(s.id)&&<Check className="tab-pick"/>}</button>)}</nav>
    <div className="gallery-workspace" data-theme={theme} data-surface-mode={params?.surfaceMode} data-density={params?.density} data-radius-scale={params?.radiusScale} data-accent-hue={params?.accentHue}>
      <div className="specimen-intro"><div className="intro-title"><span className="specimen-number">{String(style.id).padStart(2,'0')}<small>/ 10</small></span><div><div className="intro-name"><h2>{style.name}</h2><span>{style.label}</span></div><p className="specimen-dna">{style.dna}</p><p className="specimen-reference">母本 <span>{style.references}</span></p></div></div><div className="intro-controls">{style.key==='editorial'&&<div className="mode-switch" role="group" aria-label="Editorial 明暗模式"><button aria-pressed={!dark} onClick={()=>dark&&toggleDark()}><Sun/>浅色</button><button aria-pressed={dark} onClick={()=>!dark&&toggleDark()}><Moon/>深色</button></div>}<button className="button secondary reset-sample" onClick={()=>{setView(initialView);setAnnouncement('样品已重置，恢复 10 行原始数据。');}}><RotateCcw/>重置样品</button><button className={`button ${picks.includes(style.id)?'primary':'secondary'}`} aria-label={picks.includes(style.id)?'已加入候选':'加入候选'} aria-pressed={picks.includes(style.id)} onClick={choose}>{picks.includes(style.id)?<Check/>:<span className="plus">+</span>}{picks.includes(style.id)?'已加入候选':'加入候选'}</button><div className="prev-next"><button className="icon-button" aria-label="上一种风格" onClick={()=>switchTo(index-1)}><ArrowLeft/></button><button className="icon-button" aria-label="下一种风格" onClick={()=>switchTo(index+1)}><ArrowRight/></button></div></div></div>
      {systemKey&&params?<ThemeReview systemKey={systemKey} value={params} onChange={changeParameters}/>:<p className="reference-notice">阶段 1 参考样品 · 本轮固化的是 6、7、10 三种风格</p>}
      <Sample view={view} setView={setView}/>
      <section id="style-draft" className="style-draft"><button className="draft-toggle" aria-expanded={openDraft} onClick={()=>setOpenDraft(!openDraft)}><span><span className="draft-marker">STYLE SPEC</span>风格要点</span><ChevronDown className={openDraft?'rotated':''}/></button>{openDraft&&<dl>{style.draft.map((text,i)=><div key={text}><dt><span>0{i+1}</span>{['色板意图','字体意图','描边与阴影','密度','签名元素'][i]}</dt><dd>{text}</dd></div>)}</dl>}</section>
    </div>
    <footer className="selection-footer"><div><span className="selection-label">我的候选</span>{picks.length===0?<span className="selection-placeholder">选 2–3 种，再告诉我编号</span>:picks.map(id=><button key={id} onClick={()=>switchTo(id-1)}>{String(id).padStart(2,'0')} · {shortNames[id-1]}<ArrowRight/></button>)}</div><a className="selection-caption" href="?view=recipes&style=6&surfaceMode=light">阶段 4 · 打开页面模板 →</a></footer>
    <p className="screen-announcement" role="status">{announcement}</p>
  </>;
}
