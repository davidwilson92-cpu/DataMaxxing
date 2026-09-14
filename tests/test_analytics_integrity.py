from datetime import datetime, timezone, timedelta
from nova.analytics_view import dashboard


def test_window_missing_values_and_account_totals_are_not_mixed():
    now = datetime(2026, 9, 14, tzinfo=timezone.utc)
    recent = {'platform':'instagram','created_at':now.isoformat(),'likes':4,'comments':0,'shares':None,'views':None}
    old = {**recent,'created_at':(now-timedelta(days=8)).isoformat(),'likes':999}
    result = dashboard({'instagram':{'connected':True,'likes':5000,'followers':40}}, {'posts':[recent,old,{**recent,'created_at':''}]}, now)
    assert result['summary']['likes'] == 4
    assert result['summary']['shares'] is None
    assert result['summary']['impressions'] is None
    assert result['summary']['followers'] == 40
    assert result['summary']['posts'] == 1
    assert result['excluded_undated'] == 1
    assert result['summary']['engagement_rate'] is None


def test_no_accounts_is_missing_not_zero():
    result = dashboard({}, {'posts':[]})
    assert result['summary']['likes'] is None
