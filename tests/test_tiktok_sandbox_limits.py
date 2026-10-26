"""The recording app cannot send a public or paid-partnership Direct Post."""
from types import SimpleNamespace
import pytest

from nova import social, tiktok_policy as policy
from test_tiktok_direct_post import setup


@pytest.mark.parametrize('privacy', ['PUBLIC_TO_EVERYONE', 'MUTUAL_FOLLOW_FRIENDS', 'FOLLOWER_OF_CREATOR'])
def test_sandbox_rejects_nonprivate_even_when_creator_lists_it(monkeypatch, privacy):
    asset, options, context, info = setup(monkeypatch)
    monkeypatch.setenv('ZOVA_ENV', 'sandbox')
    context['privacy_options'].append(privacy)
    options['privacy_level'] = privacy
    with pytest.raises(ValueError, match='Only me visibility only'):
        policy.validate_direct(options, context, ['Caption'], [asset])
    monkeypatch.setattr(social.httpx, 'post', lambda *a, **kw: pytest.fail('Provider init must not be called'))
    with pytest.raises(RuntimeError, match='Only me visibility only'):
        social.publish_tiktok(None, None, ['Caption'], [asset], options=options)


@pytest.mark.parametrize('privacy', ['PUBLIC_TO_EVERYONE', 'SELF_ONLY'])
def test_sandbox_paid_partnership_block_explains_approval(monkeypatch, privacy):
    asset, options, context, _ = setup(monkeypatch)
    monkeypatch.setenv('ZOVA_ENV', 'sandbox')
    options.update(privacy_level=privacy, commercial_content=True, brand_content=True)
    with pytest.raises(ValueError, match='Paid partnerships.*TikTok approval'):
        policy.validate_direct(options, context, ['Caption'], [asset])


def test_sandbox_own_brand_private_remains_available(monkeypatch):
    asset, options, context, _ = setup(monkeypatch)
    monkeypatch.setenv('ZOVA_ENV', 'sandbox')
    options.update(privacy_level='SELF_ONLY', commercial_content=True, your_brand=True)
    policy.validate_direct(options, context, ['Caption'], [asset])


def test_test_limit_is_server_configuration_not_customer_payload(monkeypatch):
    asset, options, context, _ = setup(monkeypatch)
    monkeypatch.setenv('ZOVA_ENV', 'sandbox')
    options['private_test_mode'] = False
    context['private_test_mode'] = False
    with pytest.raises(ValueError, match='Only me visibility only'):
        policy.validate_direct(options, context, ['Caption'], [asset])
    monkeypatch.setenv('ZOVA_ENV', 'production')
    policy.validate_direct(options, context, ['Caption'], [asset])


def test_context_warns_about_test_limit_without_preselecting_privacy(monkeypatch):
    _, _, _, info = setup(monkeypatch)
    monkeypatch.setenv('ZOVA_ENV', 'sandbox')
    conn = SimpleNamespace(id=1, account_id='synthetic', scope='video.publish',
                           username='creator', display_name='Creator')
    monkeypatch.setattr(social, 'selected_connection', lambda *a: conn)
    result = social.publishing_context(None, 1, 'tiktok')
    assert result['private_test_mode'] is True
    assert result['privacy_options'] == info['privacy_level_options']
    assert 'privacy_level' not in result  # The user still chooses explicitly.
    monkeypatch.setenv('TIKTOK_SEND_TO_INBOX', 'true')
    result = social.publishing_context(None, 1, 'tiktok')
    assert result['posting_mode'] == 'inbox'
    assert 'private_test_mode' not in result


def test_paid_partnership_visibility_remains_public_or_friends_after_approval(monkeypatch):
    asset, options, context, _ = setup(monkeypatch)
    monkeypatch.setenv('ZOVA_ENV', 'production')
    context['privacy_options'] += ['FOLLOWER_OF_CREATOR', 'MUTUAL_FOLLOW_FRIENDS']
    options.update(commercial_content=True, brand_content=True, privacy_level='FOLLOWER_OF_CREATOR')
    with pytest.raises(ValueError, match='Choose Everyone or Friends'):
        policy.validate_direct(options, context, ['Caption'], [asset])
    options['privacy_level'] = 'MUTUAL_FOLLOW_FRIENDS'
    policy.validate_direct(options, context, ['Caption'], [asset])
