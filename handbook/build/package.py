"""Rebuild the companion ZIP from an explicitly supplied resource directory."""
from pathlib import Path, PurePosixPath
import argparse, hashlib, json, zipfile
p=argparse.ArgumentParser();p.add_argument('--resources',type=Path,default=Path(__file__).resolve().parent.parent/'resources_10.06.4');p.add_argument('--output',type=Path,default=Path(__file__).resolve().parent.parent/'FDE开发配套资源包_10.06.zip');args=p.parse_args()
files={}
for f in sorted(args.resources.rglob('*')):
 if f.is_symlink():raise ValueError('Symlink: '+str(f))
 if f.is_file() and f.name not in {'.DS_Store','SHA256SUMS.txt'}:
  n=f.relative_to(args.resources).as_posix();assert '..' not in PurePosixPath(n).parts;files[n]=f.read_bytes()
sha=lambda b:hashlib.sha256(b).hexdigest()
manifest=json.loads(files['manifest.json'])
for pkg in manifest['packages']:
 assert sha(files[pkg['file']])==pkg['sha256'],pkg['file']
files['SHA256SUMS.txt']=''.join(f'{sha(b)}  {n}\n' for n,b in sorted(files.items())).encode()
(args.resources/'SHA256SUMS.txt').write_bytes(files['SHA256SUMS.txt'])
with zipfile.ZipFile(args.output,'w',zipfile.ZIP_DEFLATED,compresslevel=9) as z:
 for n,b in sorted(files.items()):
  item=zipfile.ZipInfo(n,(2026,10,6,0,0,0));item.compress_type=zipfile.ZIP_DEFLATED;item.external_attr=0o100644<<16;z.writestr(item,b)
print(json.dumps({'file':args.output.name,'sha256':sha(args.output.read_bytes()),'packages':len(manifest['packages']),'files':len(files)}))
