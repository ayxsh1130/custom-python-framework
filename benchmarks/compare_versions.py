"""Paired, alternating old/new dispatch measurements; run on same interpreter.

Report median and range rather than treating this microbenchmark as HTTP performance.
"""
import importlib.util
import json
import statistics
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / 'verification' / 'baseline_v4'
sys.path.insert(0,str(ROOT))
from main import SlowAPI as NewSlowAPI
from request import Request
spec = importlib.util.spec_from_file_location('slowapi_old_main', BASE/'main.py')
module = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = module
spec.loader.exec_module(module)
OldSlowAPI = module.SlowAPI

def app_for(cls, count, early=False):
    def noop(request): return None
    app = cls(middlewares=[noop]*count)
    @app.get('/ping')
    def ping(request,response): return response.text('pong')
    return app

def timed(app,request,iterations):
    for _ in range(1000): app.dispatch(request)
    start=time.perf_counter_ns()
    for _ in range(iterations):app.dispatch(request)
    return (time.perf_counter_ns()-start)/iterations

def compare(count=5, rounds=12, iterations=50000):
    old,new=app_for(OldSlowAPI,count),app_for(NewSlowAPI,count)
    request=Request({'PATH_INFO':'/ping','REQUEST_METHOD':'GET','QUERY_STRING':'','CONTENT_LENGTH':'0'})
    pairs=[]
    for i in range(rounds):
        if i%2:
            n=timed(new,request,iterations);o=timed(old,request,iterations)
        else:
            o=timed(old,request,iterations);n=timed(new,request,iterations)
        pairs.append({'old_ns':o,'new_ns':n,'reduction_percent':(1-n/o)*100})
    changes=[p['reduction_percent'] for p in pairs]
    return {'middleware_count':count,'rounds':rounds,'iterations_per_trial':iterations,
            'old_median_ns':round(statistics.median(p['old_ns'] for p in pairs),1),
            'new_median_ns':round(statistics.median(p['new_ns'] for p in pairs),1),
            'median_paired_reduction_percent':round(statistics.median(changes),2),
            'min_paired_reduction_percent':round(min(changes),2),
            'max_paired_reduction_percent':round(max(changes),2)}

if __name__=='__main__':print(json.dumps([compare(n) for n in (0,1,5,10)],indent=2))
