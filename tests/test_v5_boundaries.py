import unittest
from http_parser import HTTPParseError, parse_http_request, parse_head, decode_chunked
from http_server import MAX_REQUESTS_PER_CONNECTION

class RequestBoundaryTests(unittest.TestCase):
    def head(self, target='/', host='example.com'):
        return f'GET {target} HTTP/1.1\r\nHost: {host}\r\n\r\n'.encode()

    def test_valid_ipv4_host(self):
        self.assertEqual(parse_http_request(self.head(host='127.0.0.1')).method,'GET')

    def test_invalid_authority_host(self):
        for host in ('evil/path','bad,example','@evil',':80'):
            with self.subTest(host=host),self.assertRaises(HTTPParseError):
                parse_http_request(self.head(host=host))

    def test_request_target_limit(self):
        with self.assertRaises(HTTPParseError) as caught:
            parse_head(self.head('/'+'a'*8192),max_headers=16384)
        self.assertEqual(caught.exception.status,414)

    def test_request_target_at_limit(self):
        req=parse_http_request(self.head('/'+'a'*8191))
        self.assertEqual(len(req.target),8192)

    def test_chunked_forbidden_trailer(self):
        for trailer in (b'Host: other\r\n',b'Content-Length: 0\r\n'):
            with self.subTest(trailer=trailer),self.assertRaises(HTTPParseError):
                decode_chunked(b'0\r\n'+trailer+b'\r\n')

    def test_encoded_fragment_marker_allowed(self):
        self.assertEqual(parse_http_request(self.head('/test%23fragment')).target,'/test%23fragment')

    def test_absolute_form_unsupported(self):
        with self.assertRaises(HTTPParseError):
            parse_http_request(b'GET http://example.com/ HTTP/1.1\r\nHost: example.com\r\n\r\n')

    def test_upgrade_is_not_provided(self):
        self.assertGreater(MAX_REQUESTS_PER_CONNECTION,0)

if __name__=='__main__': unittest.main()
