"""Small HTTP latency/throughput benchmark for LG3D API endpoints."""

import argparse
import asyncio
import json
import math
import statistics
import time
from typing import Optional

import httpx


def _percentile(values: list[float], percentile: float) -> Optional[float]:
    if not values:
        return None
    rank = max(0, math.ceil(percentile * len(values)) - 1)
    return sorted(values)[rank]


async def _request(
    client: httpx.AsyncClient,
    url: str,
    semaphore: asyncio.Semaphore,
) -> tuple[Optional[float], Optional[str]]:
    async with semaphore:
        started = time.perf_counter()
        try:
            response = await client.get(url)
            response.raise_for_status()
            await response.aread()
        except (httpx.HTTPError, TimeoutError) as error:
            return None, f"{type(error).__name__}: {error}"
        return (time.perf_counter() - started) * 1000, None


async def benchmark(
    url: str,
    request_count: int,
    concurrency: int,
    timeout: float,
    warmup: int,
) -> dict:
    limits = httpx.Limits(
        max_connections=concurrency,
        max_keepalive_connections=concurrency,
    )
    client_timeout = httpx.Timeout(timeout)
    semaphore = asyncio.Semaphore(concurrency)

    async with httpx.AsyncClient(timeout=client_timeout, limits=limits) as client:
        for _ in range(warmup):
            try:
                response = await client.get(url)
                await response.aread()
            except httpx.HTTPError:
                pass

        started = time.perf_counter()
        results = await asyncio.gather(*(
            _request(client, url, semaphore) for _ in range(request_count)
        ))
        elapsed = time.perf_counter() - started

    latencies = [latency for latency, error in results if latency is not None]
    errors = [error for latency, error in results if error is not None]
    return {
        "url": url,
        "requests": request_count,
        "concurrency": concurrency,
        "success": len(latencies),
        "failed": len(errors),
        "elapsed_s": round(elapsed, 3),
        "requests_per_s": round(len(latencies) / elapsed, 2),
        "latency_ms": {
            "min": round(min(latencies), 3) if latencies else None,
            "mean": round(statistics.fmean(latencies), 3) if latencies else None,
            "p50": round(statistics.median(latencies), 3) if latencies else None,
            "p95": round(_percentile(latencies, 0.95), 3) if latencies else None,
            "p99": round(_percentile(latencies, 0.99), 3) if latencies else None,
            "max": round(max(latencies), 3) if latencies else None,
        },
        "sample_errors": errors[:3],
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("urls", nargs="+", help="One or more GET endpoint URLs")
    parser.add_argument("-n", "--requests", type=int, default=200)
    parser.add_argument("-c", "--concurrency", type=int, default=20)
    parser.add_argument("--timeout", type=float, default=5.0)
    parser.add_argument("--warmup", type=int, default=5)
    args = parser.parse_args()
    if args.requests < 1 or args.concurrency < 1 or args.warmup < 0:
        parser.error("requests/concurrency must be positive and warmup non-negative")
    return args


async def main() -> None:
    args = parse_args()
    for url in args.urls:
        result = await benchmark(
            url,
            request_count=args.requests,
            concurrency=args.concurrency,
            timeout=args.timeout,
            warmup=args.warmup,
        )
        print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    asyncio.run(main())
