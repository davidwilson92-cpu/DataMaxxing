"""Rendered customer pages must link to real routes/assets with valid methods."""
from html.parser import HTMLParser
from urllib.parse import urlsplit, urljoin, unquote
from pathlib import Path

import pytest
from starlette.routing import Match
from fastapi.testclient import TestClient
from nova.app import app, HERE
from test_account_integrity import account


class References(HTMLParser):
    def __init__(self):
        super().__init__()
        self.targets = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == 'form':
            self.targets.append((attrs.get('action', ''), attrs.get('method', 'get').upper()))
        elif tag in {'a', 'link', 'script', 'img', 'video', 'source'}:
            value = attrs.get('href') if tag in {'a', 'link'} else attrs.get('src')
            if value:
                self.targets.append((value, 'GET'))


def test_rendered_customer_links_forms_and_assets_resolve():
    client, *_ = account()
    pages = ['/', '/login', '/signup', '/studio', '/drafts', '/analytics', '/account',
             '/account/deletion', '/brands', '/subscribe', '/security', '/privacy',
             '/terms', '/refunds', '/data-deletion', '/guide', '/help',
             '/onboarding/socials', '/onboarding/writing-style', '/forgot-password',
             '/reset-password', '/verify-email']
    targets = set()
    for page in pages:
        response = client.get(page)
        assert response.status_code == 200, (page, response.status_code)
        parser = References()
        parser.feed(response.text)
        for ref, method in parser.targets:
            if ref.startswith(('#', 'mailto:', 'tel:', 'data:', 'blob:')):
                continue
            url = urlsplit(urljoin('http://testserver' + page, ref))
            assert url.scheme in {'http', 'https'}, (page, ref)
            if url.netloc != 'testserver':
                continue
            targets.add((url.path, method))
    assert len(targets) >= 50
    for path, method in targets:
        if path.startswith('/static/'):
            file = (HERE / 'static' / unquote(path[len('/static/'):])).resolve()
            assert file.is_relative_to((HERE / 'static').resolve()) and file.is_file(), path
        else:
            scope = {'type': 'http', 'path': path, 'root_path': '', 'method': method}
            assert any(route.matches(scope)[0] == Match.FULL for route in app.routes), (method, path)


@pytest.mark.parametrize('path', ['/studio', '/drafts', '/analytics', '/account', '/brands', '/account/deletion'])
def test_signed_out_private_pages_return_to_login(path):
    response = TestClient(app).get(path, follow_redirects=False)
    assert response.status_code == 303
    assert response.headers['location'].startswith('/login')
