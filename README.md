# SlowAPI | Custom Python Backend Framework

An improved, educational version of the original `SlowAPI` WSGI web framework. The original project was published at https://github.com/ayxsh1130/custom-python-framework. This package is a **source-informed upgrade**, not an exact git patch: network restrictions prevented cloning the source into the build environment. Inspect differences before replacing your repository.

## Implemented features

- WSGI-compatible application dispatch plus a threaded native HTTP/1.1 development server
- Decorator and class-based GET/POST/PUT/DELETE routes
- Trie-indexed path matching with dynamic `{parameter}` segments and static-path precedence
- Global and route-specific middleware; 404, 405 (with Allow header), and safe 500 responses
- Request query/body parsing, JSON/text/HTML responses
- Minimal HTML templates using HTML-escaped `{{ name }}` substitution
- An **integrated HTTP/1.1 request parser** with bounded headers and bodies, Content-Length validation, and explicit rejection of unsupported transfer encodings
- Standard-library `unittest` test suite and repeatable router microbenchmark

## Important technical distinctions

- Trie lookup depends on URL path depth, not the number of registered routes in typical cases. Backtracking can increase work when multiple dynamic paths compete; don't advertise unconditional O(1) route lookup.
- The default native development server uses the custom parser, while `app.run(server="wsgi")` uses the WSGI adapter. Neither is intended for internet-facing production use.
- Not fully RFC 9112 compliant: chunked transfer coding, keep-alive/pipelining and upgrade requests are unsupported; the native server closes connections after each response. Do not claim strict RFC compliance.
- No verified 20% latency reduction, 15% throughput increase, 30% code reduction, or 10% overhead reduction. Benchmark and document these under comparable conditions before claiming them.
- `wsgiref` is for development; this is not a production server.

## Run (Python 3.10+)

```bash
python example.py
```

Try:

```bash
curl http://127.0.0.1:8000/
curl 'http://127.0.0.1:8000/users/42?hello=world'
curl -X POST http://127.0.0.1:8000/echo -H 'Content-Type: application/json' -d '{"message":"hi"}'
```

## Tests and benchmarks

```bash
python -m unittest discover -s tests -v
python benchmarks/benchmark_router.py
python benchmarks/benchmark_http.py
```

## Resume-friendly description (supported by this package)

- Built a WSGI-compatible Python backend framework supporting decorator-based and class-based HTTP routing with dynamic parameters.
- Replaced linear route matching with a segment-trie router, improving route lookup efficiency as the number of registered endpoints grows.
- Implemented global and route-level middleware, structured JSON responses, safe error handling, and escaped HTML template substitution.
- Developed an integrated bounded HTTP/1.1 request parser and automated tests for routing, middleware, error conditions, and message validation.

## Resume-claim audit

| Original resume claim | Evidence in this project | Verdict |
| --- | --- | --- |
| Custom Python web framework | Source code + integration tests | Supported |
| 20% lower request latency / under 15ms | `benchmark_http.py` compares two local development adapters; no comparable external baseline | Not established |
| 15% higher throughput vs standard WSGI | No matched production WSGI benchmark | Not established |
| O(1) dictionary-based dispatch | Segment trie instead of direct dictionary lookup; time depends on path length | Wording needs correction |
| Sub-millisecond route resolution | `benchmark_router.py` measures lookups locally; performance depends on hardware | Conditional, benchmark needed |
| Custom HTTP/1.1 parser | Integrated with native development server, validated in socket-level tests | Supported (subset only) |
| Strict RFC compliance | Missing transfer codings, persistence, other features | Not supported |
| Middleware pipeline | Global + route middleware exercised in tests | Supported |
| 30% less repetitive code / 10% lower overhead | No comparable baseline or formal measurement | Not established |
| Runtime template injection | Escaped placeholder replacement | Supported |

Performance outcomes are empirical, not feature switches. Never advertise unmeasured percentages.

## Recommended accurate resume bullets

- Built a custom Python backend framework with WSGI compatibility and a native HTTP/1.1 development server using a bounded request parser.
- Implemented indexed path routing with dynamic URL parameters, reducing lookup overhead against a linear-route-scan baseline in reproducible microbenchmarks.
- Designed global and route-specific middleware, structured error handling, class-based views, and HTML-escaped template rendering.
- Added automated unit and socket-level integration tests for routing, parsing, request bodies, middleware, and HTTP error responses.

## October 2026 verification update

The framework includes a **native HTTP/1.1 learning server**, accepting `Content-Length` and
`Transfer-Encoding: chunked` bodies, persistent connections, and basic HTTP/1.1 pipelining.
It validates framing and rejects ambiguous `Content-Length`/`Transfer-Encoding` messages.
This is *not* a claim of comprehensive RFC 9110/9112 compliance or production security.

The router now has a dedicated `dict` fast path for exact static paths (average O(1)
lookup for that subset) and a segment trie for dynamic paths (path-length-dependent).
It is inaccurate to claim O(1) resolution for **all** paths.

### Repeatable validation

```bash
python -m unittest discover -s tests -v
python benchmarks/benchmark_router.py
python benchmarks/benchmark_http.py
```

A recorded single local run (Python/environment dependent) reported 24 passing tests.
For 1,000 routes / 30,000 lookups, the routing microbenchmark measured a 98.9%
reduction in lookup time against a linear scan. This is **not** an HTTP end-to-end result.

The HTTP development-server comparison at concurrency 1 measured 0.240 ms median for
`wsgiref` and 0.335 ms for the native implementation, with 3522 vs 2814 requests/second.
At concurrency 4 it reported 1.184 ms vs 1.964 ms and 2943 vs 1885 requests/second.
Runs will differ on other hardware. The native server **did not outperform wsgiref**.

### Resume claim ledger

| Proposed claim | Verification |
|---|---|
| Custom Python framework | Supported |
| O(1) dictionary-based route resolution | Supported **for exact static routes only** |
| Sub-millisecond route resolution | Supported by local router microbenchmark, not a universal guarantee |
| HTTP/1.1 parser | Supported for documented subset, not full RFC compliance |
| Configurable middleware | Supported |
| Template rendering with context insertion | Supported |
| 20% lower request latency / less than 15 ms | **20% improvement not supported** by current HTTP comparison |
| 15% higher HTTP throughput | **Not supported** by current HTTP comparison |
| 30% less repetitive code | **Unmeasured**; requires a defined baseline and LOC methodology |
| 10% lower middleware overhead | **Unmeasured**; requires a matched before/after benchmark |

No measurement was altered to meet a resume target. Treat benchmarks as evidence of their
specific test conditions only.

## v4: parser hardening and independent verification

- Validates `Host` uniqueness, framing conflicts, HTTP token/header syntax, repeated list fields,
  header/body limits, forbidden trailers, and invalid request-target forms.
- Handles `Expect: 100-continue`, request pipelining, common protocol error statuses,
  response-header injection defenses, HEAD response bodies, and no-body status codes.
- Adds a regression suite for problematic wire-format requests and socket-level behavior.
- Adds `benchmarks/benchmark_middleware.py` for dispatch overhead instrumentation.
- See [`verification/RESULTS.md`](verification/RESULTS.md) for the explicit baseline,
  run-specific numerical results, and claims that **remain unsupported**.

**Important:** v4 does not claim full RFC compliance, 20% HTTP latency improvement,
15% increased throughput, 30% less repetitive code, or a 10% reduction in middleware
cost. The provided benchmarks do not substantiate those resume statements.

## V5 verification and reproducibility

This version adds request-target bounds, Host-validation regression coverage, proper connection-cap signaling, and a measured dispatch optimization. Run:

```bash
python -m unittest discover -s tests -v
python benchmarks/compare_versions.py
python benchmarks/measure_code.py
python benchmarks/benchmark_http.py
```

See `verification/RESULTS_V5.md` for the **measured** improvements, known benchmark variability, and the still-unmet original resume targets. The HTTP server is educational, **not an RFC conformance-certified production server**.
