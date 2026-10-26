import hashlib
import pytest
from scripts.synthetic_recovery import test_url as recovery_url, restore_media


@pytest.mark.parametrize('url', [
    'postgresql+psycopg://localhost/production',
    'postgresql+psycopg://cloud.example/zova_test_ci',
    'postgresql+psycopg://localhost/zova_test_ci?host=cloud.example',
    'postgresql+psycopg://localhost/zova_test_ci?service=production',
    'sqlite:///zova_test_ci',
])
def test_rehearsal_refuses_non_ci_database_and_connection_overrides(url):
    with pytest.raises(ValueError):
        recovery_url(url)


def test_media_recovery_refuses_escape_and_corrupt_backup(tmp_path):
    (tmp_path/'media-backup.bin').write_bytes(b'backup')
    digest = hashlib.sha256(b'backup').hexdigest()
    with pytest.raises(ValueError, match='path'):
        restore_media(tmp_path, tmp_path/'..'/'unexpected.png', digest)
    target = tmp_path/'synthetic-recovery.png'
    target.write_bytes(b'current')
    with pytest.raises(ValueError, match='checksum'):
        restore_media(tmp_path, target, 'invalid')
    assert target.read_bytes() == b'current'
    target.unlink()
    restore_media(tmp_path, target, digest)
    assert target.read_bytes() == b'backup'
