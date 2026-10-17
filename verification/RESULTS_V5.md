# V5 verification (2026-10-17)

This release uses **v4's `main.py`** as the controlled baseline for local dispatch measurements. The baseline is bundled at `verification/baseline_v4/main.py`. Benchmark `benchmarks/compare_versions.py` loads both implementations within one Python process and alternates test order; no external services are needed.

## Functionality

- **52/52 automated unit and socket-level tests passed** (`python -m unittest discover -s tests -v`).
- Added bounds for request targets and validation of malformed Host values.
- Fixed native-server connection cap: the 100th request advertises `Connection: close`.
- Preserved chunked messages, keep-alive, request pipelining, HEAD, 100 Continue and request-framing validation.

## Local paired dispatch benchmark

`python benchmarks/compare_versions.py` (12 alternating pairs × 50,000 dispatches each; 2026-10-17):

| No-op middleware count | Baseline median ns | v5 median ns | Median paired reduction |
|---|---:|---:|---:|
| 0 | 730.1 | 723.8 | 1.48% |
| 1 | 762.0 | 747.6 | 2.65% |
| 5 | 977.8 | 857.0 | 10.57% |
| 10 | 1161.5 | 932.1 | 19.62% |

**Interpretation:** The five-middleware dispatch microbenchmark crossed a 10% reduction in this run; the one-middleware scenario did not. Results depend on the runtime, CPU and load. This measures overall dispatch time with no-op middleware, **not isolated middleware execution overhead**, and it must not be presented as a universal 10% overhead reduction.

## Code reduction

`python benchmarks/measure_code.py` compares `main.py` between equivalent v4/v5 implementations. Statement-start lines increased from **159 to 162**, or **1.89%**; there is **no demonstrated 30% repetitive-code reduction**. Total LOC cannot establish duplicated-code reduction by itself.

## Local HTTP benchmark

`python benchmarks/benchmark_http.py` in this environment, fresh connections per request:

| Clients | wsgiref median ms | Native median ms | wsgiref req/s | Native req/s |
|---|---:|---:|---:|---:|
| 1 | 0.231 | 0.330 | 3706.4 | 2796.7 |
| 4 | 1.209 | 1.707 | 2915.1 | 2152.6 |

The user's previous Windows run showed **native faster** than `wsgiref` on their machine. These runs are not equivalent environments; don't combine or cherry-pick them into universal results. The native server is slower in this run.

## HTTP/1.1 compliance boundary

The parser/server implement a **strictly bounded HTTP/1.1 origin-server subset**, with regression tests. This is not a certificate of full RFC 9110/9112 conformance. Areas not fully supported/tested include upgrade/tunneling, proxy absolute/authority target forms, comprehensive Host/URI normalization, transfer codings beyond chunked, all informational responses, and fuzz-based/adversarial protocol conformance. Never describe this implementation as universally or fully RFC compliant.

## Resume claim guidance

Supported: built a custom Python web framework, static dictionary routing and dynamic trie routing, tested a native HTTP/1.1 origin server, middleware, rendering, 52 tests, and benchmark methodology.

Not proven: general 20% latency / 15% throughput improvements, fully compliant HTTP/1.1, 30% code-duplication reduction, or 10% isolated middleware-overhead reduction.
