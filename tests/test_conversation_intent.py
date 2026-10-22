import pytest
from nova.conversation import plan_message, ConversationPlan
from test_account_integrity import account


@pytest.mark.parametrize('message',['Do not publish this yet',"Don't schedule this",'Hold off posting; do not send'])
def test_negation_does_not_request_publication(message,monkeypatch):
    import nova.conversation as module
    monkeypatch.setattr(module.ai,'_responses',lambda *a,**k:pytest.fail('Negation must not need a model'))
    assert plan_message(message,{'selected_platforms':['x']}).action=='answer'


def test_creation_about_followers_is_not_analytics():
    result=plan_message('Write a post thanking my followers',{'selected_platforms':['instagram']})
    assert result.action=='create' and result.platforms==['instagram']
    result=plan_message('Write a post for all platforms except x',{'selected_platforms':['x','instagram']})
    assert result.platforms==['instagram']


def test_plan_only_reads_owned_drafts(monkeypatch):
    import nova.conversation as module
    client,_,_,_=account();other,_,_,_=account()
    row=client.post('/api/drafts',json={}).json()
    monkeypatch.setattr(module,'plan_message',lambda *a:ConversationPlan(action='publish',platforms=['x']))
    body={'message':'Publish this','draft_id':row['id'],'selected_platforms':['x']}
    assert other.post('/api/conversation/plan',json=body).status_code==404
    assert client.post('/api/conversation/plan',json=body).json()['action']=='publish'
    assert client.get(f"/api/drafts/{row['id']}").json()['status']=='draft'


@pytest.mark.parametrize('message', ['Why not?', 'yes', 'Go ahead'])
def test_acceptance_proposes_from_prior_topic_without_publishing(message, monkeypatch):
    import nova.conversation as module
    monkeypatch.setattr(module.ai, '_responses', lambda *a, **k: pytest.fail('Known topic can draft directly'))
    result = plan_message(message, {'selected_platforms':['instagram'], 'conversation':[
        {'role':'user','content':'Introduce our new Zova logo'},
        {'role':'assistant','content':'Would you like a first caption?'}]})
    assert result.action == 'create'
    assert result.platforms == ['instagram']
    assert result.brief == 'Introduce our new Zova logo'


def test_planner_keeps_context_and_defaults_to_selected_platform(monkeypatch):
    import nova.conversation as module
    def response(prompt, **kwargs):
        assert 'Instagram audience' in prompt
        assert 'editorial feedback' in prompt
        assert kwargs['max_output_tokens'] >= 3000
        return '{"action":"create","brief":"Introduce the Zova logo to our Instagram audience","reply":"Here is a first proposal."}'
    monkeypatch.setattr(module.ai, '_responses', response)
    result = plan_message('Why not?', {'selected_platforms':['instagram'], 'variants':{'instagram':{'posts':['Our new logo']}}, 'conversation':[{'role':'user','content':'Instagram audience'}]})
    assert result.platforms == ['instagram']
    assert 'Zova logo' in result.brief


def test_verbose_editorial_reply_is_kept_instead_of_failing(monkeypatch):
    import json
    import nova.conversation as module
    monkeypatch.setattr(module.ai,'_responses',lambda *a,**k:json.dumps({'action':'answer','reply':'Useful feedback. '*160}))
    result=plan_message('What will followers think?', {'selected_platforms':['instagram']})
    assert result.action == 'answer'
    assert result.reply.startswith('Useful feedback.') and len(result.reply)<=2000


@pytest.mark.parametrize('message', [
    'Posting this video again. Quick gag on adulting. Add link to my website www.zova-social.co.uk who are sponsoring this post.',
    'Take2: this time its a paid partnership',
])
def test_first_tiktok_caption_cannot_rewrite_a_nonexistent_x_version(message, monkeypatch):
    import nova.conversation as module
    monkeypatch.setattr(module.ai, '_responses', lambda *a, **k:
        '{"action":"rewrite","platforms":["x"],"brief":"Add the sponsorship to this caption"}')
    result = plan_message(message, {'selected_platforms':['tiktok'], 'active_platform':'x',
        'brief':'A quick gag about adulting', 'variants':{}})
    assert result.action == 'create'
    assert result.platforms == ['tiktok']
    assert 'A quick gag about adulting' in result.brief
    assert message in result.brief


def test_planner_context_uses_selected_existing_caption_instead_of_stale_active_x(monkeypatch):
    import json
    import nova.conversation as module
    def response(prompt, **kwargs):
        context = json.loads(prompt.split('\nCONTEXT:\n')[1].split('\nLATEST MESSAGE:\n')[0])
        assert context['active_platform'] == 'tiktok'
        return '{"action":"rewrite","platforms":["x"],"brief":"Add the sponsor"}'
    monkeypatch.setattr(module.ai, '_responses', response)
    result = plan_message('Add the sponsor to this caption', {'selected_platforms':['tiktok'],
        'active_platform':'x', 'variants':{'tiktok':{'posts':['Original TikTok caption']},
                                         'x':{'posts':['Unselected X caption']}}})
    assert result.action == 'rewrite' and result.platforms == ['tiktok']


def test_edit_for_selected_missing_platform_adds_a_version_without_losing_existing(monkeypatch):
    import nova.conversation as module
    monkeypatch.setattr(module.ai, '_responses', lambda *a, **k:
        '{"action":"rewrite","platforms":["x"],"brief":"Add the sponsor"}')
    context = {'selected_platforms':['tiktok'], 'active_platform':'x',
               'variants':{'instagram':{'posts':['Existing Instagram caption']}}}
    result = plan_message('Add the sponsor to this caption', context)
    assert result.action == 'add_platforms' and result.platforms == ['tiktok']
    assert context['variants']['instagram']['posts'] == ['Existing Instagram caption']


def test_explicit_platform_switch_is_honoured_but_sponsor_url_is_not_a_switch(monkeypatch):
    import nova.conversation as module
    monkeypatch.setattr(module.ai, '_responses', lambda *a, **k:
        '{"action":"rewrite","platforms":["x"]}')
    context = {'selected_platforms':['tiktok'], 'active_platform':'tiktok',
               'variants':{'tiktok':{'posts':['Existing caption']}}}
    result = plan_message('Adapt this for Instagram', context)
    assert result.action == 'add_platforms' and result.platforms == ['instagram']
    result = plan_message('Add my sponsor https://x.example.test to the caption', context)
    assert result.action == 'rewrite' and result.platforms == ['tiktok']


@pytest.mark.parametrize('response', [
    '{"action":"create","platforms":["x"]}',
    '{"action":"add_platforms","platforms":["x"]}',
])
def test_first_caption_plan_uses_all_selected_platforms(response, monkeypatch):
    import nova.conversation as module
    monkeypatch.setattr(module.ai, '_responses', lambda *a, **k: response)
    result = plan_message('A quick gag about adulting', {'selected_platforms':['tiktok','instagram'], 'variants':{}})
    assert result.action == 'create' and result.platforms == ['tiktok','instagram']


def test_empty_platform_selection_never_invents_x(monkeypatch):
    import nova.conversation as module
    monkeypatch.setattr(module.ai, '_responses', lambda *a, **k:
        '{"action":"rewrite","platforms":["x"]}')
    result = plan_message('Add a sponsor', {'selected_platforms':[], 'active_platform':'x', 'variants':{}})
    assert result.action == 'answer' and result.platforms == []


def test_rewrite_targets_active_caption_unless_all_versions_are_requested(monkeypatch):
    import nova.conversation as module
    monkeypatch.setattr(module.ai, '_responses', lambda *a, **k:
        '{"action":"rewrite","platforms":["x"]}')
    context = {'selected_platforms':['x','tiktok'], 'active_platform':'tiktok',
        'variants':{'x':{'posts':['X caption']}, 'tiktok':{'posts':['TikTok caption']}}}
    assert plan_message('Make this funnier', context).platforms == ['tiktok']
    assert plan_message('Make all versions funnier', context).platforms == ['x','tiktok']
    result = plan_message('Make all versions funnier except Twitter', context)
    assert result.platforms == ['tiktok']


def test_sponsorship_plan_and_generation_remain_drafts_without_publication_or_consent(monkeypatch):
    import json
    import nova.app as app_module
    import nova.conversation as module
    from sqlalchemy import select
    from nova.db import SessionLocal, PublishReview, Publication, ScheduledPost
    client, uid, *_ = account()
    row = client.post('/api/drafts', json={}).json()
    message = 'Posting this video again. Quick gag on adulting. Add link to my website www.zova-social.co.uk who are sponsoring this post.'
    def response(prompt, **kwargs):
        if 'conversational social editor' in prompt:
            return '{"action":"rewrite","platforms":["x"],"brief":"Add the sponsor"}'
        assert message in prompt
        return json.dumps({'tiktok':{'posts':['Adulting attempt: sponsored by www.zova-social.co.uk #ad']}})
    monkeypatch.setattr(module.ai, '_responses', response)
    monkeypatch.setattr(app_module, 'publish_platform', lambda *a, **k: pytest.fail('Drafting cannot publish'))
    planned = client.post('/api/conversation/plan', json={'message':message, 'draft_id':row['id'],
        'selected_platforms':['tiktok'], 'active_platform':'x'})
    assert planned.status_code == 200, planned.text
    plan = planned.json()
    assert plan['action'] == 'create' and plan['platforms'] == ['tiktok']
    generated = client.post('/api/ai/generate', json={'draft_id':row['id'], 'brief':plan['brief'],
        'platforms':plan['platforms']})
    assert generated.status_code == 200, generated.text
    assert set(generated.json()['variants']) == {'tiktok'}
    saved = client.get(f"/api/drafts/{row['id']}").json()
    assert saved['status'] == 'draft'
    assert saved['workspace'].get('publish_options') is None
    with SessionLocal() as db:
        for model in (PublishReview, Publication, ScheduledPost):
            assert db.scalar(select(model).where(model.user_id == uid)) is None


@pytest.mark.parametrize('message',['Post this shlop','Please post this video','Publish this to TikTok','Schedule this for tomorrow'])
def test_first_post_request_proposes_caption_without_requiring_user_to_write_one(message,monkeypatch):
    import nova.conversation as module
    monkeypatch.setattr(module.ai,'_responses',lambda *a,**k:pytest.fail('Direct first-post intent is deterministic'))
    result=plan_message(message,{'selected_platforms':['tiktok'],'active_platform':'x','variants':{},
        'attachment_observations':[{'status':'inspected','observations':'A humorous video about adulting'}]})
    assert result.action=='create' and result.platforms==['tiktok']
    assert result.brief==message


@pytest.mark.parametrize('action',['publish','schedule'])
@pytest.mark.parametrize('variants',[{}, {'tiktok':{'posts':[]}}, {'tiktok':{'posts':[' ','']}}])
def test_model_publication_plan_without_caption_is_normalized_to_drafting(action,variants,monkeypatch):
    import json
    import nova.conversation as module
    monkeypatch.setattr(module.ai,'_responses',lambda *a,**k:json.dumps({'action':action,'platforms':['x']}))
    result=plan_message('Ready to share it now',{'selected_platforms':['tiktok'],'variants':variants,
        'brief':'A funny moment on camera'})
    assert result.action=='create' and result.platforms==['tiktok']
    assert 'A funny moment on camera' in result.brief and 'Ready to share it now' in result.brief


@pytest.mark.parametrize('action',['answer','insight'])
def test_general_questions_without_caption_are_not_forced_into_drafting(action,monkeypatch):
    import json
    import nova.conversation as module
    monkeypatch.setattr(module.ai,'_responses',lambda *a,**k:json.dumps({'action':action,'reply':'Useful answer'}))
    assert plan_message('What time should I post?',{'selected_platforms':['tiktok'],'variants':{}}).action==action


def test_first_post_fix_preserves_negation_existing_caption_and_selection(monkeypatch):
    import nova.conversation as module
    monkeypatch.setattr(module.ai,'_responses',lambda *a,**k:'{"action":"publish","platforms":["tiktok"]}')
    assert plan_message('Post this video but do not publish yet',{'selected_platforms':['tiktok']}).action=='answer'
    result=plan_message('Post this shlop',{'selected_platforms':['tiktok'],'variants':{'tiktok':{'posts':['Reviewed caption']}}})
    assert result.action=='publish'
    assert plan_message('Post this shlop',{'selected_platforms':[],'variants':{}}).action=='answer'


def test_exact_uploaded_video_request_generates_caption_and_no_delivery_records(monkeypatch):
    import nova.app as app_module
    import nova.conversation as module
    import nova.media_inspection as inspection
    from sqlalchemy import select
    from nova.db import SessionLocal,MediaAsset,PublishReview,Publication,ScheduledPost
    client,uid,*_=account()
    with SessionLocal() as db:
        asset=MediaAsset(user_id=uid,filename='synthetic.mp4',mime_type='video/mp4',storage_key='synthetic',public_url='https://example.test/video.mp4',size_bytes=20)
        db.add(asset);db.commit();asset_id=asset.id
    draft=client.post('/api/drafts',json={}).json()
    observed=[]
    def inspect(db,owner,ids):
        assert owner==uid and ids==[asset_id]
        observed.append(ids)
        return [{'status':'inspected','kind':'video','coverage':'frames','observations':'A humorous video about adulting'}]
    monkeypatch.setattr(inspection,'inspect_assets',inspect)
    monkeypatch.setattr(module.ai,'_responses',lambda *a,**k:pytest.fail('No planner model needed'))
    def generate(**kwargs):
        assert kwargs['brief']=='Post this shlop'
        assert kwargs['platforms']==['tiktok']
        assert 'humorous video about adulting' in kwargs['instruction']
        return {'tiktok':{'posts':['Adulting: attempt number two.']}}
    monkeypatch.setattr(module.ai,'generate_variants',generate)
    monkeypatch.setattr(app_module,'publish_platform',lambda *a,**k:pytest.fail('Drafting cannot publish'))
    planned=client.post('/api/conversation/plan',json={'draft_id':draft['id'],'message':'Post this shlop','selected_platforms':['tiktok'],'media_asset_ids':[asset_id]})
    assert planned.status_code==200,planned.text
    plan=planned.json();assert plan['action']=='create'
    generated=client.post('/api/ai/generate',json={'draft_id':draft['id'],'brief':plan['brief'],'platforms':plan['platforms'],'media_asset_ids':[asset_id]})
    assert generated.status_code==200,generated.text
    assert generated.json()['variants']['tiktok']['posts']==['Adulting: attempt number two.']
    assert len(observed)==2
    assert client.get(f"/api/drafts/{draft['id']}").json()['status']=='draft'
    with SessionLocal() as db:
        for model in (PublishReview,Publication,ScheduledPost):
            assert db.scalar(select(model).where(model.user_id==uid)) is None
