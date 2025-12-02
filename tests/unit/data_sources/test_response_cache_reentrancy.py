from __future__ import annotations

import logging
import threading
import queue
import faulthandler

import pytest

from data_sources.base_api import ResponseCache


pytestmark = pytest.mark.unit


def test_response_cache_set_debug_stats_is_reentrant(caplog):
    # Ensure DEBUG logging path is active for the module logger
    caplog.set_level(logging.DEBUG, logger="data_sources.base_api")

    # Run the body in a worker so we can enforce a timeout and dump stacks if it deadlocks
    result_q: queue.Queue[Exception | None] = queue.Queue()

    def worker():
        try:
            cache = ResponseCache(default_ttl=5, max_size=4)

            # Calling set() at DEBUG will emit a stats() call while holding the cache lock.
            # With RLock, this must not deadlock and should return immediately.
            cache.set("k1", {"v": 1}, ttl=1)

            # Sanity: stats reflect the operation and size is correct
            st = cache.stats()
            assert st["sets"] == 1
            assert st["size"] == 1

            # A quick get to trigger a hit path while DEBUG logging is enabled
            assert cache.get("k1") == {"v": 1}
            st2 = cache.stats()
            assert st2["hits"] >= 1
            result_q.put(None)
        except Exception as e:  # pragma: no cover - only on failures
            result_q.put(e)

    t = threading.Thread(target=worker, daemon=True)
    t.start()
    t.join(timeout=10)
    if t.is_alive():
        faulthandler.dump_traceback()
        pytest.fail("test_response_cache_set_debug_stats_is_reentrant timed out (10s)")
    err = result_q.get()
    if err is not None:
        raise err
