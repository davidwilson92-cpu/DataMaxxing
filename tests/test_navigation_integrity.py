"""Rendered customer pages must link to real routes/assets with valid methods."""
from html.parser import HTMLParser
from urllib.parse import urlsplit, urljoin, unquote

import pytest
from starlette.routing import Match
from fastapi.testclient import TestClient
from nova.app import app, HERE
from test_account_integrity import account


class References(HTMLParser):
    def __init__(self):
        super().__init__()
        self.targets = []
        self.ids = set()

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if attrs.get("id"):
            self.ids.add(attrs["id"])
        if tag == 'form' and attrs.get('method','').lower() != 'dialog':
            self.targets.append((attrs.get('action', ''), attrs.get('method', 'get').upper()))
        elif tag in {'a', 'link', 'script', 'img', 'video', 'source'}:
            value = attrs.get('href') if tag in {'a', 'link'} else attrs.get('src')
            if value:
                self.targets.append((value, 'GET'))


def test_rendered_customer_links_forms_and_assets_resolve():
    client, *_ = account()
    pages = ['/', '/login', '/signup', '/studio', '/campaigns', '/drafts', '/analytics', '/account',
             '/account/deletion', '/brands', '/subscribe', '/security', '/privacy',
             '/terms', '/refunds', '/data-deletion', '/guide', '/help',
             '/onboarding/socials', '/onboarding/writing-style', '/forgot-password',
             '/reset-password', '/verify-email']
    targets = set()
    fragments = set()
    ids_by_page = {}
    for page in pages:
        response = client.get(page)
        assert response.status_code == 200, (page, response.status_code)
        parser = References()
        parser.feed(response.text)
        ids_by_page[urlsplit(str(response.url)).path] = parser.ids
        for ref, method in parser.targets:
            if ref.startswith(( 'mailto:', 'tel:', 'data:', 'blob:')):
                continue
            url = urlsplit(urljoin('http://testserver' + page, ref))
            assert url.scheme in {'http', 'https'}, (page, ref)
            if url.netloc != 'testserver':
                continue
            targets.add((url.path, method))
            if url.fragment and not url.path.startswith('/static/'):
                fragments.add((page, url.path, unquote(url.fragment)))
    for source, path, fragment in sorted(fragments):
        if path not in ids_by_page:
            destination = client.get(path)
            assert destination.status_code == 200, (source, path)
            parser = References()
            parser.feed(destination.text)
            ids_by_page[path] = parser.ids
        assert fragment in ids_by_page[path], (source, path, fragment)
    assert len(targets) >= 50
    for path, method in targets:
        if path.startswith('/static/'):
            file = (HERE / 'static' / unquote(path[len('/static/'):])).resolve()
            assert file.is_relative_to((HERE / 'static').resolve()), path
            response = client.get(path, follow_redirects=False)
            assert response.status_code == 200 and response.content, path
            assert 'text/html' not in response.headers['content-type'], path
        else:
            scope = {'type': 'http', 'path': path, 'root_path': '', 'method': method}
            assert any(route.matches(scope)[0] == Match.FULL for route in app.routes), (method, path)


@pytest.mark.parametrize('path', ['/studio', '/drafts', '/analytics', '/account', '/brands', '/account/deletion'])
def test_signed_out_private_pages_return_to_login(path):
    response = TestClient(app).get(path, follow_redirects=False)
    assert response.status_code == 303
    assert response.headers['location'].startswith('/login')

@pytest.mark.parametrize('target', ['/campaigns', '/brands', '/account/deletion', '/studio?intro=1', '/studio?strategy=1'])
def test_email_login_returns_to_requested_page(target):
    from urllib.parse import parse_qs
    _, _, _, email = account()
    guest = TestClient(app)
    start = guest.get(target, follow_redirects=False)
    assert start.status_code == 303
    login_url = start.headers['location']
    assert parse_qs(urlsplit(login_url).query)['next'] == [target]
    login_page = guest.get(login_url)
    assert login_page.status_code == 200
    assert f'name="next" value="{target}"' in login_page.text
    result = guest.post('/login', data={'email': email, 'password':'old-password-123', 'next':target}, follow_redirects=False)
    assert result.status_code == 303
    assert result.headers['location'] == target
    assert guest.get(target).status_code == 200
