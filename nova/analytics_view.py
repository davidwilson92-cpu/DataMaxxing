"""Comparable post-cohort metrics; missing observations stay missing."""
from datetime import datetime, timedelta, timezone


def dashboard(data, feed, now=None):
    now = now or datetime.now(timezone.utc)
    start = now - timedelta(days=7)
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
            posts.append(post)

    def total(rows, key):
        values = [r.get(key) for r in rows]
        # A partial sum must never masquerade as a complete observation.
        return sum(values) if values and all(isinstance(v, (int, float)) and v >= 0 for v in values) else None

    platforms = {}
    for name in ('x', 'instagram', 'facebook', 'tiktok'):
        account = data.get(name) or {}
        rows = [p for p in posts if p.get('platform') == name]
        value = {'connected': bool(account.get('connected')), 'account': account.get('account'),
                 'followers': account.get('followers'), 'posts': None if name in feed.get('unavailable', []) else len(rows),
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
    scored = sorted(posts, key=lambda p: (p.get('likes') or 0) + (p.get('comments') or 0), reverse=True)
    recommendations = [{'title': 'Compare like with like', 'detail': 'This is a limited sample of recent posts. Compare the same platform and format before deciding what works.'}] if posts else [{'title': 'Build a measurable baseline', 'detail': 'No dated posts in the last seven days are available in this sample. Connect an account or try refreshing later.'}]
    return {'period': 'Posts published in the last 7 days', 'summary': summary, 'platforms': platforms,
            'top_posts': scored[:6], 'recommendations': recommendations, 'unavailable': feed.get('unavailable', []),
            'fetched_at': now.isoformat(), 'window_start': start.isoformat(), 'excluded_undated': excluded,
            'note': 'Available lifetime totals for a limited sample of posts published in the last seven days. These are not engagement gained during those seven days. Followers are current account totals. A dash means unavailable or incomplete; views and impressions differ by platform.'}
