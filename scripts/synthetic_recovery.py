"""Disposable CI recovery rehearsal. No production keys, services or data."""
import argparse
import base64
import hashlib
import json
import os
from pathlib import Path
import secrets
import sys
from sqlalchemy.engine import make_url


def test_url(value):
    url = make_url(value)
    if (url.drivername != 'postgresql+psycopg'
            or url.host not in {'127.0.0.1', 'localhost'}
            or url.database != 'zova_test_ci' or url.query):
        raise ValueError('Recovery rehearsal requires the isolated loopback CI database')
    return url


def restore_media(root, storage_key, digest):
    root = Path(root).resolve()
    media = Path(storage_key).resolve()
    if media != root / 'synthetic-recovery.png':
        raise ValueError('Unexpected recovery media path')
    backup = (root / 'media-backup.bin').read_bytes()
    if hashlib.sha256(backup).hexdigest() != digest:
        raise ValueError('Recovery media checksum does not match')
    media.write_bytes(backup)


def run(mode):
    if os.environ.get('CI') != 'true' or not os.environ.get('RUNNER_TEMP'):
        raise ValueError('This rehearsal runs only in disposable CI')
    url = test_url(os.environ.get('ZOVA_TEST_POSTGRES', ''))
    root = Path(os.environ['RUNNER_TEMP']).resolve() / 'zova-recovery'
    if mode == 'prepare':
        root.mkdir(mode=0o700)  # Refuse to reuse an existing fixture or overwrite it.
        from cryptography.fernet import Fernet
        state = {'encryption_key': Fernet.generate_key().decode(),
                 'session_secret': secrets.token_hex(32)}
    else:
        state = json.loads((root / 'private-state.json').read_text())
        url = url.set(database='zova_test_restored')
    os.environ.update(DATABASE_URL=url.render_as_string(hide_password=False),
                      CREDENTIAL_ENCRYPTION_KEY=state['encryption_key'],
                      SESSION_SECRET=state['session_secret'],
                      ZOVA_SCHEDULER_MODE='disabled', ZOVA_WEB_REPLICAS='1',
                      ZOVA_SCHEMA_MODE='verify', S3_BUCKET='')
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from nova.db import (SessionLocal, User, SocialConnection, Draft, MediaAsset,
                         Publication, AIConsent)
    from nova.security import (encrypt, decrypt, hash_password, verify_password,
                               make_user_session, user_from_session, revoke_session)
    from nova.storage import get_bytes
    from nova.ai_consent import VERSION

    if mode == 'prepare':
        media = root / 'synthetic-recovery.png'
        data = base64.b64decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+j5N8AAAAASUVORK5CYII=')
        media.write_bytes(data)
        (root / 'media-backup.bin').write_bytes(data)
        with SessionLocal() as db:
            user = User(email=secrets.token_hex(12)+'@recovery.example.test',
                        password_hash=hash_password('Synthetic-recovery-only!'), auth_version=7)
            db.add(user); db.flush()
            connection = SocialConnection(user_id=user.id, platform='instagram',
                account_id='synthetic-only', encrypted_access_token=encrypt('synthetic-recovery-token'))
            draft = Draft(user_id=user.id, brief='Synthetic recovery only', revision=4, status='unknown')
            asset = MediaAsset(user_id=user.id, filename=media.name, mime_type='image/png',
                              storage_key=str(media), size_bytes=len(data))
            db.add_all([connection, draft, asset]); db.flush()
            publication = Publication(user_id=user.id, draft_id=draft.id, connection_id=connection.id,
                                      platform='instagram', review_code='synthetic-only', status='unknown')
            db.add_all([publication, AIConsent(user_id=user.id, version=VERSION, allowed=False)])
            db.commit()
            state.update(user_id=user.id, connection_id=connection.id, draft_id=draft.id,
                         media_id=asset.id, publication_id=publication.id,
                         media_sha256=hashlib.sha256(data).hexdigest())
        state['session'] = make_user_session(state['user_id'])
        state['revoked_session'] = make_user_session(state['user_id'])
        revoke_session(state['revoked_session'])
        private = root / 'private-state.json'
        private.write_text(json.dumps(state))
        private.chmod(0o600)
        print('Synthetic recovery fixtures prepared; include them in the database backup.')
        return

    with SessionLocal() as db:
        user = db.get(User, state['user_id'])
        assert user and user.auth_version == 7
        assert verify_password('Synthetic-recovery-only!', user.password_hash)
        connection = db.get(SocialConnection, state['connection_id'])
        assert connection.user_id == user.id
        assert decrypt(connection.encrypted_access_token) == 'synthetic-recovery-token'
        from cryptography.fernet import Fernet
        os.environ['CREDENTIAL_ENCRYPTION_KEY'] = Fernet.generate_key().decode()
        try:
            try:
                decrypt(connection.encrypted_access_token)
            except RuntimeError:
                pass
            else:
                raise AssertionError('A wrong encryption key must not decrypt restored credentials')
        finally:
            os.environ['CREDENTIAL_ENCRYPTION_KEY'] = state['encryption_key']
        assert user_from_session(state['session']).id == user.id
        assert user_from_session(state['revoked_session']) is None
        draft = db.get(Draft, state['draft_id'])
        publication = db.get(Publication, state['publication_id'])
        assert draft.user_id == publication.user_id == user.id
        assert draft.revision == 4 and draft.status == publication.status == 'unknown'
        assert db.get(AIConsent, user.id).allowed is False
        asset = db.get(MediaAsset, state['media_id'])
        assert asset.user_id == user.id
        media = Path(asset.storage_key).resolve()
        assert media == root / 'synthetic-recovery.png'
        media.unlink()  # Only the exact synthetic fixture created above.
        assert not media.exists()
        restore_media(root, asset.storage_key, state['media_sha256'])
        recovered = get_bytes(asset.storage_key)
        assert len(recovered) == asset.size_bytes
        assert hashlib.sha256(recovered).hexdigest() == state['media_sha256']
    receipt = {'status': 'passed', 'synthetic_only': True,
               'checks': ['credential decryption', 'wrong key rejected', 'password retained',
                          'session continuity', 'revoked session rejected',
                          'unknown publication retained', 'AI withdrawal retained',
                          'missing media restored with matching checksum']}
    (root / 'receipt.json').write_text(json.dumps(receipt, indent=2)+'\n')
    print('Synthetic recovery passed: keys, passwords, sessions, revocation, unknown publication, AI choice and media.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode', choices=['prepare', 'verify'])
    run(parser.parse_args().mode)
