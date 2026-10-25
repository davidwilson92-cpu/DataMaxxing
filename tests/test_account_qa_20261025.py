import json
import re
from datetime import timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from nova import app as app_module
from nova.ai_consent import VERSION
from nova.db import (AIConsent, Brand, BrandVoice, CreatorPreferences, DeletionRequest,
                     Draft, MobileSession, Publication, PublishReview, ScheduledPost,
                     SessionLocal, SocialConnection, User, get_preferences, utcnow)
from nova.security import encrypt, make_user_session, user_from_session
from nova.voice_memory import generation_examples, memory, remember_approved
from test_account_integrity import account


PROFILE = {'summary':'Warm and concise.', 'writing_tone':'Warm, direct', 'audience':'Creators',
           'topics':'Making things', 'things_to_avoid':'Jargon', 'preferred_post_length':180}


def scan_mocks(monkeypatch):
    monkeypatch.setattr(app_module,'recent_content_for_user',lambda db,uid:['A real caption sample.'])
    monkeypatch.setattr(app_module.ai,'infer_voice_profile',lambda _:dict(PROFILE))


def test_scan_returns_actual_saved_fields_and_survives_reload(monkeypatch):
    scan_mocks(monkeypatch)
    client,uid,_,_=account()
    data=client.post('/api/voice/scan-socials').json()
    assert data['status']=='learned' and data['posts_scanned']==1
    assert data['preferences']['writing_tone']==PROFILE['writing_tone']
    with SessionLocal() as db:
        prefs=get_preferences(db,uid)
        assert prefs.writing_tone==PROFILE['writing_tone']
        assert memory(prefs)['profile']['writing_tone']==PROFILE['writing_tone']
    page=client.get('/account').text
    assert 'name="writing_tone" placeholder="Warm, direct, a little playful">Warm, direct</textarea>' in page
    assert 'href="/studio?strategy=1"' in page
    assert 'account-delete-row' in page


def test_scan_preserves_explicit_edits_including_intentional_clear(monkeypatch):
    scan_mocks(monkeypatch)
    client,uid,_,_=account()
    client.post('/api/voice/scan-socials')
    client.post('/account/preferences',data={'writing_tone':'My own style','audience':'','topics':'Pottery',
        'things_to_avoid':'Never mention private clients','example_posts':'My example','timezone':'Europe/London'})
    data=client.post('/api/voice/scan-socials').json()
    assert data['preferences']['writing_tone']=='My own style'
    assert data['preferences']['audience']==''
    assert {'writing_tone','audience','topics'}<=set(data['overrides'])
    with SessionLocal() as db:
        prefs=get_preferences(db,uid)
        assert prefs.writing_tone=='My own style' and prefs.audience==''
        assert memory(prefs)['profile']['writing_tone']=='Warm, direct'


def test_empty_scan_and_failure_never_claim_success_or_erase_voice(monkeypatch):
    client,uid,_,_=account()
    with SessionLocal() as db:
        prefs=get_preferences(db,uid);prefs.writing_tone='Keep this'
        db.add(SocialConnection(user_id=uid,platform='tiktok',account_id='synthetic',encrypted_access_token=encrypt('token')))
        db.commit()
    monkeypatch.setattr(app_module,'recent_content_for_user',lambda db,uid:[])
    response=client.post('/api/voice/scan-socials')
    assert response.json()['status']=='waiting' and 'No readable captions' in response.json()['message']
    monkeypatch.setattr(app_module,'recent_content_for_user',lambda db,uid:['A caption'])
    monkeypatch.setattr(app_module.ai,'infer_voice_profile',lambda _:(_ for _ in ()).throw(RuntimeError('secret-provider-detail')))
    response=client.post('/api/voice/scan-socials')
    assert response.status_code==502 and 'secret-provider-detail' not in response.text
    with SessionLocal() as db:assert get_preferences(db,uid).writing_tone=='Keep this'


def test_voice_scan_and_approved_memory_are_brand_bound_and_consent_gated(monkeypatch):
    scan_mocks(monkeypatch)
    client,uid,_,_=account();_,other,_,_=account()
    with SessionLocal() as db:
        brand=Brand(user_id=uid,name='Second brand');foreign=Brand(user_id=other,name='Foreign')
        db.add_all([brand,foreign]);db.commit();bid,fid=brand.id,foreign.id
    assert client.post('/api/voice/scan-socials',headers={'X-Zova-Brand':str(fid)}).status_code==404
    assert client.post('/api/voice/scan-socials',headers={'X-Zova-Brand':str(bid)}).status_code==200
    payload={'targets':{'instagram':{'posts':['Approved, not necessarily published.']}}}
    with SessionLocal() as db:
        db.info.update(brand_id=bid,brand_user_id=uid)
        prefs=get_preferences(db,uid)
        remember_approved(db,uid,payload);db.commit()
        assert 'approved_examples' not in memory(prefs)
        db.add(AIConsent(user_id=uid,allowed=True,version=VERSION));db.commit()
        for _ in range(2):remember_approved(db,uid,payload)
        db.commit()
        assert memory(prefs)['approved_examples']==['Approved, not necessarily published.']
        assert 'Approved, not necessarily published.' in generation_examples(prefs)
    with SessionLocal() as db:
        assert get_preferences(db,uid).writing_tone==''
        assert get_preferences(db,other).learned_json=='{}'
    page=client.get('/account',params={'workspace':bid}).text
    assert 'Approved, not necessarily published.' in page
    assert client.post('/account/voice/clear-examples',headers={'X-Zova-Brand':str(bid)},follow_redirects=False).status_code==303
    with SessionLocal() as db:
        prefs=db.scalar(select(BrandVoice).where(BrandVoice.user_id==uid,BrandVoice.brand_id==bid))
        assert not memory(prefs)['approved_examples']


def test_unusable_voice_analysis_is_recoverable_and_keeps_saved_preferences(monkeypatch):
    client,uid,_,_=account()
    with SessionLocal() as db:
        prefs=get_preferences(db,uid);prefs.writing_tone='Keep my voice';db.commit()
    monkeypatch.setattr(app_module.ai,'infer_voice_profile',lambda _:dict(PROFILE,writing_tone=''))
    response=client.post('/api/voice/learn',json={'content':'A useful sample from my own approved content. '*3})
    assert response.status_code==502 and 'saved voice is unchanged' in response.text
    with SessionLocal() as db:assert get_preferences(db,uid).writing_tone=='Keep my voice'


def test_voice_response_arriving_after_account_revocation_cannot_write(monkeypatch):
    client,uid,_,_=account()
    with SessionLocal() as db:
        prefs=get_preferences(db,uid);prefs.writing_tone='Keep my voice';db.commit()
    def revoke_then_return(_):
        with SessionLocal() as db:
            db.get(User,uid).active=False;db.commit()
        return dict(PROFILE)
    monkeypatch.setattr(app_module.ai,'infer_voice_profile',revoke_then_return)
    response=client.post('/api/voice/learn',json={'content':'An original caption I wrote for my own community. '*3})
    assert response.status_code==401
    with SessionLocal() as db:assert get_preferences(db,uid).writing_tone=='Keep my voice'


def deletion_form(client):
    page=client.get('/account/deletion')
    return {'confirmation':'DELETE','current_password':'old-password-123',
            'proof':re.search(r'name="proof" value="([^"]+)"',page.text)[1]}


def test_deletion_requires_current_password_bound_confirmation_and_same_origin():
    client,uid,token,_=account();other,oid,_,_=account()
    data=deletion_form(client)
    assert client.post('/account/deletion',data=data,headers={'Origin':'https://evil.example'}).status_code==403
    assert other.post('/account/deletion',data=data).status_code==400
    assert client.post('/account/deletion',data={**data,'current_password':'incorrect'}).status_code==400
    assert client.post('/account/deletion',data={**data,'proof':'0.bad'}).status_code==400
    with SessionLocal() as db:
        assert db.get(User,uid).active and db.get(User,oid).active
        assert db.get(User,uid).auth_version==0
    assert user_from_session(token)


def test_deletion_revokes_all_sessions_cancels_unsent_across_brands_and_retains_uncertain():
    client,uid,token,_=account();other,oid,other_token,_=account()
    second_token=make_user_session(uid)
    data=deletion_form(client)
    with SessionLocal() as db:
        brand=Brand(user_id=uid,name='Second');db.add(brand);db.flush()
        owned=[]
        for index,status in enumerate(['scheduled','unknown']):
            draft=Draft(user_id=uid,brand_id=brand.id if index else 0,brief='Private draft')
            conn=SocialConnection(user_id=uid,brand_id=draft.brand_id,platform='x',account_id=f'synthetic-{index}',encrypted_access_token=encrypt('reconciliation-token'))
            db.add_all([draft,conn]);db.flush()
            pub=Publication(user_id=uid,brand_id=draft.brand_id,draft_id=draft.id,platform='x',connection_id=conn.id,review_code='synthetic',status=status,result_json='{"provider_receipt":"keep"}')
            job=ScheduledPost(user_id=uid,brand_id=draft.brand_id,draft_id=draft.id,connection_id=conn.id,platform='x',content_json='{}',status=status,scheduled_at=utcnow()+timedelta(days=2))
            db.add_all([pub,job]);db.flush();owned.append((pub.id,job.id,conn.id))
        db.add(MobileSession(id=f'device-{uid}',user_id=uid,auth_version=0,access_hash=f'access-{uid}',access_expires_at=utcnow()+timedelta(hours=1),expires_at=utcnow()+timedelta(days=3)))
        db.commit()
    result=client.post('/account/deletion',data={**data,'user_id':oid},follow_redirects=False)
    assert result.status_code==303
    receipt=TestClient(app_module.app).get(result.headers['location'])
    assert 'not yet been erased' in receipt.text
    assert user_from_session(token) is None and user_from_session(second_token) is None
    assert user_from_session(other_token).id==oid
    with SessionLocal() as db:
        assert not db.get(User,uid).active and db.get(User,uid).auth_version==1
        assert db.get(MobileSession,f'device-{uid}').revoked
        for index,(pid,jid,cid) in enumerate(owned):
            assert db.get(Publication,pid).status==('cancelled' if index==0 else 'unknown')
            assert db.get(ScheduledPost,jid).status==('cancelled' if index==0 else 'unknown')
            assert db.get(Publication,pid).result_json=='{"provider_receipt":"keep"}'
            assert not db.get(SocialConnection,cid).active
            assert db.get(SocialConnection,cid).encrypted_access_token
        assert db.get(User,oid).active


def test_only_immutable_confirmed_content_refreshes_voice(monkeypatch):
    from test_reviewed_publication import prepared,review
    client,uid,_,body=prepared()
    with SessionLocal() as db:
        db.add(AIConsent(user_id=uid,allowed=True,version=VERSION));db.commit()
    approved=review(client,body)
    with SessionLocal() as db:assert not memory(get_preferences(db,uid)).get('approved_examples')
    invalid={**approved,'variants':{'x':{'posts':['Unapproved replacement']}}}
    assert client.post('/api/publish',json=invalid).status_code==409
    monkeypatch.setattr(app_module,'publish_platform',lambda *a,**k:{'post_id':'synthetic'})
    assert client.post('/api/publish',json=approved).status_code==200
    assert client.post('/api/publish',json=approved).status_code==200
    with SessionLocal() as db:
        examples=memory(get_preferences(db,uid))['approved_examples']
        assert examples==['Approved text x']


def test_voice_memory_migration_is_additive_repeatable_and_preserves_preferences(tmp_path):
    from sqlalchemy import create_engine, text
    from nova.db import Base,engine
    from nova.migrations import run_migrations
    import secrets
    if engine.dialect.name=='postgresql':
        schema='voice_migration_'+secrets.token_hex(6)
        with engine.begin() as conn:conn.execute(text(f'CREATE SCHEMA {schema}'))
        isolated=create_engine(engine.url,connect_args={'options':f'-csearch_path={schema}'})
    else:
        isolated=create_engine('sqlite:///'+str(tmp_path/'voice.db'))
    try:
        Base.metadata.create_all(isolated)
        from sqlalchemy.orm import Session
        with Session(isolated) as db:
            user=User(email='voice-migration@example.test',password_hash='preserved-hash')
            db.add(user);db.flush()
            brand=Brand(user_id=user.id,name='Preserved brand');db.add(brand);db.flush()
            db.add_all([CreatorPreferences(user_id=user.id,writing_tone='Preserved account tone'),
                        BrandVoice(user_id=user.id,brand_id=brand.id,writing_tone='Preserved brand tone')])
            db.commit()
        with isolated.begin() as conn:
            for table in ('nova_creator_preferences','zova_brand_voices'):
                conn.execute(text(f'ALTER TABLE {table} DROP COLUMN learned_json'))
        run_migrations(isolated);run_migrations(isolated)
        with isolated.connect() as conn:
            for table,tone in [('nova_creator_preferences','Preserved account tone'),('zova_brand_voices','Preserved brand tone')]:
                assert conn.execute(text(f'SELECT writing_tone,learned_json FROM {table}')).one()==(tone,'{}')
    finally:
        isolated.dispose()
        if engine.dialect.name=='postgresql':
            with engine.begin() as conn:conn.execute(text(f'DROP SCHEMA {schema} CASCADE'))


def test_deletion_stops_previously_authenticated_approval_before_new_send(monkeypatch):
    from types import SimpleNamespace
    from fastapi import HTTPException
    from nova.publishing_workflow import confirm_review
    from test_reviewed_publication import prepared,review
    client,uid,_,body=prepared();approved=review(client,body)
    assert client.post('/account/deletion',data=deletion_form(client),follow_redirects=False).status_code==303
    calls=[]
    with SessionLocal() as db:
        with pytest.raises(HTTPException) as failure:
            confirm_review(db,uid,SimpleNamespace(**approved),'publish',lambda *a,**k:calls.append(k))
        assert failure.value.status_code==401
        assert not db.scalar(select(Publication.id).where(Publication.user_id==uid))
    assert not calls
