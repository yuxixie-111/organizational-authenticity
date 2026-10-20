"""Polite HTTP with on-disk cache and backoff.

Wayback's CDX server returns 429 quickly if requests are close together.
EDGAR allows a higher rate but blocks a default Python user agent.
Caching means a rerun, or a fix to the parser, does not repeat the crawl.
Failed responses are not cached.
"""

from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path

import requests

from src.constants import USER_AGENT


class PoliteClient:
    def __init__(self, cache_dir: Path, min_interval: float, timeout: float = 90):
        self.cache_dir = cache_dir
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.min_interval = min_interval
        self.timeout = timeout
        self._next_ok = 0.0
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": USER_AGENT,
            "Accept": "text/html,application/json;q=0.9,*/*;q=0.8",
        })

    def _wait(self) -> None:
        delay = self._next_ok - time.time()
        if delay > 0:
            time.sleep(delay)
        self._next_ok = time.time() + self.min_interval

    def get_bytes(self, url: str, params: dict | None = None, use_cache: bool = True) -> bytes:
        key = hashlib.sha1(
            json.dumps({"url": url, "params": params or {}}, sort_keys=True).encode("utf-8")
        ).hexdigest()
        cache_path = self.cache_dir / key
        if use_cache and cache_path.exists() and cache_path.stat().st_size > 0:
            return cache_path.read_bytes()

        last_error = None
        for attempt in range(2):
            self._wait()
            try:
                response = self.session.get(url, params=params, timeout=self.timeout)
            except requests.RequestException as exc:
                last_error = exc
                time.sleep(min(120, 5 * (2 ** attempt)))
                continue
            if response.status_code == 429 or response.status_code >= 500:
                last_error = RuntimeError(f"HTTP {response.status_code} for {response.url}")
                retry_after = response.headers.get("Retry-After")
                if retry_after and str(retry_after).isdigit():
                    pause = int(retry_after)
                else:
                    # Wayback bans get longer if the client keeps poking.
                    pause = 70
                print(f"  backoff {pause}s after HTTP {response.status_code} {str(response.url)[:140]}", flush=True)
                time.sleep(pause)
                self._next_ok = time.time() + self.min_interval
                continue
            if response.status_code == 403 and attempt < 2:
                last_error = RuntimeError(f"HTTP 403 for {response.url}")
                pause = 20 * (attempt + 1)
                print(f"  backoff {pause}s after HTTP 403", flush=True)
                time.sleep(pause)
                self._next_ok = time.time() + self.min_interval
                continue
            if response.status_code != 200:
                raise RuntimeError(f"HTTP {response.status_code} for {url}")
            content = response.content
            if use_cache:
                cache_path.write_bytes(content)
            return content
        raise RuntimeError(f"Gave up on {url}: {last_error}")

    def get_json(self, url: str, params: dict | None = None) -> object:
        raw = self.get_bytes(url, params=params)
        return json.loads(raw.decode("utf-8", errors="replace"))
