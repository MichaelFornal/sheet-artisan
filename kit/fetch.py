"""Polite, resumable HTTP for data pipes. Standard library only.

    f = Fetcher("data/cache", user_agent="my-pipe/0.1 (+https://github.com/me/my-pipe)")
    r = f.get("https://example.org/api/items", params={"page": 2})
    r.status, r.json(), r.fetched_at, r.from_cache

What it guarantees:
- Every response that is a final answer (2xx, 404, 410) is cached on disk, keyed by method + URL +
  body. Re-running a crawl replays the cache, so a crawl that dies at hour 5 resumes at hour 5.
  `fetched_at` is the time of the ORIGINAL fetch, which is what provenance columns want.
- robots.txt is honoured (RFC 9309: 4xx = allow all, 5xx/unreachable = disallow all), including a
  fractional Crawl-delay. There is deliberately no switch to turn this off.
- One request per `1/rate` seconds per host. 429/503 honour Retry-After; a 429 doubles the host's
  interval and every success decays it back toward the base (a penalty that never decays turns
  one bad minute into a permanently slow crawl).
- `offline=True` serves only from cache and raises CacheMiss otherwise (for rebuilding sheets
  without touching the network). `fresh=True` bypasses the cache without overwriting it (for
  live spot-checks).
"""
from __future__ import annotations

import email.utils
import hashlib
import http.client
import json as _json
import os
import random
import re
import socket
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
import urllib.robotparser
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

CACHEABLE = {404, 410}
RETRYABLE = {408, 425, 429, 500, 502, 503, 504}


class FetchError(Exception):
    pass


class RobotsDisallowed(FetchError):
    pass


class CacheMiss(FetchError):
    pass


def _now_iso():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


@dataclass
class Response:
    url: str
    status: int
    headers: dict
    body: bytes
    fetched_at: str
    from_cache: bool = False

    @property
    def ok(self):
        return 200 <= self.status < 300

    @property
    def text(self):
        m = re.search(r"charset=([\w-]+)", self.headers.get("Content-Type", "") or "", re.I)
        return self.body.decode(m.group(1) if m else "utf-8", errors="replace")

    def json(self):
        return _json.loads(self.text)


@dataclass
class _Host:
    base: float
    interval: float = 0.0
    next_at: float = 0.0
    lock: threading.Lock = field(default_factory=threading.Lock)
    robots_lock: threading.Lock = field(default_factory=threading.Lock)
    robots: object = None  # RobotFileParser, or "allow" / "deny"
    crawl_delay: float = 0.0

    def __post_init__(self):
        self.interval = self.base

    def reserve(self):
        """Claim the next request slot; return how long to sleep before using it."""
        with self.lock:
            now = time.monotonic()
            slot = max(now, self.next_at)
            self.next_at = slot + self.interval
            return slot - now

    def hold(self, seconds):
        with self.lock:
            self.next_at = max(self.next_at, time.monotonic() + seconds)

    def penalize(self, max_interval):
        with self.lock:
            self.interval = min(max(self.interval * 2, self.base * 2), max_interval)

    def reward(self, decay):
        with self.lock:
            self.interval = max(self.base, self.interval * decay)

    def set_floor(self, seconds):
        with self.lock:
            self.base = max(self.base, seconds)
            self.interval = max(self.interval, self.base)


def _parse_crawl_delay(text, ua):
    """Python's robotparser drops fractional Crawl-delay values; read them ourselves."""
    token = ua.split("/")[0].strip().lower()
    groups, agents, in_rules = {}, [], False
    for raw in text.splitlines():
        line = raw.split("#", 1)[0].strip()
        if ":" not in line:
            continue
        k, v = (p.strip() for p in line.split(":", 1))
        k = k.lower()
        if k == "user-agent":
            if in_rules:
                agents, in_rules = [], False
            agents.append(v.lower())
        else:
            in_rules = True
            if k == "crawl-delay":
                try:
                    d = float(v)
                except ValueError:
                    continue
                for a in agents:
                    groups[a] = d
    for a, d in groups.items():
        if a != "*" and a in token:
            return d
    return groups.get("*", 0.0)


class Fetcher:
    def __init__(self, cache_dir, user_agent, rate=1.0, max_retries=6, timeout=30,
                 base_backoff=2.0, max_backoff=300.0, max_retry_after=900.0,
                 max_interval=60.0, decay=0.95, offline=False):
        if not user_agent:
            raise ValueError("an identifying user_agent is required")
        self.cache_dir = Path(cache_dir)
        self.user_agent = user_agent
        self.base_interval = 1.0 / rate
        self.max_retries = max_retries
        self.timeout = timeout
        self.base_backoff = base_backoff
        self.max_backoff = max_backoff
        self.max_retry_after = max_retry_after
        self.max_interval = max_interval
        self.decay = decay
        self.offline = offline
        self.stats = {"requests": 0, "cache_hits": 0, "retries": 0, "errors": 0,
                      "robots_blocked": 0, "bytes": 0}
        self._hosts = {}
        self._hosts_lock = threading.Lock()
        self._stats_lock = threading.Lock()

    # ---- public API -------------------------------------------------------------------------
    def get(self, url, params=None, headers=None, fresh=False):
        return self.request("GET", url, params=params, headers=headers, fresh=fresh)

    def post(self, url, data=None, json_body=None, params=None, headers=None, fresh=False):
        headers = dict(headers or {})
        if json_body is not None:
            data = _json.dumps(json_body, sort_keys=True).encode()
            headers.setdefault("Content-Type", "application/json")
        elif isinstance(data, dict):
            data = urllib.parse.urlencode(data).encode()
            headers.setdefault("Content-Type", "application/x-www-form-urlencoded")
        elif isinstance(data, str):
            data = data.encode()
        return self.request("POST", url, params=params, headers=headers, body=data, fresh=fresh)

    def get_json(self, url, params=None, headers=None):
        r = self.get(url, params=params, headers=headers)
        if not r.ok:
            raise FetchError(f"{r.status} from {r.url}")
        return r.json()

    def request(self, method, url, params=None, headers=None, body=None, fresh=False):
        if params:
            sep = "&" if urllib.parse.urlparse(url).query else "?"
            url = url + sep + urllib.parse.urlencode(params, doseq=True)
        key = self._key(method, url, body)
        if not fresh:
            cached = self._cache_read(key)
            if cached is not None:
                self._bump("cache_hits")
                return cached
        if self.offline:
            raise CacheMiss(f"offline and not cached: {method} {url}")
        self._check_robots(url)
        resp = self._with_retries(method, url, headers, body)
        if not fresh and (resp.ok or resp.status in CACHEABLE):
            self._cache_write(key, method, resp)
        return resp

    # ---- internals ----------------------------------------------------------------------------
    def _host(self, url):
        p = urllib.parse.urlparse(url)
        k = f"{p.scheme}://{p.netloc}"
        with self._hosts_lock:
            if k not in self._hosts:
                self._hosts[k] = _Host(self.base_interval)
            return self._hosts[k]

    def _bump(self, name, n=1):
        with self._stats_lock:
            self.stats[name] += n

    def _key(self, method, url, body):
        h = hashlib.sha256()
        h.update(method.upper().encode() + b"\n" + url.encode() + b"\n")
        h.update(body or b"")
        return h.hexdigest()

    def _paths(self, key):
        d = self.cache_dir / key[:2]
        return d / f"{key}.json", d / f"{key}.bin"

    def _cache_read(self, key):
        meta_p, body_p = self._paths(key)
        if not meta_p.exists():
            return None
        try:
            meta = _json.loads(meta_p.read_text())
            body = body_p.read_bytes()
        except (OSError, ValueError):
            return None
        return Response(meta["url"], meta["status"], meta["headers"], body, meta["fetched_at"], True)

    def _cache_write(self, key, method, resp):
        meta_p, body_p = self._paths(key)
        meta_p.parent.mkdir(parents=True, exist_ok=True)
        for path, payload in ((body_p, resp.body), (meta_p, _json.dumps({
                "method": method, "url": resp.url, "status": resp.status,
                "headers": resp.headers, "fetched_at": resp.fetched_at}).encode())):
            tmp = path.with_suffix(path.suffix + f".tmp{os.getpid()}.{threading.get_ident()}")
            tmp.write_bytes(payload)
            os.replace(tmp, path)  # body first, meta last: a meta file means a complete entry

    def _check_robots(self, url):
        host = self._host(url)
        with host.robots_lock:
            if host.robots is None:
                p = urllib.parse.urlparse(url)
                robots_url = f"{p.scheme}://{p.netloc}/robots.txt"
                try:
                    r = self._with_retries("GET", robots_url, None, None, give_up_quietly=True)
                except FetchError:
                    r = None
                if r is None or r.status >= 500:
                    host.robots = "deny"
                elif r.status >= 400:
                    host.robots = "allow"
                else:
                    rp = urllib.robotparser.RobotFileParser()
                    rp.parse(r.text.splitlines())
                    host.robots = rp
                    delay = _parse_crawl_delay(r.text, self.user_agent)
                    if delay:
                        host.crawl_delay = delay
                        host.set_floor(delay)
        if host.robots == "allow":
            return
        if host.robots == "deny" or not host.robots.can_fetch(self.user_agent, url):
            self._bump("robots_blocked")
            raise RobotsDisallowed(f"robots.txt disallows {url}")

    def _retry_after(self, headers):
        v = (headers.get("Retry-After") or headers.get("retry-after") or "").strip()
        if not v:
            return None
        if re.fullmatch(r"\d+(\.\d+)?", v):
            return float(v)
        try:
            when = email.utils.parsedate_to_datetime(v)
            return max(0.0, (when - datetime.now(timezone.utc)).total_seconds())
        except (TypeError, ValueError):
            return None

    def _once(self, method, url, headers, body):
        host = self._host(url)
        wait = host.reserve()
        if wait > 0:
            time.sleep(wait)
        h = {"User-Agent": self.user_agent, "Accept": "*/*", **(headers or {})}
        req = urllib.request.Request(url, data=body, headers=h, method=method)
        self._bump("requests")
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                payload = resp.read()
                status, rheaders, final = resp.status, dict(resp.headers.items()), resp.geturl()
        except urllib.error.HTTPError as e:
            try:
                payload = e.read()
            except Exception:
                payload = b""
            status, rheaders, final = e.code, dict(e.headers.items()) if e.headers else {}, url
        self._bump("bytes", len(payload))
        return Response(final, status, rheaders, payload, _now_iso())

    def _with_retries(self, method, url, headers, body, give_up_quietly=False):
        host = self._host(url)
        last = None
        for attempt in range(self.max_retries + 1):
            try:
                resp = self._once(method, url, headers, body)
            except (urllib.error.URLError, socket.timeout, ConnectionError,
                    http.client.HTTPException, OSError) as e:
                last, resp = e, None
            if resp is not None and resp.status not in RETRYABLE:
                host.reward(self.decay)
                return resp
            if resp is not None:
                last = resp
            if attempt == self.max_retries:
                break
            self._bump("retries")
            wait = None
            if resp is not None:
                if resp.status == 429:
                    host.penalize(self.max_interval)
                wait = self._retry_after(resp.headers)
                if wait is not None and wait > self.max_retry_after:
                    raise FetchError(f"{url}: server asked us to wait {wait:.0f}s; giving up")
            if wait is None:
                wait = min(self.max_backoff, self.base_backoff * (2 ** attempt))
                wait += random.uniform(0, wait * 0.25)
            host.hold(wait)
        self._bump("errors")
        if give_up_quietly and isinstance(last, Response):
            return last
        detail = f"status {last.status}" if isinstance(last, Response) else repr(last)
        raise FetchError(f"{method} {url} failed after {self.max_retries + 1} attempts ({detail})")
