import fs from 'node:fs';
import assert from 'node:assert/strict';
import {flattenColors,accentVariants} from '../design/preview-parameters.mjs';
const t=JSON.parse(fs.readFileSync('design/tokens.json','utf8'));
assert([2,3,4,5].includes(t.phase));assert.deepEqual(Object.keys(t.systems),['bento','glass','ambient']);if(t.phase===2)assert(!fs.existsSync('packages/ui'),'Stage 3 must not start');
assert(!/#[\da-f]{3,8}\b/i.test(JSON.stringify(t)),'Use HSL/OKLCH, not hex');
const colorGroups=t.contract.colorGroups;
for(const [name,s]of Object.entries(t.systems)){
 assert.deepEqual(Object.keys(s.colors),['light','dark']);
 assert.deepEqual(Object.keys(s.density),['comfortable','compact']);
 assert.deepEqual(Object.keys(s.parameters),['accentHue','density','radiusScale','surfaceMode']);
 for(const mode of ['light','dark']){
  for(const [group,roles]of Object.entries(colorGroups)){
   for(const role of roles)assert(s.colors[mode][group]?.[role],`${name}/${mode}/${group}/${role}`);
  }
  for(const kind of colorGroups.status)for(const role of ['fg','bg'])assert(s.colors[mode].status[kind][role]);
  const env={...t.common,...s.structure,...flattenColors(s.colors[mode]),...s.effects[mode],...s.density[s.defaults.density]};
  const walk=(key,path=[])=>{assert(!path.includes(key),`Cyclic token ${[...path,key]}`);assert.equal(typeof env[key],'string',`Missing ${key}`);for(const r of env[key].matchAll(/var\(--([\w-]+)\)/g))walk(r[1],[...path,key]);};
  for(const key of Object.keys(env))walk(key);
 }
 assert(parseFloat(s.density.compact['row-height'])<parseFloat(s.density.comfortable['row-height']));
 for(const density of Object.values(s.density))for(const key of ['page-padding','panel-padding','grid-gap','row-height','control-height'])assert.equal(parseFloat(density[key])%t.contract.spacing.base,0,`${name}/${key} spacing base`);
}
const variants=accentVariants(t);assert.equal(Object.keys(variants).length,32);
assert.equal(variants.brand['client-blue'],'var(--brand-blue)');
for(const name of ['bento','glass','ambient'])assert(!t.themes[name],'Selected values must have one source in systems');
const spec=fs.readFileSync('design/style-spec.md','utf8');for(const name of ['Bento','Glass','Ambient'])assert(spec.includes(`### ${name}`));
const report={result:'passed',systems:3,modes:6,parameterNames:Object.keys(t.parameterPolicy).filter(k=>k!=='defaultsByStyle'),checks:['complete semantic groups in each mode','resolved references and no cycles','HSL colors','4pt density dimensions','independent default and compact rows','source uniqueness for selected systems','all parameter variants generated','approved phase boundary respected']};
fs.writeFileSync(`qa/phase${t.phase}-token-contract-report.json`,JSON.stringify(report,null,2));console.log(JSON.stringify(report));
