"""Regression boundaries for batching, cached provider data and durable research."""
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
import json
import threading
import time

import httpx
import pytest
from sqlalchemy import delete, event, select, update
from test_account_integrity import account
from nova import read_cache, discovery_jobs, social
from nova.assets import url as asset_url
from nova.db import (Activity, AIConsent, Brand, ContentSeries, DiscoveryJob, Draft,
                     SeriesOccurrence, SessionLocal, SocialConnection, Strategy, User, engine, utcnow)
from nova.security import encrypt


def test_strategy_can_include_the_same_revision_of_saved_ideas():
    client, *_ = account()
    strategy = client.get('/api/strategy').json()
    combined = client.get('/api/strategy?include_actions=true').json()
    saved = combined.pop('actions')
    assert combined == strategy
    assert saved == client.get('/api/strategy/actions').json()
    assert saved['revision'] == strategy['revision']


@pytest.fixture(autouse=True)
def isolate_research_queue():
    read_cache.clear()
    with SessionLocal() as db:
        existing = {row.id: row.status for row in db.scalars(select(DiscoveryJob))}
        db.execute(update(DiscoveryJob).values(status='test_paused'))
        db.commit()
    yield
    with SessionLocal() as db:
        db.execute(delete(DiscoveryJob).where(DiscoveryJob.id.not_in(existing)))
        for job_id, status in existing.items():
            db.execute(update(DiscoveryJob).where(DiscoveryJob.id == job_id).values(status=status))
        db.commit()
    read_cache.clear()


def connected(uid, brand=0, account_id='owned'):
    with SessionLocal() as db:
        row = SocialConnection(user_id=uid, brand_id=brand, platform='instagram',
            account_id=account_id, username=account_id, encrypted_access_token=encrypt('synthetic'),
            metadata_json='{"auth_provider":"instagram_login"}')
        db.add(row); db.commit()
        return row.id


def test_draft_links_are_batched_scoped_and_paginated():
    client, uid, *_ = account()
    other, foreign_uid, *_ = account()
    with SessionLocal() as db:
        drafts = [Draft(user_id=uid, title=f'Post {i}') for i in range(110)]
        db.add_all(drafts); db.flush()
        latest = drafts[-1].id
        db.add_all([Activity(user_id=uid, draft_id=latest, platform='x', status='published', url='https://example.test/older'),
                    Activity(user_id=uid, draft_id=latest, platform='instagram', status='published', url='https://example.test/newer'),
                    Activity(user_id=foreign_uid, draft_id=latest, platform='x', status='published', url='https://example.test/foreign')])
        db.commit()
    queries = []
    def count(conn, cursor, statement, *args): queries.append(statement)
    event.listen(engine, 'before_cursor_execute', count)
    try:
        result = client.get('/api/drafts').json()
    finally:
        event.remove(engine, 'before_cursor_execute', count)
    assert len(result) == 100 and len(queries) < 15
    assert [link['url'] for link in result[0]['links']] == ['https://example.test/newer','https://example.test/older']
    assert len(client.get('/api/drafts?limit=20').json()) == 20
    assert len(client.get('/api/drafts?offset=100').json()) == 10
    assert other.get('/api/drafts').json() == []


def test_series_drafts_are_batched_and_keep_status():
    client, uid, *_ = account()
    with SessionLocal() as db:
        for i in range(5):
            series = ContentSeries(user_id=uid, request_key=str(i), spec_json='{}')
            db.add(series); db.flush()
            for position in range(6):
                draft = Draft(user_id=uid, status='published')
                db.add(draft); db.flush()
                db.add(SeriesOccurrence(user_id=uid, series_id=series.id, position=position,
                    draft_id=draft.id, due_at=utcnow(), status='cancelled' if position == 0 else 'planned'))
        db.commit()
    queries = []
    def count(*args): queries.append(1)
    event.listen(engine, 'before_cursor_execute', count)
    try: result = client.get('/api/series').json()
    finally: event.remove(engine, 'before_cursor_execute', count)
    assert len(queries) < 15
    assert all(row['occurrences'][0]['status'] == 'cancelled' and row['occurrences'][1]['status'] == 'published' for row in result)


def test_cache_coalesces_and_copies_but_refresh_and_expiry_fetch(monkeypatch):
    read_cache.clear()
    calls = []
    clock = [1.0]
    monkeypatch.setattr(read_cache, 'monotonic', lambda: clock[0])
    def reader():
        calls.append(1); time.sleep(.03)
        return {'posts':[{'likes':3}]}
    with ThreadPoolExecutor(max_workers=4) as pool:
        values = list(pool.map(lambda _:read_cache.load(('test',), reader), range(4)))
    assert len(calls) == 1
    values[0]['posts'][0]['likes'] = 999
    assert read_cache.load(('test',), reader)['posts'][0]['likes'] == 3
    read_cache.load(('test',), reader, refresh=True)
    clock[0] = 100
    read_cache.load(('test',), reader)
    assert len(calls) == 3


def test_provider_cache_scopes_refreshes_and_invalidates_grants(monkeypatch):
    read_cache.clear()
    client, uid, *_ = account()
    other, foreign_uid, *_ = account()
    cid = connected(uid)
    connected(foreign_uid, account_id='foreign')
    with SessionLocal() as db:
        brand = Brand(user_id=uid, name='Second'); db.add(brand); db.commit(); bid = brand.id
    connected(uid, bid, 'other-brand')
    calls = []
    def get(url, **kwargs):
        calls.append(url)
        if url.endswith('/media'):
            return httpx.Response(200,json={'data':[{'id':'p','caption':url,'timestamp':utcnow().isoformat(),'like_count':7}]})
        return httpx.Response(200,json={'followers_count':31})
    monkeypatch.setattr(social.httpx, 'get', get)
    path='/api/analytics/dashboard?days=7&refresh=false'
    first=client.get(path); assert first.status_code == 200, first.text
    assert len(calls) == 2
    second=client.get(path).json()
    assert len(calls) == 2 and second['fetched_at'] == first.json()['fetched_at']
    assert second['summary']['shares'] is None
    client.get('/api/analytics/dashboard?days=30&refresh=false'); assert len(calls) == 2
    client.get('/api/analytics/dashboard?days=7&refresh=true'); assert len(calls) == 4
    # Older native clients omit the flag: their Refresh still fetches live data.
    client.get('/api/analytics/dashboard'); assert len(calls) == 6
    assert 'foreign' in other.get(path).json()['top_posts'][0]['text']
    assert 'other-brand' in client.get(path, headers={'X-Zova-Brand':str(bid)}).json()['top_posts'][0]['text']
    with SessionLocal() as db:
        row=db.get(SocialConnection,cid);row.active=False;db.commit()
    assert client.get(path).json()['top_posts'] == []


def test_disconnect_during_read_discards_returned_and_cached_data(monkeypatch):
    client, uid, *_ = account(); cid=connected(uid)
    def get(url, **kwargs):
        with SessionLocal() as db:
            db.execute(update(SocialConnection).where(SocialConnection.id==cid).values(active=False));db.commit()
        return httpx.Response(200,json={'data':[{'id':'p','caption':'must not be returned','timestamp':utcnow().isoformat()}]})
    monkeypatch.setattr(social.httpx,'get',get)
    response=client.get('/api/analytics/dashboard?refresh=false')
    assert response.status_code==409
    assert 'must not be returned' not in response.text


def test_renewed_token_keeps_results_across_database_timestamp_representations(monkeypatch):
    from nova.social_reads import signature
    client, uid, *_ = account(); cid = connected(uid)
    original = social.access_token
    def renewed(conn, db):
        if db is not None and conn.expires_at is None:
            conn.encrypted_access_token = encrypt('renewed-synthetic-token')
            conn.expires_at = utcnow() + timedelta(days=30)
            db.commit()
        return original(conn, db)
    monkeypatch.setattr(social, 'access_token', renewed)
    def get(url, **kwargs):
        data = {'data':[{'id':'p','caption':'Retained after renewal','timestamp':utcnow().isoformat()}]} if url.endswith('/media') else {'followers_count':31}
        return httpx.Response(200, json=data)
    monkeypatch.setattr(social.httpx, 'get', get)
    response = client.get('/api/analytics/dashboard?refresh=false')
    assert response.status_code == 200
    assert response.json()['platforms']['instagram']['followers'] == 31
    assert response.json()['top_posts'][0]['text'] == 'Retained after renewal'
    with SessionLocal() as db:
        conn = db.get(SocialConnection, cid)
        conn.expires_at = utcnow() + timedelta(days=30)
        aware = signature(conn)
        conn.expires_at = conn.expires_at.replace(tzinfo=None)
        assert signature(conn) == aware


def queue_research(monkeypatch):
    client, uid, *_ = account()
    monkeypatch.setenv('OPENAI_API_KEY','synthetic-only')
    with SessionLocal() as db:
        db.add(Strategy(user_id=uid, revision=1))
        db.add(AIConsent(user_id=uid,version='2026-10-19',allowed=True))
        db.commit();db.info.update(brand_id=0,brand_user_id=uid)
        result=discovery_jobs.topics(db,uid,'Brixton gym beginner tips',1)
        row=db.scalar(select(DiscoveryJob).where(DiscoveryJob.user_id==uid))
        return uid,row.id,result


def test_research_is_durable_deduplicated_and_reused(monkeypatch):
    calls=[]
    monkeypatch.setattr(social,'recent_posts_for_user',lambda *args,**kwargs:{'posts':[]})
    from nova import trends
    monkeypatch.setattr(trends,'discover',lambda *a: calls.append(a) or {'topics':[],'checked_at':utcnow().isoformat(),'note':'Checked'})
    uid,jid,result=queue_research(monkeypatch)
    assert not calls and 'updating' in result['note']
    with SessionLocal() as db:
        db.info.update(brand_id=0,brand_user_id=uid)
        discovery_jobs.topics(db,uid,'Brixton gym beginner tips',1)
        assert len(db.scalars(select(DiscoveryJob).where(DiscoveryJob.user_id == uid)).all())==1
    assert discovery_jobs.process_next()
    assert len(calls)==1
    with SessionLocal() as db:
        db.info.update(brand_id=0,brand_user_id=uid)
        assert discovery_jobs.topics(db,uid,'Brixton gym beginner tips',1)['note']=='Checked'
        assert db.get(DiscoveryJob,jid).status=='complete'


def test_research_recovers_a_crash_and_discards_revoked_consent(monkeypatch):
    from nova import trends
    uid,jid,_=queue_research(monkeypatch)
    monkeypatch.setenv('ZOVA_AI_CONSENT_REQUIRED','true')
    with SessionLocal() as db:
        job=db.get(DiscoveryJob,jid);job.status='running';job.lease='crashed';job.attempts=1
        job.lease_expires_at=utcnow()-timedelta(seconds=1);db.commit()
    def discover(*args):
        with SessionLocal() as db:
            consent=db.get(AIConsent,uid);consent.allowed=False;db.commit()
        return {'topics':[{'title':'Must be discarded'}]}
    monkeypatch.setattr(trends,'discover',discover)
    discovery_jobs.process_next()
    with SessionLocal() as db:
        row=db.get(DiscoveryJob,jid)
        assert row.status=='cancelled' and row.result_json=='{}' and row.attempts==2


def test_research_does_not_overwrite_newer_request(monkeypatch):
    from nova import trends
    uid,jid,_=queue_research(monkeypatch)
    def discover(*args):
        with SessionLocal() as db:
            db.info.update(brand_id=0,brand_user_id=uid)
            discovery_jobs.topics(db,uid,'Different audience topic',1)
        return {'topics':[{'title':'Obsolete result'}]}
    monkeypatch.setattr(trends,'discover',discover)
    discovery_jobs.process_next()
    with SessionLocal() as db:
        row=db.get(DiscoveryJob,jid)
        assert row.status=='pending' and row.themes=='Different audience topic' and row.result_json=='{}'
        # Leave no queued fixture for a later test's worker.
        row.status='cancelled';db.commit()


def test_public_asset_versions_compress_and_private_responses_do_not_cache():
    client, *_ = account()
    hashed=asset_url('nova.css')
    response=client.get(hashed,headers={'Accept-Encoding':'gzip'})
    assert response.status_code==200 and response.headers['content-encoding']=='gzip'
    assert 'immutable' in response.headers['cache-control']
    assert client.get(hashed,headers={'If-None-Match':response.headers['etag']}).status_code==304
    assert 'immutable' not in client.get('/static/nova.css?v=old').headers['cache-control']
    assert client.get('/api/drafts').headers['cache-control']=='no-store'
    assert client.get('/studio').headers['cache-control']=='no-store'
    assert asset_url('strategy-loader.js') in client.get('/studio').text
    from nova.assets import BASE_STYLES, BUNDLE, DIRECTORY
    bundle = client.get(asset_url(BUNDLE))
    assert bundle.content == b'\n'.join((DIRECTORY / name).read_bytes() for name in BASE_STYLES)
    assert 'immutable' in bundle.headers['cache-control']
    assert client.get(asset_url(BUNDLE), headers={'If-None-Match': bundle.headers['etag']}).status_code == 304
    assert asset_url(BUNDLE) in client.get('/login').text


def test_thumbnails_are_bounded_private_and_follow_current_source():
    import io
    from PIL import Image
    from fastapi.testclient import TestClient
    from nova.app import app
    from nova import storage
    from nova.db import MediaAsset
    client, uid, *_ = account(); other, *_ = account()
    original = io.BytesIO()
    Image.new('RGB', (2048, 1536), 'red').save(original, format='PNG')
    data = original.getvalue()
    saved = storage.save_bytes(data, 'photo.png', 'image/png', 'http://testserver')
    with SessionLocal() as db:
        brand = Brand(user_id=uid, name='Photo brand'); db.add(brand); db.flush()
        media = MediaAsset(user_id=uid, brand_id=brand.id, filename='photo.png', mime_type='image/png',
                           storage_key=saved.storage_key, size_bytes=len(data))
        db.add(media); db.commit(); aid, bid = media.id, brand.id
    path = f'/media/thumbnail/{aid}?workspace={bid}'
    assert TestClient(app).get(path).status_code == 401
    assert other.get(f'/media/thumbnail/{aid}').status_code == 404
    assert client.get(f'/media/thumbnail/{aid}').status_code == 404
    first = client.get(path)
    assert first.status_code == 200 and first.headers['cache-control'] == 'no-store'
    assert Image.open(io.BytesIO(first.content)).size == (256, 192)
    assert len(first.content) < len(data) / 2
    assert client.get(path).content == first.content
    assert client.get(f'/media/download/{aid}?workspace={bid}').content == data
    source = storage.local_path(saved.storage_key)
    revised = io.BytesIO(); Image.new('RGB', (2048, 1536), 'blue').save(revised, format='PNG')
    source.write_bytes(revised.getvalue())
    with SessionLocal() as db:
        db.get(MediaAsset, aid).size_bytes = len(revised.getvalue()); db.commit()
    assert client.get(path).content != first.content
    source.unlink()
    assert client.get(path).status_code == 404


def test_failed_cache_read_is_retryable_and_clear_discards_inflight_result():
    def fail(): raise RuntimeError('Synthetic failure')
    with pytest.raises(RuntimeError): read_cache.load(('failed',), fail)
    assert read_cache.load(('failed',), lambda: 7) == 7
    def cleared(): read_cache.clear(); return 1
    assert read_cache.load(('cleared',), cleared) == 1
    assert read_cache.load(('cleared',), lambda: 2) == 2


def test_research_retries_are_bounded_and_only_one_worker_claims(monkeypatch):
    from nova import trends
    uid, jid, _ = queue_research(monkeypatch)
    entered = threading.Event(); release = threading.Event()
    def fail(*args):
        entered.set(); assert release.wait(5)
        raise RuntimeError('Synthetic unavailable provider')
    monkeypatch.setattr(trends, 'discover', fail)
    with ThreadPoolExecutor(max_workers=2) as pool:
        running = pool.submit(discovery_jobs.process_next)
        assert entered.wait(5)
        assert discovery_jobs.process_next() is False
        release.set(); assert running.result(5)
    with SessionLocal() as db:
        row = db.get(DiscoveryJob, jid)
        assert row.status == 'pending' and row.attempts == 1 and row.lease is None
        row.attempts = 2; row.next_attempt_at = utcnow()-timedelta(seconds=1); db.commit()
    assert discovery_jobs.process_next()
    with SessionLocal() as db:
        row = db.get(DiscoveryJob, jid)
        assert row.status == 'failed' and row.attempts == 3
    assert discovery_jobs.process_next() is False


def test_account_deletion_cancels_research_and_removes_cached_previews(monkeypatch):
    from nova.account_deletion import initiate
    uid, jid, _ = queue_research(monkeypatch)
    read_cache.load(('synthetic-owner', uid), lambda: 'old')
    with SessionLocal() as db:
        initiate(db, uid, 'old-password-123')
    with SessionLocal() as db:
        row = db.get(DiscoveryJob, jid)
        assert row.status == 'cancelled' and row.lease is None
    assert discovery_jobs.process_next() is False
    assert read_cache.load(('synthetic-owner', uid), lambda: 'new') == 'new'


def test_performance_indexes_are_installed_idempotently_and_verified():
    from scripts.prepare_performance_indexes import prepare
    from nova.db import ScheduledPost
    from sqlalchemy import inspect
    prepare(); prepare()
    for model, expected in ((Draft, 'ix_drafts_owner_brand_updated_id'),
                            (ScheduledPost, 'ix_schedules_owner_brand_due_id')):
        assert expected in {item['name'] for item in inspect(engine).get_indexes(model.__tablename__)}
