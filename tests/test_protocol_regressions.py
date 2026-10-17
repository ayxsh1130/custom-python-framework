import socket
import threading
import unittest
from http_parser import parse_http_request, HTTPParseError, parse_head
from http_server import HTTPServer
from main import SlowAPI

class FramingTests(unittest.TestCase):
    def base(self, header=b'', body=b''):
        return b'POST / HTTP/1.1\r\nHost: example.com\r\n'+header+b'\r\n'+body
    def assert_code(self, wire, status):
        with self.assertRaises(HTTPParseError) as caught:
            parse_http_request(wire)
        self.assertEqual(caught.exception.status,status)
    def test_missing_host(self): self.assert_code(b'GET / HTTP/1.1\r\n\r\n',400)
    def test_duplicate_host(self): self.assert_code(self.base(b'Host: evil.example\r\n'),400)
    def test_duplicate_content_length(self): self.assert_code(self.base(b'Content-Length: 1\r\nContent-Length: 1\r\n',b'a'),400)
    def test_invalid_whitespace_header(self): self.assert_code(self.base(b'X-Name : value\r\n'),400)
    def test_folded_header(self): self.assert_code(self.base(b'X-Name: a\r\n b\r\n'),400)
    def test_transfer_encoding_unsupported(self): self.assert_code(self.base(b'Transfer-Encoding: gzip\r\n'),501)
    def test_large_body(self): self.assert_code(self.base(b'Content-Length: 1048577\r\n'),413)
    def test_bad_version(self): self.assert_code(b'GET / HTTP/2.0\r\nHost: x\r\n\r\n',505)
    def test_repeated_list_headers(self):
        parsed = parse_http_request(self.base(b'Accept: text/plain\r\nAccept: application/json\r\n'))
        self.assertEqual(parsed.headers['accept'],'text/plain, application/json')
    def test_trailer_forbidden(self):
        self.assert_code(self.base(b'Transfer-Encoding: chunked\r\n',b'0\r\nHost: injected\r\n\r\n'),400)
    def test_options_asterisk_form(self):
        parsed=parse_http_request(b'OPTIONS * HTTP/1.1\r\nHost: x\r\n\r\n')
        self.assertEqual(parsed.target,'*')
    def test_reject_request_fragment(self):
        self.assert_code(b'GET /path#frag HTTP/1.1\r\nHost: x\r\n\r\n',400)
    def test_expectation_required(self):
        self.assert_code(self.base(b'Expect: unsupported\r\n'),417)
    def test_header_size_limit(self):
        self.assert_code(self.base(b'X-Long: '+b'a'*17000+b'\r\n'),431)
    def test_chunked_extension(self):
        parsed=parse_http_request(self.base(b'Transfer-Encoding: chunked\r\n',b'3;foo=bar\r\nabc\r\n0\r\n\r\n'))
        self.assertEqual(parsed.body,b'abc')

class WireTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        app=SlowAPI()
        @app.get('/ping')
        def ping(req,res): return res.text('pong')
        @app.post('/echo')
        def echo(req,res): return res.text(req.body.decode())
        @app.get('/nocontent')
        def no(req,res): return res.text('not transmitted',204)
        cls.server=HTTPServer('127.0.0.1',0,app)
        cls.worker=threading.Thread(target=cls.server.serve_forever,daemon=True)
        cls.worker.start()
    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown();cls.server.server_close();cls.worker.join(timeout=2)
    def raw(self,data):
        with socket.create_connection(self.server.server_address,2) as s:
            s.settimeout(2);s.sendall(data)
            out=b''
            while True:
                x=s.recv(8192)
                if not x:break
                out+=x
            return out
    def test_expect_100_continue(self):
        with socket.create_connection(self.server.server_address,2) as s:
            s.settimeout(2)
            s.sendall(b'POST /echo HTTP/1.1\r\nHost: x\r\nExpect: 100-continue\r\nContent-Length: 5\r\nConnection: close\r\n\r\n')
            interim=s.recv(1024)
            self.assertIn(b'100 Continue',interim)
            s.sendall(b'hello')
            result=b''
            while True:
                fragment=s.recv(8192)
                if not fragment:break
                result+=fragment
            self.assertIn(b'200 OK',result)
            self.assertTrue(result.endswith(b'hello'))
    def test_head_no_body(self):
        data=self.raw(b'HEAD /ping HTTP/1.1\r\nHost: x\r\nConnection: close\r\n\r\n')
        self.assertNotIn(b'pong',data)
    def test_204_no_body(self):
        data=self.raw(b'GET /nocontent HTTP/1.1\r\nHost: x\r\nConnection: close\r\n\r\n')
        self.assertIn(b'204 No Content',data)
        self.assertNotIn(b'not transmitted',data)
    def test_431(self):
        data=self.raw(b'GET / HTTP/1.1\r\nHost: x\r\nX-Long: '+b'x'*17000+b'\r\nConnection: close\r\n\r\n')
        self.assertIn(b'431 Request Header Fields Too Large',data)
    def test_413(self):
        data=self.raw(b'POST /echo HTTP/1.1\r\nHost: x\r\nContent-Length: 9999999\r\n\r\n')
        self.assertIn(b'413 Content Too Large',data)

if __name__=='__main__': unittest.main()
