import gzip
import json
import tempfile
import time
import unittest
import zlib

from kit.fetch import CacheMiss, Fetcher, FetchError, RobotsDisallowed
from tests._server import ROBOTS_ALLOW_ALL, FixtureServer, ok


def fetcher(tmp, **kw):
    kw.setdefault("rate", 50.0)
    kw.setdefault("base_backoff", 0.05)
    return Fetcher(tmp, user_agent="sa-test/0.1", **kw)


class FetchTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()

    def test_cache_hit_second_call_does_not_touch_server(self):
        with FixtureServer({"/robots.txt": ROBOTS_ALLOW_ALL, "/ok": ok({"a": 1})}) as s:
            f = fetcher(self.tmp)
            r1 = f.get(s.url("/ok"))
            r2 = f.get(s.url("/ok"))
            self.assertEqual(s.hits["/ok"], 1)
            self.assertFalse(r1.from_cache)
            self.assertTrue(r2.from_cache)
            self.assertEqual(r2.json(), {"a": 1})
            self.assertEqual(r1.fetched_at, r2.fetched_at)  # provenance is the original fetch time

    def test_cache_survives_a_new_fetcher(self):
        with FixtureServer({"/robots.txt": ROBOTS_ALLOW_ALL, "/ok": ok("x")}) as s:
            fetcher(self.tmp).get(s.url("/ok"))
            r = fetcher(self.tmp).get(s.url("/ok"))
            self.assertTrue(r.from_cache)
            self.assertEqual(s.hits["/ok"], 1)

    def test_params_and_post_bodies_are_part_of_the_key(self):
        routes = {"/robots.txt": ROBOTS_ALLOW_ALL, "/q": ok("q"), "/p": ok("p")}
        with FixtureServer(routes) as s:
            f = fetcher(self.tmp)
            f.get(s.url("/q"), params={"page": 1})
            f.get(s.url("/q"), params={"page": 2})
            f.get(s.url("/q"), params={"page": 1})
            self.assertEqual(s.hits["/q"], 2)
            f.post(s.url("/p"), json_body={"a": 1})
            f.post(s.url("/p"), json_body={"a": 2})
            f.post(s.url("/p"), json_body={"a": 1})
            self.assertEqual(s.hits["/p"], 2)

    def test_fresh_bypasses_cache_without_overwriting_it(self):
        routes = {"/robots.txt": ROBOTS_ALLOW_ALL,
                  "/v": lambda m, q, b, n: (200, {}, f"v{n}")}
        with FixtureServer(routes) as s:
            f = fetcher(self.tmp)
            self.assertEqual(f.get(s.url("/v")).text, "v1")
            self.assertEqual(f.get(s.url("/v"), fresh=True).text, "v2")
            self.assertEqual(f.get(s.url("/v")).text, "v1")

    def test_robots_disallow_raises_and_never_requests_the_page(self):
        robots = ok("User-agent: *\nDisallow: /private\n")
        with FixtureServer({"/robots.txt": robots, "/private": ok("secret")}) as s:
            f = fetcher(self.tmp)
            with self.assertRaises(RobotsDisallowed):
                f.get(s.url("/private"))
            self.assertEqual(s.hits["/private"], 0)
            self.assertEqual(f.stats["robots_blocked"], 1)

    def test_robots_404_allows_everything(self):
        with FixtureServer({"/ok": ok("x")}) as s:  # no robots route -> 404
            self.assertEqual(fetcher(self.tmp).get(s.url("/ok")).status, 200)

    def test_robots_5xx_disallows_everything(self):
        routes = {"/robots.txt": ok("down", status=500), "/ok": ok("x")}
        with FixtureServer(routes) as s:
            with self.assertRaises(RobotsDisallowed):
                fetcher(self.tmp, max_retries=1).get(s.url("/ok"))
            self.assertEqual(s.hits["/ok"], 0)

    def test_robots_crawl_delay_slows_the_host(self):
        robots = ok("User-agent: *\nCrawl-delay: 0.3\nDisallow:\n")
        with FixtureServer({"/robots.txt": robots, "/a": ok("a")}) as s:
            f = fetcher(self.tmp)
            t0 = time.monotonic()
            f.get(s.url("/a"), params={"i": 1})
            f.get(s.url("/a"), params={"i": 2})
            f.get(s.url("/a"), params={"i": 3})
            self.assertGreaterEqual(time.monotonic() - t0, 0.55)

    def test_429_honours_retry_after_then_succeeds(self):
        def limited(m, q, b, n):
            return (429, {"Retry-After": "1"}, "slow down") if n == 1 else (200, {}, "fine")
        with FixtureServer({"/robots.txt": ROBOTS_ALLOW_ALL, "/limited": limited}) as s:
            f = fetcher(self.tmp)
            t0 = time.monotonic()
            r = f.get(s.url("/limited"))
            self.assertGreaterEqual(time.monotonic() - t0, 0.95)
            self.assertEqual(r.text, "fine")
            self.assertEqual(f.stats["retries"], 1)

    def test_429_penalty_decays_back_to_base(self):
        def limited(m, q, b, n):
            return (429, {"Retry-After": "0"}, "") if n == 1 else (200, {}, "ok")
        routes = {"/robots.txt": ROBOTS_ALLOW_ALL, "/limited": limited, "/ok": ok("ok")}
        with FixtureServer(routes) as s:
            f = fetcher(self.tmp, rate=100.0)
            f.get(s.url("/limited"))
            host = f._host(s.url("/"))
            self.assertGreater(host.interval, host.base)
            for i in range(40):
                f.get(s.url("/ok"), params={"i": i})
            self.assertAlmostEqual(host.interval, host.base, places=6)

    def test_5xx_is_retried(self):
        def flaky(m, q, b, n):
            return (503, {}, "") if n < 3 else (200, {}, "up")
        with FixtureServer({"/robots.txt": ROBOTS_ALLOW_ALL, "/flaky": flaky}) as s:
            self.assertEqual(fetcher(self.tmp).get(s.url("/flaky")).text, "up")

    def test_gives_up_after_max_retries(self):
        routes = {"/robots.txt": ROBOTS_ALLOW_ALL, "/down": ok("", status=500)}
        with FixtureServer(routes) as s:
            with self.assertRaises(FetchError):
                fetcher(self.tmp, max_retries=2).get(s.url("/down"))
            self.assertEqual(s.hits["/down"], 3)

    def test_404_is_returned_and_cached(self):
        with FixtureServer({"/robots.txt": ROBOTS_ALLOW_ALL}) as s:
            f = fetcher(self.tmp)
            self.assertEqual(f.get(s.url("/gone")).status, 404)
            self.assertTrue(f.get(s.url("/gone")).from_cache)
            self.assertEqual(s.hits["/gone"], 1)

    def test_403_is_returned_not_cached(self):
        routes = {"/robots.txt": ROBOTS_ALLOW_ALL, "/blocked": ok("no", status=403)}
        with FixtureServer(routes) as s:
            f = fetcher(self.tmp)
            self.assertEqual(f.get(s.url("/blocked")).status, 403)
            self.assertFalse(f.get(s.url("/blocked")).from_cache)

    def test_offline_serves_cache_and_refuses_misses(self):
        with FixtureServer({"/robots.txt": ROBOTS_ALLOW_ALL, "/ok": ok("x")}) as s:
            fetcher(self.tmp).get(s.url("/ok"))
            off = fetcher(self.tmp, offline=True)
            self.assertEqual(off.get(s.url("/ok")).text, "x")
            with self.assertRaises(CacheMiss):
                off.get(s.url("/other"))

    def test_rate_limit_spaces_requests(self):
        with FixtureServer({"/robots.txt": ROBOTS_ALLOW_ALL, "/a": ok("a")}) as s:
            f = fetcher(self.tmp, rate=5.0)
            f.get(s.url("/a"), params={"i": 0})  # also pays for robots.txt
            t0 = time.monotonic()
            for i in range(1, 4):
                f.get(s.url("/a"), params={"i": i})
            self.assertGreaterEqual(time.monotonic() - t0, 0.55)

    def test_user_agent_is_sent(self):
        with FixtureServer({"/robots.txt": ROBOTS_ALLOW_ALL, "/ua": ok("x")}) as s:
            fetcher(self.tmp).get(s.url("/ua"))
            self.assertEqual(s.last_headers["/ua"].get("User-Agent"), "sa-test/0.1")

    def test_json_helper(self):
        with FixtureServer({"/robots.txt": ROBOTS_ALLOW_ALL, "/j": ok([1, 2])}) as s:
            self.assertEqual(fetcher(self.tmp).get_json(s.url("/j")), [1, 2])

    def test_gzip_body_is_decoded_even_when_unasked(self):
        # python.org gzips whatever the request says, with lower-case header names.
        body = gzip.compress(json.dumps({"a": 1}).encode())
        headers = {"content-encoding": "gzip", "content-type": "application/json"}
        with FixtureServer({"/robots.txt": ROBOTS_ALLOW_ALL, "/z": ok(body, headers=headers)}) as s:
            f = fetcher(self.tmp)
            self.assertEqual(f.get(s.url("/z")).json(), {"a": 1})
            self.assertEqual(f.get(s.url("/z")).json(), {"a": 1})  # and from the cache
            self.assertEqual(s.hits["/z"], 1)

    def test_deflate_body_is_decoded(self):
        body = zlib.compress(b"plain words")
        routes = {"/robots.txt": ROBOTS_ALLOW_ALL, "/d": ok(body, headers={"Content-Encoding": "deflate"})}
        with FixtureServer(routes) as s:
            self.assertEqual(fetcher(self.tmp).get(s.url("/d")).text, "plain words")

    def test_undecodable_encoding_is_an_error_not_garbage(self):
        routes = {"/robots.txt": ROBOTS_ALLOW_ALL, "/br": ok(b"\x8b\x02\x80", headers={"Content-Encoding": "br"})}
        with FixtureServer(routes) as s:
            with self.assertRaises(FetchError):
                fetcher(self.tmp).get(s.url("/br"))

    def test_asks_for_gzip(self):
        with FixtureServer({"/robots.txt": ROBOTS_ALLOW_ALL, "/g": ok("x")}) as s:
            fetcher(self.tmp).get(s.url("/g"))
            self.assertIn("gzip", s.last_headers["/g"].get("Accept-Encoding", ""))

    def test_header_lookup_ignores_case(self):
        body = "café".encode("latin-1")
        routes = {"/robots.txt": ROBOTS_ALLOW_ALL,
                  "/h": ok(body, headers={"content-type": "text/plain; charset=latin-1"})}
        with FixtureServer(routes) as s:
            f = fetcher(self.tmp)
            for r in (f.get(s.url("/h")), f.get(s.url("/h"))):  # live, then cached
                self.assertEqual(r.headers.get("Content-Type"), "text/plain; charset=latin-1")
                self.assertIn("CONTENT-TYPE", r.headers)
                self.assertEqual(r.text, "café")

    def test_retry_after_in_any_case_is_honoured(self):
        def limited(m, q, b, n):
            return (429, {"RETRY-AFTER": "1"}, "slow down") if n == 1 else (200, {}, "fine")
        with FixtureServer({"/robots.txt": ROBOTS_ALLOW_ALL, "/limited": limited}) as s:
            t0 = time.monotonic()
            self.assertEqual(fetcher(self.tmp).get(s.url("/limited")).text, "fine")
            self.assertGreaterEqual(time.monotonic() - t0, 0.95)


if __name__ == "__main__":
    unittest.main()
