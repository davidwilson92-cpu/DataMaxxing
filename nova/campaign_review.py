"""Project a campaign from its current drafts and attribute only confirmed provider posts."""
import json
import re
from .db import MediaAsset
from collections import defaultdict
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from sqlalchemy import select

from .analytics_view import valid_metric
from .db import Activity, Campaign, ContentSeries, Draft, Publication, ScheduledPost, SeriesOccurrence


def dates(value, zone):
    utc = value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    return {'utc': utc.isoformat(), 'local': utc.astimezone(ZoneInfo(zone)).isoformat()}


TIMING_WORDS = re.compile(r"\b(?:today|tonight|tomorrow|yesterday|this (?:morning|afternoon|evening|weekend|week)|next week|last night|(?:mon|tues|wednes|thurs|fri|satur|sun)day|\d{1,2}(?:st|nd|rd|th)?\s+(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)\w*|\d{1,2}/\d{1,2}(?:/\d{2,4})?)\b",re.I)


def caption_date_warning(caption, original, planned):
    if original[:10] != planned[:10]:
        match = TIMING_WORDS.search(caption)
        if match:
            return f'Posting day changed. Check “{match.group()}” in the caption.'
    return ''


def current_plan(db, row):
    data = dict(json.loads(row.payload_json), id=row.id, revision=row.revision)
    ids = data['draft_ids']
    for i,post in enumerate(data['posts']):
        original = post.get('caption_date',data['dates'][i]['local'])
        warning = caption_date_warning(post['caption'],original,data['dates'][i]['local'])
        if warning: post['timing_warning'] = warning
    if not ids:
        return data
    drafts = {d.id: d for d in db.scalars(select(Draft).where(Draft.user_id == row.user_id, Draft.id.in_(ids)))}
    series = db.scalar(select(ContentSeries).where(ContentSeries.user_id == row.user_id, ContentSeries.request_key == f'campaign-{row.id}'))
    slots = {o.position:o for o in db.scalars(select(SeriesOccurrence).where(SeriesOccurrence.series_id == series.id))} if series else {}
    jobs = {}
    for job in db.scalars(select(ScheduledPost).where(ScheduledPost.user_id == row.user_id,
            ScheduledPost.draft_id.in_(ids), ScheduledPost.status == 'scheduled').order_by(ScheduledPost.scheduled_at)):
        jobs.setdefault(job.draft_id, []).append(job)
    for i, post in enumerate(data['posts']):
        draft = drafts.get(ids[i])
        slot = slots.get(i)
        if draft is None:
            post.update(status='removed', editable=False)
            continue
        variants = json.loads(draft.variants_json)
        platforms = json.loads(draft.platforms_json)
        media = json.loads(draft.workspace_json).get('media_asset_ids', [])
        post['media_ids'] = media
        platform = next(iter(platforms), post['platform'])
        captions = variants.get(platform, {}).get('posts', [])
        simple = len(platforms) == 1 and len(captions) == 1 and len(media) <= 1 and set(variants) == {platform}
        post.update(status=draft.status, draft_revision=draft.revision, platform=platform,
                    caption='\n\n'.join(captions), asset_id=media[0] if media else None,
                    editable=bool(simple and draft.status=='draft' and slot and slot.status=='planned' and series.status=='active'))
        if slot and series:
            post['series_revision'] = series.revision
            scheduled = jobs.get(draft.id, [])
            when = scheduled[0].scheduled_at if scheduled else slot.due_at
            if len(scheduled) == 1 and draft.status == 'scheduled':
                from .schedule_routes import stamp
                post['schedule'] = dict(id=scheduled[0].id, updated_at=stamp(scheduled[0].updated_at))
            original = post.get('caption_date',data['dates'][i]['local'])
            prior = data['dates'][i]
            data['dates'][i] = dates(when,data['brief']['timezone'])
            if prior.get('reason') and prior['local']==data['dates'][i]['local']:
                data['dates'][i]['reason']=prior['reason']
            post.pop('timing_warning',None)
            warning = caption_date_warning(post['caption'],original,data['dates'][i]['local'])
            if warning: post['timing_warning'] = warning
    known={a['id'] for a in data['assets'] if a.get('kind')}
    needed={aid for post in data['posts'] for aid in post.get('media_ids',[]) if aid not in known}
    if needed:
        extra={a.id:{'id':a.id,'name':a.filename,'kind':'video' if a.mime_type.startswith('video/') else 'image'}
               for a in db.scalars(select(MediaAsset).where(MediaAsset.user_id==row.user_id,MediaAsset.id.in_(needed)))}
        data['assets']=list({a['id']:a for a in [*data['assets'],*extra.values()]}.values())
    return data


def campaign_results(db, uid, view):
    rows = db.scalars(select(Campaign).where(Campaign.user_id==uid).order_by(Campaign.id.desc()))
    campaigns = [(r.id,json.loads(r.payload_json)) for r in rows]
    ids = {i for _,c in campaigns for i in c['draft_ids']}
    start = datetime.fromisoformat(view['window_start'])
    events = db.execute(select(Activity.draft_id, Activity.platform, Activity.platform_post_id, Activity.url,
            Publication.result_json).outerjoin(Publication,
            (Publication.draft_id==Activity.draft_id) & (Publication.platform==Activity.platform) &
            (Publication.user_id==Activity.user_id) & (Publication.brand_id==Activity.brand_id)).where(
        Activity.user_id==uid, Activity.draft_id.in_(ids), Activity.status=='published', Activity.created_at>=start,
        Activity.created_at<=datetime.now(timezone.utc))).all() if ids else []
    measured = {(p['platform'],str(p['id'])):p for p in view['sample_posts'] if p.get('id')}
    by_draft = defaultdict(set)
    for did,platform,receipt,url,raw in events:
        remote_ids = [receipt] if receipt else []
        if platform == 'tiktok':
            # A TikTok delivery receipt is distinct from the public video or photo ID.
            match = re.fullmatch(r'https://www\.tiktok\.com/@[\w.]+/(?:video|photo)/(\d+)', url or '', re.ASCII)
            remote_ids = [match.group(1)] if match else []
        elif platform == 'x' and raw:
            evidence = json.loads(raw)
            if evidence.get('post_id') == receipt and isinstance(evidence.get('post_ids'),list):
                remote_ids = [str(i) for i in evidence['post_ids'] if i] or remote_ids
        by_draft[did].update((platform,str(i)) for i in remote_ids)
        if not remote_ids:
            by_draft[did].add((platform,None))
    reports = []
    for cid,c in campaigns:
        keys = {(p,pid) for did in c['draft_ids'] for p,pid in by_draft[did] if pid}
        missing = {(did,p) for did in c['draft_ids'] for p,pid in by_draft[did] if not pid}
        matched = [measured[k] for k in keys if k in measured]
        published = len(keys)+len(missing)
        report = dict(id=cid, name=c.get('name') or f'Campaign {cid}', published=published, measured=len(matched),
                      posts=[{key:p.get(key) for key in ('platform','text','views','likes','comments','shares')}
                             for p in sorted(matched,key=lambda p:p.get('created_at',''),reverse=True)])
        for metric in ('views','likes','comments','shares'):
            values = [p.get(metric) for p in matched]
            report[metric] = sum(values) if values and len(values)==published and all(valid_metric(v) for v in values) else None
        reports.append(report)
    return reports
