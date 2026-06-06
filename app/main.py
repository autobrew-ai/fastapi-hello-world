"""Minimal FastAPI app for the Autobrew → Railway deploy demo.

Endpoints:
  GET  /            — hello message + whether a cache is wired in
  GET  /healthz     — liveness check; ALWAYS available, no external dependency,
                      so the platform healthcheck passes the moment the app boots
  GET  /cache/{key} — read a key from Redis (demonstrates the injected REDIS_URL)
  PUT  /cache/{key} — write a key to Redis

The Redis connection is made **lazily**, per request — so a missing or
unreachable cache never blocks startup or the healthcheck. `REDIS_URL` is
injected by the deployment engine as a Railway reference variable
(`${{redis.REDIS_URL}}`); locally it is simply absent and the cache endpoints
return 503.
"""

from __future__ import annotations

import os

from fastapi import FastAPI, HTTPException

app = FastAPI(title="autobrew-fastapi-hello-world")

REDIS_URL = os.environ.get("REDIS_URL")


@app.get("/")
def root() -> dict:
    return {
        "message": "Hello from Autobrew on Railway",
        "cache_configured": REDIS_URL is not None,
    }


@app.get("/healthz")
def healthz() -> dict:
    """Liveness probe. Intentionally dependency-free so the deploy is healthy
    as soon as the process is up, regardless of the cache's state."""
    return {"status": "ok"}


def _redis_client():
    """Build a Redis client on demand. Imported lazily so the app starts even
    if `redis` or the cache is unavailable."""
    if not REDIS_URL:
        raise HTTPException(status_code=503, detail="REDIS_URL is not configured")
    import redis  # lazy: never touched at startup

    return redis.from_url(
        REDIS_URL, decode_responses=True, socket_connect_timeout=2
    )


@app.get("/cache/{key}")
def cache_get(key: str) -> dict:
    client = _redis_client()
    try:
        return {"key": key, "value": client.get(key)}
    except Exception as exc:  # never crash the process on a cache hiccup
        raise HTTPException(status_code=503, detail=f"cache unavailable: {exc}")


@app.put("/cache/{key}")
def cache_set(key: str, value: str) -> dict:
    client = _redis_client()
    try:
        client.set(key, value)
        return {"key": key, "value": value, "stored": True}
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"cache unavailable: {exc}")
