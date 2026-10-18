#!/usr/bin/env python3
"""Exercise frozen-decision gates; synthetic inputs are not client approvals."""
import argparse
import copy
import hashlib
import json
import shutil
from pathlib import Path
from generator_regression import PACKAGE, prepare, run_command, save
from structure_regression import content_fixture, prepare_review_fixture


def register(root):
    return root / 'input/sources/decision-register.json'


def change_register(root, edit):
    p = register(root); obj = json.loads(p.read_text()); edit(obj); save(p, obj)


def run(root, failed_run=None):
    root.mkdir(parents=True, exist_ok=False)
    cases = []
    def stage(directory, label, preview=False):
        return run_command(root, label, [PACKAGE / 'scripts/run_meta_stages.py', '--stage',
            'render_documents', '--run-dir', directory, *(['--preview'] if preview else [])])
    def acquire(directory, label):
        out = run_command(root, label, [PACKAGE / 'scripts/run_meta_stages.py',
            '--stage', 'acquire_sources', '--run-dir', directory]); assert out['exit_code'] == 0, out
    def negative(name, edit, expected, after=False):
        directory = root / name; prepare(directory, content_fixture())
        if after: acquire(directory, name + '-acquire')
        edit(directory)
        if not after: acquire(directory, name + '-acquire')
        for preview in [True, False]:
            out = stage(directory, name + ('-preview' if preview else '-final'), preview)
            assert out['exit_code'] == expected, out
            assert not (directory / 'design').exists() and not (directory / 'working/previews').exists()
            assert not (directory / 'render_documents_receipt.json').exists()
        cases.append({'case': name, 'verdict': 'PASS', 'blocked_both_entrypoints': True, 'exit_code': expected})
    negative('empty_request_cannot_close_open_decision',
             lambda d: change_register(d, lambda x: x['decisions'][0].update(state='open')), 3)
    negative('missing_required_topic',
             lambda d: change_register(d, lambda x: x['decisions'].pop(1)), 3)
    def remove_manifest_register(d):
        p=d/'input/source_manifest.json';x=json.loads(p.read_text())
        x['sources']=[s for s in x['sources'] if s['kind']!='decision-register'];save(p,x)
    negative('legacy_no_register_not_ready', remove_manifest_register, 3)
    def source_kind(d, kind):
        p=d/'input/source_manifest.json';x=json.loads(p.read_text())
        next(s for s in x['sources'] if s['id']=='decision-premises')['kind']=kind;save(p,x)
    negative('simulation_cannot_close_project_decision',lambda d:source_kind(d,'simulation'),2)
    negative('reference_cannot_close_project_decision',lambda d:source_kind(d,'reference'),2)
    negative('unclassified_cannot_close_project_decision',lambda d:source_kind(d,'markdown'),2)
    negative('invented_quote',lambda d:change_register(d,lambda x:x['decisions'][0]['evidence'][0].update(quote='编造的确认')),2)
    negative('duplicate_decision_id',lambda d:change_register(d,lambda x:x['decisions'][1].update(id='D-1')),2)
    def duplicate_topic(x):
        row=copy.deepcopy(x['decisions'][0]);row['id']='D-4';x['decisions'].append(row)
    negative('duplicate_current_topic',lambda d:change_register(d,duplicate_topic),2)
    negative('invalid_state',lambda d:change_register(d,lambda x:x['decisions'][0].update(state='approved')),2)
    negative('stale_source_classification',lambda d:source_kind(d,'project-decision'),2,after=True)
    negative('edited_frozen_register',lambda d:change_register(d,lambda x:x['decisions'][0].update(state='defined')),2,after=True)
    negative('edited_original_evidence',lambda d:(d/'input/sources/decision-premises.txt').write_text('原件已改变\n'),2,after=True)
    negative('quote_boolean_line',lambda d:change_register(d,lambda x:x['decisions'][0]['evidence'][0].update(line_start=True)),2)
    def explicit_question(d):
        p=d/'working/render_request.json';x=json.loads(p.read_text());x['unresolved_questions']=['Q-1: 业务授权仍未决定'];save(p,x)
    negative('explicit_question_has_preview_and_final_stop_receipt',explicit_question,3)
    assert (root/'explicit_question_has_preview_and_final_stop_receipt/working/render_blocked.json').is_file()

    for state in ['proposed','defined']:
        d=root/('valid-'+state);prepare(d,content_fixture())
        change_register(d,lambda x:[v.update(state=state) for v in x['decisions']])
        acquire(d,state+'-acquire');prepare_review_fixture(d)
        out=stage(d,state+'-final');assert out['exit_code']==0,out
        assert json.loads((d/'render_documents_receipt.json').read_text())['review_status']=='PENDING_CHIEF_ARCHITECT_REVIEW'
        assert len(list((d/'design').glob('*.md')))==9
        out=run_command(root,state+'-audit',[PACKAGE/'scripts/audit.py',d,'--all','--json'])
        assert out['exit_code']==0,out
        cases.append({'case':state+'_source_allows_candidate_and_schema_derivation','verdict':'PASS','prior_chief_approval_required':False})

    # The final auditor must reject an output whose request still falsely says [].
    d=root/'forged-ready-output';shutil.copytree(root/'valid-proposed',d)
    change_register(d,lambda x:x['decisions'][0].update(state='open'))
    # Rebind the altered source all the way through its mechanical receipts.
    m=json.loads((d/'input/source_manifest.json').read_text());snap=json.loads((d/'working/source_snapshot.json').read_text())
    for s in m['sources']:
        raw=(d/'input'/s['path']).read_bytes();(d/'working/sources'/ (s['id']+'.bin')).write_bytes(raw)
        row=next(v for v in snap['sources'] if v['id']==s['id']);row.update(content_sha256=hashlib.sha256(raw).hexdigest(),byte_count=len(raw))
    save(d/'working/source_snapshot.json',snap)
    rec=json.loads((d/'acquire_sources_receipt.json').read_text())
    for row in rec['outputs']:row['sha256']=hashlib.sha256((d/row['id']).read_bytes()).hexdigest()[:16]
    rec['outputs_sha256']=hashlib.sha256(json.dumps(rec['outputs'],ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()).hexdigest()[:16]
    save(d/'acquire_sources_receipt.json',rec)
    proof=json.loads((d/'working/content_review_proof.json').read_text());proof['source_snapshot_sha256']=hashlib.sha256((d/'working/source_snapshot.json').read_bytes()).hexdigest();save(d/'working/content_review_proof.json',proof)
    out=run_command(root,'forged-ready-audit',[PACKAGE/'scripts/audit.py',d,'--all','--json'])
    assert out['exit_code']==1,out
    failures=[v['id'] for v in json.loads(out['stdout'])['rows'] if v['status']=='FAIL']
    assert failures==['render.decision_basis'],failures
    cases.append({'case':'independent_audit_rejects_resigned_open_decision','verdict':'PASS','rejected_by':failures})
    if failed_run:
        src=Path(failed_run);d=root/'actual-failed-request'
        (d/'working').mkdir(parents=True);(d/'input').mkdir()
        for name in ['input/source_manifest.json','working/render_request.json']:
            shutil.copy2(src/name,d/name)
        assert json.loads((d/'working/render_request.json').read_text())['unresolved_questions']==[]
        acquire(d,'actual-acquire')
        for preview in [True,False]:
            out=stage(d,'actual-'+('preview' if preview else 'final'),preview)
            assert out['exit_code']==3,out
        assert not (d/'design').exists() and not (d/'working/previews').exists()
        cases.append({'case':'actual_previous_failed_request_blocked','verdict':'PASS',
                      'request_sha256':hashlib.sha256((d/'working/render_request.json').read_bytes()).hexdigest(),
                      'scope':'Unmodified failed request and original source manifest; no project decisions added.'})
    result={'verdict':'PASS','engineering_fixture_only':True,'actual_failure_replay':bool(failed_run),'cases':cases}
    save(root/'result.json',result);return result


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--run-dir',required=True);p.add_argument('--failed-run')
    a=p.parse_args();result=run(Path(a.run_dir),a.failed_run)
    print(json.dumps({'verdict':result['verdict'],'cases':len(result['cases'])}))
