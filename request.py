"""Request abstraction compatible with a WSGI environ."""
import json
from urllib.parse import parse_qs

class Request:
    def __init__(self, environ):
        self.environ = environ
        self.path_info = environ.get('PATH_INFO', '/')
        self.request_method = environ.get('REQUEST_METHOD', 'GET').upper()
        self.queries = {k: v[-1] for k, v in parse_qs(environ.get('QUERY_STRING', ''), keep_blank_values=True).items()}
        self.headers = {k[5:].replace('_','-').lower():v for k,v in environ.items() if k.startswith('HTTP_')}
        if 'CONTENT_TYPE' in environ:
            self.headers['content-type'] = environ['CONTENT_TYPE']
        try: size = int(environ.get('CONTENT_LENGTH') or 0)
        except (TypeError, ValueError): raise ValueError('Invalid content length')
        if size < 0 or size > 1024 * 1024: raise ValueError('Body exceeds 1 MiB limit')
        self.body = environ.get('wsgi.input').read(size) if size and environ.get('wsgi.input') else b''
    def json(self):
        return json.loads(self.body.decode('utf-8'))
