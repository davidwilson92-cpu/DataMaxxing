from test_account_integrity import account


def test_signup_keeps_nonsecret_inputs_after_error():
    client,*_=account()
    response=client.post('/signup',data={'name':'Synthetic Person','email':'person@example.test','country':'GB','password':'long-password-123','password_confirmation':'different','accept_terms':'yes'},follow_redirects=False)
    assert response.status_code==303
    assert 'long-password' not in response.headers.get('set-cookie','')
    page=client.get(response.headers['location'])
    assert 'value="Synthetic Person"' in page.text
    assert 'value="person@example.test"' in page.text
    assert 'United Kingdom' in page.text
    assert 'long-password-123' not in page.text


def test_checkout_disabled_while_testing(monkeypatch):
    client,*_=account()
    monkeypatch.setenv('STRIPE_SECRET_KEY','mock')
    monkeypatch.setenv('STRIPE_PRICE_ID','mock')
    assert client.get('/billing/checkout').status_code==409
