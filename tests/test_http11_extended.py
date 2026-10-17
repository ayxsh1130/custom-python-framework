import socket
import threading
import unittest
from http_parser import HTTPParseError, parse_http_request
from http_server import HTTPServer
from main import SlowAPI, Router

class ParserExtendedTests(unittest.TestCase):
    def test_chunked_body(self):
        msg = (b'POST /echo HTTP/1.1\r\nHost: localhost\r\nTransfer-Encoding: chunked\r\n\r\n'
               b'5\r\nhello\r\n6\r\n world\r\n0\r\nX-Trace: 123\r\n\r\n')
        self.assertEqual(parse_http_request(msg).body,b'hello world')
    def test_reject_request_smuggling(self):
        data = b'POST / HTTP/1.1\r\nHost: a\r\nContent-Length: 1\r\nTransfer-Encoding: chunked\r\n\r\n'
        with self.assertRaises(HTTPParseError): parse_http_request(data)
    def test_reject_extra_bytes(self):
        data = b'POST / HTTP/1.1\r\nHost: a\r\nContent-Length: 1\r\n\r\nab'
        with self.assertRaises(HTTPParseError): parse_http_request(data)
    def test_static_routing_exact_and_parameters(self):
        r = Router()
        r.add('/users/{id}','GET', lambda *_: None)
        static = lambda *_: None
        r.add('/users/me','GET',static)
        self.assertIs(r.resolve('/users/me','GET')[0][0],static)
        self.assertEqual(r.resolve('/users/123','GET')[1], {'id':'123'})
        self.assertIsNotNone(r.exact.get('/users/me'))

class ServerExtendedTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        app = SlowAPI()
        @app.post('/echo')
        def echo(req,res): return res.text(req.body.decode())
        @app.get('/ping')
        def ping(req,res): return res.text('pong')
        cls.server = HTTPServer('127.0.0.1',0,app)
        cls.worker = threading.Thread(target=cls.server.serve_forever,daemon=True)
        cls.worker.start()
    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown();cls.server.server_close();cls.worker.join(timeout=2)
    def test_chunked_server(self):
        with socket.create_connection(self.server.server_address,2) as sock:
            sock.settimeout(2)
            sock.sendall(b'POST /echo HTTP/1.1\r\nHost: x\r\nTransfer-Encoding: chunked\r\nConnection: close\r\n\r\n5\r\nhello\r\n0\r\n\r\n')
            data=b''
            while True:
                part=sock.recv(8192)
                if not part:break
                data+=part
            self.assertIn(b'200 OK',data)
            self.assertTrue(data.endswith(b'hello'))
    def test_pipelined_keepalive(self):
        with socket.create_connection(self.server.server_address,2) as sock:
            sock.settimeout(2)
            sock.sendall(b'GET /ping HTTP/1.1\r\nHost: x\r\n\r\nGET /ping HTTP/1.1\r\nHost: x\r\nConnection: close\r\n\r\n')
            data=b''
            while True:
                part=sock.recv(8192)
                if not part:break
                data+=part
            self.assertEqual(data.count(b'200 OK'),2)
            self.assertEqual(data.count(b'pong'),2)

if __name__=='__main__':unittest.main()
