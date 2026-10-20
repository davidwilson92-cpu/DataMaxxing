from pathlib import Path
import os
import pytest
from scripts.rehearse_render_restore import media_path, local_environment, target_connection, file_digest


def test_recovery_children_do_not_inherit_live_credentials(monkeypatch):
    for key in ('DATABASE_URL','OPENAI_API_KEY','SMTP_PASSWORD','SESSION_SECRET','ADMIN_API_KEY','CREDENTIAL_ENCRYPTION_KEY'):
        monkeypatch.setenv(key,'synthetic-secret')
    clean=local_environment()
    assert set(clean)=={'PATH','LANG','LC_ALL','TZ'}
    assert 'synthetic-secret' not in str(clean)


def test_restore_destination_cannot_be_production_or_an_arbitrary_directory(tmp_path):
    with pytest.raises(ValueError):target_connection(tmp_path)
    with pytest.raises((ValueError,FileNotFoundError,OSError)):target_connection('/app/uploads')


def test_media_copy_rejects_escape_and_missing_files(tmp_path):
    root=tmp_path/'uploads';root.mkdir()
    media=root/'valid.png';media.write_bytes(b'synthetic-upload')
    assert media_path(root,media)==media.resolve()
    assert len(file_digest(media))==64
    other=tmp_path/'secret';other.write_bytes(b'not-upload')
    with pytest.raises(ValueError):media_path(root,other)
    with pytest.raises(FileNotFoundError):media_path(root,root/'missing')
    with pytest.raises(ValueError):media_path(root,root)


def test_rehearsal_never_imports_application_or_accepts_restore_url():
    source=(Path(__file__).parents[1]/'scripts/rehearse_render_restore.py').read_text()
    assert 'import nova' not in source and 'from nova' not in source
    assert 'default_transaction_read_only=on' in source
    assert "listen_addresses=''" in source
    assert '--snapshot=' in source
    assert 'source.execute(\'CREATE' not in source
