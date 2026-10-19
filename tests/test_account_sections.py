from html.parser import HTMLParser

from test_account_integrity import account


class Groups(HTMLParser):
    def __init__(self):
        super().__init__()
        self.stack, self.groups, self.forms = [], {}, {}

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == 'details':
            group = attrs.get('data-account-group')
            self.stack.append(group)
            if group:
                self.groups[group] = 'open' in attrs
        if tag == 'form':
            self.forms[attrs.get('action')] = next((g for g in reversed(self.stack) if g), None)

    def handle_endtag(self, tag):
        if tag == 'details':
            self.stack.pop()


def test_grouping_preserves_account_forms_and_reveals_save_errors():
    client, _, _, _ = account()
    parser = Groups()
    parser.feed(client.get('/account').text)
    assert set(parser.groups) == {'profile', 'voice', 'socials', 'security', 'plan'}
    assert not any(parser.groups.values())
    assert not parser.stack
    assert parser.forms['/account/profile'] == 'profile'
    assert parser.forms['/account/preferences'] == 'voice'
    assert parser.forms['/account/password'] == 'security'
    assert parser.forms['/logout'] == 'plan'
    for query, expected in [('saved=profile', 'profile'), ('saved=password', 'security'), ('saved=voice', 'voice'),
                            ('error=password_match', 'security'), ('connection_failed=instagram', 'socials')]:
        parsed = Groups()
        page = client.get('/account?' + query)
        assert page.status_code == 200
        parsed.feed(page.text)
        assert parsed.groups[expected]


def test_shared_night_theme_and_clear_creation_action_keep_routes_available():
    client, _, _, _ = account()
    for route in ['/studio', '/drafts', '/analytics', '/account']:
        page = client.get(route)
        assert page.status_code == 200
        assert '/static/zova-night.css' in page.text
    studio = client.get('/studio').text
    assert 'aria-label="Start a new post"' in studio
    assert 'onclick="newConversation()"' in studio
    assert 'id="brief"' in studio
