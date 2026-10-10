import importlib.util
import json
from pathlib import Path
import pytest

spec=importlib.util.spec_from_file_location('beta_gate',Path(__file__).resolve().parents[1]/'scripts/check_beta_release.py')
gate=importlib.util.module_from_spec(spec);spec.loader.exec_module(gate)

def test_current_beta_scope_matches():
    assert 'commercial readiness remains unapproved' in gate.validate()

@pytest.mark.parametrize('change',['source','gap','commercial'])
def test_beta_gate_rejects_drift(tmp_path,change):
    (tmp_path/'nova').mkdir();(tmp_path/'nova/app.py').write_text('safe')
    folder=tmp_path/'docs/beta';folder.mkdir(parents=True)
    (folder/'KNOWN_GAPS.md').write_text('Pending')
    (folder/'deferred-register.json').write_text(json.dumps({'sections':[{'id':i} for i in range(1,80)]}))
    manifest={'release_class':'limited-beta','authorised_on':'2026-10-10','commercial_ready':False,'files':gate.files(tmp_path)}
    if change=='source':(tmp_path/'nova/app.py').write_text('changed')
    elif change=='gap':(folder/'KNOWN_GAPS.md').write_text('forgotten')
    else:manifest['commercial_ready']=True
    (folder/'release-scope.json').write_text(json.dumps(manifest))
    with pytest.raises(ValueError):gate.validate(tmp_path)
