"""Small load test with latency percentiles (NFR-101..103), standard library only.

k6 is AGPL-3.0 and autocannon pulls many packages, so this is a plain script: threads send GET
requests for a fixed time and the p50/p95/p99 latencies and the error rate are printed.

    python scripts/perf/load_test.py https://undercut.example /api/v1/seasons/ /drivers \
        --connections 10 --seconds 30

Set INTERNAL_API_TOKEN to send X-Internal-Token (skips the anonymous throttle; only use it against
your own deployment). Exit code 1 when p95 is above --p95-ms or the error rate above --max-errors.
"""

import argparse
import os
import statistics
import sys
import threading
import time
import urllib.error
import urllib.request


def percentile(sorted_ms: list[float], fraction: float) -> float:
    if not sorted_ms:
        return 0.0
    index = min(len(sorted_ms) - 1, max(0, round(fraction * len(sorted_ms)) - 1))
    return sorted_ms[index]


def worker(urls, deadline, headers, results, lock):
    local, errors, i = [], 0, 0
    while time.monotonic() < deadline:
        url = urls[i % len(urls)]
        i += 1
        started = time.perf_counter()
        try:
            request = urllib.request.Request(url, headers=headers)  # noqa: S310
            with urllib.request.urlopen(request, timeout=30) as response:  # noqa: S310
                response.read()
                ok = response.status < 400
        except urllib.error.HTTPError:
            ok = False
        except (urllib.error.URLError, TimeoutError, OSError):
            ok = False
        elapsed = (time.perf_counter() - started) * 1000
        if ok:
            local.append(elapsed)
        else:
            errors += 1
    with lock:
        results["ms"].extend(local)
        results["errors"] += errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("base_url")
    parser.add_argument("paths", nargs="+")
    parser.add_argument("--connections", type=int, default=10)
    parser.add_argument("--seconds", type=int, default=30)
    parser.add_argument("--p95-ms", type=float, default=500.0)
    parser.add_argument("--max-errors", type=float, default=0.01, help="Allowed error fraction.")
    args = parser.parse_args()

    base = args.base_url.rstrip("/")
    urls = [f"{base}{p if p.startswith('/') else '/' + p}" for p in args.paths]
    headers = {"User-Agent": "undercut-load-test", "Accept": "application/json, text/html"}
    token = os.environ.get("INTERNAL_API_TOKEN", "")
    if token:
        headers["X-Internal-Token"] = token

    results = {"ms": [], "errors": 0}
    lock = threading.Lock()
    deadline = time.monotonic() + args.seconds
    threads = [
        threading.Thread(target=worker, args=(urls, deadline, headers, results, lock))
        for _ in range(args.connections)
    ]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    ms = sorted(results["ms"])
    total = len(ms) + results["errors"]
    error_rate = results["errors"] / total if total else 1.0
    print(
        f"requests: {total} in {args.seconds}s ({total / args.seconds:.1f}/s), "
        f"errors: {results['errors']}"
    )
    if ms:
        print(
            f"latency ms: p50 {percentile(ms, 0.5):.0f}  p95 {percentile(ms, 0.95):.0f}  "
            f"p99 {percentile(ms, 0.99):.0f}  max {ms[-1]:.0f}  mean {statistics.fmean(ms):.0f}"
        )
    failed = error_rate > args.max_errors or not ms or percentile(ms, 0.95) > args.p95_ms
    print(
        "FAILED" if failed else "OK",
        f"(p95 limit {args.p95_ms:.0f} ms, error rate {error_rate:.2%})",
    )
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
