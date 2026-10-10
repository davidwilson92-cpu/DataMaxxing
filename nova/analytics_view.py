"""Comparable post-cohort metrics; missing observations stay missing."""
from datetime import datetime, timedelta, timezone
from math import isfinite


def valid_metric(value):
    return type(value) in (int,float) and isfinite(value) and value>=0


def dashboard(data, feed, now=None, window_days=7):
    if window_days not in (7,30):
        raise ValueError('Choose a 7 or 30 day post window')
    now = now or datetime.now(timezone.utc)
    start = now - timedelta(days=window_days)
    posts = []
    excluded = 0
    for post in feed.get('posts', []):
        try:
            created = datetime.fromisoformat(post.get('created_at', '').replace('Z', '+00:00'))
            if created.tzinfo is None:
                raise ValueError('Timestamp needs a timezone')
        except (ValueError, TypeError):
            excluded += 1
            continue
        if start <= created <= now:
            posts.append({**post,**{key:post.get(key) if valid_metric(post.get(key)) else None for key in ('likes','comments','shares','views')}})

    def total(rows, key):
        values = [r.get(key) for r in rows]
        # A partial sum must never masquerade as a complete observation.
        return sum(values) if values and all(valid_metric(v) for v in values) else None

    platforms = {}
    for name in ('x', 'instagram', 'facebook', 'tiktok'):
        account = data.get(name) or {}
        rows = [p for p in posts if p.get('platform') == name]
        value = {'connected': bool(account.get('connected')), 'account': account.get('account'),
                 'followers': account.get('followers') if valid_metric(account.get('followers')) else None, 'posts': None if name in feed.get('unavailable', []) else len(rows),
                 'error': 'Feed unavailable' if name in feed.get('unavailable', []) else account.get('error')}
        for key in ('likes', 'comments', 'shares'):
            value[key] = total(rows, key)
        value['impressions'] = total(rows, 'views')
        value['engagements'] = total([value], 'likes')
        value['engagements'] = sum(value[k] for k in ('likes', 'comments', 'shares')) if all(value[k] is not None for k in ('likes', 'comments', 'shares')) else None
        value['engagement_rate'] = None  # Providers expose different view/impression definitions.
        platforms[name] = value
    connected = [v for v in platforms.values() if v['connected']]
    summary = {key: total(connected, key) for key in ('impressions', 'likes', 'comments', 'shares', 'followers', 'posts', 'engagements')}
    summary['engagement_rate'] = None
    # Unknown engagement cannot be ranked as a real zero. Show it after observed posts.
    scored = sorted(posts, key=lambda p: (all(valid_metric(p.get(k)) for k in ('likes','comments')), sum(p[k] for k in ('likes','comments')) if all(valid_metric(p.get(k)) for k in ('likes','comments')) else -1), reverse=True)
    recommendations = [{'title': 'Compare like with like', 'detail': 'This is a limited sample of recent posts. Compare the same platform and format before deciding what works.'}] if posts else [{'title': 'Build a measurable baseline', 'detail': 'No dated posts in the last seven days are available in this sample. Connect an account or try refreshing later.'}]
    for name in ('x','instagram','facebook','tiktok'):
        comparable=[p for p in scored if p.get('platform')==name and all(valid_metric(p.get(k)) for k in ('likes','comments'))]
        if len(comparable)>=2:
            strongest=comparable[0]
            label='X' if name=='x' else name.title()
            recommendations.insert(0,{'title':f'Test a follow-up on {label}', 'detail':f'Of {len(comparable)} sampled posts with likes and comments, “{str(strongest.get("text") or "Media post")[:100]}” has the most combined responses. Try a related angle, then compare. Older posts have had more time to collect responses; this is an experiment, not proof of a winning topic.'})
    if not posts:
        recommendations[0]['detail']=f'No dated posts in the last {window_days} days are available in this sample. Connect an account or try refreshing later.'
    return {'period': f'Posts published in the last {window_days} days', 'summary': summary, 'platforms': platforms,
            'top_posts': scored[:6], 'recommendations': recommendations, 'unavailable': feed.get('unavailable', []),
            'fetched_at': now.isoformat(), 'window_start': start.isoformat(), 'excluded_undated': excluded,
            'note': f'Available lifetime totals for a limited sample of posts published in the last {window_days} days. These are not engagement gained during that period. Followers are current account totals. A dash means unavailable or incomplete; views and impressions differ by platform.'}
