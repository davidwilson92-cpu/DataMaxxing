"""Read-only, workspace-owned media selection; reuse never copies or deletes assets."""
import json
from collections import defaultdict

from fastapi import APIRouter, Depends, Query, Request, Response
from sqlalchemy import select

from .db import Draft, MediaAsset, Publication, PublishReview, ScheduledPost, Campaign, CampaignBriefDraft, get_db
from .security import current_user

router = APIRouter()


def object_json(raw):
    try:
        value = json.loads(raw or '{}')
        return value if isinstance(value, dict) else {}
    except (ValueError, TypeError):
        return {}


def media_ids(value):
    return {i for i in value if type(i) is int and i > 0} if isinstance(value, list) else set()


def library_usage(db, uid, ids):
    """Use confirmed publication snapshots, not a draft's aggregate status.

    Read narrow columns in batches. An attachment can be both published and planned.
    Conversation-only historic attachments are retained, but not called scheduled.
    """
    brand = db.info.get('brand_id', 0)
    usage = defaultdict(lambda: {'states': set(), 'uses': []})
    drafts = {}
    for did, title, brief, raw in db.execute(select(Draft.id, Draft.title, Draft.brief, Draft.workspace_json).where(
            Draft.user_id == uid, Draft.brand_id == brand)):
        drafts[did] = ' '.join((title or brief or 'Untitled post').split())[:120]
        workspace = object_json(raw)
        saved_ids = media_ids(workspace.get('media_asset_ids')) | media_ids(workspace.get('pending_media_asset_ids'))
        for message in workspace.get('conversation', []) if isinstance(workspace.get('conversation'), list) else []:
            if isinstance(message, dict): saved_ids |= media_ids(message.get('media_asset_ids'))
        for aid in saved_ids & ids:
            usage[aid]['states'].add('saved')
            usage[aid]['uses'].append({'draft_id': did, 'title': drafts[did], 'state': 'saved'})
    for did, status, raw in db.execute(select(Publication.draft_id, Publication.status, PublishReview.payload_json)
            .join(PublishReview, (PublishReview.code == Publication.review_code) &
                  (PublishReview.user_id == Publication.user_id) & (PublishReview.brand_id == Publication.brand_id) &
                  (PublishReview.draft_id == Publication.draft_id))
            .where(Publication.user_id == uid, Publication.brand_id == brand)):
        state = {'published': 'published', 'scheduled': 'planned', 'pending': 'processing',
                 'publishing': 'unconfirmed', 'unknown': 'unconfirmed', 'queued': 'processing',
                 'failed': 'needs_attention'}.get(status)
        if not state:
            continue
        for aid in media_ids(object_json(raw).get('media_asset_ids')) & ids:
            usage[aid]['states'].add(state)
            usage[aid]['uses'].append({'draft_id': did, 'title': drafts.get(did, 'Retained post'), 'state': state})
    for sid, did, raw in db.execute(select(ScheduledPost.id, ScheduledPost.draft_id, ScheduledPost.media_asset_ids_json).where(
            ScheduledPost.user_id == uid, ScheduledPost.brand_id == brand, ScheduledPost.status == 'scheduled')):
        try: scheduled_ids = media_ids(json.loads(raw))
        except (ValueError, TypeError): scheduled_ids = set()
        for aid in scheduled_ids & ids:
            usage[aid]['states'].add('planned')
            usage[aid]['uses'].append({'draft_id': did, 'schedule_id': sid, 'title': drafts.get(did, 'Scheduled post'), 'state': 'planned'})
    for cid, raw in db.execute(select(Campaign.id, Campaign.payload_json).where(Campaign.user_id == uid, Campaign.brand_id == brand)):
        value = object_json(raw)
        for asset in value.get('assets', []) if isinstance(value.get('assets'), list) else []:
            if isinstance(asset, dict) and type(asset.get('id')) is int and asset['id'] in ids:
                usage[asset['id']]['states'].add('saved')
                usage[asset['id']]['uses'].append({'campaign_id': cid, 'title': value.get('name') or 'Saved campaign', 'state': 'saved'})
    for raw in db.scalars(select(CampaignBriefDraft.payload_json).where(CampaignBriefDraft.user_id == uid, CampaignBriefDraft.brand_id == brand)):
        for aid in media_ids(object_json(raw).get('media')) & ids:
            usage[aid]['states'].add('saved')
    for used in usage.values():
        references = {}
        for ref in used['uses']:
            key = ('draft', ref['draft_id']) if ref.get('draft_id') else ('campaign', ref['campaign_id']) if ref.get('campaign_id') else ('schedule', ref['schedule_id'])
            if key not in references: references[key] = {**ref, 'states': set()}
            references[key]['states'].add(ref['state'])
        used['uses'] = [{**ref, 'state': ' · '.join(sorted(ref['states'])), 'states': sorted(ref['states'])} for ref in references.values()]
    return usage


@router.get('/api/media/library')
def library(request: Request, response: Response, q: str = Query('', max_length=100),
            kind: str = Query('all', pattern='^(all|image|video)$'),
            before: int | None = Query(None, gt=0), limit: int = Query(30, ge=1, le=50), db=Depends(get_db)):
    uid = current_user(request).id
    query = select(MediaAsset).where(MediaAsset.user_id == uid, MediaAsset.brand_id == db.info.get('brand_id', 0))
    if before is not None:
        query = query.where(MediaAsset.id < before)
    if q.strip():
        query = query.where(MediaAsset.filename.icontains(q.strip(), autoescape=True))
    if kind != 'all':
        query = query.where(MediaAsset.mime_type.startswith(kind + '/'))
    rows = list(db.scalars(query.order_by(MediaAsset.id.desc()).limit(limit + 1)))
    more = len(rows) > limit
    rows = rows[:limit]
    usage = library_usage(db, uid, {row.id for row in rows}) if rows else {}
    assets = []
    for row in rows:
        used = usage.get(row.id, {'states': set(), 'uses': []})
        assets.append({'id': row.id, 'filename': row.filename,
            'kind': 'video' if row.mime_type.startswith('video/') else 'image', 'mime_type': row.mime_type,
            'url': f'/media/preview/{row.id}', 'thumbnail': f'/media/thumbnail/{row.id}',
            'size_bytes': row.size_bytes, 'states': sorted(used['states']) or ['unused'],
            'uses': list({json.dumps(u, sort_keys=True): u for u in used['uses']}.values())})
    response.headers['Cache-Control'] = 'no-store'
    return {'assets': assets, 'next_before': rows[-1].id if more else None}
