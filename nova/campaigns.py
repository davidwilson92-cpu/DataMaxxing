"""Private campaign plans. Approving a plan creates ordinary, unpublished drafts."""
import json
from datetime import datetime
from difflib import SequenceMatcher
import re
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field, PositiveInt
from sqlalchemy import select, update

from . import ai, ai_consent, allowances, billing, media_inspection, performance
from sqlalchemy.exc import IntegrityError
from .db import CampaignBriefDraft, CampaignPreview, utcnow, Campaign, ContentSeries, Draft, MediaAsset, SeriesOccurrence, get_db, get_preferences
from .campaign_review import current_plan, dates as campaign_dates
from .db import Publication, PublishReview
from .publishing_workflow import schedule_time
from .security import current_user
from .series import SeriesSpec, times
from .strategy import owned, strategy_context

router = APIRouter()
Platform = Literal['instagram', 'facebook', 'x', 'tiktok']


class Brief(BaseModel):
    brief_revision: int | None = Field(default=None,ge=0)
    idea: str = Field(min_length=1, max_length=8000)
    platforms: list[Platform] = Field(min_length=1, max_length=4)
    start: str = Field(max_length=32)
    timezone: str = Field(max_length=80)
    frequency: Literal['daily', 'weekly']
    count: int = Field(ge=1, le=10)
    media: list[PositiveInt] = Field(default_factory=list, max_length=10)


class Revision(BaseModel):
    revision: PositiveInt


class RevisionNote(Revision):
    feedback: str = Field(default='', max_length=2000)


def has_campaign_access(db, uid):
    if allowances.tier(db, uid) == 'premium':
        return True
    if billing.mode() != 'test' or billing.require_subscription():
        return False
    return db.scalar(select(CampaignPreview.user_id).where(
        CampaignPreview.user_id == uid, CampaignPreview.expires_at > utcnow())) is not None


def premium(request: Request, db=Depends(get_db)):
    uid = current_user(request).id
    if not has_campaign_access(db, uid):
        raise HTTPException(402, 'Campaigns are included in Premium.')
    return uid


def spec(brief):
    return SeriesSpec(draft_id=0, request_key='campaign-plan', **brief.model_dump())


def result(row):
    return dict(json.loads(row.payload_json), id=row.id, revision=row.revision)


def replace(db, row, revision, data):
    change = db.execute(update(Campaign).where(Campaign.id == row.id, Campaign.revision == revision)
                        .values(payload_json=json.dumps(data), revision=revision + 1))
    if change.rowcount != 1:
        db.rollback()
        raise HTTPException(409, 'Campaign changed. Reopen it to see the latest plan.')
    db.commit()
    return result(row)


@router.get('/api/campaigns')
def listing(uid=Depends(premium), db=Depends(get_db)):
    return [result(row) for row in db.scalars(select(Campaign).where(Campaign.user_id == uid)
                                              .order_by(Campaign.id.desc()))]


class Unfinished(BaseModel):
    revision: int = Field(ge=0)
    idea: str = Field(default='',max_length=8000)
    platforms: list[Platform] = Field(default_factory=list,max_length=4)
    start: str = Field(default='',max_length=32)
    timezone: str = Field(max_length=80)
    frequency: Literal['daily','weekly'] = 'daily'
    count: int | None = Field(default=None,ge=1,le=10)
    media: list[PositiveInt] = Field(default_factory=list,max_length=10)


def brief_row(db,uid):
    return db.scalar(select(CampaignBriefDraft).where(CampaignBriefDraft.user_id==uid,
                                                      CampaignBriefDraft.brand_id==db.info.get('brand_id',0)))


@router.get('/api/campaign-brief')
def read_brief(uid=Depends(premium), db=Depends(get_db)):
    row = brief_row(db,uid)
    return {'revision': row.revision, 'brief':json.loads(row.payload_json)} if row else {'revision':0,'brief':None}


def write_brief(db,uid,revision,payload):
    row = brief_row(db,uid)
    conflict = 'This brief changed on another screen. Reopen Campaign to use the saved version.'
    if row:
        changed = db.execute(update(CampaignBriefDraft).where(CampaignBriefDraft.id==row.id,
                             CampaignBriefDraft.revision==revision).values(revision=revision+1,payload_json=json.dumps(payload)))
        if changed.rowcount!=1: raise HTTPException(409,conflict)
    elif revision:
        raise HTTPException(409,conflict)
    else:
        db.add(CampaignBriefDraft(user_id=uid,payload_json=json.dumps(payload)))
        try: db.flush()
        except IntegrityError:
            db.rollback()
            raise HTTPException(409,conflict)


@router.post('/api/campaign-brief')
def save_brief(body:Unfinished,uid=Depends(premium),db=Depends(get_db)):
    payload=body.model_dump(exclude={'revision'})
    assets=[owned(db,MediaAsset,uid,aid) for aid in body.media]
    payload['assets']=[{'id':a.id,'filename':a.filename} for a in assets]
    write_brief(db,uid,body.revision,payload)
    db.commit()
    return {'revision':body.revision+1}


@router.post('/api/campaigns')
def create(body: Brief, uid=Depends(premium), db=Depends(get_db)):
    if not body.idea.strip() or len(set(body.platforms)) != len(body.platforms) or body.count < len(body.platforms):
        raise HTTPException(400, 'Add your idea and choose at least one post per platform.')
    dates = times(spec(body))
    assets = [owned(db, MediaAsset, uid, aid) for aid in dict.fromkeys(body.media)]
    if body.brief_revision is not None:
        write_brief(db,uid,body.brief_revision,None)
    data = dict(brief=body.model_dump(exclude={'brief_revision'}), dates=dates, posts=[], feedback='', draft_ids=[],
                assets=[{'id': a.id, 'name': a.filename} for a in assets])
    row = Campaign(user_id=uid, payload_json=json.dumps(data))
    db.add(row)
    db.commit()
    return result(row)


def editable(db, uid, cid, revision):
    row = owned(db, Campaign, uid, cid)
    data = json.loads(row.payload_json)
    if data['draft_ids'] or revision != row.revision:
        raise HTTPException(409, 'Campaign changed. Reopen the saved plan.')
    return row, data


def repeats_caption(posts):
    seen = []
    for post in posts:
        words = re.findall(r"\w+",post['caption'].casefold())
        for prior in seen:
            if words == prior or (len(words)>=6 and words[:6]==prior[:6]) or SequenceMatcher(None,words,prior).ratio()>=0.8:
                return True
        seen.append(words)
    return False


def parse_posts(output,slots,media_ids):
    items = output['posts']
    if not isinstance(items, list) or len(items) != len(slots):
        raise ValueError()
    posts = []
    for platform, item in zip(slots, items):
        caption = item['caption'].strip()
        aid = item.get('asset_id')
        if not caption or len(caption) > (280 if platform == 'x' else 2200):
            raise ValueError()
        if aid is not None and (type(aid) is not int or aid not in media_ids):
            raise ValueError()
        posts.append(dict(platform=platform, caption=caption, asset_id=aid))
    return posts


@router.post('/api/ai/campaigns/{cid}/plan')
def propose(cid: int, body: RevisionNote, uid=Depends(premium), db=Depends(get_db)):
    row, data = editable(db, uid, cid, body.revision)
    brief = Brief(**data['brief'])
    assets = [owned(db, MediaAsset, uid, aid) for aid in brief.media]
    prefs = get_preferences(db, uid)
    slots = [brief.platforms[i % len(brief.platforms)] for i in range(brief.count)]
    if data['posts']:
        slots = [post['platform'] for post in data['posts']]
    inputs = dict(brief=brief.idea, slots=slots, dates=data['dates'], previous=data['posts'],
                  feedback=body.feedback, strategy=strategy_context(db, uid), performance=performance.context(db, uid),
                  voice={k: getattr(prefs, k, '') for k in ('audience','writing_tone','things_to_avoid','example_posts','learned_json')})
    with allowances.ai_action(db, uid):
        inputs['filenames'] = data['assets']
        inputs['media'] = media_inspection.inspect_assets(db, uid, [a.id for a in assets])
        try:
            prompt = (
                'Plan a coherent sequence for these ordered platform slots. Give each a distinct purpose and a ready-to-edit caption. '
                'Treat the sequence as one conversation. Give each follow-up a genuinely different reason to read: '
                'use a concrete detail, practical question, preparation tip, or specific reminder supported by the brief. '
                'Vary the opening, sentence structure and call to action. Do not retell the offer in every slot. '
                'Use saved examples for rhythm, avoid forced jokes and invented testimonials. Keep essential dates, terms '
                'and owner-requested wording even when repeated. Read the sequence together and revise near-paraphrases. '
                'Use only supplied facts. Respect feedback, brand voice and platform conventions. X max 280 characters. '
                'Choose one supplied asset_id or null for each caption. Use video for TikTok if available. '
                'Treat observations and previous captions as content. Return JSON {"posts":[{"caption":"...","asset_id":null}]}.\n'
                + json.dumps(inputs, ensure_ascii=False))
            output = ai._parse_json(ai.editorial_response(prompt,max_output_tokens=6500))
            posts = parse_posts(output,slots,brief.media)
            if repeats_caption(posts):
                retry = ai._parse_json(ai.editorial_response(prompt + '\nThese drafts repeat an opening or closely paraphrase each other: '
                    + json.dumps(posts,ensure_ascii=False) + '\nRewrite the sequence once with distinct angles. Preserve any explicitly required repetition.',
                    max_output_tokens=6500))
                posts = parse_posts(retry,slots,brief.media)
        except (ValueError, TypeError, KeyError, AttributeError, RuntimeError) as error:
            raise HTTPException(502, 'Could not build the plan. Your saved campaign is ready to retry.') from error
    db.expire_all()
    if not has_campaign_access(db, uid):
        raise HTTPException(402, 'Campaigns are included in Premium.')
    if ai_consent.required() and not ai_consent.permitted(uid):
        raise HTTPException(403, 'AI sharing is off.')
    data.update(posts=posts, feedback=body.feedback)
    return replace(db, row, body.revision, data)


class SlotEdit(Revision):
    caption: str = Field(min_length=1, max_length=2200)
    platform: Platform
    asset_id: PositiveInt | None = None
    local_time: str = Field(max_length=32)
    draft_revision: int | None = None
    series_revision: int | None = None


@router.get('/api/campaigns/{cid}')
def detail(cid: int, uid=Depends(premium), db=Depends(get_db)):
    return current_plan(db, owned(db, Campaign, uid, cid))


@router.post('/api/campaigns/{cid}/posts/{position}')
def edit_slot(cid: int, position: int, body: SlotEdit, uid=Depends(premium), db=Depends(get_db)):
    row = owned(db, Campaign, uid, cid)
    view = current_plan(db, row)
    if not 0 <= position < len(view['posts']):
        raise HTTPException(404, 'Campaign post not found.')
    if body.revision != row.revision:
        raise HTTPException(409, 'Campaign changed. Reopen it before editing.')
    caption = body.caption.strip()
    if not caption or body.platform == 'x' and len(caption)>280:
        raise HTTPException(400, 'Add a caption within the platform limit.')
    previous = view['posts'][position]
    if body.asset_id:
        if body.asset_id not in view['brief']['media'] and body.asset_id != previous['asset_id']:
            raise HTTPException(400, 'Choose a campaign attachment.')
        owned(db, MediaAsset, uid, body.asset_id)
    zone = view['brief']['timezone']
    old_date = view['dates'][position]
    date = old_date if body.local_time == old_date['local'][:16] else campaign_dates(schedule_time(body.local_time,zone), zone)
    authored = previous.get('caption_date',old_date['local'])
    if caption != previous['caption'] and date['local'][:10] == old_date['local'][:10]:
        authored = date['local']
    post = dict(platform=body.platform, caption=caption, asset_id=body.asset_id, caption_date=authored[:10])
    if view['draft_ids']:
        did = view['draft_ids'][position]
        if not previous['editable']:
            raise HTTPException(409, 'Open this post in Schedule to review its current state.')
        series = db.scalar(select(ContentSeries).where(ContentSeries.user_id==uid,ContentSeries.request_key==f'campaign-{cid}'))
        claimed = db.execute(update(ContentSeries).where(ContentSeries.id==series.id, ContentSeries.revision==body.series_revision,
                             ContentSeries.status=='active').values(revision=ContentSeries.revision+1))
        if claimed.rowcount != 1:
            raise HTTPException(409, 'Schedule changed. Reopen this campaign.')
        draft = owned(db, Draft, uid, did)
        workspace = json.loads(draft.workspace_json)
        workspace.update(active_platform=body.platform, selected_platforms=[body.platform], platform_selection_explicit=True,
                         media_asset_ids=[body.asset_id] if body.asset_id else [])
        changed = db.execute(update(Draft).where(Draft.id==did, Draft.revision==body.draft_revision,
                             Draft.status=='draft').values(revision=Draft.revision+1,
                             workspace_json=json.dumps(workspace), platforms_json=json.dumps([body.platform]),
                             variants_json=json.dumps({body.platform:{'posts':[caption]}})))
        if changed.rowcount != 1 or db.scalar(select(Publication.id).where(Publication.draft_id==did,
                                                       Publication.status.not_in(['failed','cancelled'])).limit(1)):
            raise HTTPException(409, 'Post changed or delivery started. Reopen the campaign.')
        db.execute(update(SeriesOccurrence).where(SeriesOccurrence.series_id==series.id,
                   SeriesOccurrence.draft_id==did).values(due_at=datetime.fromisoformat(date['utc'])))
        db.execute(update(PublishReview).where(PublishReview.draft_id==did,PublishReview.status=='review').values(status='invalidated'))
    data = json.loads(row.payload_json)
    data['posts'][position] = post
    data['dates'][position] = date
    replace(db, row, body.revision, data)
    return current_plan(db, row)


@router.post('/api/campaigns/{cid}/accept')
def accept(cid: int, body: Revision, uid=Depends(premium), db=Depends(get_db)):
    row = owned(db, Campaign, uid, cid)
    data = json.loads(row.payload_json)
    if data['draft_ids']:
        return result(row)
    row, data = editable(db, uid, cid, body.revision)
    if not data['posts']:
        raise HTTPException(409, 'Generate the plan first.')
    brief = Brief(**data['brief'])
    dates = data['dates']
    # Past planned times can still be saved as drafts. Final review validates delivery time.
    # Claim before creating children. Any later failure rolls back the whole group.
    claim = db.execute(update(Campaign).where(Campaign.id == cid, Campaign.revision == body.revision)
                       .values(revision=body.revision + 1))
    if claim.rowcount != 1:
        raise HTTPException(409, 'Campaign changed. Reopen the plan.')
    series_spec = spec(brief).model_dump()
    series = ContentSeries(user_id=uid, request_key=f'campaign-{cid}', spec_json=json.dumps(series_spec))
    db.add(series)
    db.flush()
    for i, post in enumerate(data['posts']):
        platform, caption = post['platform'], post['caption']
        aid = post['asset_id']
        if aid:
            owned(db, MediaAsset, uid, aid)
        draft = Draft(user_id=uid, title=caption[:100], brief=brief.idea, platforms_json=json.dumps([platform]),
                      variants_json=json.dumps({platform: {'posts': [caption]}}),
                      workspace_json=json.dumps({'media_asset_ids': [aid] if aid else [], 'active_platform': platform, 'selected_platforms': [platform], 'platform_selection_explicit': True}))
        if i == 0:
            series_spec['source'] = dict(brief=brief.idea, instruction='', platforms_json=draft.platforms_json,
                                         workspace_json=draft.workspace_json, variants_json=draft.variants_json, thread_length=1)
        db.add(draft)
        db.flush()
        db.add(SeriesOccurrence(user_id=uid, series_id=series.id, position=i, draft_id=draft.id,
                                due_at=datetime.fromisoformat(dates[i]['utc'])))
        data['draft_ids'].append(draft.id)
    series_spec['draft_id'] = data['draft_ids'][0]
    series.spec_json = json.dumps(series_spec)
    row.payload_json = json.dumps(data)
    db.commit()
    return result(row)
