# Verification report — 17 October 2026

Environment: Linux x86_64, CPython 3.13.5. Benchmarks ran locally with an identical SlowAPI application and fresh TCP connection per HTTP request. Figures are a snapshot, not platform-neutral guarantees.

## Automated tests

`python -m unittest discover -s tests -q`

**44 / 44 passed** (existing tests plus new protocol regression tests).

## Routing comparison

`python benchmarks/benchmark_router.py`

- 1,000 static paths; 30,000 lookups per trial; median of 5 trials.
- Linear route scan: **14,084 ns / lookup**.
- Indexed router: **172 ns / lookup**.
- Measured lookup reduction: **98.8%** vs this intentionally linear baseline.
- This benchmark does **not** establish end-to-end HTTP latency, universal O(1) for parameter routes, or third-party-framework superiority.

## End-to-end HTTP comparison

`python benchmarks/benchmark_http.py`

| Clients | Server | Median response latency | Throughput |
|---:|---|---:|---:|
| 1 | WSGI dev server (`wsgiref`) | 0.223 ms | 3,626.9 req/s |
| 1 | Native threaded server | 0.375 ms | 2,396.3 req/s |
| 4 | WSGI dev server (`wsgiref`) | 1.327 ms | 2,890.0 req/s |
| 4 | Native threaded server | 1.871 ms | 2,064.5 req/s |

**Outcome:** Native server is slower for this workload. Requested 20% lower HTTP latency and 15% higher HTTP throughput **not achieved** against this stated baseline. Sub-15-ms latency is observed in these small local tests, but does not establish a general service-level guarantee.

## Middleware dispatch costs

`python benchmarks/benchmark_middleware.py`

- 0 middleware functions: 716.9 ns/dispatch (reference)
- 1 no-op middleware: 793.8 ns/dispatch (**+10.73%**)
- 5 no-op middleware: 975.0 ns/dispatch (**+36.0%**)
- 10 no-op middleware: 1235.9 ns/dispatch (**+72.39%**)

**Outcome:** Current overhead is measured. A **10% reduction relative to earlier middleware** has not been demonstrated because a matched previous-version baseline is not included.

## Repetitive code reduction

**30% reduction: not established.** Quantifying duplicated application code requires a defined and preserved before/after implementation of the same workflows, a line-counting protocol, and a scope of files. Inventing an arbitrary baseline would not support the claim.

## HTTP/1.1 conformance statement

Implemented and integration-tested: strict CRLF framing, Host validation, request-line token validation, bounded headers/bodies, Content-Length, chunked body decoding and extensions, trailer validation, rejection of conflicting framing, persistent connections, pipelined requests, `100 Continue`, `HEAD` suppression of response body, 204 empty body, and selected protocol error codes (400, 413, 417, 431, 501, 505).

**Not certified as fully compliant with RFC 9110/9112.** This educational origin server omits some protocol features (e.g., HTTP upgrades, support for all transfer-coding chains, broad request-target handling, robust resource exhaustion resistance, and production-level intermediary compatibility). Exhaustive RFC conformance requires an external protocol suite and extensive integration/security hardening.

## Resume mapping

| Resume statement | Evidence status |
|---|---|
| Custom Python backend framework | Implemented |
| Under 15ms | Observed on local benchmark workload only |
| 20% latency reduction | Not achieved |
| 15% throughput increase | Not achieved |
| O(1) dict route lookup | Implemented for exact static routes, not all dynamic routes |
| Submillisecond route resolution | Measured on specified route microbenchmark |
| HTTP/1.1 parser supporting GET/POST/DELETE | Implemented |
| Strict RFC compliance | Not established |
| Configurable middleware | Implemented |
| 30% repetitive code reduction | Not established |
| 10% lower middleware overhead | Not established |
| Template context insertion | Implemented |

**Do not cite the unachieved or unverified percentages as accomplishments.**
