"""In-memory GitHub transport for offline verification; never calls the network."""
import copy
import feedback as f


class FixtureGitHub:
    def __init__(self):
        self.rows, self.comments, self.writes = [], {}, []
        self.fail_after = None
        self.actor = 'fixture-bot'

    def call(self, method, endpoint, payload=None):
        if method == 'GET':
            if endpoint == '/user':
                return {'login': self.actor}
            if endpoint == f.API:
                return {'full_name': f.REPO, 'private': False, 'has_issues': True}
            number = int(endpoint.rsplit('/', 1)[1])
            return copy.deepcopy(self.rows[number - 1])
        self.writes.append((method, endpoint, copy.deepcopy(payload)))
        if endpoint.endswith('/comments'):
            number = int(endpoint.split('/')[-2])
            row = {'id': len(self.comments.get(number, [])) + 1, 'body': payload['body'],
                   'user': {'login': self.actor}}
            self.comments.setdefault(number, []).append(row)
        elif method == 'POST':
            number = len(self.rows) + 1
            row = {'number': number, 'title': payload['title'], 'body': payload['body'],
                   'labels': [{'name': x} for x in payload['labels']], 'assignees': [],
                   'state': 'open', 'state_reason': None, 'updated_at': '2026-10-06T12:00:00Z',
                   'html_url': 'https://github.com/' + f.REPO + '/issues/' + str(number)}
            self.rows.append(row)
        else:
            number = int(endpoint.rsplit('/', 1)[1])
            row = self.rows[number - 1]
            row.update({k: v for k, v in payload.items() if k not in {'labels', 'assignees'}})
            row['labels'] = [{'name': x} for x in payload['labels']]
            row['assignees'] = [{'login': x} for x in payload['assignees']]
        if self.fail_after == method:
            self.fail_after = None
            raise f.Stop('TRANSPORT_UNKNOWN', 'simulated lost response')
        return copy.deepcopy(row)

    def pages(self, endpoint):
        if endpoint == f.API + '/labels':
            return [{'name': x} for x in set(f.CATEGORIES.values()) | f.STATUS_LABELS]
        if '/comments' in endpoint:
            return copy.deepcopy(self.comments.get(int(endpoint.split('/')[-2]), []))
        return copy.deepcopy(self.rows)

