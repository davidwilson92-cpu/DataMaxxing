from pathlib import Path
from types import SimpleNamespace
from jinja2 import Environment, DictLoader

ROOT = Path(__file__).resolve().parents[1]

def templates():
    return Environment(loader=DictLoader({name:(ROOT/'nova/templates'/name).read_text(encoding='utf-8') for name in ['offer_summary.html','membership.html']} | {'base.html':'{% block head %}{% endblock %}{% block body %}{% endblock %}', 'support_link.html':''}))

def test_beta_offer_leads_with_no_card_and_secondary_prices():
    env=templates()
    html=env.get_template('offer_summary.html').render(testing_access=True,offer_state='unavailable',offer_catalog={'basic':{'name':'Basic','monthly':999,'annual':9900}})
    assert html.index('No card required') < html.index('<details>') < html.index('£9.99')
    assert 'does not start a subscription or an automatic charge' in html
    paid=env.get_template('offer_summary.html').render(testing_access=False,offer_state='live',offer_catalog={})
    assert 'Free beta' not in paid and 'payment method is required' in paid

def test_beta_membership_hides_live_checkout_but_preserves_existing_management():
    env=templates()
    billing=dict(mode='live',status='active',checkout_enabled=True,ready=True,customer=True,plan_label='Basic',plans={},trial_eligible=False)
    context=dict(billing_info=billing,subscription_required=False,request=SimpleNamespace(query_params={}),user=SimpleNamespace(email_verified_at=True),catalog={},usage={'period':'2026-10','enabled':False})
    html=env.get_template('membership.html').render(**context)
    assert 'No card required' in html and 'Any existing subscription keeps its own renewal terms' in html
    assert 'action="/billing/portal"' in html
    assert 'action="/billing/checkout"' not in html
    assert '<details class="upcoming-plans">' in html
    billing.update(mode='test',status='none')
    html=env.get_template('membership.html').render(**context)
    assert 'Optional Stripe test checkout' in html and 'action="/billing/checkout"' in html
