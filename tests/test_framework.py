import io
import json
import unittest
from main import SlowAPI, Router, render_template
from http_parser import parse_http_request, HTTPParseError

def call(app, path='/', method='GET', query='', body=b''):
    result = {}
    def start(status, headers):
        result['status'] = status; result['headers'] = dict(headers)
    data = b''.join(app({'PATH_INFO':path,'REQUEST_METHOD':method,'QUERY_STRING':query,
                         'CONTENT_LENGTH':str(len(body)),'wsgi.input':io.BytesIO(body)}, start))
    return int(result['status'][:3]), result['headers'], data

class FrameworkTests(unittest.TestCase):
    def test_routes(self):
        app = SlowAPI()
        @app.get('/users/{id}')
        def user(req, resp, id): resp.json({'id': id, 'q': req.queries})
        code, headers, data = call(app, '/users/123', query='x=one&x=two')
        self.assertEqual(code, 200)
        self.assertEqual(json.loads(data), {'id': '123', 'q': {'x':'two'}})
        self.assertEqual(int(headers['Content-Length']), len(data))
    def test_static_precedence(self):
        app = SlowAPI()
        @app.get('/users/{id}')
        def dynamic(req, resp, id): resp.text('dynamic')
        @app.get('/users/me')
        def static(req, resp): resp.text('static')
        self.assertEqual(call(app,'/users/me')[2], b'static')
    def test_404_and_405(self):
        app = SlowAPI()
        @app.get('/one')
        def one(req, resp): resp.text('ok')
        self.assertEqual(call(app,'/absent')[0], 404)
        code, headers, _ = call(app,'/one','POST')
        self.assertEqual(code,405)
        self.assertEqual(headers['Allow'],'GET')
    def test_middlewares(self):
        calls = []
        app = SlowAPI([lambda req: calls.append('global')])
        @app.get('/ok', middlewares=[lambda req: calls.append('route')])
        def ok(req, resp): resp.text('ok')
        self.assertEqual(call(app,'/ok')[0], 200)
        self.assertEqual(calls, ['global','route'])
    def test_error(self):
        app = SlowAPI()
        @app.get('/boom')
        def boom(req, resp): raise RuntimeError('secret')
        self.assertEqual(json.loads(call(app,'/boom')[2]), {'error':'Internal Server Error'})
    def test_class_routes(self):
        app = SlowAPI()
        @app.route('/items/{id}')
        class Items:
            def get(self, req, resp, id): resp.text(id)
            def delete(self, req, resp, id): resp.text('removed ' + id)
        self.assertEqual(call(app,'/items/4','DELETE')[2], b'removed 4')
    def test_duplicate_rejected(self):
        router = Router()
        router.add('/a','GET',lambda: None)
        with self.assertRaises(ValueError): router.add('/a','GET',lambda: None)
    def test_body_length_limit(self):
        app=SlowAPI()
        status,_,_=call(app,'/',body=b'a' * (1024*1024+1))
        self.assertEqual(status,400)

class ParserTests(unittest.TestCase):
    def test_valid(self):
        parsed=parse_http_request(b'POST /a HTTP/1.1\r\nHost: example.org\r\nContent-Length: 3\r\n\r\nabc')
        self.assertEqual((parsed.method, parsed.body), ('POST',b'abc'))
    def test_invalid(self):
        samples=[b'GET / HTTP/1.0\r\nHost: x\r\n\r\n',b'GET / HTTP/1.1\r\n\r\n',
                 b'GET / HTTP/1.1\r\nHost: x\r\nHost: y\r\n\r\n',
                 b'POST / HTTP/1.1\r\nHost: x\r\nTransfer-Encoding: chunked\r\n\r\n',
                 b'POST / HTTP/1.1\r\nHost: x\r\nContent-Length: 5\r\n\r\na']
        for message in samples:
            with self.subTest(message=message), self.assertRaises(HTTPParseError):
                parse_http_request(message)

if __name__ == '__main__': unittest.main()

class TemplateTests(unittest.TestCase):
    def test_escapes_substitution(self):
        import tempfile
        from pathlib import Path
        with tempfile.TemporaryDirectory() as directory:
            Path(directory, 'example.html').write_text('<p>{{ username }}</p>',encoding='utf-8')
            self.assertEqual(render_template('example.html', {'username':'<script>'}, directory), '<p>&lt;script&gt;</p>')
    def test_blocks_path_traversal(self):
        import tempfile
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(ValueError): render_template('../secret.txt', {}, directory)
