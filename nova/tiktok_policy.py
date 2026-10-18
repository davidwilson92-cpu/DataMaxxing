"""Shared Direct Post rules, applied to reviewed and dispatched content."""
import io
import math
import os
from urllib.parse import urlsplit
from .storage import get_bytes, get_public_url


def private_test_mode():
    """The isolated recording sandbox is not approved for public Direct Post."""
    return os.environ.get('ZOVA_ENV', '').strip().lower() == 'sandbox'


def direct_media_url(asset):
    url = get_public_url(asset.storage_key, asset.public_url)
    prefix = os.environ.get('TIKTOK_VERIFIED_MEDIA_PREFIX', '').strip()
    parsed, allowed = urlsplit(url), urlsplit(prefix)
    if (not prefix or allowed.scheme != 'https' or not allowed.hostname or allowed.username
            or allowed.query or allowed.fragment or parsed.scheme != 'https'
            or parsed.netloc != allowed.netloc or parsed.username
            or not parsed.path.startswith(allowed.path.rstrip('/') + '/')):
        raise ValueError('TikTok Direct Post needs a media URL prefix verified in the TikTok developer portal.')
    return url


def video_duration(asset):
    import av
    try:
        with av.open(io.BytesIO(get_bytes(asset.storage_key))) as container:
            stream = container.streams.video[0]
            duration = float(stream.duration * stream.time_base) if stream.duration else float(container.duration or 0) / av.time_base
        if not math.isfinite(duration) or duration <= 0:
            raise ValueError()
        return duration
    except Exception as exc:
        raise ValueError('The video duration could not be verified. Upload a readable video.') from exc


def validate_direct(settings, context, posts, assets):
    if not isinstance(settings, dict):
        raise ValueError('Invalid TikTok settings.')
    for key in ('allow_comment', 'allow_duet', 'allow_stitch', 'commercial_content', 'your_brand', 'brand_content', 'consent', 'is_aigc'):
        if key in settings and type(settings[key]) is not bool:
            raise ValueError('TikTok selections must be true or false.')
    if settings.get('consent') is not True:
        raise ValueError('Confirm TikTok music usage and any applicable branded-content policy before reviewing.')
    if settings.get('privacy_level') not in context.get('privacy_options', []):
        raise ValueError('Choose an available TikTok privacy setting.')
    commercial = settings.get('commercial_content', False)
    own, paid = settings.get('your_brand', False), settings.get('brand_content', False)
    if commercial != bool(own or paid):
        raise ValueError('Select Your brand or Branded content when disclosing commercial content.')
    if private_test_mode():
        if paid:
            raise ValueError('Paid partnerships cannot be published from this TikTok test app. TikTok approval is required; keep this as a draft.')
        if settings.get('privacy_level') != 'SELF_ONLY':
            raise ValueError('This TikTok test app can publish with Only me visibility only. Choose Only me and review again.')
    if paid and settings.get('privacy_level') not in {'PUBLIC_TO_EVERYONE','MUTUAL_FOLLOW_FRIENDS'}:
        raise ValueError('Branded content cannot use Only me or Followers privacy. Choose Everyone or Friends.')
    if not assets or len(posts) != 1:
        raise ValueError('TikTok requires media and one caption.')
    video = assets[0].mime_type.startswith('video/')
    if video and len(assets) != 1:
        raise ValueError('Select one TikTok video.')
    if not video and any(a.mime_type not in {'image/jpeg', 'image/webp'} for a in assets):
        raise ValueError('TikTok photo posts require JPEG or WebP images.')
    for key, disabled in [('allow_comment','comment_disabled'),('allow_duet','duet_disabled'),('allow_stitch','stitch_disabled')]:
        if settings.get(key) and (context.get(disabled) or (not video and key != 'allow_comment')):
            raise ValueError('A selected TikTok interaction is unavailable.')
    if len(posts[0].encode('utf-16-le')) // 2 > 2200:
        raise ValueError('Shorten the TikTok caption to 2,200 UTF-16 characters.')
    for asset in assets:
        direct_media_url(asset)
    if video:
        duration = video_duration(assets[0])
        maximum = float(context.get('max_video_duration_sec') or 0)
        if not math.isfinite(maximum) or maximum <= 0 or duration > maximum:
            raise ValueError('The video exceeds or lacks a verified TikTok account duration limit.')
