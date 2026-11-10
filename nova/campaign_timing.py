"""Recommend local test windows using comparable observations from this workspace."""
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from statistics import median
from zoneinfo import ZoneInfo

from .analytics_view import valid_metric
from .campaign_review import dates


def suggest(slots, planned, zone_name, evidence, now):
    zone = ZoneInfo(zone_name)
    windows = defaultdict(lambda: defaultdict(dict))
    for post in evidence.get('evidence', {}).get('posts', []) if evidence.get('available') else []:
        try:
            stamp = datetime.fromisoformat(post['created_at'].replace('Z', '+00:00'))
            if stamp.utcoffset() is None or stamp > now-timedelta(days=1):
                continue
            stamp = stamp.astimezone(zone)
        except (AttributeError, KeyError, ValueError):
            continue
        if not all(valid_metric(post.get(k)) for k in ('likes','comments')):
            continue
        hour = stamp.hour // 2 * 2
        daily = windows[post['platform']][hour].setdefault(stamp.date(), [])
        daily.append(post['likes'] + post['comments'])
    results = []
    for i, (platform, original) in enumerate(zip(slots, planned)):
        comparable = [(median([median(scores) for scores in days.values()]), len(days), hour)
                      for hour,days in windows[platform].items() if len(days)>=3]
        local = datetime.fromisoformat(original['utc']).astimezone(zone)
        if len(comparable)>=2 and len({score for score,_,_ in comparable})>1:
            _, days, hour = max(comparable)
            note = f'Best observed two-hour window for likes and comments across {days} posting days.'
        else:
            hour = (12,18)[i % 2]
            note = 'Test window. Too little comparable engagement history to identify a best time.'
        proposed = local.replace(hour=hour,minute=0,second=0,microsecond=0)
        # Stay on the requested day and keep the cadence. Never suggest a past instant.
        if proposed.astimezone(timezone.utc)<=now+timedelta(minutes=1) or proposed.replace(fold=0).utcoffset()!=proposed.replace(fold=1).utcoffset():
            proposed = local
            note = 'Kept the planned time to stay on your chosen day.'
        results.append(dict(**dates(proposed.astimezone(timezone.utc),zone_name),reason=note))
    return results
