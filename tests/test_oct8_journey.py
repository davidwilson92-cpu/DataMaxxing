import json
import secrets
from datetime import timedelta
import pytest
from sqlalchemy import select
from fastapi import HTTPException
from fastapi.testclient import TestClient
from nova.app import app
from nova.db import SessionLocal, Draft, Brand, User, ScheduledPost, Publication, SocialConnection, utcnow
from nova.workspace import clean_workspace
from nova.work_summary import draft_title, work_summary
from test_account_integrity import account


def test_titles_prefer_customer_words_and_do_not_expose_internal_brief():
    row=Draft(brief='Topic: Internal instruction. Assumptions: hidden details',workspace_json=json.dumps({'conversation':[{'role':'user','content':'Welcome to my pottery studio'}]}))
    assert draft_title(row)=='Welcome to my pottery studio'
    row.workspace_json='{}'
    assert draft_title(row)=='Internal instruction.'
    row.title='My launch'
    assert draft_title(row)=='My launch'


def test_rename_is_isolated_versioned_searchable_and_content_preserving():
    client,uid,*_=account()
    with SessionLocal() as db:
        row=Draft(user_id=uid,brief='Topic: original',variants_json='{"x":{"posts":["Original caption"]}}');db.add(row);db.commit();did=row.id
        brand=Brand(user_id=uid,name='Second brand');db.add(brand);db.commit();bid=brand.id
    assert client.post(f'/drafts/{did}/title?workspace={bid}',data={'title':'Wrong brand','revision':0}).status_code==404
    result=client.post(f'/drafts/{did}/title',data={'title':'Autumn launch','revision':0})
    assert result.status_code==200
    assert client.post(f'/drafts/{did}/title',data={'title':'Stale','revision':0}).status_code==409
    assert 'Autumn launch' in client.get('/drafts?q=Autumn').text
    saved=client.get(f'/api/drafts/{did}').json()
    assert saved['display_title']=='Autumn launch'
    assert saved['variants']['x']['posts']==['Original caption']
    assert saved['brief']=='Topic: original'
    stranger,*_=account()
    assert stranger.post(f'/drafts/{did}/title',data={'title':'Stolen','revision':1}).status_code==404


def test_title_validation_and_html_escaping():
    client,uid,*_=account()
    did=client.post('/api/drafts').json()['id']
    assert client.post(f'/drafts/{did}/title',data={'title':' '*3,'revision':0}).status_code==400
    assert client.post(f'/drafts/{did}/title',data={'title':'x'*121,'revision':0}).status_code==400
    assert client.post(f'/drafts/{did}/title',data={'title':'<script>alert(1)</script>','revision':0}).status_code==200
    assert '<h2><script>' not in client.get('/drafts').text


def test_work_summary_brand_scope_due_windows_and_statuses():
    client,uid,*_=account()
    with SessionLocal() as db:
        brand=Brand(user_id=uid,name='Other');db.add(brand);db.commit()
        for bid,status in [(0,'draft'),(0,'failed'),(brand.id,'draft')]:db.add(Draft(user_id=uid,brand_id=bid,status=status))
        for bid,days,status in [(0,1,'scheduled'),(0,-1,'scheduled'),(0,9,'scheduled'),(0,1,'cancelled'),(brand.id,1,'scheduled')]:
            db.add(ScheduledPost(user_id=uid,brand_id=bid,platform='instagram',content_json='{}',scheduled_at=utcnow()+timedelta(days=days),status=status))
        db.commit()
        result=work_summary(db,uid)
        assert result=={'drafts':1,'needs_review':1,'scheduled':1,'overdue':1,'unconfirmed':0}
    page=client.get('/studio').text
    assert '1 scheduled delivery is overdue' in page
    assert 'Pending does not mean published' in page


def test_explicit_empty_platform_selection_roundtrips_and_rejects_nonboolean():
    with SessionLocal() as db:
        result=clean_workspace({'selected_platforms':[],'platform_selection_explicit':True},db,1)
        assert result['selected_platforms']==[] and result['platform_selection_explicit'] is True
        assert clean_workspace({},db,1)['platform_selection_explicit'] is False
        with pytest.raises(HTTPException):clean_workspace({'platform_selection_explicit':'false'},db,1)


def test_signup_country_can_wait_but_invalid_supplied_country_rejected():
    email=secrets.token_hex(8)+'@example.test'
    client=TestClient(app)
    body={'email':email,'name':'New customer','password':'testing-password-1','password_confirmation':'testing-password-1','accept_terms':'yes'}
    rejected=client.post('/signup',data={**body,'country':'not a country'},follow_redirects=False)
    assert 'valid+country' in rejected.headers['location']
    result=client.post('/signup',data=body,follow_redirects=False)
    assert result.status_code==303 and result.headers['location']=='/onboarding/socials'
    with SessionLocal() as db:
        assert db.scalar(select(User).where(User.email==email)).country_code==''


def test_pending_delivery_has_actionable_filter_and_corrupt_legacy_title_survives():
    client,uid,*_=account()
    with SessionLocal() as db:
        draft=Draft(user_id=uid,brief='My pending post',workspace_json='broken',platforms_json='broken',status='pending')
        connection=SocialConnection(user_id=uid,platform='instagram',account_id='synthetic',encrypted_access_token='synthetic')
        db.add_all([draft,connection]);db.commit()
        db.add(Publication(user_id=uid,draft_id=draft.id,platform='instagram',connection_id=connection.id,review_code='synthetic',status='unknown'))
        db.add(ScheduledPost(user_id=uid,platform='instagram',content_json='{}',scheduled_at=utcnow()-timedelta(seconds=20),status='scheduled'))
        db.commit()
        assert work_summary(db,uid)['overdue']==0
    assert client.get('/api/drafts').status_code==200
    assert 'My pending post' in client.get('/drafts?status=awaiting_results').text
    assert 'Check publication results before retrying' in client.get('/studio').text


def test_title_migration_keeps_existing_draft_and_is_repeatable():
    from sqlalchemy import create_engine, text, inspect
    from nova.db import Base
    from nova.migrations import run_migrations
    engine=create_engine('sqlite:///:memory:')
    Base.metadata.create_all(engine)
    with engine.begin() as conn:
        conn.execute(text('ALTER TABLE nova_drafts DROP COLUMN title'))
        conn.execute(text("INSERT INTO nova_drafts(id,user_id,brand_id,brief,instruction,platforms_json,variants_json,workspace_json,revision,thread_length,status,created_at,updated_at) VALUES(1,1,0,'Keep this','','[]','{}','{}',7,1,'draft',CURRENT_TIMESTAMP,CURRENT_TIMESTAMP)"))
    run_migrations(engine);run_migrations(engine)
    assert 'title' in {c['name'] for c in inspect(engine).get_columns('nova_drafts')}
    with engine.connect() as conn:
        assert conn.execute(text('SELECT brief,revision,title FROM nova_drafts WHERE id=1')).one()==('Keep this',7,'')
