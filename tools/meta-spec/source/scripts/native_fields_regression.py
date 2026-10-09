"""Exercise actual native-field rejection and independent on-disk auditing."""
import argparse
import copy
import hashlib
import json
import shutil
from pathlib import Path

from generator_regression import PACKAGE, prepare, resign, run_command, save
from structure_regression import content_fixture, prepare_review_fixture


def field(request, index=3):
    return request['documents']['03-data-model.md']['业务表']['tables'][0][index]


def run(root, failed_request):
    root.mkdir(parents=True, exist_ok=False)
    request = content_fixture()
    rows = []
    good = root / 'golden'
    prepare(good, request)
    for stage in ['acquire_sources', 'render_documents']:
        if stage == 'render_documents':
            save(root / 'execution/golden-preview-fixture.json', prepare_review_fixture(good))
        out = run_command(root, 'golden-' + stage,
                          [PACKAGE / 'scripts/run_meta_stages.py', '--stage', stage, '--run-dir', good])
        assert out['exit_code'] == 0, out
    out = run_command(root, 'golden-audit', [PACKAGE / 'scripts/audit.py', good, '--all', '--json'])
    assert out['exit_code'] == 0, out
    assert any(x['id'] == 'render.native_fields' and x['status'] == 'PASS'
               for x in json.loads(out['stdout'])['rows'])
    rows.append({'case': 'known_native_options_through_real_pipeline', 'verdict': 'PASS'})

    options = json.loads(field(request)[7])
    bad_options = {}
    bad_options['missing_mode'] = {'options': {'items': options['options']['items']}}
    bad_options['missing_items'] = {'options': {'mode': 'custom'}}
    bad_options['empty_items'] = {'options': {'mode': 'custom', 'items': []}}
    for name, key in [('string_key', '1'), ('boolean_key', True)]:
        changed = copy.deepcopy(options)
        changed['options']['items'][0]['key'] = key
        bad_options[name] = changed
    changed = copy.deepcopy(options); changed['options']['items'][1]['key'] = 1
    bad_options['duplicate_key'] = changed
    changed = copy.deepcopy(options); changed['options']['items'][0]['value'] = ''
    bad_options['empty_value'] = changed
    mutations = {}
    for name, value in bad_options.items():
        bad = copy.deepcopy(request); field(bad)[7] = json.dumps(value, ensure_ascii=False)
        mutations[name] = bad
    for name, index, value in [('text_missing_type', 0, '{}'),
                               ('textarea_boolean_as_string', 1, '{"html":"false"}'),
                               ('datetime_missing_precision', 2, '{}')]:
        bad = copy.deepcopy(request); field(bad, index)[7] = value; mutations[name] = bad
    if failed_request:
        actual = json.loads(Path(failed_request).read_text())
        old_options = actual['documents']['03-data-model.md']['样品']['tables'][0][2][7]
        bad = copy.deepcopy(request); field(bad)[7] = old_options
        mutations['actual_failed_select_options'] = bad
    for name, bad in mutations.items():
        dest = root / name; prepare(dest, bad)
        out = run_command(root, name, [PACKAGE / 'scripts/run_meta_stages.py',
                                      '--stage', 'render_documents', '--run-dir', dest])
        assert out['exit_code'] == 2, out
        assert not (dest / 'design').exists()
        rows.append({'case': name, 'verdict': 'PASS', 'rejected': out['stderr']})

    # Make malformed native content agree with both receipts and frozen input.
    # Only the independently implemented native contract can reject this case.
    mutant = root / 'mutant-native-resigned'
    shutil.copytree(good, mutant)
    before = field(request)[7]
    corrupted = copy.deepcopy(request)
    field(corrupted)[7] = json.dumps(bad_options['string_key'], ensure_ascii=False)
    save(mutant / 'working/render_request.json', corrupted)
    doc = mutant / 'design/03-data-model.md'
    body = doc.read_text(); assert before in body
    doc.write_text(body.replace(before, field(corrupted)[7], 1))
    resign(mutant)
    receipt = json.loads((mutant / 'render_input_receipt.json').read_text())
    receipt['request_sha256'] = hashlib.sha256((mutant / 'working/render_request.json').read_bytes()).hexdigest()[:16]
    save(mutant / 'render_input_receipt.json', receipt)
    out = run_command(root, 'mutant-native-resigned', [PACKAGE / 'scripts/audit.py', mutant, '--all', '--json'])
    report = json.loads(out['stdout'])
    failures = [x['id'] for x in report['rows'] if x['status'] == 'FAIL']
    assert out['exit_code'] == 1 and failures == ['render.native_fields'], out
    rows.append({'case': 'resigned_bad_native_options', 'verdict': 'PASS', 'rejected_by': failures})

    # The literal table codec must not make a valid JSON option invalid on disk.
    encoded = copy.deepcopy(request)
    unusual = copy.deepcopy(options)
    unusual['options']['items'][0]['value'] = 'A | B & <br> `text` \\ C'
    field(encoded)[7] = json.dumps(unusual, ensure_ascii=False)
    dest = root / 'literal_options'; prepare(dest, encoded)
    for stage in ['acquire_sources', 'render_documents']:
        if stage == 'render_documents':
            save(root / 'execution/literal-preview-fixture.json', prepare_review_fixture(dest))
        out = run_command(root, 'literal-' + stage, [PACKAGE / 'scripts/run_meta_stages.py',
                           '--stage', stage, '--run-dir', dest])
        assert out['exit_code'] == 0, out
    out = run_command(root, 'literal-audit', [PACKAGE / 'scripts/audit.py', dest, '--all', '--json'])
    assert out['exit_code'] == 0, out
    rows.append({'case': 'native_options_literal_codec_roundtrip', 'verdict': 'PASS'})
    result = {'verdict': 'PASS', 'engineering_fixture_only': True, 'cases': rows}
    save(root / 'result.json', result)
    return result


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--run-dir', required=True)
    ap.add_argument('--failed-request')
    args = ap.parse_args()
    result = run(Path(args.run_dir), args.failed_request)
    print(json.dumps({'verdict': result['verdict'], 'cases': len(result['cases'])}))
