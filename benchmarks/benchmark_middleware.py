"""Compare identical dispatch flows with/without no-op middleware.

This measures COST of middleware, not a claimed improvement over an earlier
middleware implementation. Run multiple processes for stable results.
"""
import json
import statistics
import sys
import time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from main import SlowAPI
from request import Request

def get_request():
    return Request({'PATH_INFO':'/ping','REQUEST_METHOD':'GET','QUERY_STRING':'', 'CONTENT_LENGTH':'0'})

def make_app(middleware_count):
    def noop(request): return None
    app=SlowAPI(middlewares=[noop]*middleware_count)
    @app.get('/ping')
    def ping(request,response): return response.text('pong')
    return app

def measure(app, req, iterations=50000, rounds=7):
    for _ in range(1000): app.dispatch(req)
    records=[]
    for _ in range(rounds):
        t=time.perf_counter_ns()
        for __ in range(iterations): app.dispatch(req)
        records.append((time.perf_counter_ns()-t)/iterations)
    return statistics.median(records)

if __name__=='__main__':
    req=get_request()
    values={n:measure(make_app(n),req) for n in (0,1,5,10)}
    base=values[0]
    print(json.dumps({'unit':'nanoseconds per dispatch', 'baseline_without_middleware':base,
                      'observations':{str(n):{'dispatch_ns':round(v,1), 'additional_ns':round(v-base,1),
                                               'overhead_percent':round((v/base-1)*100,2)} for n,v in values.items()},
                      'interpretation':'No before/after middleware optimization claimed'},indent=2))
