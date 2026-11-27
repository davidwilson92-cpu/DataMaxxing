"""Deterministic evidence disclosure; model prose cannot manufacture measurements."""
from .analytics_view import valid_metric
from .performance import fresh


def evidence_basis(performance, platform=None):
    evidence = performance.get('evidence') or {}
    checked = evidence.get('fetched_at')
    posts = [p for p in evidence.get('posts', []) if isinstance(p, dict)
             and (platform is None or p.get('platform') == platform)
             and any(valid_metric(p.get(k)) for k in ('likes', 'comments', 'shares', 'views'))]
    if not performance.get('available') or not fresh(checked) or not posts:
        return {'summary': 'A test based on your direction and voice.', 'checked_at': None,
                'note': 'Not enough fresh performance evidence for this recommendation. Results are not predicted.', 'examples': [], 'sample_size': 0}
    examples = []
    for post in posts[:3]:
        metrics = {k: post[k] if valid_metric(post.get(k)) else None for k in ('likes', 'comments', 'shares', 'views')}
        examples.append({'platform': post.get('platform'), 'text': str(post.get('text') or '')[:240],
                         'created_at': post.get('created_at'), 'format': post.get('format'), 'metrics': metrics})
    return {'summary': f'Informed by {len(posts)} recent posts' + (f' on {platform.title() if platform != "x" else "X"}.' if platform else '.'),
            'checked_at': checked, 'sample_size': len(posts), 'examples': examples,
            'note': 'Lifetime counters from a limited sample, not growth or sales. Post ages and formats can differ. This is a test, not proof of what caused results.'}
