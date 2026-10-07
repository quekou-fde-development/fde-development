import {spawn} from 'node:child_process';
import {setTimeout as delay} from 'node:timers/promises';
import {mkdir} from 'node:fs/promises';
const port = 4197;
const base = `http://127.0.0.1:${port}`;
try { await fetch(base); throw new Error(`Port ${port} is already in use; stop that preview before testing.`); }
catch (error) { if (error.message.includes('already in use')) throw error; }
for (const dir of ['qa/phase3','qa/phase4','qa/release']) await mkdir(dir,{recursive:true});
// Test built output, including the same CSS and package exports shipped to colleagues.
const server = spawn(process.execPath,['node_modules/vite/bin/vite.js','preview','--host','127.0.0.1','--port',String(port),'--strictPort'],{stdio:'pipe'});
server.stderr.pipe(process.stderr);
const run = file => new Promise((resolve,reject)=>{
  const child=spawn(process.execPath,[file],{stdio:'inherit',env:{...process.env,WORKBENCH_BASE_URL:base}});
  child.on('error',reject);child.on('exit',code=>code===0?resolve():reject(new Error(`${file} exited ${code}`)));
});
try {
  let ready=false;
  for(let i=0;i<100;i++){try {const res=await fetch(base);if(res.ok){ready=true;break;}}catch{}await delay(100);}
  if(!ready)throw new Error('Built preview did not start. Run npm run check first.');
  await run('qa/check-phase3.cjs');
  await run('qa/check-phase4.cjs');
  await run('qa/check-release-browser.cjs');
} finally { server.kill(); }
