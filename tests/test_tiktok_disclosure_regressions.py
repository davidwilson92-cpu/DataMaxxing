"""Synthetic evidence for commercial disclosure; never submits a real post."""
import copy
from pathlib import Path
import shutil
import subprocess

import httpx
import pytest
from sqlalchemy import select

from nova import social
from nova.db import MediaAsset, SessionLocal, SocialConnection
from test_reviewed_publication import prepared
from test_tiktok_direct_post import setup


@pytest.mark.parametrize("own,paid,privacy", [
    (False, False, "SELF_ONLY"),
    (True, False, "SELF_ONLY"),
    (True, False, "PUBLIC_TO_EVERYONE"),
    (False, True, "PUBLIC_TO_EVERYONE"),
    (True, True, "PUBLIC_TO_EVERYONE"),
])
def test_disclosure_choices_reach_mock_provider_exactly(monkeypatch, own, paid, privacy):
    asset, options, _, _ = setup(monkeypatch)
    options.update(commercial_content=own or paid, your_brand=own,
                   brand_content=paid, privacy_level=privacy)
    calls = []

    def post(url, **kwargs):
        calls.append(kwargs["json"])
        return httpx.Response(200, json={"data": {"publish_id": "synthetic-disclosure"}})

    monkeypatch.setattr(social.httpx, "post", post)
    result = social.publish_tiktok(None, None, ["Reviewed caption"], [asset], options=options)
    assert result["pending"]
    assert len(calls) == 1
    assert calls[0]["post_info"]["brand_organic_toggle"] is own
    assert calls[0]["post_info"]["brand_content_toggle"] is paid
    assert calls[0]["post_info"]["privacy_level"] == privacy


@pytest.mark.parametrize("choices", [
    {"commercial_content": True, "your_brand": False, "brand_content": False},
    {"commercial_content": False, "your_brand": True, "brand_content": False},
    {"commercial_content": False, "your_brand": False, "brand_content": True},
    {"commercial_content": True, "your_brand": False, "brand_content": True, "privacy_level": "SELF_ONLY"},
    {"commercial_content": True, "your_brand": True, "brand_content": True, "privacy_level": "SELF_ONLY"},
])
def test_inconsistent_or_private_paid_disclosure_never_dispatches(monkeypatch, choices):
    asset, options, _, _ = setup(monkeypatch)
    options.update(choices)
    calls = []
    monkeypatch.setattr(social.httpx, "post", lambda *a, **kw: calls.append(kw))
    with pytest.raises(RuntimeError, match="Select Your brand|Only me"):
        social.publish_tiktok(None, None, ["Caption"], [asset], options=options)
    assert calls == []


def test_review_snapshot_binds_all_disclosure_choices_and_consent(monkeypatch):
    asset, options, _, _ = setup(monkeypatch)
    options.update(commercial_content=True, your_brand=True, brand_content=True,
                   allow_comment=False, allow_duet=False, allow_stitch=False,
                   is_aigc=False)
    client, uid, _, body = prepared(("tiktok",))
    with SessionLocal() as db:
        conn = db.scalar(select(SocialConnection).where(SocialConnection.user_id == uid))
        conn.scope = "user.info.basic,video.publish"
        media = MediaAsset(user_id=uid, filename="synthetic.mp4", mime_type=asset.mime_type,
                           storage_key=asset.storage_key, public_url=asset.public_url, size_bytes=20)
        db.add(media)
        db.commit()
        body["media_asset_ids"] = [media.id]
    body["publish_options"] = {"tiktok": options}
    saved = client.patch(f"/api/drafts/{body['draft_id']}", json={
        "platforms": ["tiktok"], "variants": body["variants"],
        "workspace": {"media_asset_ids": body["media_asset_ids"]},
    })
    assert saved.status_code == 200, saved.text
    review = client.post("/api/publish-review", json=body)
    assert review.status_code == 200, review.text
    assert review.json()["snapshot"]["publish_options"]["tiktok"] == options
    approved = {**body, "review_token": review.json()["review_token"]}
    calls = []
    monkeypatch.setattr(social.httpx, "post", lambda *a, **kw: calls.append(kw))
    for field in ("commercial_content", "your_brand", "brand_content", "consent",
                  "allow_comment", "allow_duet", "allow_stitch", "is_aigc"):
        changed = copy.deepcopy(approved)
        changed["publish_options"]["tiktok"][field] = not options[field]
        response = client.post("/api/publish", json=changed)
        assert response.status_code == 409, (field, response.text)
    changed = copy.deepcopy(approved)
    changed["publish_options"]["tiktok"]["privacy_level"] = "SELF_ONLY"
    assert client.post("/api/publish", json=changed).status_code == 409
    assert calls == []


def test_client_disclosure_choices_reset_consent_and_show_correct_label():
    node = shutil.which("node")
    if not node:
        pytest.skip("Node is required for client disclosure regression checks")
    script = r"""
const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const nodes=new Map();
function get(id){if(!nodes.has(id))nodes.set(id,{checked:false,disabled:false,value:'',options:[],textContent:'',innerHTML:'',hidden:false});return nodes.get(id);}
const ctx=vm.createContext({document:{getElementById:get},esc:String,uploadedMediaKind:'video'});
vm.runInContext(fs.readFileSync(process.argv[1],'utf8'),ctx);
const run=code=>vm.runInContext(code,ctx);
const html=run("tiktokDirectControls({display_name:'Synthetic creator',privacy_options:['SELF_ONLY','PUBLIC_TO_EVERYONE']})");
assert.doesNotMatch(html,/<input[^>]*\schecked(?:\s|>)/);
assert.match(html,/<option value="">Choose privacy<\/option>/);
const privacy=get('reviewPrivacy'),own=get('review_your_brand'),paid=get('review_brand_content'),commercial=get('review_commercial_content'),consent=get('review_consent');
privacy.options=[{value:'SELF_ONLY'},{value:'PUBLIC_TO_EVERYONE'}];
function change(id){const tag=html.match(new RegExp('<(?:input|select)\\b[^>]*id="'+id+'"[^>]*>'))[0];const handler=tag.match(/onchange="([^"]+)"/)[1];run(handler);}
privacy.value='PUBLIC_TO_EVERYONE';consent.checked=true;commercial.checked=true;change('review_commercial_content');
assert.equal(consent.checked,false);assert.equal(get('tiktokDisclosure').hidden,false);assert.equal(get('reviewFinalPost').disabled,true);
own.checked=true;change('review_your_brand');assert.match(get('tiktokDisclosureLabel').textContent,/Promotional content/);assert.doesNotMatch(get('tiktokDeclaration').innerHTML,/Branded Content Policy/);
consent.checked=true;assert.equal(run('updateTikTokControls()'),true);
paid.checked=true;change('review_brand_content');assert.equal(consent.checked,false);assert.match(get('tiktokDisclosureLabel').textContent,/Paid partnership/);assert.match(get('tiktokDeclaration').innerHTML,/Branded Content Policy/);assert.equal(privacy.options[0].disabled,true);
consent.checked=true;commercial.checked=false;change('review_commercial_content');assert.equal(consent.checked,false);assert.equal(own.checked,false);assert.equal(paid.checked,false);assert.equal(get('tiktokDisclosure').hidden,true);assert.equal(privacy.options[0].disabled,false);
commercial.checked=true;change('review_commercial_content');privacy.value='SELF_ONLY';change('reviewPrivacy');assert.equal(paid.disabled,true);assert.match(get('tiktokPrivacyNote').textContent,/cannot use Only me/);
own.checked=true;change('review_your_brand');consent.checked=true;assert.equal(run('updateTikTokControls()'),true);
run("tiktokDirectControls({display_name:'Test creator',private_test_mode:true,privacy_options:['SELF_ONLY','PUBLIC_TO_EVERYONE']})");
privacy.value='PUBLIC_TO_EVERYONE';consent.checked=true;assert.equal(run('updateTikTokControls()'),false);assert.equal(privacy.options[1].disabled,true);assert.match(get('tiktokPrivacyNote').textContent,/private account.*Only me.*TikTok approval/);
privacy.value='SELF_ONLY';assert.equal(run('updateTikTokControls()'),true,'own-brand private test remains available');assert.equal(privacy.options[0].disabled,false);
privacy.value='';paid.checked=true;assert.equal(run('updateTikTokControls()'),false,'partnership controls may be demonstrated but cannot submit from sandbox');assert.match(get('tiktokDisclosureLabel').textContent,/Paid partnership/);
run("tiktokDirectControls({display_name:'Audited creator',privacy_options:['SELF_ONLY','PUBLIC_TO_EVERYONE']})");privacy.value='PUBLIC_TO_EVERYONE';assert.equal(run('updateTikTokControls()'),true,'sandbox restriction must not leak into another review');assert.equal(privacy.options[1].disabled,false);
console.log('Commercial selection, consent resets, labels, private restriction and own-brand private review verified');
"""
    source = Path(__file__).resolve().parents[1] / "nova/static/studio-publish.js"
    result = subprocess.run([node, "-e", script, str(source)], capture_output=True, text=True, timeout=30)
    assert result.returncode == 0, result.stdout + result.stderr
