import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import { fileURLToPath } from 'node:url';
import { marked } from './vendor/marked.mjs';
const here=path.dirname(fileURLToPath(import.meta.url));
const args=process.argv.slice(2);
const value=(name,fallback)=>args.includes(name)?args[args.indexOf(name)+1]:fallback;
const localSource=path.join(here,'../FDE开发技术手册_10.06.md');
const source=path.resolve(value('--source',fs.existsSync(localSource)?localSource:path.join(here,'../development-handbook.md')));
const output=path.resolve(value('--output',path.join(here,path.basename(source)==='development-handbook.md'?'../index.html':'../FDE开发技术手册_10.06.html')));
const raw=fs.readFileSync(source,'utf8');
const version=raw.match(/^version: "([^"]+)"/m)?.[1];
if(!version)throw Error('Source version missing');
const body=raw.replace(/^---\n[\s\S]*?\n---\n/,'');
const hash=s=>crypto.createHash('sha256').update(s).digest('hex');
const escape=s=>s.replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('>','&gt;').replaceAll('"','&quot;');
let html=marked.parse(body,{gfm:true});
const canonicalHash=hash(html);
const headings=[];
html=html.replace(/<h([1-6])(?:\s[^>]*)?>([\s\S]*?)<\/h\1>/g,(_,level,content)=>{
 const title=content.replace(/<[^>]+>/g,'');
 const id=`section-${headings.length}`;
 headings.push({level:+level,title,id});
 return `<h${level} id="${id}">${content}</h${level}>`;
});
html=html.replace(/<table>/g,'<div class="table-wrap" tabindex="0" role="region" aria-label="横向滚动查看表格"><table>').replace(/<\/table>/g,'</table></div>');
const toc=headings.filter(h=>[2,3].includes(h.level)).map(h=>`<a class="toc-level-${h.level}" href="#${h.id}">${h.title}</a>`).join('\n');
const titleHtml=html.match(/<h1[^>]*>[\s\S]*?<\/h1>/)?.[0] || '';
html=html.replace(titleHtml,'');
const css=fs.readFileSync(path.join(here,'handbook.css'),'utf8');
const zip='FDE开发配套资源包_10.06.zip';
const repo='https://github.com/quekou-fde-development/fde-development';
const page=`<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="source-sha256" content="${hash(raw)}"><meta name="canonical-html-sha256" content="${canonicalHash}"><title>FDE 开发技术手册 · ${version} 待审阅</title><style>${css}</style></head>
<body><a class="skip" href="#content">跳到正文</a><aside class="sidebar"><div class="brand">QUEKOU · FDE</div><strong>开发技术手册</strong><div class="edition">${version} · 待审阅版本</div><button class="menu-toggle" aria-controls="handbook-toc" aria-expanded="false" onclick="const s=this.closest('aside');const open=s.toggleAttribute('data-open');this.setAttribute('aria-expanded',open);this.textContent=open?'收起目录':'展开目录'">展开目录</button><nav id="handbook-toc" aria-label="章节目录">${toc}</nav><button class="print" onclick="window.print()">打印 / 另存为 PDF</button></aside>
<main id="content"><article class="sheet"><div class="eyebrow">从调研语料到开发、发布与反馈</div>${titleHtml}<span class="badge">${version} · 待审阅</span><div class="download-box"><a class="download-button" href="${zip}" download>下载配套资源总 ZIP</a><br><a class="download-button secondary" href="${escape(path.basename(source))}" download>Markdown 源文档</a><a class="download-button secondary" href="${repo}">统一开发规范仓库</a><a class="download-button secondary" href="${repo}/issues/new?template=feedback.yml">提交反馈</a></div>
<div class="path" aria-label="工作路径"><div class="stage"><span>第一部分</span><strong>出架构</strong><small>调研输入 → 九份架构 Markdown<br>配套开发计划（标准化待补）</small></div><div class="gate">夏洛克审核<br>通过后进入 →</div><div class="stage"><span>第二部分</span><strong>开发与上线测试</strong><small>独立项目仓库 → 开发、测试、发布<br>问题回到仓库反馈入口</small></div></div>
<section id="handbook-body">${html}</section><footer class="foot">缺口 FDE · ${version}。本文与 Markdown 同源；正文及本地配套资料可离线阅读，GitHub 与网站服务需联网。</footer></article></main></body></html>`;
fs.writeFileSync(output,page);
const result={version,source:path.basename(source),output:path.basename(output),source_sha256:hash(raw),canonical_html_sha256:canonicalHash,html_sha256:hash(page),headings:headings.length,bytes:Buffer.byteLength(page)};
fs.writeFileSync(path.join(path.dirname(output),'build-manifest.json'),JSON.stringify(result,null,2)+'\n');
console.log(JSON.stringify(result));
