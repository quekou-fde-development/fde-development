import fs from 'node:fs';import path from 'node:path';import {createHash} from 'node:crypto';import {fileURLToPath} from 'node:url';
const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..');
const digest=p=>createHash('sha256').update(fs.readFileSync(p)).digest('hex');
const entries=fs.readFileSync(path.join(root,'SHA256SUMS.txt'),'utf8').trim().split('\n');
const expected=new Set(['SHA256SUMS.txt']);
for(const entry of entries){const match=/^([a-f0-9]{64})  (.+)$/.exec(entry);if(!match)throw Error('Malformed manifest');const [,hash,name]=match;if(path.isAbsolute(name)||name.split('/').includes('..'))throw Error('Unsafe path');const p=path.resolve(root,name);if(fs.lstatSync(p).isSymbolicLink()||digest(p)!==hash)throw Error('Checksum mismatch: '+name);expected.add(name);}
function walk(dir){for(const e of fs.readdirSync(dir,{withFileTypes:true})){const p=path.join(dir,e.name),rel=path.relative(root,p).split(path.sep).join('/');if(e.isDirectory())walk(p);else if(!expected.has(rel))throw Error('Unexpected file: '+rel);}}
walk(root);console.log('Verified '+entries.length+' files. Run before installing dependencies; installation adds new files.');
