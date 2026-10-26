import json
from sqlalchemy import select
from nova.db import SessionLocal, SocialConnection, Publication
from nova import tiktok_status
from test_reviewed_publication import prepared


def pending():
    client, uid, _, body = prepared(('tiktok',))
    with SessionLocal() as db:
        conn = db.scalar(select(SocialConnection).where(SocialConnection.user_id == uid))
        row = Publication(user_id=uid, draft_id=body['draft_id'], platform='tiktok', connection_id=conn.id, review_code='synthetic', status='pending', result_json=json.dumps({'post_id':'receipt-only','pending':True,'privacy_level':'PUBLIC_TO_EVERYONE'}))
        db.add(row); db.commit()
        return client, body['draft_id'], row.id


def test_studio_get_reconciles_public_link_and_never_resends(monkeypatch):
    client, draft, _ = pending(); calls=[]
    monkeypatch.setattr(tiktok_status, 'resolve_tiktok_post', lambda *a: calls.append(a[-1]) or {'status':'PUBLISH_COMPLETE','public_ids':['1234567890123456789']})
    result=client.get(f'/api/publications/{draft}').json()
    assert result['draft_status']=='published'
    assert result['results']['tiktok']['url']=='https://www.tiktok.com/@demo/video/1234567890123456789'
    client.get(f'/api/publications/{draft}')
    assert calls==['receipt-only']


def test_private_complete_has_no_invented_link(monkeypatch):
    client, draft, row_id=pending()
    with SessionLocal() as db:
        row=db.get(Publication,row_id);stored=json.loads(row.result_json);stored['privacy_level']='SELF_ONLY';row.result_json=json.dumps(stored);db.commit()
    monkeypatch.setattr(tiktok_status,'resolve_tiktok_post',lambda *a:{'status':'PUBLISH_COMPLETE','public_ids':[]})
    result=client.get(f'/api/publications/{draft}').json()['results']['tiktok']
    assert result['status']=='published' and not result.get('url')


def test_processing_throttles_checks_and_preserves_receipt(monkeypatch):
    client,draft,_=pending();calls=[]
    monkeypatch.setattr(tiktok_status,'resolve_tiktok_post',lambda *a:calls.append(a[-1]) or {'status':'PROCESSING_UPLOAD'})
    for _ in range(3):
        result=client.get(f'/api/publications/{draft}').json()['results']['tiktok']
        assert result['status']=='pending' and result['post_id']=='receipt-only'
    assert len(calls)==1


def test_provider_failure_does_not_report_success(monkeypatch):
    client,draft,_=pending()
    def failed(*args): raise RuntimeError('temporary provider outage')
    monkeypatch.setattr(tiktok_status,'resolve_tiktok_post',failed)
    assert client.get(f'/api/publications/{draft}').json()['results']['tiktok']['status']=='pending'
