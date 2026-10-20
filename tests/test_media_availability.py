"""Missing uploads must fail before sending, without losing drafts or approvals."""
from pathlib import Path
import pytest
from sqlalchemy import select
from nova import storage
from nova.db import SessionLocal, MediaAsset, PublishReview, Publication, UsageEntry
from test_instagram_formats import story_draft


def asset_path(body):
    with SessionLocal() as db:
        return Path(db.get(MediaAsset,body['media_asset_ids'][0]).storage_key)


def test_missing_attachment_cannot_enter_review_and_draft_remains(monkeypatch):
    client,body=story_draft(monkeypatch)
    asset_path(body).unlink()
    response=client.post('/api/publish-review',json=body)
    assert response.status_code==409 and 'upload it again' in response.json()['detail']
    saved=client.get('/api/drafts/'+str(body['draft_id'])).json()
    assert saved['workspace']['media_asset_ids']==body['media_asset_ids']
    assert saved['variants']==body['variants']
    assert client.get('/media/preview/'+str(body['media_asset_ids'][0])).status_code==404
    with SessionLocal() as db:
        assert not db.scalar(select(PublishReview).where(PublishReview.draft_id==body['draft_id']))


def test_media_lost_after_review_is_definite_failure_without_provider_call(monkeypatch):
    import nova.app as module
    client,body=story_draft(monkeypatch)
    response=client.post('/api/publish-review',json=body)
    assert response.status_code==200,response.text
    approved={**body,'review_token':response.json()['review_token']}
    path=asset_path(body);path.unlink();calls=[]
    monkeypatch.setattr(module,'publish_platform',lambda *a,**kw:calls.append(kw))
    result=client.post('/api/publish',json=approved)
    assert result.status_code==200,result.text
    assert result.json()['results']['instagram']['status']=='failed'
    assert not calls
    with SessionLocal() as db:
        row=db.scalar(select(Publication).where(Publication.draft_id==body['draft_id']))
        assert db.get(UsageEntry,'publication:'+str(row.id)).state=='released'
    client.post('/api/publish',json=approved)
    assert not calls


def test_local_media_checks_size_and_boundary(tmp_path):
    from test_reviewed_publication import synthetic_storage
    valid=Path(synthetic_storage())
    storage.verify_available(str(valid),20)
    with pytest.raises(RuntimeError):storage.verify_available(str(valid),21)
    outside=tmp_path/'private';outside.write_bytes(b'x'*20)
    with pytest.raises(RuntimeError):storage.verify_available(str(outside),20)


def test_s3_check_is_read_only_and_does_not_return_provider_errors(monkeypatch):
    from types import SimpleNamespace
    monkeypatch.setenv('S3_BUCKET','synthetic-bucket');calls=[]
    def head(**kw):calls.append(kw);return {'ContentLength':20}
    monkeypatch.setattr(storage,'_s3_client',lambda:SimpleNamespace(head_object=head))
    storage.verify_available('nova/media',20)
    assert calls==[{'Bucket':'synthetic-bucket','Key':'nova/media'}]
    with pytest.raises(RuntimeError):storage.verify_available('nova/media',21)
    def fail(**kw):raise RuntimeError('private provider credential')
    monkeypatch.setattr(storage,'_s3_client',lambda:SimpleNamespace(head_object=fail))
    with pytest.raises(RuntimeError) as error:storage.verify_available('nova/media',20)
    assert 'private' not in str(error.value)
