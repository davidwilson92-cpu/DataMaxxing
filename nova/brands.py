"""Brand boundaries for web sessions; legacy data belongs to workspace zero."""
from fastapi import HTTPException
from sqlalchemy import event, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, with_loader_criteria
from .db import (Brand, BrandVoice, BrandScoped, SessionLocal, CreatorPreferences)


def bind_request(db, request):
    from .security import user_from_session
    user = user_from_session(request.cookies.get('nova_session'))
    if not user:
        return
    raw = request.headers.get('X-Zova-Brand', request.query_params.get('workspace', request.cookies.get('zova_brand', '0')))
    try:
        brand_id = int(raw)
    except (ValueError, TypeError):
        raise HTTPException(400, 'Invalid brand workspace')
    if brand_id:
        brand = db.get(Brand, brand_id)
        if not brand or brand.user_id != user.id:
            if 'X-Zova-Brand' in request.headers or 'workspace' in request.query_params:
                raise HTTPException(404, 'Brand workspace not found')
            brand_id=0  # A cookie from another signed-in account is not authority.
    db.info.update(brand_id=brand_id, brand_user_id=user.id)
    request.state.brand_id = brand_id


@event.listens_for(Session, 'do_orm_execute')
def scope_queries(state):
    if 'brand_id' not in state.session.info or state.execution_options.get('all_brands'):
        return
    brand_id = state.session.info['brand_id']
    user_id = state.session.info['brand_user_id']
    state.statement = state.statement.options(with_loader_criteria(
        BrandScoped, lambda cls: (cls.brand_id == brand_id) & (cls.user_id == user_id), include_aliases=True))


@event.listens_for(Session, 'before_flush')
def scope_writes(db, context, instances):
    if 'brand_id' not in db.info:
        return
    for row in db.new.union(db.dirty).union(db.deleted):
        if not isinstance(row, BrandScoped):
            continue
        if row.user_id != db.info['brand_user_id']:
            raise HTTPException(404, 'Workspace item not found')
        if row in db.new:
            row.brand_id = db.info['brand_id']
        elif row.brand_id != db.info['brand_id']:
            raise HTTPException(404, 'Workspace item not found')


def context(user, brand_id=0):
    with SessionLocal() as db:
        rows = db.scalars(select(Brand).where(Brand.user_id == user.id).order_by(Brand.id)).all()
        choices = [{'id': 0, 'name': user.default_brand_name}] + [{'id': row.id, 'name': row.name} for row in rows]
    return {'id': brand_id, 'name': next((b['name'] for b in choices if b['id'] == brand_id), 'My brand'), 'choices': choices}


def voice(db, user_id):
    brand_id = db.info.get('brand_id', 0)
    if not brand_id:
        return None
    row = db.scalar(select(BrandVoice).where(BrandVoice.user_id == user_id, BrandVoice.brand_id == brand_id))
    if not row:
        row = BrandVoice(user_id=user_id, brand_id=brand_id)
        db.add(row)
        try:db.commit(); db.refresh(row)
        except IntegrityError:
            db.rollback()
            row=db.scalar(select(BrandVoice).where(BrandVoice.user_id==user_id,BrandVoice.brand_id==brand_id))
            if row is None:raise
    return row
