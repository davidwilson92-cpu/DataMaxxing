import io
import json
from types import SimpleNamespace

import httpx
import pytest
from PIL import Image
from nova import ai, media_inspection as visual
from nova.db import MediaAsset, SessionLocal
from test_account_integrity import account


def uploaded(client):
    data = io.BytesIO()
    Image.new('RGB', (96, 64), 'purple').save(data, format='JPEG')
    response = client.post('/api/media', files={'files': ('untrusted-name.jpg', data.getvalue(), 'image/jpeg')})
    assert response.status_code == 200, response.text
    return response.json()['assets'][0]['id']


def test_owned_image_payload_cached_and_passed_to_generation(monkeypatch):
    client, uid, _, _ = account()
    asset_id = uploaded(client)
    calls = []
    def response(prompt, **kwargs):
        calls.append(prompt)
        return json.dumps({'observations': 'A purple rectangle. No horse is visible.'})
    monkeypatch.setattr(ai, '_responses', response)
    body = {'message': 'Create a post about this image', 'selected_platforms': ['instagram'], 'media_asset_ids': [asset_id]}
    plan = client.post('/api/conversation/plan', json=body)
    assert plan.status_code == 200, plan.text
    assert plan.json()['media_inspection'][0]['status'] == 'inspected'
    image = calls[0][0]['content'][1]
    assert image['type'] == 'input_image' and image['image_url'].startswith('data:image/jpeg;base64,')
    assert 'untrusted-name' not in json.dumps(calls)
    seen = []
    monkeypatch.setattr(ai, 'generate_variants', lambda **kw: seen.append(kw) or {'instagram': {'posts': ['Purple mood.']}})
    generated = client.post('/api/ai/generate', json={'brief': 'Caption this', 'platforms': ['instagram'], 'media_asset_ids': [asset_id]})
    assert generated.status_code == 200, generated.text
    assert 'A purple rectangle' in seen[0]['instruction'] and len(calls) == 1
    with SessionLocal() as db:
        assert json.loads(db.get(MediaAsset, asset_id).analysis_json)['result']['status'] == 'inspected'


def test_foreign_asset_rejected_before_any_storage_or_ai(monkeypatch):
    owner, _, _, _ = account()
    other, _, _, _ = account()
    asset_id = uploaded(owner)
    def forbidden(*args, **kwargs):
        pytest.fail('Foreign content must never be read or sent')
    monkeypatch.setattr(visual.storage, 'get_bytes', forbidden)
    monkeypatch.setattr(ai, '_responses', forbidden)
    for route, body in [('/api/conversation/plan', {'message': 'Create a post', 'selected_platforms': ['instagram']}),
                        ('/api/ai/generate', {'brief': 'caption', 'platforms': ['instagram']}),
                        ('/api/ai/rewrite', {'platform': 'instagram', 'posts': ['caption']})]:
        assert other.post(route, json={**body, 'media_asset_ids': [asset_id]}).status_code == 404


def test_same_owner_other_brand_cannot_inspect(monkeypatch):
    client, _, _, _ = account()
    asset_id = uploaded(client)
    client.post('/brands', data={'name': 'Second brand'})
    monkeypatch.setattr(visual.storage, 'get_bytes', lambda *a: pytest.fail('Cross-brand read'))
    response = client.post('/api/conversation/plan', json={'message': 'Create a post', 'selected_platforms': ['instagram'], 'media_asset_ids': [asset_id]})
    assert response.status_code == 404


def test_profile_name_change_preserves_voice_guidance():
    client, uid, _, _ = account()
    client.post('/account/profile', data={'display_name': 'Original', 'guidance': 'No jargon'})
    client.post('/account/profile', data={'display_name': 'New name'})
    with SessionLocal() as db:
        from nova.db import get_preferences
        assert get_preferences(db, uid).things_to_avoid == 'No jargon'


def test_draft_pagination_keeps_older_work_accessible():
    client, uid, _, _ = account()
    from nova.db import Draft
    with SessionLocal() as db:
        for index in range(32): db.add(Draft(user_id=uid, brief=f'Synthetic idea {index}'))
        db.commit()
    first = client.get('/drafts').text
    second = client.get('/drafts?page=2').text
    assert 'Older drafts' in first and 'Newer drafts' in second
    assert first.count('class="draft-card"') == 30 and second.count('class="draft-card"') == 2


@pytest.mark.parametrize('phase,expected', [('container_created', 'failed'), ('publish_requested', 'unknown'), ('published', 'published')])
def test_publication_checkpoint_survives_exception(monkeypatch, phase, expected):
    from test_instagram_formats import story_draft
    from nova import app as module
    from nova.publication_evidence import checkpoint
    client, body = story_draft(monkeypatch)
    reviewed = client.post('/api/publish-review', json=body).json()
    def publish(*args, **kwargs):
        checkpoint(phase, container_id='container-synthetic', **({'post_id': 'post-synthetic'} if phase == 'published' else {}))
        raise httpx.ReadTimeout('secret provider diagnostic')
    monkeypatch.setattr(module, 'publish_platform', publish)
    result = client.post('/api/publish', json={**body, 'review_token': reviewed['review_token']}).json()['results']['instagram']
    assert result['status'] == expected and result['container_id'] == 'container-synthetic'
    assert 'secret provider diagnostic' not in json.dumps(result)


def test_uncertain_instagram_reconciles_only_authoritative_published(monkeypatch):
    from test_instagram_formats import story_draft
    from nova import app as module, social
    from nova.publication_evidence import checkpoint
    from nova.publishing_workflow import results_for
    client, body = story_draft(monkeypatch)
    reviewed = client.post('/api/publish-review', json=body).json()
    def publish(*args, **kwargs):
        checkpoint('publish_requested', container_id='container-synthetic')
        raise httpx.ReadTimeout('uncertain')
    monkeypatch.setattr(module, 'publish_platform', publish)
    client.post('/api/publish', json={**body, 'review_token': reviewed['review_token']})
    monkeypatch.setattr(social, 'access_token', lambda *a: 'synthetic')
    monkeypatch.setattr(social.httpx, 'get', lambda *a, **kw: SimpleNamespace(status_code=200, json=lambda: {'status_code': 'PUBLISHED'}))
    monkeypatch.setattr('nova.request_security.allowed_request', lambda *a: True)
    from nova.db import Draft
    with SessionLocal() as db:
        draft = db.get(Draft, body['draft_id'])
        result = results_for(db, draft.user_id, draft.id)
        assert result['results']['instagram']['status'] == 'published'
        assert result['draft_status'] == 'published'


def test_failed_inspection_is_truthful_and_retryable(monkeypatch):
    client, _, _, _ = account()
    asset_id = uploaded(client)
    monkeypatch.setattr(ai, '_responses', lambda *a, **kw: (_ for _ in ()).throw(RuntimeError('private error')))
    body = {'message': 'Create a post', 'selected_platforms': ['instagram'], 'media_asset_ids': [asset_id]}
    result = client.post('/api/conversation/plan', json=body).json()['media_inspection'][0]
    assert result['status'] == 'unavailable' and result['observations'] == ''
    assert 'private error' not in json.dumps(result)
    monkeypatch.setattr(ai, '_responses', lambda *a, **kw: '{"observations":"Purple rectangle"}')
    assert client.post('/api/conversation/plan', json=body).json()['media_inspection'][0]['status'] == 'inspected'


def test_multiple_images_do_not_block_usage_telemetry(monkeypatch):
    from sqlalchemy import select
    from nova.db import AICall
    client, uid, _, _ = account()
    ids = [uploaded(client), uploaded(client)]
    monkeypatch.setattr(ai, '_request_response', lambda *a, **kw: ('{"observations":"A purple rectangle"}', {'status':'completed'}))
    response = client.post('/api/conversation/plan', json={'message':'Create a post', 'selected_platforms':['instagram'], 'media_asset_ids':ids})
    assert response.status_code == 200
    assert len(response.json()['media_inspection']) == 2
    with SessionLocal() as db:
        assert len(db.scalars(select(AICall).where(AICall.user_id == uid)).all()) == 2


def test_real_video_decoder_samples_frames_without_claiming_audio():
    import av
    output = io.BytesIO()
    with av.open(output, 'w', format='mp4') as container:
        stream = container.add_stream('mpeg4', rate=10)
        stream.width, stream.height, stream.pix_fmt = 64, 64, 'yuv420p'
        for index in range(30):
            frame = av.VideoFrame.from_image(Image.new('RGB', (64, 64), (index * 8, 0, 100)))
            for packet in stream.encode(frame): container.mux(packet)
        for packet in stream.encode(): container.mux(packet)
    inputs, coverage, times = visual.visual_inputs(output.getvalue(), 'video/mp4')
    assert 2 <= len(times) <= 8 and times == sorted(set(times))
    assert times[-1] > 2 and len([i for i in inputs if i['type'] == 'input_image']) == len(times)
    assert 'Audio and unsampled moments were not inspected' in coverage


def test_responses_disables_response_storage(monkeypatch):
    monkeypatch.setenv('OPENAI_API_KEY', 'synthetic')
    bodies = []
    monkeypatch.setattr(ai.httpx, 'post', lambda *a, **kw: bodies.append(kw['json']) or SimpleNamespace(status_code=200, json=lambda: {'output_text': 'ok'}))
    ai._request_response([{'role': 'user', 'content': [{'type': 'input_text', 'text': 'test'}]}], max_output_tokens=10)
    assert bodies[0]['store'] is False and isinstance(bodies[0]['input'], list)


@pytest.mark.parametrize('posts', [[''], [{'caption': 'not a string'}], ['only one part']])
def test_invalid_or_incomplete_threads_are_not_saved(monkeypatch, posts):
    monkeypatch.setattr(ai, '_responses', lambda *a, **kw: json.dumps({'x': {'posts': posts}}))
    with pytest.raises(RuntimeError):
        ai.generate_variants(brief='A factual test', instruction='', platforms=['x'], thread_length=3, preferences=SimpleNamespace())


def test_testing_offer_does_not_imply_subscription_or_management():
    client, _, _, _ = account()
    page = client.get('/subscribe')
    assert page.status_code == 200
    assert 'Testing access' in page.text and 'View future GBP plans' in page.text
    assert 'No subscription has been verified' not in page.text
    assert 'Cancel through Manage billing' not in page.text


def test_confirmed_instagram_publication_survives_permalink_failure(monkeypatch):
    from nova import social
    monkeypatch.setattr(social, 'access_token', lambda *a: 'synthetic')
    monkeypatch.setattr(social, 'json_meta', lambda c: {'auth_provider': 'instagram_login'})
    monkeypatch.setattr(social, 'get_public_url', lambda *a: 'https://example.test/image.jpg')
    monkeypatch.setattr(social.httpx, 'post', lambda *a, **kw: SimpleNamespace(status_code=200, json=lambda: {'id': 'confirmed-id'}))
    def get(*args, **kwargs):
        if kwargs['params']['fields'] == 'permalink': raise httpx.ReadTimeout('timeout')
        return SimpleNamespace(status_code=200, json=lambda: {'status_code': 'FINISHED'})
    monkeypatch.setattr(social.httpx, 'get', get)
    result = social.publish_instagram(None, SimpleNamespace(account_id='synthetic'), ['caption'], [SimpleNamespace(mime_type='image/jpeg', storage_key='x', public_url='x')])
    assert result['post_id'] == 'confirmed-id' and result['url'] is None
