from datetime import datetime, timedelta, timezone
from sqlalchemy import select, delete
import pytest
from nova.db import SessionLocal, ScheduledPost, Brand
from test_account_integrity import account

START=datetime(2026,10,5,tzinfo=timezone.utc)
END=START+timedelta(days=7)


@pytest.fixture(autouse=True)
def cleanup_window_jobs():
    # This file deliberately creates a backlog larger than a worker batch.
    # Do not leak it into worker-boundary tests that expect two polling passes.
    with SessionLocal() as db:
        existing = set(db.scalars(select(ScheduledPost.id)).all())
    yield
    with SessionLocal() as db:
        added = set(db.scalars(select(ScheduledPost.id)).all()) - existing
        if added:
            db.execute(delete(ScheduledPost).where(ScheduledPost.id.in_(added)))
            db.commit()


def add_jobs(db,uid,times,brand=0):
    rows=[ScheduledPost(user_id=uid,brand_id=brand,platform='x',content_json='{}',scheduled_at=when,status='scheduled') for when in times]
    db.add_all(rows);db.flush()
    return [row.id for row in rows]


def window():return {'from':START.isoformat(),'to':END.isoformat()}


def test_window_filters_before_limit_and_preserves_default_array():
    client,uid,*_=account()
    with SessionLocal() as db:
        within=add_jobs(db,uid,[START,END-timedelta(microseconds=1)])
        add_jobs(db,uid,[START-timedelta(seconds=1),END])
        add_jobs(db,uid,[END+timedelta(days=20,minutes=i) for i in range(105)])
        db.commit()
    default=client.get('/api/schedules')
    assert isinstance(default.json(),list) and len(default.json())==100
    assert default.headers['X-Zova-Has-More']=='true'
    assert not set(within).intersection(row['id'] for row in default.json())
    response=client.get('/api/schedules',params=window())
    assert response.status_code==200
    assert {row['id'] for row in response.json()}==set(within)
    assert response.headers['X-Zova-Has-More']=='false'


def test_exact_limit_is_not_reported_as_truncated_and_brands_are_isolated():
    client,uid,*_=account();_,other,*_=account()
    with SessionLocal() as db:
        b=Brand(user_id=uid,name='Other brand');db.add(b);db.flush();brand=b.id
        expected=add_jobs(db,uid,[START+timedelta(minutes=i) for i in range(100)])
        branded=add_jobs(db,uid,[START+timedelta(hours=2)],brand)
        add_jobs(db,other,[START]);db.commit()
    response=client.get('/api/schedules',params=window())
    assert len(response.json())==100 and {r['id'] for r in response.json()}==set(expected)
    assert response.headers['X-Zova-Has-More']=='false'
    response=client.get('/api/schedules',params={**window(),'workspace':brand})
    assert [r['id'] for r in response.json()]==branded
    with SessionLocal() as db:add_jobs(db,uid,[START+timedelta(hours=3)]);db.commit()
    assert client.get('/api/schedules',params=window()).headers['X-Zova-Has-More']=='true'


@pytest.mark.parametrize('params',[
    {'from':START.isoformat()}, {'to':END.isoformat()},
    {'from':'invalid','to':END.isoformat()},
    {'from':'2026-10-05T00:00:00','to':END.isoformat()},
    {'from':'2026-10-05T00:00:00+01:00','to':END.isoformat()},
    {'from':END.isoformat(),'to':START.isoformat()},
    {'from':START.isoformat(),'to':START.isoformat()},
    {'from':START.isoformat(),'to':(START+timedelta(days=33)).isoformat()},
])
def test_invalid_schedule_window_is_rejected(params):
    client,*_=account()
    assert client.get('/api/schedules',params=params).status_code==400
