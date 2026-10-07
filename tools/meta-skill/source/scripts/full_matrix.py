#!/usr/bin/env python3
"""Build the bundled mechanical test sources in a fresh isolated workspace.

The historical 18 arms are reproduced from generators against this package.
No external project tree or historical result files are used. --prepare-only
materializes input fixtures but does not claim a test verdict.
"""
import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

PACKAGE = Path(__file__).resolve().parent.parent


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--run-dir',required=True);ap.add_argument('--prepare-only',action='store_true')
    args=ap.parse_args();root=Path(args.run_dir).resolve()
    if PACKAGE==root or PACKAGE in root.parents:
        ap.error('--run-dir must be outside the skill package')
    root.mkdir(parents=True,exist_ok=False)
    package=root/'v3.8-draft';shutil.copytree(PACKAGE,package,ignore=shutil.ignore_patterns('__pycache__','runs'))
    work=root/'exec-ledger-isolation';shutil.copytree(PACKAGE/'references/mechanical',work)
    for name in ('layer1_results','layer3_results'): (work/name).mkdir()
    env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1',PYTHONUNBUFFERED='1')
    # The legacy tools call python3 internally. Resolve it to the selected runtime.
    bindir=root/'bin';bindir.mkdir();(bindir/'python3').symlink_to(sys.executable)
    env['PATH']=str(bindir)+os.pathsep+env.get('PATH','')
    def execute(name,argv,expected=0):
        with open(root/f'{name}.log','w') as out:
            proc=subprocess.run(argv,cwd=work,env=env,stdout=out,stderr=subprocess.STDOUT)
        print(f'{name}: rc={proc.returncode} expected={expected}',flush=True)
        return {'name':name,'argv':argv,'rc':proc.returncode,'expected_rc':expected,
                'pass':proc.returncode==expected,'log':f'{name}.log'}
    generators=[('runs',['make_runs.py','runs']),('mutants',['make_mutants.py','runs']),
                ('jh',['make_jh_runs.py','runs-jh','fixtures/assertions_jh.json']),
                ('multiop',['make_multiop_fixture.py','runs-multiop','fixtures/assertions_multiop.json']),
                ('e2e',['make_e2e_package.py','packages/e2e-orders-probe']),
                ('gate',['make_gate_fixtures.py','gate-fixtures']),
                ('custom',['make_custom_fixtures.py','custom-fixtures']),
                ('predicate',['make_predicate_fixtures.py','predicate-fixtures'])]
    preparation=[]
    for name,argv in generators:
        row=execute('prepare-'+name,[sys.executable,'tools/'+argv[0],*argv[1:]])
        preparation.append(row)
        if not row['pass']:
            (root/'result.json').write_text(json.dumps({'status':'PREPARATION_FAILED','preparation':preparation},indent=2)+'\n')
            return 1
    if args.prepare_only:
        (root/'result.json').write_text(json.dumps({'status':'PREPARED_NOT_TESTED','preparation':preparation},indent=2)+'\n')
        return 0
    v='../v3.8-draft/scripts/validate.py';a='../v3.8-draft/scripts/audit.py'
    arms=[
      ('gate_matrix',['tools/gate_matrix.py','gate-fixtures','custom-fixtures',v,'layer1_results/gate_matrix.json'],0),
      ('accept_matrix',['tools/accept_matrix.py','runs','fixtures/assertions_oaq.json','fixtures/mock-task1.md','fixtures/mock-task3.md','layer3_results/accept_matrix.json','runs-jh','fixtures/assertions_jh.json','runs-multiop','fixtures/assertions_multiop.json'],0),
      ('ambiguous_ref',[a,'runs-multiop/golden-multiop','--contract','fixtures/assertions_multiop_ambiguous.json','--all'],1),
      ('e2e_chain',['tools/e2e_chain.py','packages/e2e-orders-probe','runs-e2e','layer3_results/e2e_chain.json'],0),
      ('ir_drift',['tools/ir_drift.py'],0),('manifest_consumer',['tools/manifest_consumer.py','--self-test'],0),
      ('validate_e2e',[v,'packages/e2e-orders-probe'],0),
      ('mutant_matrix',['tools/gen_mutant_matrix.py','../v3.8-draft/references/mutant_matrix.md','--check'],0),
      ('render_negatives',['tools/render_contract_negatives.py'],0),
      ('contract_identity',['tools/contract_identity_negatives.py'],0),
      ('predicate_fixture',['tools/make_predicate_fixtures.py','predicate-fixtures','--check'],0),
      ('predicate_family',['tools/predicate_family_behavior.py','../v3.8-draft'],0),
      ('reason_binding',['tools/gate_reason_binding_negatives.py'],0),
      ('contract_path',['tools/contract_path_behavior.py'],0),
      ('skill_drift',['tools/skill_drift.py'],0),('skill_drift_neg',['tools/skill_drift_negatives.py'],0),
      ('persistent_self',[v,'../v3.8-draft','--persistent'],0),
      ('fixture_material',['tools/fixture_materialization_negatives.py'],0)]
    rows=[execute(name,[sys.executable,*argv],expected) for name,argv,expected in arms]
    ok=all(r['pass'] for r in rows)
    (root/'result.json').write_text(json.dumps({'status':'PASS' if ok else 'FAIL','python':sys.executable,
        'preparation':preparation,'arms':rows},ensure_ascii=False,indent=2)+'\n')
    print(f"{'PASS' if ok else 'FAIL'} {sum(r['pass'] for r in rows)}/{len(rows)}",flush=True)
    return 0 if ok else 1


if __name__=='__main__':sys.exit(main())
