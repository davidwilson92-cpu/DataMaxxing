"""Project a campaign from its current drafts and attribute only confirmed provider posts."""
import json
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from sqlalchemy import select

from .analytics_view import valid_metric
from .db import Activity, Campaign, ContentSeries, Draft, ScheduledPost, SeriesOccurrence


def dates(value, zone):
    utc = value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    return {'utc': utc.isoformat(), 'local': utc.astimezone(ZoneInfo(zone)).isoformat()}


def current_plan(db, row):
    data = dict(json.loads(row.payload_json), id=row.id, revision=row.revision)
    ids = data['draft_ids']
    if not ids:
        return data
    drafts = {d.id: d for d in db.scalars(select(Draft).where(Draft.user_id == row.user_id, Draft.id.in_(ids)))}
    series = db.scalar(select(ContentSeries).where(ContentSeries.user_id == row.user_id, ContentSeries.request_key == f'campaign-{row.id}'))
    slots = {o.position:o for o in db.scalars(select(SeriesOccurrence).where(SeriesOccurrence.series_id == series.id))} if series else {}
    jobs = {j.draft_id:j for j in db.scalars(select(ScheduledPost).where(ScheduledPost.user_id == row.user_id,
                ScheduledPost.draft_id.in_(ids), ScheduledPost.status == 'scheduled').order_by(ScheduledPost.scheduled_at.desc()))}
    for i, post in enumerate(data['posts']):
        draft = drafts.get(ids[i])
        slot = slots.get(i)
        if draft is None:
            post.update(status='removed', editable=False)
            continue
        variants = json.loads(draft.variants_json)
        platforms = json.loads(draft.platforms_json)
        media = json.loads(draft.workspace_json).get('media_asset_ids', [])
        platform = next(iter(platforms), post['platform'])
        captions = variants.get(platform, {}).get('posts', [])
        simple = len(platforms) == 1 and len(captions) == 1 and len(media) <= 1 and set(variants) == {platform}
        post.update(status=draft.status, draft_revision=draft.revision, platform=platform,
                    caption='\n\n'.join(captions), asset_id=media[0] if media else None,
                    editable=bool(simple and draft.status=='draft' and slot and slot.status=='planned' and series.status=='active'))
        if slot and series:
            post['series_revision'] = series.revision
            when = jobs[draft.id].scheduled_at if draft.id in jobs else slot.due_at
            data['dates'][i] = dates(when, data['brief']['timezone'])
    return data


def campaign_results(db, uid, view):
    rows = db.scalars(select(Campaign).where(Campaign.user_id==uid).order_by(Campaign.id.desc()))
    campaigns = [json.loads(r.payload_json) for r in rows]
    ids = {i for c in campaigns for i in c['draft_ids']}
    start = datetime.fromisoformat(view['window_start'])
    events = db.execute(select(Activity.draft_id, Activity.platform, Activity.platform_post_id).where(
        Activity.user_id==uid, Activity.draft_id.in_(ids), Activity.status=='published', Activity.created_at>=start,
        Activity.created_at<=datetime.now(timezone.utc))).all() if ids else []
    measured = {(p['platform'],str(p['id'])):p for p in view['sample_posts'] if p.get('id')}
    reports = []
    for c in campaigns:
        members = set(c['draft_ids'])
        keys = {(p,str(pid)) for did,p,pid in events if did in members and pid}
        missing = {(did,p) for did,p,pid in events if did in members and not pid}
        matched = [measured[k] for k in keys if k in measured]
        published = len(keys)+len(missing)
        report = dict(name=c['brief']['idea'], published=published, measured=len(matched),
                      posts=[{key:p.get(key) for key in ('platform','text','views','likes','comments','shares')}
                             for p in sorted(matched,key=lambda p:p.get('created_at',''),reverse=True)])
        for metric in ('views','likes','comments','shares'):
            values = [p.get(metric) for p in matched]
            report[metric] = sum(values) if values and len(values)==published and all(valid_metric(v) for v in values) else None
        reports.append(report)
    return reports
