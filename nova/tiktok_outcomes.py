"""Safe TikTok init rejection evidence; no response bodies or credentials."""
import re


REJECTIONS = {
    'invalid_param': 'TikTok rejected the post settings. Review the caption, media and TikTok options before trying again.',
    'unaudited_client_can_only_post_to_private_accounts': 'TikTok has not approved public posting for this app. Test posts need a private TikTok account and Only me visibility; paid partnerships cannot be posted in this test mode.',
    'url_ownership_unverified': 'TikTok could not verify the media host. Zova needs to verify its upload address before this can be posted.',
    'privacy_level_option_mismatch': 'TikTok rejected the visibility setting. Open the review again and choose an available option.',
    'access_token_invalid': 'TikTok rejected the connection. Reconnect TikTok, then review the post again.',
    'scope_not_authorized': 'This TikTok connection does not have the required posting permission. Reconnect after the permission is approved.',
    'rate_limit_exceeded': 'TikTok declined this request because too many requests were made. Wait before reviewing and trying again.',
    'spam_risk_too_many_posts': 'TikTok has reached this account’s daily posting limit. Wait before trying another post.',
    'spam_risk_user_banned_from_posting': 'TikTok has restricted posting for this account. Check the account in TikTok before trying again.',
    'reached_active_user_cap': 'TikTok has reached this app’s daily posting-account limit. Try again later.',
}

FAILURES = {
    'file_format_check_failed': 'TikTok could not accept this media format. Upload a supported video or image, then review again.',
    'duration_check_failed': 'TikTok rejected the video duration. Check the account’s video limit before reviewing again.',
    'frame_rate_check_failed': 'TikTok rejected the video frame rate. Export a supported video, then review again.',
    'picture_size_check_failed': 'TikTok rejected the media dimensions. Resize the video or image, then review again.',
    'video_pull_failed': 'TikTok could not download the video from Zova. Check the upload is still available before reviewing again.',
    'photo_pull_failed': 'TikTok could not download the images from Zova. Check the uploads are still available before reviewing again.',
    'internal': 'TikTok could not finish processing this post. Wait before reviewing and trying again.',
    'publish_cancelled': 'TikTok confirmed this publication was cancelled.',
    'auth_removed': 'TikTok access was removed while processing. Reconnect and review before sending another post.',
    'spam_risk_too_many_posts': REJECTIONS['spam_risk_too_many_posts'],
    'spam_risk_user_banned_from_posting': REJECTIONS['spam_risk_user_banned_from_posting'],
    'spam_risk_text': 'TikTok rejected the caption under its safety rules. Check TikTok’s guidance; do not resend this caption.',
    'spam_risk': 'TikTok rejected this publication under its safety rules. Check the account in TikTok; do not resend this post.',
}


def failed_result(reason):
    if isinstance(reason, str) and reason in FAILURES:
        return {'provider_error_code': reason, 'error': FAILURES[reason], 'pending': False}
    return {'error': 'TikTok reported this publication failed. Review before retrying.', 'pending': False}


def init_rejection(status, payload):
    """Only a documented explicit rejection with no receipt is safe to retry."""
    if not 200 <= status < 500 or not isinstance(payload, dict):
        return None
    error = payload.get('error')
    data = payload.get('data')
    if not isinstance(error, dict) or (isinstance(data, dict) and data.get('publish_id')):
        return None
    code = error.get('code')
    if not isinstance(code, str) or code not in REJECTIONS:
        return None
    evidence = {'provider_error_code': code}
    log_id = error.get('log_id') or error.get('logid')
    if isinstance(log_id, str) and re.fullmatch(r'[A-Za-z0-9_-]{1,128}', log_id):
        evidence['provider_log_id'] = log_id
    return evidence


def recover_evidence(evidence):
    """Recover a recorded stage without sending or guessing an old outcome."""
    phase = evidence.get('phase')
    if phase == 'tiktok_accepted' and evidence.get('post_id'):
        evidence.pop('error', None)
        evidence.update(pending=True, requires_tiktok_completion=evidence.get('posting_mode') == 'inbox')
        return 'pending'
    if phase == 'tiktok_rejected' and evidence.get('provider_error_code') in REJECTIONS:
        evidence['error'] = REJECTIONS[evidence['provider_error_code']]
        return 'failed'
    if phase == 'tiktok_validating':
        evidence['error'] = 'TikTok validation could not finish; no post was sent. Check the media and connection, then review again.'
        return 'failed'
    return None
