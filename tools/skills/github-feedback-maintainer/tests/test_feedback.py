import copy
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
import uuid
import sys

sys.path.insert(0, str(Path(__file__).parents[1] / 'scripts'))

import feedback as f


from fixture_transport import FixtureGitHub as FakeGitHub


class FeedbackTests(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.TemporaryDirectory()
        self.addCleanup(self.root.cleanup)
        self.api = FakeGitHub()
        self.config = {'repository': f.REPO, 'expected_actor': 'fixture-bot',
                       'approvers': ['trusted-fixture-user'], 'maintainer_actors': ['fixture-bot'],
                       'maintainer_approvers': ['trusted-fixture-user']}
        self.draft = {'request_id': str(uuid.uuid4()), 'source_alias': 'TEST reporter',
                      'project': 'TEST public fixture', 'category': '手册问题',
                      'target': 'handbook/index.html 10.06', 'title': 'TEST download failure',
                      'description': 'TEST click download button, no download starts.',
                      'expected': 'TEST a download begins.', 'evidence': ''}
        self.preview = f.wrap_preview(f.render(self.draft))

    def approval(self, preview=None):
        return {'approved': True, 'approved_by': 'trusted-fixture-user', 'approved_at': f.now(),
                'preview_sha256': (preview or self.preview)['preview_sha256']}

    def submit(self, preview=None, **kwargs):
        preview = preview or self.preview
        return f.transaction(self.api, self.config, preview, self.approval(preview), self.root.name, **kwargs)

    def error(self, code, fn):
        with self.assertRaises(f.Stop) as ctx:
            fn()
        self.assertEqual(code, ctx.exception.code)

    def update_preview(self, state='closed'):
        return f.wrap_preview(f.prepare_update(self.api, {
            'request_id': str(uuid.uuid4()), 'number': 1, 'state': state, 'decision': 'TEST scenario finished',
            'link': 'https://github.com/' + f.REPO + '/issues/1',
            'verification': 'TEST create/query/dedupe verified', 'reason': 'completed'}))

    def test_complete_create_query_close(self):
        result = self.submit()
        self.assertEqual('new', result['state'])
        self.assertEqual(1, result['number'])
        query = f.status_receipt(f.issue(self.api, 1))
        self.assertEqual(result['url'], query['url'])
        result = self.submit(self.update_preview())
        self.assertEqual('closed', result['state'])
        self.assertEqual(3, len(self.api.writes))

    def test_query_does_not_invent_status_for_missing_or_conflicting_labels(self):
        self.submit()
        self.api.rows[0]['labels'] = []
        self.assertEqual('unclassified', f.status_receipt(self.api.rows[0])['state'])
        self.api.rows[0]['labels'] = [{'name': x} for x in f.STATUS_LABELS]
        self.assertEqual('conflicting_labels', f.status_receipt(self.api.rows[0])['state'])

    def test_repeat_and_distinct_request_same_content(self):
        first = self.submit()
        self.assertEqual(first['number'], self.submit()['number'])
        d = dict(self.draft, request_id=str(uuid.uuid4()), source_alias='TEST second source')
        result = self.submit(f.wrap_preview(f.render(d)))
        self.assertEqual('DUPLICATE', result['result'])
        self.assertEqual(1, len(self.api.writes))

    def test_changed_request_rejected(self):
        self.submit()
        changed = f.wrap_preview(f.render(dict(self.draft, expected='Different expectation')))
        self.error('REQUEST_CONFLICT', lambda: self.submit(changed))
        self.assertEqual(1, len(self.api.writes))

    def test_private_material_rejected(self):
        for raw in ['password=secret', 'client@example.com', '13812345678', '/Users/person/private',
                    'https://a.example.com/x?token=hi', '@owner', '<script>alert(1)</script>']:
            self.error('PRIVACY_BLOCKED', lambda: f.render(dict(self.draft, description=raw)))
        self.assertEqual([], self.api.writes)

    def test_missing_minimum_fields(self):
        self.error('INVALID_INPUT', lambda: f.render(dict(self.draft, expected='')))
        self.assertIn('未提供', self.preview['payload']['body'])

    def test_wrong_identity_no_effect(self):
        self.api.actor = 'wrong-bot'
        self.error('IDENTITY_MISMATCH', self.submit)
        self.assertEqual([], self.api.writes)

    def test_approval_tampering_no_effect(self):
        p = copy.deepcopy(self.preview)
        p['payload']['title'] += ' altered'
        self.error('APPROVAL_MISMATCH', lambda: self.submit(p))
        self.assertEqual([], self.api.writes)

    def test_approved_preview_still_checks_privacy_at_write_boundary(self):
        p = copy.deepcopy(self.preview)
        p['payload']['body'] += '\npassword=secret'
        p['preview_sha256'] = f.digest(p['payload'])
        self.error('PRIVACY_BLOCKED', lambda: self.submit(p))
        self.assertEqual([], self.api.writes)

    def test_create_effect_lost_response_recovers_once(self):
        self.api.fail_after = 'POST'
        self.error('TRANSPORT_UNKNOWN', self.submit)
        result = self.submit(reconcile_only=True)
        self.assertEqual(1, result['number'])
        self.assertEqual(1, len(self.api.writes))

    def test_crash_before_effect_no_blind_replay(self):
        self.error('INJECTED_CRASH', lambda: self.submit(fault='CREATE_INTENT'))
        self.error('RECONCILE_REQUIRED', self.submit)
        self.assertEqual([], self.api.writes)

    def test_crash_after_receipt_recovers_once(self):
        self.error('INJECTED_CRASH', lambda: self.submit(fault='CREATE_RECEIPT'))
        self.assertEqual(1, self.submit()['number'])
        self.assertEqual(1, len(self.api.writes))

    def test_committed_crash_releases_lock_and_never_replays(self):
        self.error('INJECTED_CRASH', lambda: self.submit(fault='COMMITTED'))
        self.assertEqual(1, self.submit()['number'])
        self.assertEqual(1, len(self.api.writes))

    def test_committed_without_remote_evidence_halts(self):
        self.submit()
        self.api.rows.clear()
        self.error('RECONCILE_REQUIRED', self.submit)
        self.assertEqual(1, len(self.api.writes))

    def test_process_lock_excludes_second_writer(self):
        with f.Journal(self.root.name):
            self.error('BUSY', self.submit)
        self.assertEqual([], self.api.writes)
        self.assertEqual(1, self.submit()['number'])

    def test_two_targets_are_separate(self):
        self.submit()
        d = dict(self.draft, request_id=str(uuid.uuid4()), description='TEST different failure')
        result = self.submit(f.wrap_preview(f.render(d)))
        self.assertEqual(2, result['number'])

    def test_state_preview_stale_no_update(self):
        self.submit()
        p = self.update_preview()
        self.api.rows[0]['updated_at'] = '2026-10-06T13:00:00Z'
        self.error('STALE_PREVIEW', lambda: self.submit(p))
        self.assertEqual(1, len(self.api.writes))

    def test_maintainer_required(self):
        self.submit()
        self.config['maintainer_actors'] = []
        self.error('MAINTAINER_REQUIRED', lambda: self.submit(self.update_preview()))
        self.assertEqual(1, len(self.api.writes))

    def test_close_requires_evidence(self):
        self.submit()
        self.error('INVALID_INPUT', lambda: f.prepare_update(self.api, {
            'request_id': str(uuid.uuid4()), 'number': 1, 'state': 'closed', 'decision': 'TEST done'}))

    def test_ordinary_reporter_cannot_approve_state_change(self):
        self.submit()
        self.config['maintainer_approvers'] = []
        self.error('MAINTAINER_REQUIRED', lambda: self.submit(self.update_preview()))
        self.assertEqual(1, len(self.api.writes))

    def test_comment_repeat_and_unknown_recovery_without_state_rights(self):
        self.submit()
        self.config['maintainer_actors'] = []
        self.config['maintainer_approvers'] = []
        p = f.wrap_preview(f.prepare_comment(self.api, {'request_id': str(uuid.uuid4()),
                              'number': 1, 'comment': 'TEST synthetic extra reproduction evidence'}))
        self.api.fail_after = 'POST'
        self.error('TRANSPORT_UNKNOWN', lambda: self.submit(p))
        r = self.submit(p, reconcile_only=True)
        self.assertEqual('new', r['state'])
        self.assertEqual(1, r['comment_id'])
        self.assertEqual(2, len(self.api.writes))

    def test_update_comment_unknown_halts_without_duplicate(self):
        self.submit()
        p = self.update_preview()
        self.api.fail_after = 'POST'
        self.error('TRANSPORT_UNKNOWN', lambda: self.submit(p))
        self.error('RECONCILE_REQUIRED', lambda: self.submit(p))
        self.assertEqual(2, len(self.api.writes))
        self.assertEqual('open', self.api.rows[0]['state'])

    def test_update_patch_unknown_reconciles(self):
        self.submit()
        p = self.update_preview()
        self.api.fail_after = 'PATCH'
        self.error('TRANSPORT_UNKNOWN', lambda: self.submit(p))
        self.assertEqual('closed', self.submit(p, reconcile_only=True)['state'])
        self.assertEqual(3, len(self.api.writes))

    def test_comment_receipt_resume_does_not_repeat_comment(self):
        self.submit()
        p = self.update_preview()
        self.error('INJECTED_CRASH', lambda: self.submit(p, fault='COMMENT_RECEIPT'))
        self.assertEqual('closed', self.submit(p)['state'])
        self.assertEqual(3, len(self.api.writes))
        self.assertEqual(1, len(self.api.comments[1]))

    def test_patch_intent_crash_stops_without_automatic_state_replay(self):
        self.submit()
        p = self.update_preview()
        self.error('INJECTED_CRASH', lambda: self.submit(p, fault='PATCH_INTENT'))
        self.error('RECONCILE_REQUIRED', lambda: self.submit(p))
        self.assertEqual('open', self.api.rows[0]['state'])
        self.assertEqual(2, len(self.api.writes))

    def test_other_labels_preserved(self):
        self.submit()
        self.api.rows[0]['labels'].append({'name': 'priority-high'})
        self.submit(self.update_preview('in_progress'))
        self.assertIn('priority-high', [x['name'] for x in self.api.rows[0]['labels']])

    def test_failed_early_target_does_not_block_another(self):
        self.error('INJECTED_CRASH', lambda: self.submit(fault='CREATE_INTENT'))
        d = dict(self.draft, request_id=str(uuid.uuid4()), description='TEST another target')
        self.assertEqual(1, self.submit(f.wrap_preview(f.render(d)))['number'])
        with f.Journal(self.root.name) as journal:
            rows = journal.pending()
        self.assertEqual([self.draft['request_id']], [r['request_id'] for r in rows])

    def test_production_adapter_rejects_revoked_fence_and_evidence(self):
        p = self.preview['payload'];rid = p['request_id']
        with f.Journal(self.root.name) as journal:
            row = {'request_id': rid, 'revision': f.digest(p), 'phase': 'PREPARED', 'attempt_id': 'owner1', 'fence': 1, 'actor': 'fixture-bot'}
            journal.put(rid, row)
            adapter = f.RemoteEffectAdapter(self.api, p, dict(row), journal, 'create', lambda *a, **k: None)
            journal.put(rid, dict(row, fence=2, attempt_id='owner2'))
            self.error('STALE_FENCE', lambda: adapter.effect(rid + ':create'))
            journal.put(rid, dict(row, revision='lost-evidence'))
            self.error('RECONCILE_REQUIRED', lambda: adapter.effect(rid + ':create'))
        self.assertEqual([], self.api.writes)


if __name__ == '__main__':
    unittest.main(verbosity=2)

class PythonTransportTests(unittest.TestCase):
    def test_missing_identity_and_foreign_target_block_before_network(self):
        from unittest.mock import patch
        with patch.dict(f.os.environ, {}, clear=True), patch.object(f.urllib.request, 'build_opener') as network:
            for endpoint, code in [(f.API, 'CREDENTIAL_MISSING'), ('https://outside.invalid', 'TARGET_BLOCKED')]:
                with self.assertRaises(f.Stop) as caught:
                    f.GitHub('python').call('GET', endpoint)
                self.assertEqual(code, caught.exception.code)
            network.assert_not_called()

    def test_fixed_host_and_json_body_without_cli_or_redirect(self):
        from unittest.mock import patch, MagicMock
        response = MagicMock()
        response.__enter__.return_value.read.return_value = b'{"ok":true}'
        opener = MagicMock()
        opener.open.return_value = response
        with patch.dict(f.os.environ, {'GH_TOKEN': 'synthetic-test-secret'}, clear=True), patch.object(f.urllib.request, 'build_opener', return_value=opener), patch.object(f.subprocess, 'run') as cli:
            self.assertEqual({'ok': True}, f.GitHub('python').call('POST', f.API + '/issues', {'title': 'TEST'}))
            request = opener.open.call_args[0][0]
            self.assertEqual('https://api.github.com' + f.API + '/issues', request.full_url)
            self.assertEqual({'title': 'TEST'}, json.loads(request.data))
            self.assertEqual('Bearer synthetic-test-secret', request.get_header('Authorization'))
            cli.assert_not_called()
            with self.assertRaises(f.Stop) as caught:
                f.NoRedirect().redirect_request(request, None, 302, '', {}, 'https://outside.invalid')
            self.assertEqual('TARGET_BLOCKED', caught.exception.code)

    def test_http_error_never_exposes_server_body_or_secret(self):
        from unittest.mock import patch, MagicMock
        opener = MagicMock()
        opener.open.side_effect = f.urllib.error.HTTPError('sensitive', 403, 'sensitive-secret', {}, None)
        with patch.dict(f.os.environ, {'GITHUB_TOKEN': 'synthetic-test-secret'}, clear=True), patch.object(f.urllib.request, 'build_opener', return_value=opener):
            with self.assertRaises(f.Stop) as caught:
                f.GitHub('python').call('GET', f.API)
            self.assertEqual('GITHUB_ERROR', caught.exception.code)
            self.assertNotIn('sensitive', str(caught.exception))

class PublicIdentifierTests(unittest.TestCase):
    def test_host_uuid_digits_do_not_become_phone_false_positive(self):
        draft = {'request_id': '00000000-0000-4000-8000-138123456789', 'source_alias': 'TEST', 'project': 'TEST', 'category': '手册问题', 'target': 'README', 'title': 'TEST', 'description': 'TEST', 'expected': 'TEST'}
        self.assertEqual(draft['request_id'], f.render(draft)['request_id'])

if __name__ == '__main__':
    unittest.main()
