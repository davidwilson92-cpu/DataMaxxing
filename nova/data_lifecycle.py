"""Assisted account lifecycle. No public erase endpoint; operator verification required.

Call only after the operator has verified ownership and retention requirements.
Local-file erasure is retryable. Remote storage, active billing and uncertain
publication outcomes deliberately require operator reconciliation first.
"""
import hashlib
from pathlib import Path
from sqlalchemy import select, delete
from . import db as models
from .security import hash_password
from .storage import UPLOAD_DIR
import secrets

EXPORT = {
    models.User: ['id','email','display_name','country_code','created_at'],
    models.Brand: ['id','name'],
    models.CreatorPreferences: ['writing_tone','audience','topics','things_to_avoid','example_posts','timezone'],
    models.BrandVoice: ['brand_id','writing_tone','audience','topics','things_to_avoid','example_posts','timezone'],
    models.Draft: ['id','brand_id','brief','instruction','variants_json','workspace_json','status'],
    models.MediaAsset: ['id','brand_id','filename','mime_type','analysis_json'],
    models.SocialConnection: ['brand_id','platform','account_id','username','active'],
    models.Publication: ['id','brand_id','draft_id','platform','status','result_json'],
    models.ScheduledPost: ['id','brand_id','draft_id','platform','status','scheduled_at'],
    models.BillingAccount: ['mode','status','price_id','period_end','cancel_at_period_end'],
    models.UsageEntry: ['kind','period','amount','state'],
    models.ProductEvent: ['kind','created_at'],
    models.AICall: ['model','status','input_tokens','cached_tokens','output_tokens','estimated_gbp','rate_date'],
}


def rows(db, model, uid):
    key=model.id if model is models.User else model.user_id
    return db.scalars(select(model).where(key==uid).execution_options(all_brands=True)).all()


def export_account(db, uid):
    if db.info.get('brand_id') is not None:raise ValueError('Use a dedicated unscoped support session')
    if not db.get(models.User,uid):raise ValueError('Account not found')
    def serial(value):return value.isoformat() if hasattr(value,'isoformat') else value
    return {model.__tablename__:[{field:serial(getattr(row,field)) for field in fields} for row in rows(db,model,uid)] for model,fields in EXPORT.items()}


def erase_plan(db, uid):
    if db.info.get('brand_id') is not None:raise ValueError('Use a dedicated unscoped support session')
    if not db.get(models.User,uid):raise ValueError('Account not found')
    blockers=[]
    if any(r.status in {'scheduled','queued','publishing','pending','unknown'} for cls in [models.Publication,models.ScheduledPost] for r in rows(db,cls,uid)):
        blockers.append('Resolve scheduled or uncertain publishing outcomes first')
    if any(r.status in {'active','trialing','past_due','unpaid','incomplete','paused'} for r in rows(db,models.BillingAccount,uid)):
        blockers.append('Reconcile subscriptions and cancellation with the billing provider first')
    if rows(db,models.UserCreatorLink,uid):blockers.append('Legacy linked creator requires a separate credential and retention review')
    for asset in rows(db,models.MediaAsset,uid):
        if not asset.storage_key:continue
        shared=db.scalar(select(models.MediaAsset.id).where(models.MediaAsset.storage_key==asset.storage_key,models.MediaAsset.user_id!=uid).execution_options(all_brands=True).limit(1))
        if shared: blockers.append('Upload reference is shared with another account; investigate ownership first');break
        path=Path(asset.storage_key).resolve()
        if not path.is_relative_to(UPLOAD_DIR.resolve()):
            blockers.append('Remote or unexpected upload storage needs a verified storage-specific erasure process');break
    return {'user_id':uid,'blockers':blockers,'counts':{m.__tablename__:len(rows(db,m,uid)) for m in EXPORT},
        'retained':'Pseudonymous billing, usage and delivery ledger retained pending the operator-approved retention schedule. Backups and third-party posts are outside active-store erasure.'}


def erase_local_account(db, uid, verified_case, *, writes_paused=False):
    if not writes_paused:raise ValueError('Pause application writes and workers before assisted erasure')
    if not verified_case or len(verified_case.strip())<8:raise ValueError('Verified support case reference required')
    from .allowances import lock
    lock(db,uid)
    plan=erase_plan(db,uid)
    if plan['blockers']:db.rollback();raise ValueError('; '.join(plan['blockers']))
    user=db.get(models.User,uid)
    user.active=False;user.auth_version+=1
    user.password_hash=hash_password(secrets.token_urlsafe(32))
    case=hashlib.sha256(f'{uid}:{verified_case}'.encode()).hexdigest()
    request=db.get(models.DeletionRequest,case)
    if not request:
        request=models.DeletionRequest(code=case,subject_hash=hashlib.sha256(str(uid).encode()).hexdigest(),scope=plan['retained'])
        db.add(request)
    request.status='erasing';db.commit()  # Revoke access before storage operations.
    for asset in rows(db,models.MediaAsset,uid):
        if asset.storage_key:
            path=Path(asset.storage_key).resolve()
            if not path.is_relative_to(UPLOAD_DIR.resolve()):raise ValueError('Upload path escaped the configured storage root')
            path.unlink(missing_ok=True)
        asset.storage_key='';asset.public_url=None;asset.filename='erased'
    fields={
        models.CreatorPreferences:['writing_tone','audience','topics','things_to_avoid','example_posts'],
        models.BrandVoice:['writing_tone','audience','topics','things_to_avoid','example_posts'],
        models.Brand:['name'],
        models.Draft:['brief','instruction','variants_json','workspace_json'],
        models.PublishReview:['payload_json'],
        models.Activity:['text','error','url','platform_post_id','metrics_json'],
        models.Publication:['result_json'],
        models.ScheduledPost:['content_json','error','post_url','platform_post_id'],
        models.SocialConnection:['account_id','username','display_name','encrypted_access_token','encrypted_refresh_token','metadata_json','scope'],
    }
    for cls,names in fields.items():
        for row in rows(db,cls,uid):
            for name in names:setattr(row,name,'{}' if name.endswith('_json') else '')
            if cls is models.SocialConnection:row.active=False
            if cls is models.PublishReview:row.status='erased'
    for cls in [models.AuthIdentity,models.RecoveryToken,models.EmailVerification,models.OAuthState,models.PendingConnection,models.ProductEvent]:
        db.execute(delete(cls).where(cls.user_id==uid))
    user.email=f'erased-{uid}@deleted.invalid';user.display_name='Deleted account';user.default_brand_name='Deleted brand';user.country_code='';user.email_verified_at=None;user.marketing_consent=False
    request.status='active_store_erased';db.commit()
    return {'status':request.status,'scope':request.scope,'receipt':case}
