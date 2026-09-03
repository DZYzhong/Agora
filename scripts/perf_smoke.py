#!/usr/bin/env python3
"""Agora performance smoke: 50 concurrent clients, latency percentiles.

Baseline evidence only — the formal PR5-PERF acceptance (fixed dataset,
30 minutes, no error-rate degradation, §8.1 p95 target) still needs a
dedicated benchmark environment. This runs a short concurrent burst against
the live instance and prints p50/p95/p99 + error count.

Usage: python scripts/perf_smoke.py [url] [clients] [requests]
Defaults: https://127.0.0.1:8443 50 300 (against /ready and /health).
"""

import concurrent.futures
import ssl
import statistics
import sys
import time
import urllib.request

BASE = sys.argv[1] if len(sys.argv) > 1 else "https://127.0.0.1:8443"
# nginx applies 20 r/s (burst 40) on the API location; keep the default burst
# inside that envelope so results reflect latency, not deliberate rate-limit
# 503s. Formal PR5-PERF should bypass the limiter (direct api target) or raise it.
CLIENTS = int(sys.argv[2]) if len(sys.argv) > 2 else 8
TOTAL = int(sys.argv[3]) if len(sys.argv) > 3 else 32
PATH = "/ready"


def _hit(_i: int) -> float:
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    start = time.perf_counter()
    try:
        with urllib.request.urlopen(f"{BASE}{PATH}", timeout=10, context=ctx) as resp:
            assert resp.status == 200
    except Exception as exc:  # count as error, record elapsed
        return time.perf_counter() - start, f"ERR:{type(exc).__name__}"
    return time.perf_counter() - start, None


def run() -> None:
    results: list[float] = []
    errors = 0
    with concurrent.futures.ThreadPoolExecutor(max_workers=CLIENTS) as pool:
        futures = [pool.submit(_hit, i) for i in range(TOTAL)]
        for future in concurrent.futures.as_completed(futures):
            elapsed, error = future.result()
            if error:
                errors += 1
            else:
                results.append(elapsed)
    results.sort()
    def pct(p: float) -> float:
        if not results:
            return float("nan")
        idx = min(len(results) - 1, int(len(results) * p))
        return round(results[idx] * 1000, 2)
    print(
        json_dump(
            {
                "url": f"{BASE}{PATH}",
                "clients": CLIENTS,
                "requests": TOTAL,
                "ok": len(results),
                "errors": errors,
                "p50_ms": pct(0.50),
                "p95_ms": pct(0.95),
                "p99_ms": pct(0.99),
                "mean_ms": round(statistics.mean(results) * 1000, 2) if results else None,
            }
        )
    )


def json_dump(obj) -> str:
    import json

    return json.dumps(obj, indent=2, ensure_ascii=False)


if __name__ == "__main__":
    run()
