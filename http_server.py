"""Bounded threaded HTTP/1.1 origin server for education, not production exposure."""
import io
import socket
import socketserver
from http import HTTPStatus
from urllib.parse import urlsplit, unquote
from http_parser import HTTPParseError, parse_head, parse_http_request, TOKEN

HEADER_LIMIT = 16384
BODY_LIMIT = 1048576
MAX_REQUESTS_PER_CONNECTION = 100

class _Handler(socketserver.StreamRequestHandler):
    def _read_headers(self):
        first = self.rfile.readline(HEADER_LIMIT+1)
        if not first: return None
        data = bytearray(first)
        if len(data)>HEADER_LIMIT: raise HTTPParseError('Headers too large',431)
        while not data.endswith(b'\r\n\r\n'):
            line = self.rfile.readline(HEADER_LIMIT+1)
            if not line: raise HTTPParseError('Incomplete headers')
            data.extend(line)
            if len(data)>HEADER_LIMIT: raise HTTPParseError('Headers too large',431)
        return bytes(data)

    def _read_chunked_body(self):
        out = bytearray()
        decoded = 0
        trailer_total = 0
        while True:
            line = self.rfile.readline(130)
            if not line.endswith(b'\r\n'): raise HTTPParseError('Invalid chunk header')
            out.extend(line)
            size_part=line[:-2].split(b';',1)[0]
            if not size_part or any(c not in b'0123456789abcdefABCDEF' for c in size_part):
                raise HTTPParseError('Invalid chunk size')
            size=int(size_part,16)
            if size>BODY_LIMIT-decoded: raise HTTPParseError('Body exceeds limit',413)
            if size==0:
                while True:
                    trailer=self.rfile.readline(HEADER_LIMIT+1)
                    if not trailer.endswith(b'\r\n'): raise HTTPParseError('Invalid trailer')
                    trailer_total+=len(trailer)
                    if trailer_total>HEADER_LIMIT: raise HTTPParseError('Trailers too large',431)
                    out.extend(trailer)
                    if trailer==b'\r\n': return bytes(out)
            else:
                # Avoid allocating arbitrarily large buffers for malicious inputs.
                chunk=self.rfile.read(size+2)
                if len(chunk)!=size+2 or not chunk.endswith(b'\r\n'):
                    raise HTTPParseError('Incomplete chunk')
                out.extend(chunk);decoded+=size

    def handle(self):
        self.connection.settimeout(5)
        for request_index in range(MAX_REQUESTS_PER_CONNECTION):
            method='GET'
            try:
                head=self._read_headers()
                if head is None: return
                method,target,headers=parse_head(head)
                if headers.get('expect','').lower()=='100-continue':
                    announced = int(headers.get('content-length','0'))
                    if announced>BODY_LIMIT: raise HTTPParseError('Body exceeds limit',413)
                    self.wfile.write(b'HTTP/1.1 100 Continue\r\n\r\n');self.wfile.flush()
                if headers.get('transfer-encoding','').lower()=='chunked':
                    body=self._read_chunked_body()
                else:
                    size=int(headers.get('content-length','0'))
                    if size>BODY_LIMIT: raise HTTPParseError('Body exceeds limit',413)
                    body=self.rfile.read(size)
                    if len(body)!=size: raise HTTPParseError('Incomplete body')
                req=parse_http_request(head+body,max_body=BODY_LIMIT)
                parts=urlsplit(req.target) if req.target!='*' else None
                from request import Request
                environ={'REQUEST_METHOD':req.method,'PATH_INFO': unquote(parts.path) if parts else '*',
                         'QUERY_STRING':parts.query if parts else '', 'CONTENT_LENGTH':str(len(req.body)),
                         'wsgi.input':io.BytesIO(req.body),'SERVER_PROTOCOL':req.version,
                         'CONTENT_TYPE':req.headers.get('content-type','')}
                environ.update({'HTTP_'+k.upper().replace('-','_'):v for k,v in req.headers.items()
                                if k not in ('content-type','content-length')})
                response=self.server.app.dispatch(Request(environ))
                connection_tokens={s.strip().lower() for s in headers.get('connection','').split(',')}
                keep='close' not in connection_tokens and request_index + 1 < MAX_REQUESTS_PER_CONNECTION
                self._send(response.status,response.body,response.headers,method,keep)
                if not keep: return
            except HTTPParseError as exc:
                try: self._send(exc.status,b'{"error":"Invalid HTTP request"}',{'Content-Type':'application/json'},method,False)
                except OSError: pass
                return
            except (ValueError,UnicodeError,TimeoutError,socket.timeout):
                try: self._send(400,b'{"error":"Bad Request"}',{'Content-Type':'application/json'},method,False)
                except OSError: pass
                return
            except (BrokenPipeError,ConnectionResetError,OSError): return
            except Exception:
                try: self._send(500,b'{"error":"Internal Server Error"}',{'Content-Type':'application/json'},method,False)
                except OSError: pass
                return

    def _send(self,status,body,headers,method='GET',keep=False):
        body=body if isinstance(body,bytes) else body.encode()
        if status in (204,304) or 100<=status<200: body=b''
        safe={}
        for key,value in headers.items():
            encoded_key=str(key).encode('ascii','strict')
            value=str(value)
            if not encoded_key or any(c not in TOKEN for c in encoded_key) or '\r' in value or '\n' in value:
                raise ValueError('Unsafe response header')
            if key.lower() not in ('connection','transfer-encoding','content-length'):
                safe[key]=value
        if status not in (204,304) and not 100<=status<200:
            safe['Content-Length']=str(len(body))
        safe['Connection']='keep-alive' if keep else 'close'
        status_line=f'HTTP/1.1 {status} {HTTPStatus(status).phrase}\r\n'.encode('ascii')
        header_bytes=b''.join(f'{k}: {v}\r\n'.encode('latin-1') for k,v in safe.items())
        self.wfile.write(status_line+header_bytes+b'\r\n'+(b'' if method=='HEAD' else body))
        self.wfile.flush()

class HTTPServer(socketserver.ThreadingTCPServer):
    allow_reuse_address=True
    daemon_threads=True
    request_queue_size=128
    def __init__(self,host,port,app):
        self.app=app
        super().__init__((host,port),_Handler)
