"""Compare development HTTP servers with the *same* SlowAPI application.

Not a comparison against production frameworks. Results vary by machine.
"""
import concurrent.futures
import contextlib
import socket
import statistics
import threading
import time
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from main import SlowAPI
from http_server import HTTPServer
from wsgiref.simple_server import make_server, WSGIRequestHandler

class QuietHandler(WSGIRequestHandler):
    def log_message(self, *args): pass

app = SlowAPI()
@app.get('/ping')
def ping(request, response): return response.json({'ok': True})

def request(addr):
    started = time.perf_counter_ns()
    with socket.create_connection(addr, timeout=3) as sock:
        sock.settimeout(3)
        sock.sendall(b'GET /ping HTTP/1.1\r\nHost: localhost\r\nConnection: close\r\n\r\n')
        out = b''
        while True:
            chunk = sock.recv(8192)
            if not chunk: break
            out += chunk
    if b'200 OK' not in out: raise RuntimeError('Unexpected HTTP response')
    return (time.perf_counter_ns() - started)/1e6

def run_one(factory, num=120, concurrency=1):
    srv = factory()
    thread = threading.Thread(target=srv.serve_forever, daemon=True)
    thread.start()
    try:
        address = srv.server_address
        for _ in range(10): request(address)
        start = time.perf_counter()
        with concurrent.futures.ThreadPoolExecutor(max_workers=concurrency) as pool:
            times = list(pool.map(lambda _: request(address), range(num)))
        seconds = time.perf_counter()-start
        return statistics.median(times), num/seconds
    finally:
        srv.shutdown(); srv.server_close(); thread.join(timeout=2)

if __name__ == '__main__':
    print('Local HTTP comparison: identical SlowAPI app, fresh connection per request.')
    for concurrency in (1, 4):
        for label, factory in (
            ('wsgiref', lambda: make_server('127.0.0.1',0,app,handler_class=QuietHandler)),
            ('native', lambda: HTTPServer('127.0.0.1',0,app))):
            latency, rps = run_one(factory, concurrency=concurrency)
            print(f'{label:8} concurrency={concurrency} median_latency_ms={latency:.3f} throughput_rps={rps:.1f}')
    print('Do not interpret these as measured improvements relative to standard WSGI frameworks.')
