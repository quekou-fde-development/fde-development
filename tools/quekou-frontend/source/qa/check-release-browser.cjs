const assert=require('node:assert/strict'),fs=require('node:fs'),http=require('node:http'),path=require('node:path');
const {build}=require('esbuild');const {chromium,launchOptions}=require('./browser-runtime.cjs');
(async()=>{
 const report={result:'running',checks:[],errors:[]};
 const check=(name,value)=>{assert.ok(value,name);report.checks.push(name);};
 const browser=await chromium.launch(launchOptions);const page=await browser.newPage({viewport:{width:390,height:844}});
 page.on('pageerror',e=>report.errors.push(e.message));
 const base=process.env.WORKBENCH_BASE_URL||'http://127.0.0.1:4173';
 await page.goto(base+'/?view=recipes&style=6&page=overview');
 const sizes=await page.locator('.qk-trend-chart text').evaluateAll(nodes=>nodes.map(n=>{const m=n.getScreenCTM();return parseFloat(getComputedStyle(n).fontSize)*Math.hypot(m.a,m.b);}));
 check('mobile chart labels render at least 13 CSS pixels',sizes.length>0&&Math.min(...sizes)>=13);
 const source=`import React from 'react';import{createRoot}from'react-dom/client';import{ThemeProvider,DangerZone,TrendPanel,BreakdownPanel,EntitySummary,normalizeTheme}from'@quekou/ui';import'@quekou/theme/tokens.css';import'@quekou/ui/styles.css';
 window.calls=0;window.testTheme=normalizeTheme({theme:'__proto__'}).theme;
 function App(){return <ThemeProvider><DangerZone title="Archive" description="Async acceptance" actionLabel="Archive" confirmText="yes" confirmDescription="Test only" onConfirm={async()=>{window.calls++;await new Promise(r=>setTimeout(r,600));if(window.calls===1)throw Error('simulated');}}/><TrendPanel title="Negative trend" description="signed values" unit="unit" points={[{label:'a',value:-20,target:-10},{label:'b',value:30,target:40}]}/><TrendPanel title="Invalid trend" description="error state" unit="unit" points={[{label:'a',value:NaN}]}/><EntitySummary title="Loading" description="Busy" status="info" statusLabel="Loading" fields={[]} progress={77} loading insight={{text:'stale insight',source:'stale'}}/></ThemeProvider>}createRoot(document.getElementById('root')).render(<React.StrictMode><App/></React.StrictMode>);`;
 const output=await build({stdin:{contents:source,loader:'tsx',resolveDir:process.cwd()},bundle:true,format:'esm',platform:'browser',outdir:'fixture',write:false});
 const files=new Map(output.outputFiles.map(file=>['/'+path.basename(file.path),file.contents]));
 files.set('/',Buffer.from('<!doctype html><html><head><meta charset="utf-8"><link rel="stylesheet" href="/stdin.css"></head><body><div id="root"></div><script type="module" src="/stdin.js"></script></body></html>'));
 const server=http.createServer((req,res)=>{const file=files.get(req.url);if(!file){res.writeHead(404).end();return;}res.setHeader('Content-Type',req.url.endsWith('.js')?'text/javascript':req.url.endsWith('.css')?'text/css':'text/html');res.end(file);});
 await new Promise(resolve=>server.listen(0,'127.0.0.1',resolve));
 try{
 await page.goto('http://127.0.0.1:'+server.address().port);
 await page.getByRole('button',{name:'Archive',exact:true}).click();
 const dialog=page.getByRole('dialog',{name:'Archive',exact:true}),confirm=dialog.getByRole('button',{name:'确认Archive',exact:true});
 await dialog.getByRole('textbox').fill('yes');await confirm.click();check('pending request disables double submission',await confirm.isDisabled());await page.keyboard.press('Escape');check('pending dialog does not dismiss',await dialog.isVisible());
 await dialog.getByRole('alert').waitFor();check('failure is visible without false success',await dialog.isVisible()&&await page.evaluate(()=>window.calls)===1);
 await confirm.click();await dialog.waitFor({state:'hidden'});check('successful retry closes once complete',await page.evaluate(()=>window.calls)===2);
 const points=await page.locator('.qk-trend-line').getAttribute('points');check('signed chart values stay inside the plotting area',points.split(' ').every(p=>{const y=Number(p.split(',')[1]);return y>=40&&y<=192;}));
 check('invalid values show an explicit state',await page.getByText('趋势数据格式有误',{exact:true}).isVisible());
 check('loading hides stale progress and AI text',await page.locator('.qk-summary-progress,.qk-insight').count()===0);
 check('inherited theme names cannot crash the app',await page.evaluate(()=>window.testTheme)==='bento');
 check('no browser errors',report.errors.length===0);
 report.result='passed';report.browser=await browser.version();report.minRenderedChartLabel=Math.min(...sizes);fs.writeFileSync('qa/release/hardening-report.json',JSON.stringify(report,null,2));console.log(JSON.stringify(report));
 }finally{await browser.close();await new Promise(resolve=>server.close(resolve));}
})().catch(e=>{console.error(e);process.exit(1);});
