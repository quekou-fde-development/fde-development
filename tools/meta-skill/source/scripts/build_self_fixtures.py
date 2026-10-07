#!/usr/bin/env python3
"""Materialize helper fixtures from real files, then apply directed mutations.

These are deterministic pipeline fixtures; they do not measure model behavior.
Write only to the explicit new output directory. Existing evidence is preserved.
"""
import argparse
import copy
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--output', required=True)
    args = ap.parse_args()
    out = Path(args.output).resolve()
    out.mkdir(parents=True, exist_ok=False)
    package = Path(__file__).resolve().parent.parent
    golden = out/'golden-self'
    golden.mkdir()
    stages = ('init_eval_workspace', 'run_trigger_eval', 'aggregate_benchmark')
    for stage in stages:
        subprocess.run([sys.executable, str(package/'scripts/run_meta_stages.py'), '--stage', stage, '--run-dir', str(golden)], check=True)
        subprocess.run([sys.executable, str(package/'scripts/audit.py'), str(golden), '--stage', stage, '--json'], check=True)
    # Normalize only the shipping fixtures. Original helper outputs remain in
    # golden/workspace; normalized fixture bytes receive new, real file hashes.
    for path in (golden/'stage_outputs').rglob('*'):
        if path.is_file():
            value = path.read_text(encoding='utf-8')
            value = value.replace(str(golden), 'fixture://run').replace(str(package), 'fixture://package')
            path.write_text(value, encoding='utf-8')
    for path in golden.glob('*_receipt.json'):
        receipt = json.loads(path.read_text())
        for item in receipt['outputs']:
            item['sha256'] = hashlib.sha256((golden/item['id']).read_bytes()).hexdigest()[:16]
        canonical = json.dumps(receipt['outputs'], ensure_ascii=False, sort_keys=True, separators=(',', ':'))
        receipt['outputs_sha256'] = hashlib.sha256(canonical.encode()).hexdigest()[:16]
        path.write_text(json.dumps(receipt, ensure_ascii=False, indent=2)+'\n')
    subprocess.run([sys.executable, str(package/'scripts/audit.py'), str(golden), '--all', '--json', '--manifest', str(golden/'run_manifest.json')], check=True)
    manifest = golden/'run_manifest.json'
    manifest.write_text(manifest.read_text().replace(str(golden), 'fixture://run'))
    # Ship the immutable stage files and receipts, not the mutable eval workspace.
    for suffix, stage in zip(('init', 'trigger', 'aggregate'), stages):
        dest = out/f'mutant-self-{suffix}'
        dest.mkdir()
        for path in golden.glob('*_receipt.json'):
            shutil.copyfile(path, dest/path.name)
        shutil.copytree(golden/'stage_outputs', dest/'stage_outputs')
        name = f'{stage}_receipt.json'
        receipt = json.loads((dest/name).read_text())
        receipt.pop('fetched_at')
        receipt['output_count'] += 1
        receipt['outputs'][0].pop('sha256')
        (dest/name).write_text(json.dumps(receipt, ensure_ascii=False, indent=2)+'\n')
        injection = {'mutation': f'M-self-{suffix}',
                     'must_be_rejected_by': '/'.join(f'self.{suffix}.{a}' for a in ('receipt', 'schema', 'count_hash')),
                     'doc': 'Remove receipt timestamp and a file hash; alter declared count.'}
        (dest/'INJECTION.json').write_text(json.dumps(injection,ensure_ascii=False,indent=2)+'\n')
    print(out)


if __name__ == '__main__':
    main()
