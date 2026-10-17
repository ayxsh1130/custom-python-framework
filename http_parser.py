"""Strict, bounded HTTP/1.1 origin-server request framing (RFC 9110/9112 subset).

This is not a full HTTP/1.1 implementation (e.g. upgrades, proxy target forms,
transfer codings other than chunked, and internationalized hostnames are out of scope).
"""
from dataclasses import dataclass

TOKEN = frozenset(b"!#$%&'*+-.^_`|~0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz")
FORBIDDEN_TRAILERS = {'host', 'content-length', 'transfer-encoding', 'connection', 'trailer', 'te', 'upgrade', 'authorization', 'proxy-authorization'}

class HTTPParseError(ValueError):
    def __init__(self, message, status=400):
        super().__init__(message)
        self.status = status

@dataclass(frozen=True)
class HTTPRequest:
    method: str
    target: str
    version: str
    headers: dict[str, str]
    body: bytes

def _valid_value(value):
    # obs-text permitted in HTTP field values, but NUL, DEL and controls are not.
    return all(c == 9 or c == 32 or 33 <= c <= 126 or 128 <= c <= 255 for c in value)

def _field(line):
    if not line or line.startswith((b' ',b'\t')) or b':' not in line:
        raise HTTPParseError('Malformed header field')
    name, value = line.split(b':', 1)
    if not name or any(c not in TOKEN for c in name) or not _valid_value(value):
        raise HTTPParseError('Invalid header field')
    return name.decode('ascii').lower(), value.strip(b' \t').decode('latin-1')

def parse_head(data: bytes, max_headers=16384):
    if len(data) > max_headers:
        raise HTTPParseError('Header section too large', 431)
    if not data.endswith(b'\r\n\r\n'):
        raise HTTPParseError('Malformed headers')
    lines = data[:-4].split(b'\r\n')
    parts = lines[0].split(b' ')
    if len(parts) != 3:
        raise HTTPParseError('Malformed request line')
    method, target, version = parts
    if not method or any(c not in TOKEN for c in method):
        raise HTTPParseError('Invalid method')
    if len(target) > 8192:
        raise HTTPParseError('Request target too long', 414)
    if version != b'HTTP/1.1':
        raise HTTPParseError('HTTP version not supported', 505)
    # This is an origin server: origin-form, and asterisk-form for OPTIONS.
    if not (target.startswith(b'/') or (method == b'OPTIONS' and target == b'*')):
        raise HTTPParseError('Unsupported request target form')
    if any(c < 33 or c > 126 for c in target) or b'#' in target:
        raise HTTPParseError('Invalid request target')
    headers = {}
    hosts = 0
    for line in lines[1:]:
        name, value = _field(line)
        if name == 'host':
            hosts += 1
            if hosts > 1 or not value or any(c.isspace() for c in value) or any(c in value for c in '/\\@,') or value.startswith(':'):
                raise HTTPParseError('Invalid or duplicate Host')
        if name in ('content-length', 'transfer-encoding') and name in headers:
            raise HTTPParseError('Duplicate framing header')
        # Field repetition generally allowed. Combine comma-list fields; cookie uses '; '.
        if name in headers:
            headers[name] += ('; ' if name == 'cookie' else ', ') + value
        else:
            headers[name] = value
    if hosts != 1:
        raise HTTPParseError('One Host field required')
    if 'transfer-encoding' in headers and 'content-length' in headers:
        raise HTTPParseError('Ambiguous message framing')
    if 'transfer-encoding' in headers and headers['transfer-encoding'].lower() != 'chunked':
        raise HTTPParseError('Unsupported transfer coding', 501)
    if 'content-length' in headers and (not headers['content-length'].isascii() or not headers['content-length'].isdecimal()):
        raise HTTPParseError('Invalid content length')
    if 'expect' in headers and headers['expect'].lower() != '100-continue':
        raise HTTPParseError('Unsupported expectation', 417)
    return method.decode('ascii'), target.decode('ascii'), headers

def decode_chunked(data: bytes, max_body=1048576):
    pos = 0
    chunks = []
    total = 0
    trailer_bytes = 0
    while True:
        end = data.find(b'\r\n', pos)
        if end < 0 or end-pos > 128:
            raise HTTPParseError('Invalid chunk header')
        size_line = data[pos:end].split(b';',1)[0]
        if not size_line or any(c not in b'0123456789abcdefABCDEF' for c in size_line):
            raise HTTPParseError('Invalid chunk size')
        size = int(size_line,16)
        pos = end+2
        if size > max_body-total:
            raise HTTPParseError('Body exceeds limit', 413)
        if not size:
            while True:
                end = data.find(b'\r\n',pos)
                if end < 0:
                    raise HTTPParseError('Incomplete trailers')
                trailer_bytes += end-pos+2
                if trailer_bytes > 16384:
                    raise HTTPParseError('Trailers too large', 431)
                trailer = data[pos:end]
                pos = end+2
                if not trailer:
                    return b''.join(chunks), pos
                name, _ = _field(trailer)
                if name in FORBIDDEN_TRAILERS:
                    raise HTTPParseError('Forbidden trailer field')
        if pos+size+2 > len(data) or data[pos+size:pos+size+2] != b'\r\n':
            raise HTTPParseError('Incomplete chunk')
        chunks.append(data[pos:pos+size]); total += size; pos += size+2

def parse_http_request(data: bytes, max_headers=16384, max_body=1048576) -> HTTPRequest:
    if not isinstance(data, bytes):
        raise TypeError('Expected bytes')
    boundary = data.find(b'\r\n\r\n')
    if boundary < 0:
        raise HTTPParseError('Missing header delimiter')
    method,target,headers = parse_head(data[:boundary+4], max_headers)
    wire_body = data[boundary+4:]
    if headers.get('transfer-encoding','').lower() == 'chunked':
        body, consumed = decode_chunked(wire_body,max_body)
        if consumed != len(wire_body):
            raise HTTPParseError('Extra bytes after message')
    else:
        length = int(headers.get('content-length','0'))
        if length > max_body:
            raise HTTPParseError('Body exceeds limit',413)
        if length != len(wire_body):
            raise HTTPParseError('Body size mismatch')
        body = wire_body
    return HTTPRequest(method,target,'HTTP/1.1',headers,body)
