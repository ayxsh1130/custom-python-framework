"""Compare indexed routing against a deliberately simple linear scan baseline.

Run: python benchmarks/benchmark_router.py
Results depend on CPU, Python version, URL shape, and number of routes.
This is NOT a comparison against third-party WSGI frameworks.
"""
import sys
import statistics
import time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from main import Router

def run(count=1000, iterations=30000):
    patterns = [f'/api/resource{i}' for i in range(count)]
    router = Router()
    for path in patterns: router.add(path, 'GET', lambda *_: None)
    target = patterns[-1]
    def linear():
        for path in patterns:
            if path == target: return path
    def indexed(): return router.resolve(target, 'GET')
    def measure(fn):
        timings=[]
        for _ in range(5):
            start=time.perf_counter_ns()
            for _ in range(iterations): fn()
            timings.append((time.perf_counter_ns()-start)/iterations)
        return statistics.median(timings)
    old, new = measure(linear), measure(indexed)
    print(f'Routes: {count}; iterations: {iterations}; per-lookup nanoseconds (median of five runs)')
    print(f'Linear scan: {old:.0f}; indexed trie: {new:.0f}; reduction: {(1-new/old)*100:.1f}%')
    print('NOTE: These are microbenchmarks, not HTTP request latency or throughput.')
if __name__=='__main__': run()
