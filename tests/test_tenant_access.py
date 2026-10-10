import secrets
import pytest
from sqlalchemy import select, update
from fastapi import HTTPException
from nova.db import SessionLocal, User, Brand, TenantWorkspace, WorkspaceMembership, Publication
from nova.security import make_user_session, user_from_session
from nova.tenant_access import require_member, WorkspaceDenied
from nova.tenant_migration import workspace_key
from test_account_integrity import account
from test_reviewed_publication import prepared,review


def role_for(uid, role=None, active=True):
    with SessionLocal() as db:
        row=db.get(WorkspaceMembership,(workspace_key(uid),uid))
        if role is not None:row.role=role
        row.active=active
        db.commit()


def fresh_cookie(client,uid):
    client.cookies.clear()
    client.cookies.set('nova_session',make_user_session(uid))


def test_account_brand_and_memberships_are_atomic_and_isolated():
    _,uid,_,_=account();_,other,_,_=account()
    with SessionLocal() as db:
        brand=Brand(user_id=uid,name='Separate brand');db.add(brand);db.commit()
        assert db.get(TenantWorkspace,workspace_key(uid,brand.id)).owner_user_id==uid
        assert db.get(WorkspaceMembership,(workspace_key(uid,brand.id),uid)).role=='owner'
        assert db.get(WorkspaceMembership,(workspace_key(uid),other)) is None
        with pytest.raises(WorkspaceDenied):require_member(db,other,brand.id,'posts.read')
        transient=Brand(user_id=uid,name='Rolled back');db.add(transient);db.flush();key=workspace_key(uid,transient.id)
        db.rollback()
        assert db.get(TenantWorkspace,key) is None
        assert db.get(WorkspaceMembership,(key,uid)) is None


@pytest.mark.parametrize('role,read,create,publish',[
    ('owner',True,True,True),('admin',True,True,True),('publisher',True,True,True),
    ('creator',True,True,False),('viewer',True,False,False),('analyst',False,False,False)])
def test_existing_owner_role_is_enforced_server_side(role,read,create,publish):
    client,uid,_,_=account();role_for(uid,role);fresh_cookie(client,uid)
    assert (client.get('/api/drafts').status_code==200)==read
    response=client.post('/api/drafts',json={})
    assert response.status_code==(200 if create else 403)
    # Missing body data is not permission to reach the publisher; validation follows permission.
    response=client.post('/api/publish',json={})
    assert response.status_code==(422 if publish else 403)


def test_revocation_invalidates_session_and_fresh_login_does_not_restore_membership():
    client,uid,token,_=account();role_for(uid,active=False)
    assert user_from_session(token) is None
    fresh_cookie(client,uid)
    assert client.get('/studio').status_code==403
    assert client.post('/api/drafts',json={}).status_code==403
    with SessionLocal() as db:assert not db.get(WorkspaceMembership,(workspace_key(uid),uid)).active


def test_missing_membership_fails_closed_without_auto_repair():
    client,uid,_,_=account()
    with SessionLocal() as db:
        db.delete(db.get(WorkspaceMembership,(workspace_key(uid),uid)));db.commit()
    assert client.get('/api/drafts').status_code==403
    with SessionLocal() as db:assert db.get(WorkspaceMembership,(workspace_key(uid),uid)) is None


def test_current_permission_is_not_read_from_session_identity_cache():
    _,uid,_,_=account()
    with SessionLocal() as db:
        assert require_member(db,uid,0,'posts.publish')
        with SessionLocal() as other:
            other.execute(update(WorkspaceMembership).where(WorkspaceMembership.user_id==uid).values(active=False));other.commit()
        with pytest.raises(WorkspaceDenied):require_member(db,uid,0,'posts.publish')


def test_worker_rechecks_revocation_after_review_and_enqueue(monkeypatch):
    client,uid,_,body=prepared();approved=review(client,body)
    assert client.post('/api/publish',json=approved).status_code==200
    role_for(uid,active=False)
    calls=[]
    monkeypatch.setattr('nova.scheduler.publish_platform',lambda *a,**k:calls.append(k))
    from nova.scheduler import process_due
    process_due()
    with SessionLocal() as db:
        row=db.scalar(select(Publication).where(Publication.draft_id==body['draft_id']))
        assert row.status=='failed'
    assert not calls


def test_workspace_and_membership_ownership_cannot_be_reassigned():
    _,uid,_,_=account();_,other,_,_=account()
    with SessionLocal() as db:
        row=db.get(TenantWorkspace,workspace_key(uid));row.owner_user_id=other
        with pytest.raises(HTTPException,match='identity'):db.commit()
        db.rollback()
        row=db.get(WorkspaceMembership,(workspace_key(uid),uid));row.user_id=other
        with pytest.raises(HTTPException,match='identity'):db.commit()
        db.rollback()


def test_every_existing_api_mutation_has_an_explicit_permission():
    from nova.app import app
    from nova.tenant_access import request_capability
    from starlette.requests import Request
    for route in app.routes:
        path=getattr(route,'path','')
        if not path.startswith('/api/'):
            continue
        for method in getattr(route,'methods',set()) - {'GET','HEAD','OPTIONS'}:
            request=Request({'type':'http','method':method,'path':path,'route':route,'headers':[]})
            assert request_capability(request) not in {None,'__deny__'},(method,path)


def test_new_mutation_paths_fail_closed():
    from nova.tenant_access import request_capability
    from starlette.requests import Request
    for path in ['/api/unreviewed','/api/strategy/publish-new','/api/series/send-new']:
        assert request_capability(Request({'type':'http','method':'POST','path':path,'headers':[]}))=='__deny__'


def test_new_membership_defaults_do_not_grant_access():
    _,uid,_,_=account();_,other,_,_=account()
    with SessionLocal() as db:
        member=WorkspaceMembership(workspace_id=workspace_key(uid),user_id=other)
        db.add(member);db.flush()
        assert member.role=='viewer' and not member.active
        db.rollback()
