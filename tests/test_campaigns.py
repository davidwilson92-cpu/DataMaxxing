import json
from datetime import timedelta
from sqlalchemy import select
from nova import ai, allowances
from nova.db import Brand, Draft, SessionLocal, ScheduledPost, utcnow
from test_account_integrity import account


def brief():
    return dict(idea="Launch Zova with a demo and an invitation.", start=(utcnow()+timedelta(days=3)).strftime('%Y-%m-%dT10:30'),
                frequency='daily', timezone='Europe/London', platforms=['instagram','x'], count=2)


def test_premium_gate_and_explicit_approval(monkeypatch):
    client, uid, *_ = account()
    other, *_ = account()
    assert client.post('/api/campaigns', json=brief()).status_code == 402
    assert 'Explore Premium' in client.get('/campaigns').text
    monkeypatch.setattr(allowances, 'tier', lambda db, user: 'premium')
    row = client.post('/api/campaigns', json=brief()).json()
    cid = row['id']
    plan = f'/api/ai/campaigns/{cid}/plan'
    accept = f'/api/campaigns/{cid}/accept'
    rev = {'revision':1}
    assert other.post(plan, json=rev).status_code == 404
    with SessionLocal() as db:
        brand = Brand(user_id=uid, name='Other'); db.add(brand); db.commit(); bid=brand.id
    assert client.post(accept, headers={'X-Zova-Brand':str(bid)}, json=rev).status_code == 404
    assert client.post(accept, json=rev).status_code == 409
    monkeypatch.setenv('ZOVA_AI_CONSENT_REQUIRED','true')
    assert client.post(plan, json=rev).status_code == 403
    monkeypatch.setenv('ZOVA_AI_CONSENT_REQUIRED','false')
    def generate(prompt, **kwargs):
        return json.dumps({'posts':[{'caption':'See the demo.','asset_id':None},{'caption':'Try it this Friday.','asset_id':None}]})
    monkeypatch.setattr(ai, 'editorial_response', generate)
    assert client.post(plan, json=rev).json()['revision'] == 2
    assert client.post(plan, json=rev).status_code == 409
    revised = client.post(plan, json={'revision':2,'feedback':'Lead with the demo.'}).json()
    assert revised['feedback'] == 'Lead with the demo.'
    result = client.post(accept, json={'revision':3}).json()
    assert len(result['draft_ids']) == 2
    assert client.post(accept,json={'revision':3}).json()['draft_ids'] == result['draft_ids']
    assert client.get('/api/campaigns').json()[0] == result
    with SessionLocal() as db:
        assert len(list(db.scalars(select(Draft).where(Draft.user_id==uid)))) == 2
        assert not db.scalar(select(ScheduledPost).where(ScheduledPost.user_id==uid))


def test_bulk_media_survives_review_and_failed_revision(monkeypatch):
    from io import BytesIO
    from PIL import Image
    from nova import media_inspection
    client, *_ = account()
    other, *_ = account()
    monkeypatch.setattr(allowances, 'tier', lambda db, uid: 'premium')
    image = BytesIO()
    Image.new('RGB', (2, 2)).save(image, format='PNG')
    ids = []
    for name in ['launch.png', 'demo.png']:
        upload = client.post('/api/media', files={'files':(name,image.getvalue(),'image/png')})
        ids.append(upload.json()['assets'][0]['id'])
    assert other.post('/api/campaigns',json=dict(brief(),media=ids)).status_code == 404
    row = client.post('/api/campaigns',json=dict(brief(),media=ids)).json()
    plan = f"/api/ai/campaigns/{row['id']}/plan"
    monkeypatch.setattr(media_inspection,'inspect_assets',lambda db,uid,ids: [])
    monkeypatch.setattr(ai,'editorial_response',lambda *args,**kw: json.dumps({'posts':[
        {'caption': 'See the launch.', 'asset_id':ids[0]}, {'caption':'Watch the demo.', 'asset_id':ids[1]}]}))
    approved = client.post(plan,json={'revision':1}).json()
    monkeypatch.setattr(ai,'editorial_response',lambda *args,**kw:'{"posts":[]}')
    assert client.post(plan,json={'revision':2,'feedback':'Try again.'}).status_code == 502
    assert client.get('/api/campaigns').json()[0] == approved
    accepted = client.post(f"/api/campaigns/{row['id']}/accept", json={'revision':2}).json()
    with SessionLocal() as db:
        for draft_id, aid in zip(accepted['draft_ids'], ids):
            assert json.loads(db.get(Draft,draft_id).workspace_json)['media_asset_ids'] == [aid]


def test_missing_media_and_invalid_platform_count(monkeypatch):
    client, *_ = account()
    monkeypatch.setattr(allowances,'tier',lambda db,uid:'premium')
    assert client.post('/api/campaigns',json=dict(brief(),media=[993938])).status_code == 404
    assert client.post('/api/campaigns',json=dict(brief(),count=1)).status_code == 400
