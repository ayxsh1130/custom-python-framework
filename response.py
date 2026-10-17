import json
from http import HTTPStatus

class Response:
    def __init__(self, body=b'', status=200, headers=None):
        self.body = body.encode() if isinstance(body, str) else body
        self.status = status
        self.headers = dict(headers or {'Content-Type': 'text/plain; charset=utf-8'})
    def text(self, body, status=200):
        self.body = body.encode('utf-8'); self.status = status
        self.headers['Content-Type'] = 'text/plain; charset=utf-8'; return self
    def html(self, body, status=200):
        self.body = body.encode('utf-8'); self.status = status
        self.headers['Content-Type'] = 'text/html; charset=utf-8'; return self
    def json(self, data, status=200):
        self.body = json.dumps(data).encode('utf-8'); self.status = status
        self.headers['Content-Type'] = 'application/json'; return self
    def as_wsgi(self, start_response):
        self.headers['Content-Length'] = str(len(self.body))
        start_response(f'{self.status} {HTTPStatus(self.status).phrase}', list(self.headers.items()))
        return [self.body]
