import socket
import threading
import unittest
from main import SlowAPI
from http_server import HTTPServer

class NativeServerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        app = SlowAPI()
        @app.get('/hello/{name}')
        def hello(request, response, name):
            return response.json({'name': name, 'q': request.queries.get('q')})
        @app.post('/echo')
        def echo(request, response):
            return response.text(request.body.decode())
        cls.server = HTTPServer('127.0.0.1', 0, app)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown(); cls.server.server_close(); cls.thread.join(timeout=2)
    def request(self, payload):
        with socket.create_connection(self.server.server_address, 2) as sock:
            sock.sendall(payload); sock.shutdown(socket.SHUT_WR)
            chunks = []
            while True:
                part = sock.recv(4096)
                if not part: break
                chunks.append(part)
            return b''.join(chunks)
    def test_get_and_query(self):
        result = self.request(b'GET /hello/Ayush?q=yes HTTP/1.1\r\nHost: localhost\r\n\r\n')
        self.assertIn(b'200 OK', result)
        self.assertIn(b'"name": "Ayush"', result)
        self.assertIn(b'"q": "yes"', result)
    def test_post_body(self):
        result = self.request(b'POST /echo HTTP/1.1\r\nHost: localhost\r\nContent-Length: 5\r\n\r\nhello')
        self.assertTrue(result.endswith(b'hello'))
    def test_missing_host(self):
        result = self.request(b'GET / HTTP/1.1\r\n\r\n')
        self.assertIn(b'400 Bad Request', result)
    def test_duplicate_length(self):
        result = self.request(b'POST /echo HTTP/1.1\r\nHost: localhost\r\nContent-Length: 1\r\nContent-Length: 1\r\n\r\na')
        self.assertIn(b'400 Bad Request', result)
    def test_chunked_rejected(self):
        result = self.request(b'POST /echo HTTP/1.1\r\nHost: localhost\r\nTransfer-Encoding: chunked\r\n\r\n')
        self.assertIn(b'400 Bad Request', result)
    def test_not_found_and_wrong_method(self):
        self.assertIn(b'404 Not Found', self.request(b'GET /unknown HTTP/1.1\r\nHost: localhost\r\n\r\n'))
        self.assertIn(b'405 Method Not Allowed', self.request(b'DELETE /hello/test HTTP/1.1\r\nHost: localhost\r\n\r\n'))
if __name__ == '__main__': unittest.main()
