"""Small synthetic hash-workload probe; run in a constrained hosting image."""
import json
import os
from pathlib import Path
import sys
import time
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ['DATABASE_URL'] = 'sqlite:///:memory:'
from nova.security import hash_password, verify_password


def probe(index):
    password = f'Synthetic-budget-probe-{index}'
    started = time.monotonic()
    encoded = hash_password(password)
    assert encoded.startswith('scrypt-v2$') and verify_password(password, encoded)
    return round(time.monotonic() - started, 3)


if __name__ == '__main__':
    started = time.monotonic()
    with ThreadPoolExecutor(max_workers=4) as pool:
        durations = list(pool.map(probe, range(4)))
    print(json.dumps({'synthetic_only': True, 'concurrent_workers': 4,
                      'hash_and_verify_seconds': durations,
                      'elapsed_seconds': round(time.monotonic() - started, 3)}))
