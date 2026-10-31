"""Small process-local cache for scoped, read-only provider observations.

Callers recheck current ownership and connection state on every request. Entries
contain no credentials. Misses are coalesced, failures are never cached, and a
restart simply requires another provider read. Publishing never uses this cache.
"""
from collections import OrderedDict
from concurrent.futures import Future
from copy import deepcopy
import json
from threading import Lock
from time import monotonic

_lock = Lock()
_entries = OrderedDict()
_pending = {}
_generation = 0
MAX_ENTRIES = 64
MAX_ENTRY_BYTES = 128 * 1024


def load(key, reader, *, refresh=False, ttl=60):
    now = monotonic()
    with _lock:
        for expired in [entry for entry, value in _entries.items() if now >= value[0]]:
            _entries.pop(expired, None)
        generation = _generation
        cached = _entries.get(key)
        if not refresh and cached and now < cached[0]:
            _entries.move_to_end(key)
            return deepcopy(cached[1])
        pending = _pending.get(key)
        owner = pending is None
        if owner:
            pending = Future()
            _pending[key] = pending
    if not owner:
        return deepcopy(pending.result())
    try:
        value = reader()
        size = len(json.dumps(value).encode('utf-8'))
        with _lock:
            if generation == _generation and size <= MAX_ENTRY_BYTES:
                _entries[key] = (monotonic() + ttl, deepcopy(value))
                _entries.move_to_end(key)
                while len(_entries) > MAX_ENTRIES:
                    _entries.popitem(last=False)
        pending.set_result(value)
        return deepcopy(value)
    except BaseException as error:
        pending.set_exception(error)
        raise
    finally:
        with _lock:
            _pending.pop(key, None)


def clear():
    """Drop retained observations, including in isolated test setup."""
    global _generation
    with _lock:
        _generation += 1
        _entries.clear()
