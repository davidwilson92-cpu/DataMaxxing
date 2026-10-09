from pathlib import Path
import shutil
import subprocess
import pytest


def test_studio_client_lifecycle_regressions():
    node = shutil.which('node')
    if not node:
        pytest.skip('Node is required for browser-state regression harness')
    result = subprocess.run([node, str(Path(__file__).with_name('studio_clarity_client.cjs'))],
                            capture_output=True, text=True, timeout=30)
    assert result.returncode == 0, result.stdout + result.stderr
