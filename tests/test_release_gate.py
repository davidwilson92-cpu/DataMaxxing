import copy
import importlib.util
import json
from pathlib import Path

spec = importlib.util.spec_from_file_location('release_gate', Path(__file__).resolve().parents[1] / 'scripts/release_gate.py')
gate = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gate)


def register():
    return json.loads((gate.ROOT / gate.REGISTER).read_text(encoding='utf-8'))


def test_real_assessment_is_valid_but_cannot_release_with_open_requirements():
    data = register()
    assert not gate.validate(data, release=False)
    assert gate.validate(data, release=True)


def test_missing_duplicate_unknown_and_unreviewed_sections_fail_closed():
    for mutate in [lambda d: d['sections'].pop(),
                   lambda d: d['sections'].__setitem__(0, d['sections'][1]),
                   lambda d: d['sections'][0].update(status='waived'),
                   lambda d: d['sections'][0].update(status='met', evidence=[]),
                   lambda d: d.update(baseline_sha256='wrong')]:
        data = register(); mutate(data)
        assert gate.validate(data, release=False)


def test_even_low_severity_open_requirement_blocks_production():
    data = register()
    data['sections'][0].update(severity='P3', status='partial')
    assert any('Section 1 [P3]' in e for e in gate.validate(data))


def test_missing_stale_and_outside_repository_evidence_is_rejected():
    for path in ['not-present.txt', '../outside.md', 'nova/app.py']:
        data = register()
        data['sections'][0]['evidence'] = [{'path': path, 'sha256': 'wrong'}]
        assert gate.validate(data, release=False)


def test_source_change_invalidates_release_approval():
    data = register()
    data['reviewed_source_digest'] = 'stale'
    assert any('Source changed' in e for e in gate.validate(data))


def test_not_applicable_requires_review_and_rationale():
    data = register()
    data['sections'][0].update(status='not_applicable', reviewed_by='reviewer', reviewed_at='2026-09-28')
    assert any('applicability rationale' in e for e in gate.validate(data, release=False))


def test_complete_review_of_exact_candidate_can_pass_without_changing_real_register():
    data = register()
    for row in data['sections']:
        row.update(status='met', reviewed_by='synthetic test reviewer', reviewed_at='2026-09-28')
    data['reviewed_source_digest'] = gate.source_digest()
    assert not gate.validate(data)
