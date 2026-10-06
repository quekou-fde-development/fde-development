import {tmpdir} from 'node:os';import path from 'node:path';import {pathToFileURL} from 'node:url';
import {build} from 'esbuild';import fs from 'node:fs';import assert from 'node:assert/strict';
const output=path.join(fs.mkdtempSync(path.join(tmpdir(),'quekou-model-')),'model.mjs');await build({entryPoints:['app/workbench/model.ts'],bundle:true,format:'esm',platform:'node',outfile:output});const m=await import(pathToFileURL(output).href);
assert.deepEqual(m.totals(m.initialWorkProjects),{amount:1286000,count:10,average:67.1,risks:2,completed:2});
const totalTrend=m.trend(m.initialWorkProjects).reduce((s,p)=>s+p.value,0);assert(Math.abs(totalTrend-128.6)<.001);
const sorted=m.selectProjects(m.initialWorkProjects,m.emptyQuery,{column:'amount',direction:'desc'});assert.deepEqual(sorted.map(p=>p.amount),[210000,186000,168000,148000,128000,112000,96000,88000,78000,72000]);
const originalIds=m.initialWorkProjects.map(p=>p.id);m.selectProjects(m.initialWorkProjects,m.emptyQuery,{column:'amount',direction:'asc'});assert.deepEqual(m.initialWorkProjects.map(p=>p.id),originalIds);
assert.deepEqual(m.selectProjects(m.initialWorkProjects,{...m.emptyQuery,search:'林悦',from:'2026-10-01'},null).map(p=>p.id),['QK-1027','QK-1032']);
assert.equal(m.selectProjects(m.initialWorkProjects,{...m.emptyQuery,status:'存在风险',client:'星野零售'},null).length,1);
assert.deepEqual(m.totals([]),{amount:0,count:0,average:0,risks:0,completed:0});
const fresh={...m.initialWorkProjects[0],id:'QK-DEMO-1',progress:0};assert.equal(m.timeline(fresh).length,1);assert.equal(m.relatedRecords(fresh).length,0);
const report={result:'passed',checks:['same ten project records','derived amount average count risk totals','chart reconciles to contract amount','global numeric sort before page slicing','non-mutating query','combined text status client and date filters','empty totals','new record has no fabricated history or documents']};fs.writeFileSync('qa/phase4/model-report.json',JSON.stringify(report,null,2));console.log(JSON.stringify(report));

fs.rmSync(path.dirname(output),{recursive:true,force:true});
