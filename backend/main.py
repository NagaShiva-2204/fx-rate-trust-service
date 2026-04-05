from __future__ import annotations

from datetime import datetime, timezone
import asyncio
from statistics import median
from typing import Dict, List, Optional, Tuple

import httpx
from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="Real-Time Data Aggregation Service")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


DEFAULT_BASE = "USD"
DEFAULT_SYMBOLS = ["EUR", "GBP", "INR", "JPY", "AUD", "CAD"]
CACHE_TTL_SECONDS = 120
SOURCE_TIMEOUT = 4.0


class Cache:
    def __init__(self) -> None:
        self.payload: Optional[dict] = None
        self.saved_at: Optional[datetime] = None

    def get(self) -> Optional[dict]:
        if not self.payload or not self.saved_at:
            return None
        age = (datetime.now(timezone.utc) - self.saved_at).total_seconds()
        if age > CACHE_TTL_SECONDS:
            return None
        return self.payload

    def set(self, payload: dict) -> None:
        self.payload = payload
        self.saved_at = datetime.now(timezone.utc)


cache = Cache()


def parse_date_only(date_str: str) -> Optional[datetime]:
    try:
        return datetime.strptime(date_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    except ValueError:
        return None


def freshness_label(seconds: Optional[float]) -> str:
    if seconds is None:
        return "unknown"
    if seconds <= 600:
        return "fresh"
    if seconds <= 3600:
        return "acceptable"
    return "stale"


async def fetch_er_api(base: str, symbols: List[str]) -> Tuple[Optional[dict], Optional[str]]:
    url = f"https://open.er-api.com/v6/latest/{base}"
    try:
        async with httpx.AsyncClient(timeout=SOURCE_TIMEOUT) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            data = resp.json()
        if data.get("result") != "success":
            return None, "ER-API returned non-success result"
        rates = {k: v for k, v in data.get("rates", {}).items() if k in symbols}
        as_of = None
        if "time_last_update_unix" in data:
            as_of = datetime.fromtimestamp(data["time_last_update_unix"], tz=timezone.utc)
        return {
            "source": "open.er-api.com",
            "rates": rates,
            "as_of": as_of,
        }, None
    except Exception as exc:
        return None, f"ER-API error: {exc}"


async def fetch_exchangerate_host(base: str, symbols: List[str]) -> Tuple[Optional[dict], Optional[str]]:
    symbols_param = ",".join(symbols)
    url = f"https://api.exchangerate.host/latest?base={base}&symbols={symbols_param}"
    try:
        async with httpx.AsyncClient(timeout=SOURCE_TIMEOUT) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            data = resp.json()
        rates = {k: v for k, v in data.get("rates", {}).items() if k in symbols}
        as_of = parse_date_only(data.get("date", ""))
        return {
            "source": "exchangerate.host",
            "rates": rates,
            "as_of": as_of,
        }, None
    except Exception as exc:
        return None, f"exchangerate.host error: {exc}"


async def fetch_frankfurter(base: str, symbols: List[str]) -> Tuple[Optional[dict], Optional[str]]:
    symbols_param = ",".join(symbols)
    url = f"https://api.frankfurter.dev/v1/latest?from={base}&to={symbols_param}"
    try:
        async with httpx.AsyncClient(timeout=SOURCE_TIMEOUT) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            data = resp.json()
        rates = {k: v for k, v in data.get("rates", {}).items() if k in symbols}
        as_of = parse_date_only(data.get("date", ""))
        return {
            "source": "frankfurter.app",
            "rates": rates,
            "as_of": as_of,
        }, None
    except Exception as exc:
        return None, f"frankfurter.app error: {exc}"


def aggregate_rates(sources: List[dict], symbols: List[str]) -> Dict[str, float]:
    aggregated: Dict[str, float] = {}
    for symbol in symbols:
        values = [src["rates"].get(symbol) for src in sources if symbol in src.get("rates", {})]
        values = [v for v in values if isinstance(v, (int, float))]
        if not values:
            continue
        aggregated[symbol] = float(median(values))
    return aggregated


def best_as_of(sources: List[dict]) -> Optional[datetime]:
    dates = [src.get("as_of") for src in sources if isinstance(src.get("as_of"), datetime)]
    if not dates:
        return None
    return max(dates)


@app.get("/api/rates")
async def get_rates(
    base: str = Query(DEFAULT_BASE, min_length=3, max_length=3),
    symbols: str = Query(",".join(DEFAULT_SYMBOLS)),
):
    base = base.upper()
    symbols_list = [s.strip().upper() for s in symbols.split(",") if s.strip()]
    if not symbols_list:
        symbols_list = DEFAULT_SYMBOLS

    tasks = [
        fetch_er_api(base, symbols_list),
        fetch_exchangerate_host(base, symbols_list),
        fetch_frankfurter(base, symbols_list),
    ]

    source_payloads: List[dict] = []
    errors: List[str] = []

    results = await asyncio.gather(*tasks, return_exceptions=False)
    for payload, err in results:
        if payload:
            source_payloads.append(payload)
        if err:
            errors.append(err)

    if not source_payloads:
        cached = cache.get()
        if cached:
            cached_copy = dict(cached)
            cached_copy["warnings"] = list(cached.get("warnings", []))
            cached_copy["warnings"].append("All sources failed; serving cached data.")
            return cached_copy
        return {
            "base": base,
            "rates": {},
            "as_of": None,
            "fetched_at": datetime.now(timezone.utc).isoformat(),
            "freshness": "stale",
            "sources": [],
            "warnings": ["All sources failed; no cached data available."],
            "errors": errors,
        }

    aggregated_rates = aggregate_rates(source_payloads, symbols_list)
    as_of = best_as_of(source_payloads)
    fetched_at = datetime.now(timezone.utc)
    staleness_seconds = None
    warnings: List[str] = []
    if as_of:
        staleness_seconds = (fetched_at - as_of).total_seconds()
        if staleness_seconds > 86400:
            warnings.append(
                "Upstream timestamps are over 24 hours old; showing fetch time instead."
            )
            as_of = fetched_at
            staleness_seconds = 0.0

    payload = {
        "base": base,
        "rates": aggregated_rates,
        "as_of": as_of.isoformat() if as_of else None,
        "fetched_at": fetched_at.isoformat(),
        "freshness": freshness_label(staleness_seconds),
        "staleness_seconds": staleness_seconds,
        "sources": [src["source"] for src in source_payloads],
        "warnings": warnings,
        "errors": errors,
    }

    cache.set(payload)
    return payload
