// Executed inside a real browser. Range compositing covers transparent gradients conservatively.
module.exports=function scanContrast(){
 const canvas=document.createElement('canvas');canvas.width=canvas.height=1;const ctx=canvas.getContext('2d',{willReadFrequently:true});
 const rgba=color=>{ctx.clearRect(0,0,1,1);ctx.fillStyle=color;ctx.fillRect(0,0,1,1);const d=ctx.getImageData(0,0,1,1).data;return [d[0],d[1],d[2],d[3]/255];};
 const blend=(a,b)=>a.slice(0,3).map((v,i)=>v*a[3]+b[i]*(1-a[3])).concat(1);
 const lum=rgb=>rgb.slice(0,3).map(v=>v/255).map(v=>v<=.04045?v/12.92:((v+.055)/1.055)**2.4).reduce((s,v,i)=>s+v*[.2126,.7152,.0722][i],0);
 const ratio=(a,b)=>{const x=lum(a),y=lum(b);return (Math.max(x,y)+.05)/(Math.min(x,y)+.05);};
 const layers=value=>{const out=[];let depth=0,start=0;for(let i=0;i<value.length;i++){if(value[i]==='(')depth++;if(value[i]===')')depth--;if(value[i]===','&&!depth){out.push(value.slice(start,i));start=i+1;}}out.push(value.slice(start));return out;};
 const cache=new WeakMap();
 function bg(el){
  if(!el)return [[255,255,255,1],[255,255,255,1]];
  if(cache.has(el))return cache.get(el);
  const cs=getComputedStyle(el),base=rgba(cs.backgroundColor);let range=bg(el.parentElement).map(b=>blend(base,b));
  for(const layer of layers(cs.backgroundImage).reverse()){
   const colors=(layer.match(/(?:rgba?|hsla?|color|oklch)\([^)]*\)|transparent/g)||[]).map(rgba);
   if(!colors.length)continue;
   const points=colors.flatMap(c=>range.map(b=>blend(c,b)));
   range=[0,1].map(upper=>[0,1,2].map(i=>Math[upper?'max':'min'](...points.map(p=>p[i]))).concat(1));
  }
  cache.set(el,range);return range;
 }
 let min=100,count=0;const violations=[];
 const check=(el,color,text)=>{const range=bg(el);const values=range.map(b=>ratio(blend(rgba(color),b),b));const r=Math.min(...values);min=Math.min(min,r);count++;if(r<4.5)violations.push({text:text.slice(0,70),ratio:+r.toFixed(2),class:typeof el.className==='string'?el.className:el.tagName});};
 const walker=document.createTreeWalker(document.body,NodeFilter.SHOW_TEXT);let n;
 while(n=walker.nextNode()){
  const el=n.parentElement;if(!el||!n.textContent.trim()||['SCRIPT','STYLE','TITLE','OPTION'].includes(el.tagName)||el.closest('.sr-only,dialog:not([open])'))continue;
  const r=el.getBoundingClientRect(),cs=getComputedStyle(el);if(!r.width||!r.height||cs.visibility==='hidden')continue;
  check(el,el instanceof SVGElement?cs.fill:cs.color,n.textContent.trim());
 }
 for(const el of document.querySelectorAll('input,select')){const r=el.getBoundingClientRect();if(!r.width||!r.height||['checkbox','range'].includes(el.type))continue;check(el,getComputedStyle(el).color,el.getAttribute('aria-label')||el.value);if(el.placeholder)check(el,getComputedStyle(el,'::placeholder').color,el.placeholder);}
 const root=document.querySelector('.gallery-workspace');const cs=getComputedStyle(root);const c=name=>rgba(cs.getPropertyValue('--'+name).trim());
 const pairs=[];
 for(const fg of ['fg-primary','fg-muted','fg-subtle','accent-default'])for(const surface of ['surface-base','surface-raised','surface-overlay','surface-hover'])pairs.push([fg,surface,4.5]);
 for(const status of ['success','warning','danger','info'])pairs.push(['status-'+status,'status-'+status+'-bg',4.5]);
 pairs.push(['accent-fg','accent-solid',4.5],['accent-fg','accent-hover',4.5],['accent-default','accent-soft',4.5],['hero-fg','hero-bg',4.5],['hero-muted','hero-bg',4.5],['focus-ring','surface-base',3],['focus-ring','surface-raised',3]);
 const semanticPairs=pairs.map(([fg,bg,min])=>({fg,bg,min,ratio:+ratio(c(fg),c(bg)).toFixed(3)}));
 return {count,minContrast:+min.toFixed(3),violations,semanticPairs,overflow:document.documentElement.scrollWidth>innerWidth};
};
