import {build} from 'esbuild';
import {cp,mkdir,readFile,writeFile} from 'node:fs/promises';
import {execFileSync} from 'node:child_process';
const onlyTheme=process.argv.includes('--theme-only');
for(const name of onlyTheme?['theme']:['theme','ui']){
 const base=`packages/${name}`;await mkdir(`${base}/dist`,{recursive:true});
 for(const format of ['esm','cjs'])await build({entryPoints:[`${base}/src/index.ts`],outfile:`${base}/dist/index.${format==='esm'?'js':'cjs'}`,bundle:true,format,platform:'browser',target:'es2022',external:['react','react-dom','react/jsx-runtime','@quekou/theme','lucide-react'],jsx:'automatic'});
 execFileSync(process.execPath,['node_modules/typescript/bin/tsc','-p',`${base}/tsconfig.json`],{stdio:'inherit'});
 if(name==='theme'){
  await cp(`${base}/src/tokens.css`,`${base}/dist/tokens.css`);
  for(const format of ['esm','cjs'])await build({entryPoints:[`${base}/src/tailwind.preset.ts`],outfile:`${base}/dist/tailwind.preset.${format==='esm'?'js':'cjs'}`,bundle:true,format,platform:'node',target:'es2022'});
 }else await writeFile(`${base}/dist/styles.css`,(await readFile(`${base}/src/styles.css`,'utf8'))+'\n'+(await readFile(`${base}/src/blocks.css`,'utf8')));
}
console.log('Built typed ESM and CommonJS packages.');
