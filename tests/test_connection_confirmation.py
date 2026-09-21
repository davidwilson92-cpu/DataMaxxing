from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from urllib.parse import urlsplit
from sqlalchemy import select
from fastapi.testclient import TestClient
from nova import app as module
from nova.db import SessionLocal,PendingConnection,SocialConnection,BrandVoice,User,utcnow
from nova.security import decrypt,make_user_session
from test_social_login_routes import signed_in,state_from
from test_account_integrity import account
import pytest


def staged(client,monkeypatch):
    monkeypatch.setattr(module,'instagram_exchange',lambda code:{'profile':{'id':'real-returned-id','username':'intended_creator','name':'My <brand>'},'access_token':'synthetic-pending-secret'})
    start=client.get('/oauth/instagram/start',follow_redirects=False)
    callback=client.get('/oauth/instagram/callback',params={'state':state_from(start),'code':'mock'},follow_redirects=False)
    assert callback.status_code==303,callback.text
    return callback.headers['location']


def test_no_connection_before_confirmation_no_secrets_in_html(signed_in,monkeypatch):
    client,uid=signed_in;url=staged(client,monkeypatch)
    page=client.get(url)
    assert page.status_code==200 and 'intended_creator' in page.text and 'My &lt;brand&gt;' in page.text
    assert 'synthetic-pending-secret' not in page.text
    with SessionLocal() as db:
        assert db.scalar(select(SocialConnection).where(SocialConnection.user_id==uid)) is None
        pending=db.scalar(select(PendingConnection).where(PendingConnection.user_id==uid))
        assert 'synthetic-pending-secret' not in pending.encrypted_payload
        assert 'synthetic-pending-secret' in decrypt(pending.encrypted_payload)
    assert client.post(url,data={'choice':0,'account_id':'attacker','action':'connect'}).status_code==200
    with SessionLocal() as db:
        row=db.scalar(select(SocialConnection).where(SocialConnection.user_id==uid))
        assert row.account_id=='real-returned-id'
        assert db.scalar(select(PendingConnection).where(PendingConnection.user_id==uid)).encrypted_payload==''
    assert client.post(url,data={'choice':0}).status_code==410


def test_other_user_and_brand_cannot_accept(signed_in,monkeypatch):
    client,uid=signed_in;url=staged(client,monkeypatch)
    other,*_=account()
    assert other.get(url).status_code==404
    assert other.post(url,data={'choice':0}).status_code==404
    client.post('/brands',data={'name':'Another brand'})
    bid=client.cookies.get('zova_brand')
    wrong=url.replace('workspace=0','workspace='+bid)
    assert client.post(wrong,data={'choice':0}).status_code==404
    # Pinned review still explicitly confirms its original brand.
    assert client.post(url,data={'choice':0}).status_code==200
    with SessionLocal() as db:
        assert db.scalar(select(SocialConnection).where(SocialConnection.user_id==uid)).brand_id==0


def test_switch_cancel_and_expiry_preserve_existing_connections(signed_in,monkeypatch):
    client,uid=signed_in
    with SessionLocal() as db:module.upsert_connection(db,user_id=uid,platform='instagram',account_id='old',username='old',display_name='Old',access='keep-me')
    for action in ('switch','cancel'):
        url=staged(client,monkeypatch)
        response=client.post(url,data={'choice':0,'action':action})
        assert response.status_code==200
        assert client.post(url,data={'choice':0}).status_code==410
    url=staged(client,monkeypatch)
    with SessionLocal() as db:
        pending=db.scalar(select(PendingConnection).where(PendingConnection.user_id==uid,PendingConnection.used.is_(False)))
        pending.expires_at=utcnow()-timedelta(seconds=1);db.commit()
    assert client.post(url,data={'choice':0}).status_code==410
    with SessionLocal() as db:
        rows=db.scalars(select(SocialConnection).where(SocialConnection.user_id==uid)).all()
        assert len(rows)==1 and decrypt(rows[0].encrypted_access_token)=='keep-me'


def test_meta_selects_only_confirmed_page(signed_in,monkeypatch):
    client,uid=signed_in
    monkeypatch.setattr(module,'meta_exchange',lambda code:[{'id':str(i),'name':f'Page {i}','access_token':f'secret{i}'} for i in (1,2)])
    start=client.get('/oauth/meta/start',follow_redirects=False)
    pending=client.get('/oauth/meta/callback',params={'code':'mock','state':state_from(start)},follow_redirects=False)
    url=pending.headers['location']
    assert client.post(url,data={'choice':22}).status_code==400
    assert client.post(url,data={'choice':1}).status_code==200
    with SessionLocal() as db:
        rows=db.scalars(select(SocialConnection).where(SocialConnection.user_id==uid)).all()
        assert len(rows)==1 and rows[0].account_id=='2'


def test_concurrent_confirm_and_cross_site_post(signed_in,monkeypatch):
    client,uid=signed_in;url=staged(client,monkeypatch)
    assert client.post(url,data={'choice':0},headers={'Origin':'https://evil.test'}).status_code==403
    def submit(_):
        c=TestClient(module.app);c.cookies.set('nova_session',make_user_session(uid))
        return c.post(url,data={'choice':0},follow_redirects=False).status_code
    with ThreadPoolExecutor(max_workers=2) as pool:statuses=list(pool.map(submit,range(2)))
    assert statuses.count(303)==1 and all(s in {303,409,410} for s in statuses)


def test_new_signup_does_not_inherit_prior_brand_voice(signed_in):
    import secrets
    client,uid=signed_in
    client.post('/brands',data={'name':'Old customer'})
    bid=int(client.cookies.get('zova_brand'))
    client.post('/account/preferences',data={'writing_tone':'Old private tone'})
    client.cookies.set('zova_onboarding',str(uid))
    email=f'fresh-{secrets.token_hex(6)}@example.test'
    response=client.post('/signup',data={'name':'Fresh Creator','email':email,'country':'GB','password':'fresh-password-123','password_confirmation':'fresh-password-123','accept_terms':'yes'})
    assert response.status_code==200 and 'Fresh Creator' in response.text and email in response.text
    assert 'Old customer' not in response.text
    voice=client.get('/onboarding/writing-style').text
    assert 'Old private tone' not in voice
    with SessionLocal() as db:
        new=db.scalar(select(User).where(User.email==email))
        assert db.scalar(select(BrandVoice).where(BrandVoice.user_id==new.id)) is None
        assert db.scalar(select(BrandVoice).where(BrandVoice.brand_id==bid)).writing_tone=='Old private tone'


@pytest.mark.parametrize('platform',['x','tiktok'])
def test_other_providers_also_require_explicit_confirmation(signed_in,monkeypatch,platform):
    client,uid=signed_in
    monkeypatch.setattr(module,'x_exchange',lambda *a:({'access_token':'synthetic-x'},{'id':'x-user','username':'my_x'}))
    monkeypatch.setattr(module,'tiktok_exchange',lambda *a:({'access_token':'synthetic-tiktok'},{'open_id':'tiktok-user','display_name':'My TikTok'}))
    start=client.get(f'/oauth/{platform}/start',follow_redirects=False)
    pending=client.get(f'/oauth/{platform}/callback',params={'code':'mock','state':state_from(start)},follow_redirects=False)
    url=pending.headers['location']
    assert url.startswith('/connections/review/')
    with SessionLocal() as db:assert db.scalar(select(SocialConnection).where(SocialConnection.user_id==uid)) is None
    assert client.post(url,data={'choice':0}).status_code==200


def test_revoked_session_cannot_complete_pending_connection(signed_in,monkeypatch):
    client,uid=signed_in;url=staged(client,monkeypatch)
    with SessionLocal() as db:
        user=db.get(User,uid);user.auth_version+=1;db.commit()
    client.cookies.clear();client.cookies.set('nova_session',make_user_session(uid))
    assert client.post(url,data={'choice':0}).status_code==404


def test_worker_scrubs_expired_pending_grants(signed_in,monkeypatch):
    from nova.scheduler import process_due
    client,uid=signed_in;staged(client,monkeypatch)
    with SessionLocal() as db:
        row=db.scalar(select(PendingConnection).where(PendingConnection.user_id==uid));row.expires_at=utcnow()-timedelta(minutes=1);db.commit()
    process_due()
    with SessionLocal() as db:assert db.scalar(select(PendingConnection).where(PendingConnection.user_id==uid)) is None

@pytest.mark.parametrize('platform',['instagram','tiktok','x'])
def test_same_browser_new_signup_never_inherits_connection(signed_in,monkeypatch,platform):
    import secrets
    from urllib.parse import parse_qs
    client,old_uid=signed_in
    with SessionLocal() as db:
        module.upsert_connection(db,user_id=old_uid,platform=platform,account_id='prior-account',username='prior_private_identity',display_name='Prior account',access='prior-private-token')
    old_start=client.get(f'/oauth/{platform}/start',follow_redirects=False)
    email=f'new-owner-{secrets.token_hex(6)}@example.test'
    page=client.post('/signup',data={'name':'New owner','email':email,'country':'GB','password':'new-owner-password-123','password_confirmation':'new-owner-password-123','accept_terms':'yes'})
    assert page.status_code==200
    for path in ['/onboarding/socials','/account','/studio']:
        assert 'prior_private_identity' not in client.get(path).text
    with SessionLocal() as db:
        new_uid=db.scalar(select(User.id).where(User.email==email))
        assert new_uid!=old_uid
        assert db.scalar(select(SocialConnection).where(SocialConnection.user_id==new_uid)) is None
    # Returning from an older user's open provider tab cannot attach it to this signup.
    assert client.get(f'/oauth/{platform}/callback',params={'code':'mock','state':state_from(old_start)}).status_code==400
    start=client.get(f'/oauth/{platform}/start',follow_redirects=False)
    assert state_from(start)!=state_from(old_start)
    if platform=='instagram':
        query=parse_qs(urlsplit(start.headers['location']).query)
        assert query['force_reauth']==['true'] and 'force_authentication' not in query
    # Simulate a provider returning the remembered identity anyway: cancel must save nothing.
    monkeypatch.setattr(module,'instagram_exchange',lambda *a:{'profile':{'id':'prior-account','username':'prior_private_identity'},'access_token':'returned-token'})
    monkeypatch.setattr(module,'tiktok_exchange',lambda *a:({'access_token':'returned-token'},{'open_id':'prior-account','display_name':'Prior account'}))
    monkeypatch.setattr(module,'x_exchange',lambda *a:({'access_token':'returned-token'},{'id':'prior-account','username':'prior_private_identity'}))
    pending=client.get(f'/oauth/{platform}/callback',params={'code':'mock','state':state_from(start)},follow_redirects=False)
    assert pending.headers['location'].startswith('/connections/review/')
    assert client.post(pending.headers['location'],data={'choice':0,'action':'cancel'}).status_code==200
    with SessionLocal() as db:
        assert db.scalar(select(SocialConnection).where(SocialConnection.user_id==new_uid)) is None
        old=db.scalar(select(SocialConnection).where(SocialConnection.user_id==old_uid))
        assert decrypt(old.encrypted_access_token)=='prior-private-token'


def test_switch_account_restarts_with_reauthentication(signed_in,monkeypatch):
    from urllib.parse import parse_qs
    client,uid=signed_in
    url=staged(client,monkeypatch)
    switched=client.post(url,data={'choice':0,'action':'switch'},follow_redirects=False)
    page=client.get(switched.headers['location'])
    assert 'Use the account you intended' in page.text
    start=client.get('/oauth/instagram/start',follow_redirects=False)
    assert parse_qs(urlsplit(start.headers['location']).query)['force_reauth']==['true']
    assert client.post(url,data={'choice':0}).status_code==410
