import json
from test_account_integrity import account
from nova import security
from nova.db import SessionLocal, MediaAsset, Brand, PerformanceSnapshot, utcnow
from nova.storage import UPLOAD_DIR
from nova.data_lifecycle import erase_local_account, export_account

def test_erasure_removes_observations_without_files_across_brands():
    _, uid, token, _ = account()
    _, other, _, _ = account()
    with SessionLocal() as db:
        brand = Brand(user_id=uid, name="Synthetic second brand")
        db.add(brand); db.flush()
        path = UPLOAD_DIR / f"derived-erasure-{uid}.png"
        path.write_bytes(b"synthetic")
        own = []
        for brand_id, storage in [(0, str(path)), (brand.id, "")]:
            asset = MediaAsset(user_id=uid, brand_id=brand_id, filename="private.png",
                mime_type="image/png", storage_key=storage,
                analysis_json=json.dumps({"fingerprint":"PRIVATE_FINGERPRINT", "result":{"observations":"PRIVATE_VISUAL_DETAIL"}}))
            db.add(asset); own.append(asset)
        other_asset = MediaAsset(user_id=other, filename="other.png", mime_type="image/png",
            storage_key="", analysis_json='{"result":{"observations":"OTHER_OWNER"}}')
        db.add(other_asset); db.commit()
        assert "PRIVATE_VISUAL_DETAIL" in json.dumps(export_account(db, uid))
        result = erase_local_account(db, uid, "synthetic-privacy-case", writes_paused=True)
        assert result["status"] == "active_store_erased" and not path.exists()
        assert all(a.analysis_json == "{}" for a in own)
        exported = json.dumps(export_account(db, uid))
        assert "PRIVATE_VISUAL_DETAIL" not in exported and "PRIVATE_FINGERPRINT" not in exported
        assert "OTHER_OWNER" in db.get(MediaAsset, other_asset.id).analysis_json
        # Retrying an already completed case remains safe and clears any old missing-file cache.
        erase_local_account(db, uid, "synthetic-privacy-case", writes_paused=True)
    assert security.user_from_session(token) is None

def test_performance_snapshot_export_and_erasure_are_account_scoped():
    _, uid, _, _ = account()
    _, other, _, _ = account()
    with SessionLocal() as db:
        owned = PerformanceSnapshot(user_id=uid, brand_id=0, payload_json='{"caption":"PRIVATE_CAPTION"}')
        unrelated = PerformanceSnapshot(user_id=other, brand_id=0, payload_json='{"caption":"OTHER_CAPTION"}')
        db.add_all([owned, unrelated]); db.commit()
        own_id, other_id = owned.id, unrelated.id
        exported = json.dumps(export_account(db, uid))
        assert "PRIVATE_CAPTION" in exported and "OTHER_CAPTION" not in exported
        erase_local_account(db, uid, "synthetic-performance-case", writes_paused=True)
        assert db.get(PerformanceSnapshot, own_id) is None
        assert "OTHER_CAPTION" in db.get(PerformanceSnapshot, other_id).payload_json
