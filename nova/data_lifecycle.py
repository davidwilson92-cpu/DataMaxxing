"""Assisted account lifecycle. No public erase endpoint; operator verification required.

Call only after the operator has verified ownership and retention requirements.
Local-file erasure is retryable. Remote storage, active billing and uncertain
publication outcomes deliberately require operator reconciliation first.
"""
import hashlib
import re
from pathlib import Path
from sqlalchemy import select, delete
from . import db as models
from .security import hash_password, hash_api_key
from .storage import UPLOAD_DIR
import secrets

ERASE_FIELDS={
    models.CreatorPreferences:['writing_tone','audience','topics','things_to_avoid','example_posts','learned_json'],
    models.BrandVoice:['writing_tone','audience','topics','things_to_avoid','example_posts','learned_json'],
    models.Brand:['name'],
    models.Draft:['title','brief','instruction','variants_json','workspace_json','platforms_json'],
    models.PublishReview:['payload_json'],
    models.Activity:['text','error','url','platform_post_id','metrics_json'],
    models.Publication:['result_json'],
    models.ScheduledPost:['content_json','error','post_url','platform_post_id','media_asset_ids_json'],
    models.SocialConnection:['account_id','username','display_name','encrypted_access_token','encrypted_refresh_token','encrypted_audio_user_token','metadata_json','scope'],
}
ERASE_ROWS=[models.AIConsent,models.SeriesApproval,models.SeriesOccurrence,models.ContentSeries,models.StrategyAction,
    models.Strategy,models.PerformanceSnapshot,models.AuthIdentity,models.RecoveryToken,models.EmailVerification,
    models.OAuthState,models.PendingConnection,models.ProductEvent]


def empty_field(name):
    return ('[]' if name in {'platforms_json','media_asset_ids_json'} else '{}') if name.endswith('_json') else ''

EXPORT = {
    models.PerformanceSnapshot: ['brand_id','payload_json','fetched_at'],
    models.SeriesApproval: ['brand_id','series_id','revision','payload_json','expires_at'],
    models.Strategy: ['brand_id','confirmed_json','proposal_json','revision'],
    models.StrategyAction: ['brand_id','payload_json','status','feedback','draft_id'],
    models.ContentSeries: ['id','brand_id','spec_json','status'],
    models.SeriesOccurrence: ['series_id','brand_id','draft_id','due_at','status'],
    models.User: ['id','email','display_name','country_code','created_at'],
    models.Brand: ['id','name'],
    models.CreatorPreferences: ['writing_tone','audience','topics','things_to_avoid','example_posts','learned_json','timezone'],
    models.BrandVoice: ['brand_id','writing_tone','audience','topics','things_to_avoid','example_posts','learned_json','timezone'],
    models.Draft: ['id','brand_id','title','brief','instruction','variants_json','workspace_json','status'],
    models.MediaAsset: ['id','brand_id','filename','mime_type','analysis_json'],
    models.SocialConnection: ['brand_id','platform','account_id','username','active'],
    models.Publication: ['id','brand_id','draft_id','platform','status','result_json'],
    models.ScheduledPost: ['id','brand_id','draft_id','platform','status','scheduled_at'],
    models.BillingAccount: ['mode','status','price_id','period_end','cancel_at_period_end'],
    models.UsageEntry: ['kind','period','amount','state'],
    models.ProductEvent: ['kind','created_at'],
    models.AIConsent: ['version','allowed','updated_at'],
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
    foreign_keys=db.scalars(select(models.MediaAsset.storage_key).where(models.MediaAsset.user_id!=uid).execution_options(all_brands=True)).all()
    for asset in rows(db,models.MediaAsset,uid):
        if not asset.storage_key:continue
        shared=db.scalar(select(models.MediaAsset.id).where(models.MediaAsset.storage_key==asset.storage_key,models.MediaAsset.user_id!=uid).execution_options(all_brands=True).limit(1))
        if shared: blockers.append('Upload reference is shared with another account; investigate ownership first');break
        raw=Path(asset.storage_key)
        path=raw.resolve()
        if raw.is_symlink() or not path.is_relative_to(UPLOAD_DIR.resolve()) or (path.exists() and not path.is_file()):
            blockers.append('Remote or unexpected upload storage needs a verified storage-specific erasure process');break
        # Different spellings or hardlinks must not erase another owner's upload.
        if any(key and (Path(key).resolve()==path or (path.exists() and Path(key).exists() and path.samefile(Path(key)))) for key in foreign_keys):
            blockers.append('Upload reference is shared with another account; investigate ownership first');break
    return {'user_id':uid,'blockers':blockers,'counts':{m.__tablename__:len(rows(db,m,uid)) for m in EXPORT},
        'retained':'Pseudonymous billing, usage and delivery ledger retained pending the operator-approved retention schedule. Backups and third-party posts are outside active-store erasure.'}


def verify_active_erasure(db,uid,removed_paths=()):
    """Read back committed cleanup. Never turn a partial cleanup into completion."""
    db.expire_all()
    user=db.get(models.User,uid)
    if not user or user.active or user.email!=f'erased-{uid}@deleted.invalid' or user.display_name!='Deleted account':
        raise ValueError('Account identity cleanup is incomplete')
    for cls,names in ERASE_FIELDS.items():
        for row in rows(db,cls,uid):
            if any(getattr(row,name)!=empty_field(name) for name in names):
                raise ValueError('Account content cleanup is incomplete')
            if cls is models.SocialConnection and (row.active or row.expires_at or row.audio_user_token_expires_at):
                raise ValueError('Connection credential cleanup is incomplete')
    for cls in ERASE_ROWS+[models.MobileSession,models.MobileGrant]:
        if rows(db,cls,uid):raise ValueError('Account authority or profile cleanup is incomplete')
    for asset in rows(db,models.MediaAsset,uid):
        if asset.storage_key or asset.public_url or asset.analysis_json!='{}' or asset.filename!='erased' or asset.size_bytes:
            raise ValueError('Media cleanup is incomplete')
    if any(Path(path).exists() for path in removed_paths):raise ValueError('Upload file cleanup is incomplete')
    for row in rows(db,models.BillingAccount,uid):
        if row.checkout_payload or row.checkout_key or row.checkout_session:raise ValueError('Checkout cleanup is incomplete')
    return True


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
    receipts = db.scalars(select(models.DeletionRequest).where(
        models.DeletionRequest.subject_hash.in_((hash_api_key(f'account:{uid}'),hashlib.sha256(str(uid).encode()).hexdigest())),
        models.DeletionRequest.status.in_(('received', 'access_revoked', 'erasing','active_store_erased')))).all()
    receipts=[receipt for receipt in receipts if receipt.subject_hash==hash_api_key(f'account:{uid}')
              or re.fullmatch(r'[0-9a-f]{64}',receipt.code)]
    # Prefer the customer's existing receipt; don't create a second queue entry
    # for each operator case/retry. Include old helper receipts in cleanup so a
    # prior interrupted case cannot remain permanently in the manual queue.
    request=next((receipt for receipt in receipts if receipt.subject_hash==hash_api_key(f'account:{uid}')),None)
    if request is None:
        request=db.get(models.DeletionRequest,case)
    if request is None:
        request=models.DeletionRequest(code=case,subject_hash=hash_api_key(f'account:{uid}'),scope=plan['retained'])
        db.add(request)
    for receipt in receipts:
        receipt.status='erasing';receipt.scope=plan['retained'];receipt.completed_at=None
    request.status='erasing';request.completed_at=None;db.commit()  # Revoke access before storage operations.
    removed_paths=[]
    for asset in rows(db,models.MediaAsset,uid):
        if asset.storage_key:
            raw=Path(asset.storage_key);path=raw.resolve()
            if raw.is_symlink() or not path.is_relative_to(UPLOAD_DIR.resolve()):raise ValueError('Upload path escaped the configured storage root')
            path.unlink(missing_ok=True)
            removed_paths.append(path)
        asset.storage_key='';asset.public_url=None;asset.filename='erased'
        asset.size_bytes=0;asset.mime_type='application/octet-stream'
        # Derived observations and fingerprints are customer content, even without a file.
        asset.analysis_json='{}'
    for cls,names in ERASE_FIELDS.items():
        for row in rows(db,cls,uid):
            for name in names:setattr(row,name,empty_field(name))
            if cls is models.SocialConnection:row.active=False
            if cls is models.SocialConnection:row.audio_user_token_expires_at=None;row.expires_at=None
            if cls in (models.CreatorPreferences,models.BrandVoice):row.timezone='UTC';row.preferred_post_length=220
            if cls is models.PublishReview:row.status='erased'
    for cls in ERASE_ROWS:
        db.execute(delete(cls).where(cls.user_id==uid))
    device_ids=select(models.MobileSession.id).where(models.MobileSession.user_id==uid)
    db.execute(delete(models.MobileHandoff).where(models.MobileHandoff.session_id.in_(device_ids)))
    db.execute(delete(models.MobileRefresh).where(models.MobileRefresh.session_id.in_(device_ids)))
    db.execute(delete(models.MobileSession).where(models.MobileSession.user_id==uid))
    db.execute(delete(models.MobileGrant).where(models.MobileGrant.user_id==uid))
    for row in rows(db,models.BillingAccount,uid):
        row.checkout_payload=None;row.checkout_key=None;row.checkout_session=None;row.checkout_started=None
    user.email=f'erased-{uid}@deleted.invalid';user.display_name='Deleted account';user.default_brand_name='Deleted brand';user.country_code='';user.email_verified_at=None;user.marketing_consent=False;user.marketing_consent_at=None;user.last_login_at=None
    user.stripe_customer_id=None;user.stripe_subscription_id=None
    db.commit()
    verify_active_erasure(db,uid,removed_paths)
    completed=models.utcnow()
    for receipt in receipts:receipt.status='active_store_erased';receipt.completed_at=completed
    request.status='active_store_erased';request.completed_at=completed;db.commit()
    return {'status':request.status,'scope':request.scope,'receipt':request.code}
