"""Shared owner-facing states. These projections never dispatch or retry a post."""
from collections import Counter

LABELS = {'draft': 'Draft', 'review': 'Awaiting approval', 'scheduled': 'Scheduled',
          'queued': 'Preparing', 'publishing': 'Sending — outcome unconfirmed',
          'pending': 'Processing', 'published': 'Published', 'failed': 'Needs attention',
          'partial': 'Needs attention', 'unknown': 'Outcome unconfirmed',
          'needs_review': 'Outcome unconfirmed', 'cancelled': 'Cancelled', 'removed': 'Removed'}


def summary(posts):
    counts = Counter(p.get('status', 'draft') for p in posts)
    attention = sum(counts[k] for k in ('failed', 'partial', 'unknown', 'needs_review', 'publishing'))
    parts = []
    for key, label in [('scheduled', 'scheduled'), ('published', 'published'), ('draft', 'drafts'), ('review', 'awaiting approval'), ('queued', 'preparing'), ('pending', 'processing')]:
        if counts[key]: parts.append(f'{counts[key]} {label}')
    if attention: parts.append(f"{attention} {'needs' if attention == 1 else 'need'} attention")
    return {'text': ' · '.join(parts), 'attention': attention,
            'draft_ids': [p['draft_id'] for p in posts if p.get('draft_id') and p.get('status') in ('failed','partial','unknown','needs_review','publishing')]}


def guidance(status):
    if status in ('unknown', 'publishing', 'needs_review'):
        return 'Check results and the destination before retrying. Zova will not resend automatically.'
    if status == 'pending': return 'The platform is processing this post. Refresh its results; do not resend.'
    if status in ('failed', 'partial'): return 'Open this post to review the affected destination. Your caption and media are retained.'
    return ''
