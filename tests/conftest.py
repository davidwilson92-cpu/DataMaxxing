"""Every test run owns disposable data; never inherit deployment credentials."""
import os
import tempfile
from pathlib import Path

from urllib.parse import urlsplit

TEST_ROOT = Path(tempfile.mkdtemp(prefix="zova-tests-"))
test_database="sqlite:///" + (TEST_ROOT / "test.db").as_posix()
if os.environ.get('ZOVA_TEST_POSTGRES'):
    test_database=os.environ['ZOVA_TEST_POSTGRES']
    parsed=urlsplit(test_database)
    if parsed.hostname not in {'localhost','127.0.0.1'} or not parsed.path.startswith('/zova_test_'):
        raise RuntimeError('PostgreSQL tests require an explicitly isolated loopback zova_test_ database')
os.environ.update(DATABASE_URL=test_database,
                  UPLOAD_DIR=str(TEST_ROOT / "uploads"), REQUIRE_SUBSCRIPTION="false",
                  PUBLIC_BASE_URL="http://testserver", SESSION_SECRET="test-session-secret",
                  CREDENTIAL_ENCRYPTION_KEY="eV7ZGbkgONCU5t6fVtxgBMvCKx6-4UlAHWVHN2LoflE=")
for key in ("OPENAI_API_KEY", "SMTP_HOST", "STRIPE_SECRET_KEY", "BOOTSTRAP_CREATOR_API_KEY", "S3_BUCKET", "AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY"):
    os.environ.pop(key, None)

import pytest
import httpx

@pytest.fixture(autouse=True)
def block_external_http(monkeypatch):
    """A missing provider mock must fail locally, never make a live request."""
    def blocked(*args, **kwargs):
        raise RuntimeError('External HTTP is disabled in tests')
    for method in ('get', 'post', 'put', 'patch', 'delete'):
        monkeypatch.setattr(httpx, method, blocked)
