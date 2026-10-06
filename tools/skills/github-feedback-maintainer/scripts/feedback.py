#!/usr/bin/env python3
"""Bounded public GitHub Issue adapter. Python 3.10+, approved GitHub transport, POSIX host."""
import argparse
import datetime as dt
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import uuid
import urllib.request
import urllib.error

from entrypoints import apply_feedback_effect

REPO = 'quekou-fde-development/fde-development'
API = '/repos/' + REPO
STATUS_LABELS = {'待处理', '处理中'}
CATEGORIES = {'手册问题': 'documentation', '工具使用问题': 'bug', '流程建议': 'enhancement', '链接或下载问题': 'bug'}
VERSION = '10.06.1'


class Stop(Exception):
    def __init__(self, code, message):
        self.code, self.message = code, message
        super().__init__(message)


def now():
    return dt.datetime.now(dt.timezone.utc).isoformat()


def digest(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True,
                                     separators=(',', ':')).encode()).hexdigest()


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def save(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    fd, temp = tempfile.mkstemp(prefix='.feedback-', dir=path.parent)
    try:
        os.fchmod(fd, 0o600)
        with os.fdopen(fd, 'w', encoding='utf-8') as stream:
            json.dump(value, stream, ensure_ascii=False, indent=2)
            stream.write('\n')
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temp, path)
        directory = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
    finally:
        # No raw input or credentials are persisted in temporary diagnostics.
        if os.path.exists(temp):
            os.unlink(temp)


def text_field(data, key, limit=6000, optional=False):
    value = data.get(key, '')
    if not isinstance(value, str) or (not optional and not value.strip()) or len(value) > limit:
        raise Stop('INVALID_INPUT', '字段缺失或格式不合要求：' + key)
    return value.strip()


def public_scan(value):
    """Conservative preflight; semantic privacy review remains the host's job."""
    patterns = {
        'credential': r'(?i)(?:gh[pousr]_[a-z0-9_]{15,}|github_pat_[a-z0-9_]+|sk-[a-z0-9_-]{15,}|-----BEGIN [A-Z ]*PRIVATE KEY|(?:authorization|password|passwd|api[_-]?key|token)\s*[:=]\s*\S+)',
        'email': r'[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}',
        'phone': r'(?<!\d)1[3-9]\d{9}(?!\d)',
        'private_path': r'(?:/Users/|/home/|[A-Za-z]:\\Users\\|agentfs://)',
        'private_url': r'(?i)https?://(?:localhost|127\.|10\.|192\.168\.|172\.(?:1[6-9]|2\d|3[01])\.|[^/\s]+\.(?:local|internal))',
        'url_secret': r'https?://[^\s<>]+[?#][^\s<>]+',
        'mention': r'(?<!\w)@[A-Za-z0-9_/-]+',
        'html': r'<(?:!--|/?[A-Za-z])',
    }
    for name, pattern in patterns.items():
        if re.search(pattern, value):
            raise Stop('PRIVACY_BLOCKED', '公开预检发现需移除的内容类型：' + name)


def request_id(value):
    try:
        result = str(uuid.UUID(value))
    except (ValueError, TypeError, AttributeError):
        raise Stop('INVALID_INPUT', 'request_id 必须是宿主生成并保留的 UUID。')
    return result


def render(draft):
    allowed = {'request_id', 'source_alias', 'project', 'category', 'target', 'description',
               'expected', 'evidence', 'title'}
    if set(draft) - allowed:
        raise Stop('INVALID_INPUT', '输入含未知字段；只传公开摘要。')
    data = {key: text_field(draft, key, 400 if key in {'source_alias', 'project', 'target', 'title'} else 6000)
            for key in ('source_alias', 'project', 'target', 'description', 'expected', 'title')}
    data['request_id'] = request_id(draft.get('request_id'))
    data['category'] = draft.get('category')
    if data['category'] not in CATEGORIES:
        raise Stop('INVALID_INPUT', 'category 必须为手册问题/工具使用问题/流程建议/链接或下载问题。')
    data['evidence'] = text_field(draft, 'evidence', optional=True) or '未提供；可后续补充公开证据。'
    if '\n' in data['title'] or len(data['title']) > 160:
        raise Stop('INVALID_INPUT', '标题须为单行且最多 160 字。')
    public_scan(json.dumps({k: v for k, v in data.items() if k != 'request_id'}, ensure_ascii=False))
    # Exclude source/request/evidence: repeated reports with identical facts share one record.
    fingerprint = digest({k: data[k] for k in ('project', 'category', 'target', 'description', 'expected')})
    body = '\n\n'.join('### ' + label + '\n' + data[key] for key, label in (
        ('source_alias', '来源人（公开称呼）'), ('project', '项目（公开代称）'),
        ('category', '反馈类型'), ('target', '对象路径与版本'),
        ('description', '问题现象与复现步骤'), ('expected', '期望结果'), ('evidence', '证据')))
    body += '\n\n<!-- feedback-request:' + data['request_id'] + ' -->'
    body += '\n<!-- feedback-fingerprint:' + fingerprint + ' -->'
    return {'schema_version': 1, 'operation': 'create', 'repository': REPO,
            'request_id': data['request_id'], 'fingerprint': fingerprint,
            'title': data['title'], 'body': body, 'labels': [CATEGORIES[data['category']], '待处理']}


def wrap_preview(payload):
    return {'payload': payload, 'preview_sha256': digest(payload), 'created_at': now()}


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, request, fp, code, message, headers, new_url):
        raise Stop('TARGET_BLOCKED', 'GitHub API 不接受重定向。')


class GitHub:
    def __init__(self, transport='gh'):
        if transport not in {'gh', 'python'}:
            raise Stop('CONFIG_BLOCKED', 'transport 仅支持 gh 或 python。')
        self.transport = transport

    def call(self, method, endpoint, payload=None):
        if not (endpoint == '/user' or endpoint == API or endpoint.startswith(API + '/')):
            raise Stop('TARGET_BLOCKED', 'API 路径超出固定仓库。')
        if self.transport == 'python':
            return self._python_call(method, endpoint, payload)
        command = ['gh', 'api', '--hostname', 'github.com', '-X', method, endpoint,
                   '-H', 'Accept: application/vnd.github+json', '-H', 'X-GitHub-Api-Version: 2022-11-28']
        if payload is not None:
            command += ['--input', '-']
        try:
            r = subprocess.run(command, input=json.dumps(payload) if payload is not None else None,
                               capture_output=True, text=True, timeout=35)
        except (subprocess.TimeoutExpired, OSError):
            raise Stop('TRANSPORT_UNKNOWN', 'GitHub 请求未取得确定回执；写操作须先回查。')
        if r.returncode:
            # Never echo CLI stderr, which may contain host paths or supplied content.
            status = re.search(r'HTTP (\d{3})', r.stderr)
            raise Stop('GITHUB_ERROR', 'GitHub 请求失败' + ('，HTTP ' + status[1] if status else '') + '；请检查连接、权限或限流。')
        try:
            return json.loads(r.stdout) if r.stdout.strip() else None
        except ValueError:
            raise Stop('TRANSPORT_UNKNOWN', 'GitHub 响应格式无法核验。')

    def _python_call(self, method, endpoint, payload):
        token = os.environ.get('GH_TOKEN') or os.environ.get('GITHUB_TOKEN')
        if not token:
            raise Stop('CREDENTIAL_MISSING', '宿主未配置 GH_TOKEN 或 GITHUB_TOKEN；请由宿主管理人安全配置。')
        data = json.dumps(payload).encode('utf-8') if payload is not None else None
        request = urllib.request.Request('https://api.github.com' + endpoint, data=data, method=method,
            headers={'Authorization': 'Bearer ' + token, 'Accept': 'application/vnd.github+json',
                     'Content-Type': 'application/json', 'User-Agent': 'fde-feedback-adapter',
                     'X-GitHub-Api-Version': '2022-11-28'})
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect())
        try:
            with opener.open(request, timeout=35) as response:
                raw = response.read(16 * 1024 * 1024 + 1)
                if len(raw) > 16 * 1024 * 1024:
                    raise Stop('READBACK_INVALID', 'GitHub API 响应超出安全读取上限。')
            return json.loads(raw) if raw.strip() else None
        except urllib.error.HTTPError as exc:
            raise Stop('GITHUB_ERROR', 'GitHub 请求失败，HTTP ' + str(exc.code) + '；请检查连接、权限或限流。')
        except (urllib.error.URLError, TimeoutError, OSError):
            raise Stop('TRANSPORT_UNKNOWN', 'GitHub 请求未取得确定回执；写操作须先回查。')
        except ValueError:
            raise Stop('TRANSPORT_UNKNOWN', 'GitHub 响应格式无法核验。')

    def pages(self, endpoint):
        result = []
        sep = '&' if '?' in endpoint else '?'
        for page in range(1, 101):
            rows = self.call('GET', endpoint + sep + 'per_page=100&page=' + str(page))
            if not isinstance(rows, list):
                raise Stop('READBACK_INVALID', '分页回读格式错误。')
            result.extend(rows)
            if len(rows) < 100:
                return result
        raise Stop('SCAN_LIMIT', '回查超过 100 页；停止写入并交维护人定位。')


def verify_host(api, config, maintain=False):
    if config.get('repository') != REPO or not config.get('expected_actor'):
        raise Stop('CONFIG_BLOCKED', '配置必须锁定仓库及预期 GitHub 账号。')
    identity = api.call('GET', '/user')
    if identity.get('login') != config['expected_actor']:
        raise Stop('IDENTITY_MISMATCH', 'GitHub 当前账号与宿主配置不一致。')
    repo = api.call('GET', API)
    if repo.get('full_name') != REPO or repo.get('private') is not False or not repo.get('has_issues'):
        raise Stop('TARGET_BLOCKED', '目标仓库或公开 Issue 能力不符合合同。')
    if maintain and identity['login'] not in config.get('maintainer_actors', []):
        raise Stop('MAINTAINER_REQUIRED', '宿主尚未授权此账号维护处理状态。')
    return identity['login']


def issue(api, number):
    if type(number) is not int or number < 1:
        raise Stop('INVALID_INPUT', 'Issue 编号必须为正整数。')
    row = api.call('GET', API + '/issues/' + str(number))
    if 'pull_request' in row:
        raise Stop('TARGET_BLOCKED', '此编号属于 Pull Request。')
    if row.get('html_url') != 'https://github.com/' + REPO + '/issues/' + str(number):
        raise Stop('READBACK_INVALID', 'Issue 链接核验失败。')
    return row


def status_receipt(row, result='SUCCESS'):
    labels = [x['name'] for x in row.get('labels', [])]
    state = 'closed' if row['state'] == 'closed' else (
        'conflicting_labels' if STATUS_LABELS.issubset(set(labels)) else
        'in_progress' if '处理中' in labels else 'new' if '待处理' in labels else 'unclassified')
    return {'result': result, 'number': row['number'], 'url': row['html_url'],
            'state': state, 'state_reason': row.get('state_reason'), 'labels': labels,
            'assignees': [x['login'] for x in row.get('assignees', [])],
            'updated_at': row['updated_at'], 'checked_at': now()}


def prepare_update(api, change):
    allowed = {'request_id', 'number', 'state', 'decision', 'link', 'verification', 'reason', 'assignees'}
    if set(change) - allowed:
        raise Stop('INVALID_INPUT', '状态变更含未知字段。')
    rid = request_id(change.get('request_id'))
    row = issue(api, change.get('number'))
    state = change.get('state')
    if state not in {'new', 'in_progress', 'closed'}:
        raise Stop('INVALID_INPUT', '处理状态只接受 new/in_progress/closed。')
    decision = text_field(change, 'decision')
    link = text_field(change, 'link', optional=state != 'closed')
    verification = text_field(change, 'verification', optional=state != 'closed')
    reason = change.get('reason', 'completed')
    if reason not in {'completed', 'not_planned'}:
        raise Stop('INVALID_INPUT', '关闭理由只接受 completed/not_planned。')
    if link and not re.fullmatch(r'https://[^\s<>]+', link):
        raise Stop('INVALID_INPUT', '依据链接须为可公开 HTTPS 地址。')
    public_scan('\n'.join((decision, link, verification)))
    assignees = change.get('assignees', [x['login'] for x in row.get('assignees', [])])
    if not isinstance(assignees, list) or len(assignees) > 10 or any(not isinstance(x, str) or not re.fullmatch(r'[A-Za-z0-9-]{1,39}', x) for x in assignees):
        raise Stop('INVALID_INPUT', 'assignees 格式错误。')
    labels = [x['name'] for x in row['labels'] if x['name'] not in STATUS_LABELS]
    if state != 'closed':
        labels.append('处理中' if state == 'in_progress' else '待处理')
    patch = {'state': 'closed' if state == 'closed' else 'open', 'labels': labels, 'assignees': assignees}
    if state == 'closed':
        patch['state_reason'] = reason
    comment = '处理决定：' + decision + '\n\n依据：' + (link or '本次处理安排') + '\n\n验证：' + (verification or '尚未进入验证')
    comment += '\n\n<!-- feedback-update:' + rid + ' -->'
    return {'schema_version': 1, 'operation': 'update', 'repository': REPO, 'request_id': rid,
            'number': row['number'], 'expected_updated_at': row['updated_at'],
            'before': {'state': row['state'], 'labels': [x['name'] for x in row['labels']],
                       'assignees': [x['login'] for x in row.get('assignees', [])]},
            'patch': patch, 'comment': comment}


def prepare_comment(api, change):
    if set(change) - {'request_id', 'number', 'comment'}:
        raise Stop('INVALID_INPUT', '补充说明含未知字段。')
    rid = request_id(change.get('request_id'))
    row = issue(api, change.get('number'))
    comment = text_field(change, 'comment')
    public_scan(comment)
    return {'schema_version': 1, 'operation': 'comment', 'repository': REPO,
            'request_id': rid, 'number': row['number'],
            'comment': comment + '\n\n<!-- feedback-comment:' + rid + ' -->'}


def check_approval(preview, approval, config):
    p = preview['payload']
    if preview.get('preview_sha256') != digest(p) or approval.get('preview_sha256') != digest(p):
        raise Stop('APPROVAL_MISMATCH', '公开预览已变化，请重新展示并取得确认。')
    if p.get('repository') != REPO or p.get('operation') not in {'create', 'update', 'comment'}:
        raise Stop('TARGET_BLOCKED', '预览目标或操作不符合合同。')
    rid = request_id(p.get('request_id'))
    if p['operation'] == 'create':
        title, body = text_field(p, 'title', 160), text_field(p, 'body', 30000)
        fingerprint = p.get('fingerprint', '')
        if not re.fullmatch(r'[0-9a-f]{64}', fingerprint) or '\n' in title:
            raise Stop('INVALID_PREVIEW', '新建预览的标题或指纹不符合合同。')
        markers = ['<!-- feedback-request:' + rid + ' -->', '<!-- feedback-fingerprint:' + fingerprint + ' -->']
        if any(body.count(marker) != 1 for marker in markers) or p.get('labels') not in [[label, '待处理'] for label in set(CATEGORIES.values())]:
            raise Stop('INVALID_PREVIEW', '新建预览的标记或标签不符合合同。')
        for marker in markers:
            body = body.replace(marker, '')
        public_scan(title + '\n' + body)
    else:
        comment = text_field(p, 'comment', 20000)
        marker = '<!-- feedback-' + ('update' if p['operation'] == 'update' else 'comment') + ':' + rid + ' -->'
        if comment.count(marker) != 1:
            raise Stop('INVALID_PREVIEW', '评论预览缺少唯一请求标记。')
        public_scan(comment.replace(marker, ''))
    if approval.get('approved') is not True or approval.get('approved_by') not in config.get('approvers', []):
        raise Stop('APPROVAL_REQUIRED', '缺少宿主从真实用户确认生成的批准记录。')
    if p['operation'] == 'update' and approval['approved_by'] not in config.get('maintainer_approvers', []):
        raise Stop('MAINTAINER_REQUIRED', '确认者未获宿主维护授权，不能修改处理状态。')
    try:
        stamped = dt.datetime.fromisoformat(approval['approved_at'])
        age = (dt.datetime.now(dt.timezone.utc) - stamped).total_seconds()
        if age < -60 or age > 86400:
            raise ValueError()
    except (KeyError, TypeError, ValueError):
        raise Stop('APPROVAL_EXPIRED', '公开确认超过 24 小时或时间格式错误。')
    # Host files are trusted control inputs, never generated from the report text.
    return p


class Journal:
    def __init__(self, root):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True, mode=0o700)

    def __enter__(self):
        self.lock = open(self.root / 'writer.lock', 'a+')
        os.chmod(self.root / 'writer.lock', 0o600)
        try:
            fcntl.flock(self.lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            self.lock.close()
            raise Stop('BUSY', '同一宿主有反馈正在提交；稍后使用原 request_id 回查。')
        return self

    def __exit__(self, *args):
        fcntl.flock(self.lock, fcntl.LOCK_UN)
        self.lock.close()

    def load(self, rid):
        path = self.root / (request_id(rid) + '.json')
        return read(path) if path.exists() else None

    def put(self, rid, value):
        save(self.root / (request_id(rid) + '.json'), value)

    def pending(self):
        rows = []
        for path in self.root.glob('*.json'):
            row = read(path)
            if row.get('phase') != 'COMMITTED':
                rows.append({'request_id': request_id(row['request_id']), 'phase': row['phase'],
                             'checked_at': row.get('checked_at', ''),
                             'created_at': row.get('created_at', row.get('checked_at', '')),
                             'next_action': 'reconcile_with_original_preview'})
        return sorted(rows, key=lambda r: (r['created_at'], r['request_id']))


def locate(api, payload):
    rows = api.pages(API + '/issues?state=all&sort=created&direction=desc')
    by_request, by_content = [], []
    for row in rows:
        if 'pull_request' in row:
            continue
        body = row.get('body') or ''
        if '<!-- feedback-request:' + payload['request_id'] + ' -->' in body:
            by_request.append(row)
        elif '<!-- feedback-fingerprint:' + payload['fingerprint'] + ' -->' in body:
            by_content.append(row)
    matches = by_request or by_content
    if len(matches) > 1:
        raise Stop('DUPLICATES_FOUND', '已有多条匹配记录；交维护人合并后继续。')
    if by_request and by_request[0].get('body') != payload['body']:
        raise Stop('REQUEST_CONFLICT', '同一 request_id 对应另一版正文。')
    return matches[0] if matches else None


def matches_patch(row, patch):
    return (row['state'] == patch['state'] and
            set(x['name'] for x in row['labels']) == set(patch['labels']) and
            set(x['login'] for x in row.get('assignees', [])) == set(patch['assignees']) and
            (patch['state'] != 'closed' or row.get('state_reason') == patch['state_reason']))


class RemoteEffectAdapter:
    """Production IO adapter for the pure transaction kernel; caller holds Journal's lock."""
    def __init__(self, api, payload, entry, journal, kind, checkpoint):
        self.api, self.p, self.entry, self.journal = api, payload, entry, journal
        self.kind, self.checkpoint = kind, checkpoint
        self.initial_phase = entry['phase']
        self.expected_fence = entry['fence']
        self.expected_attempt = entry['attempt_id']
        self.result = None
        self.reads = 0

    def _guard(self, key):
        state = self.journal.load(self.p['request_id'])
        if key != self.p['request_id'] + ':' + self.kind or not state or state['fence'] != self.expected_fence or state['attempt_id'] != self.expected_attempt:
            raise Stop('STALE_FENCE', '本次尝试的写入权已失效。')
        if state.get('revision') != digest(self.p):
            raise Stop('RECONCILE_REQUIRED', '持久化证据版本不一致，停止写入并核查。')

    def intent(self, key):
        self._guard(key)
        self.checkpoint(self.kind.upper() + '_INTENT')

    def readback(self, key):
        self._guard(key)
        self.reads += 1
        if self.kind == 'create':
            found = locate(self.api, self.p)
            if found:
                row = issue(self.api, found['number'])
                if row.get('title') != self.p['title'] or row.get('body') != self.p['body']:
                    raise Stop('READBACK_MISMATCH', '原请求的公开内容不一致。')
                self.result = row
                return 'APPLIED'
        elif self.kind == 'comment':
            rows = self.api.pages(API + '/issues/' + str(self.p['number']) + '/comments')
            marker = '<!-- feedback-' + ('comment' if self.p['operation'] == 'comment' else 'update') + ':' + self.p['request_id'] + ' -->'
            found = [r for r in rows if marker in (r.get('body') or '')]
            if len(found) > 1:
                raise Stop('DUPLICATES_FOUND', '评论回读发现重复请求标记。')
            if found:
                if found[0].get('body') != self.p['comment'] or found[0].get('user', {}).get('login') != self.entry['actor']:
                    raise Stop('READBACK_MISMATCH', '评论正文或作者回读不一致。')
                self.result = found[0]
                return 'APPLIED'
        else:
            row = issue(self.api, self.p['number'])
            if matches_patch(row, self.p['patch']):
                self.result = row
                return 'APPLIED'
        if self.reads > 1 or self.initial_phase in {self.kind.upper() + '_INTENT', self.kind.upper() + '_RECEIPT', 'COMMITTED'}:
            return 'UNKNOWN'
        return 'ABSENT'

    def effect(self, key):
        self._guard(key)
        if self.kind == 'create':
            self.result = self.api.call('POST', API + '/issues', {k: self.p[k] for k in ('title', 'body', 'labels')})
        elif self.kind == 'comment':
            self.result = self.api.call('POST', API + '/issues/' + str(self.p['number']) + '/comments', {'body': self.p['comment']})
        else:
            self.result = self.api.call('PATCH', API + '/issues/' + str(self.p['number']), self.p['patch'])

    def receipt(self, key):
        self._guard(key)
        values = {'number': self.result['number']} if self.kind == 'create' else ({'comment_id': self.result['id']} if self.kind == 'comment' else {})
        self.checkpoint(self.kind.upper() + '_RECEIPT', **values)

    def commit(self, key):
        self._guard(key)
        effects = dict(self.entry.get('effects', {}))
        effects[self.kind] = {'state': 'COMMITTED', 'checked_at': now(),
                              'remote_id': self.result.get('id', self.result.get('number'))}
        self.entry['effects'] = effects
        self.journal.put(self.p['request_id'], self.entry)

    def unlock(self, key):
        # Journal's context owns the process lock across the multi-effect operation.
        self._guard(key)


def transaction(api, config, preview, approval, state_dir, reconcile_only=False, fault=None):
    """Single production mutation path. All uncertain writes stay halted until readback."""
    p = check_approval(preview, approval, config)
    actor = verify_host(api, config, maintain=p['operation'] == 'update')
    rid, revision = request_id(p['request_id']), digest(p)
    with Journal(state_dir) as journal:
        previous = journal.load(rid)
        if previous and previous['revision'] != revision:
            raise Stop('REQUEST_CONFLICT', '同一 request_id 不可更换已提交内容。')
        entry = previous or {'revision': revision, 'request_id': rid, 'phase': 'PREPARED', 'fence': 0}
        entry.setdefault('created_at', entry.get('checked_at', now()))
        entry.update(attempt_id=str(uuid.uuid4()), fence=entry['fence'] + 1, actor=actor, checked_at=now())
        journal.put(rid, entry)

        def checkpoint(phase, **values):
            entry.update(phase=phase, **values)
            journal.put(rid, entry)
            if fault == phase:
                raise Stop('INJECTED_CRASH', '隔离故障注入：' + phase)

        def apply_effect(kind):
            adapter = RemoteEffectAdapter(api, p, entry, journal, kind, checkpoint)
            state = apply_feedback_effect(rid + ':' + kind, revision, entry['attempt_id'], entry['fence'], adapter)
            if state['state'] != 'COMMITTED':
                raise Stop('RECONCILE_REQUIRED', '外部效果仍无法确认，保留原请求并先回查。')
            return adapter.result

        if p['operation'] == 'create':
            found = locate(api, p)
            if found:
                row = issue(api, found['number'])
                result = status_receipt(row, 'SUCCESS' if '<!-- feedback-request:' + rid + ' -->' in (row.get('body') or '') else 'DUPLICATE')
                checkpoint('COMMITTED', receipt=result)
                return result
            if previous and previous['phase'] != 'PREPARED':
                raise Stop('RECONCILE_REQUIRED', '先前请求结果仍不明；未找到记录，禁止自动重建，请维护人核查。')
            if reconcile_only:
                raise Stop('NOT_SUBMITTED', '回查未发现记录；本次未提交。')
            available = {x['name'] for x in api.pages(API + '/labels')}
            if not set(p['labels']).issubset(available):
                raise Stop('LABELS_MISSING', '缺少仓库约定标签；请仓库维护人配置后再提交。')
            created = apply_effect('create')
            row = issue(api, created['number'])
            if row.get('body') != p['body'] or row.get('title') != p['title'] or not set(p['labels']).issubset({x['name'] for x in row['labels']}):
                raise Stop('READBACK_MISMATCH', 'Issue 已建但回读内容不一致；请核查，勿重建。')
        elif p['operation'] == 'comment':
            row = issue(api, p['number'])
            endpoint = API + '/issues/' + str(p['number']) + '/comments'
            comments = api.pages(endpoint)
            marker = '<!-- feedback-comment:' + rid + ' -->'
            found = [x for x in comments if marker in (x.get('body') or '')]
            if len(found) > 1:
                raise Stop('DUPLICATES_FOUND', '补充说明有重复标记，请维护人核查。')
            if found:
                if found[0].get('body') != p['comment'] or found[0].get('user', {}).get('login') != actor:
                    raise Stop('REQUEST_CONFLICT', '补充说明与本次内容或执行账号不一致。')
                result = status_receipt(row)
                result['comment_id'] = found[0]['id']
                checkpoint('COMMITTED', receipt=result)
                return result
            if reconcile_only or (previous and previous['phase'] != 'PREPARED'):
                raise Stop('RECONCILE_REQUIRED', '补充说明结果未明，停止重复写入并交维护人核查。')
            posted = apply_effect('comment')
            comments = api.pages(endpoint)
            if not any(c.get('id') == posted['id'] and c.get('body') == p['comment'] for c in comments):
                raise Stop('READBACK_MISMATCH', '补充说明已发送但未成功回读，请勿重发。')
            result = status_receipt(issue(api, p['number']))
            result['comment_id'] = posted['id']
            checkpoint('COMMITTED', receipt=result)
            return result
        else:
            row = issue(api, p['number'])
            comments = api.pages(API + '/issues/' + str(p['number']) + '/comments')
            marker = '<!-- feedback-update:' + rid + ' -->'
            found = [x for x in comments if marker in (x.get('body') or '')]
            if len(found) > 1:
                raise Stop('DUPLICATES_FOUND', '处理回执有重复标记，停止自动维护。')
            if found and (found[0].get('body') != p['comment'] or found[0].get('user', {}).get('login') != actor):
                raise Stop('REQUEST_CONFLICT', '处理回执与本次批准内容或执行账号不一致。')
            if found and matches_patch(row, p['patch']):
                result = status_receipt(row)
                checkpoint('COMMITTED', receipt=result)
                return result
            if reconcile_only or (previous and previous['phase'] not in {'PREPARED', 'COMMENT_RECEIPT'}):
                raise Stop('RECONCILE_REQUIRED', '状态维护尚未完整确认；保留现状，需人工核查后用新的预览续办。')
            if not found:
                if row['updated_at'] != p['expected_updated_at']:
                    raise Stop('STALE_PREVIEW', 'Issue 已被更新；重新读取并生成状态预览。')
                receipt = apply_effect('comment')
                comments = api.pages(API + '/issues/' + str(p['number']) + '/comments')
                if not any(c.get('id') == receipt['id'] and c.get('body') == p['comment'] for c in comments):
                    raise Stop('READBACK_MISMATCH', '处理说明尚未回读成功，状态未改。')
                row = issue(api, p['number'])
            if any(row[k] != p['before'][k] for k in ['state']) or set(x['name'] for x in row['labels']) != set(p['before']['labels']) or set(x['login'] for x in row.get('assignees', [])) != set(p['before']['assignees']):
                raise Stop('STALE_PREVIEW', '其他维护人已修改状态、标签或负责人；重新生成预览。')
            apply_effect('patch')
            row = issue(api, p['number'])
            if not matches_patch(row, p['patch']):
                raise Stop('READBACK_MISMATCH', '维护操作回读不一致；请核查当前 Issue。')
        result = status_receipt(row)
        checkpoint('COMMITTED', receipt=result)
        return result


def verify_offline(run_dir):
    from fixture_transport import FixtureGitHub
    root = Path(run_dir)
    source = read(root / 'input/request.json')
    api = FixtureGitHub()
    config = {'repository': REPO, 'expected_actor': 'fixture-bot',
              'approvers': ['trusted-fixture-user'], 'maintainer_actors': ['fixture-bot'],
              'maintainer_approvers': ['trusted-fixture-user']}
    preview = wrap_preview(render(source['draft']))
    approval = {'approved': True, 'approved_by': 'trusted-fixture-user',
                'approved_at': now(), 'preview_sha256': preview['preview_sha256']}
    with tempfile.TemporaryDirectory(prefix='offline-journal-', dir=root) as journal_dir:
        result = transaction(api, config, preview, approval, journal_dir)
        second = transaction(api, config, preview, approval, journal_dir)
    receipts = [result, second]
    observed = {'source_id': REPO, 'fetched_at': now(),
                'locator': {'transport': 'isolated-fixture', 'request_id': source['draft']['request_id']},
                'created': result, 'repeated': second, 'receipts': receipts,
                'receipt_count': len(receipts), 'receipts_sha256': digest(receipts)[:16],
                'effect_calls': len(api.writes), 'remote_issues': len(api.rows), 'input_sha256': digest(source)}
    artifact = root / 'stage_outputs/process_feedback/observed.json'
    save(artifact, observed)
    outputs = [{'id': str(artifact.relative_to(root)), 'kind': 'verified-issue-receipts',
                'sha256': hashlib.sha256(artifact.read_bytes()).hexdigest()[:16]}]
    receipt = {'source_id': REPO, 'fetched_at': now(),
               'locator': {'transport': 'isolated-fixture', 'request_id': source['draft']['request_id']},
               'outputs': outputs, 'output_count': len(outputs), 'outputs_sha256': digest(outputs)[:16]}
    save(root / 'process_feedback_receipt.json', receipt)
    return receipt



def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    p = sub.add_parser('prepare')
    p.add_argument('--input', required=True)
    p.add_argument('--out', required=True)
    for name in ('prepare-update', 'prepare-comment'):
        p = sub.add_parser(name)
        p.add_argument('--input', required=True)
        p.add_argument('--out', required=True)
        p.add_argument('--config', required=True)
    for name in ('submit', 'reconcile'):
        p = sub.add_parser(name)
        for key in ('preview', 'approval', 'config', 'state-dir', 'receipt'):
            p.add_argument('--' + key, required=True)
    p = sub.add_parser('query')
    p.add_argument('--number', required=True, type=int)
    p.add_argument('--config', required=True)
    p.add_argument('--out', required=True)
    p = sub.add_parser('doctor')
    p.add_argument('--config', required=True)
    p = sub.add_parser('verify-offline')
    p.add_argument('--run-dir', required=True)
    p = sub.add_parser('pending')
    p.add_argument('--state-dir', required=True)
    args = parser.parse_args()
    try:
        config = read(args.config) if hasattr(args, 'config') else {}
        api = GitHub(config.get('transport', 'gh'))
        if args.command == 'pending':
            with Journal(args.state_dir) as journal:
                result = {'result': 'PENDING', 'requests': journal.pending(), 'checked_at': now()}
        elif args.command == 'verify-offline':
            result = verify_offline(args.run_dir)
        elif args.command == 'prepare':
            result = wrap_preview(render(read(args.input)))
            save(args.out, result)
        elif args.command == 'prepare-update':
            verify_host(api, config, maintain=True)
            result = wrap_preview(prepare_update(api, read(args.input)))
            save(args.out, result)
        elif args.command == 'prepare-comment':
            verify_host(api, config)
            result = wrap_preview(prepare_comment(api, read(args.input)))
            save(args.out, result)
        elif args.command in {'submit', 'reconcile'}:
            result = transaction(api, config, read(args.preview), read(args.approval),
                                 args.state_dir, args.command == 'reconcile')
            save(args.receipt, result)
        elif args.command == 'query':
            verify_host(api, config)
            result = status_receipt(issue(api, args.number))
            save(args.out, result)
        else:
            actor = verify_host(api, config)
            result = {'result': 'CONNECTED', 'repository': REPO, 'actor': actor, 'checked_at': now()}
        print(json.dumps(result, ensure_ascii=False, indent=2))
    except Stop as exc:
        result = {'result': 'FAILED', 'code': exc.code, 'message': exc.message, 'checked_at': now()}
        if hasattr(args, 'receipt'):
            save(args.receipt, result)
        print(json.dumps(result, ensure_ascii=False), file=sys.stderr)
        return 2
    except (ValueError, KeyError, TypeError, OSError):
        result = {'result': 'FAILED', 'code': 'LOCAL_INPUT_ERROR',
                  'message': '文件、配置或输入格式无法读取；未确认成功。', 'checked_at': now()}
        if hasattr(args, 'receipt'):
            try:
                save(args.receipt, result)
            except OSError:
                pass
        print(json.dumps(result, ensure_ascii=False), file=sys.stderr)
        return 2
    return 0


if __name__ == '__main__':
    sys.exit(main())
