import json
import secrets

import pytest

from nova.db import SessionLocal, Draft, PublishReview, Publication, SocialConnection
from nova.publishing_workflow import publication_connection, reconcile_instagram
from nova.security import encrypt
from test_account_integrity import account


@pytest.mark.parametrize('mismatch', ['connection_brand','draft_brand','review_brand','account','missing_connection','valid'])
def test_reconciliation_requires_exact_reviewed_boundary(mismatch, monkeypatch):
    _, uid, _, _ = account()
    with SessionLocal() as db:
        draft=Draft(user_id=uid,brand_id=1 if mismatch=='draft_brand' else 0)
        conn=SocialConnection(user_id=uid,brand_id=1 if mismatch=='connection_brand' else 0,
                              platform='instagram',account_id='expected',encrypted_access_token=encrypt('synthetic'))
        db.add_all([draft,conn]);db.flush()
        review=PublishReview(code=secrets.token_hex(16),user_id=uid,
                             brand_id=1 if mismatch=='review_brand' else 0,draft_id=draft.id,revision=0,
                             payload_json=json.dumps({'targets':{'instagram':{'connection_id':conn.id,
                             'account_id':'changed' if mismatch=='account' else 'expected'}}}))
        from nova.db import utcnow
        review.expires_at=utcnow()
        db.add(review);db.flush()
        row=Publication(user_id=uid,draft_id=draft.id,platform='instagram',review_code=review.code,
                        connection_id=conn.id,
                        status='unknown',result_json=json.dumps({'container_id':'synthetic-container'}))
        db.add(row);db.commit()
        if mismatch=='missing_connection':row.connection_id=None
        if mismatch=='valid':
            assert publication_connection(db,row).id==conn.id
        else:
            with pytest.raises(RuntimeError):publication_connection(db,row)
            monkeypatch.setattr('httpx.get',lambda *a,**k:pytest.fail('Wrong-account provider access'))
            reconcile_instagram(db,row)
            assert row.status=='unknown'
