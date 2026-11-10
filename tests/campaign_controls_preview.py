"""Disposable local UI fixture. No real credentials, model or provider access."""
import json
import os
import sys
from pathlib import Path

sys.path[:0] = [str(Path(__file__).resolve().parent), str(Path(__file__).resolve().parents[1])]
import conftest
os.environ.update(PUBLIC_BASE_URL='http://127.0.0.1:8797', RATE_LIMIT_SCALE='20')
import httpx
from fastapi.responses import RedirectResponse
from nova import ai, allowances, media_inspection
from nova.app import app
from test_account_integrity import account

def blocked(*args, **kwargs):
    raise RuntimeError('External services are disabled in the campaign preview')
for method in ('get', 'post', 'put', 'patch', 'delete'):
    setattr(httpx, method, blocked)
accounts = [account() for _ in range(4)]
allowances.tier = lambda db, uid: 'premium' if uid in [a[1] for a in accounts[:3]] else None
media_inspection.inspect_assets = lambda *args: []
generation = 0
def generate(prompt, **kwargs):
    global generation
    generation += 1
    payload = json.loads(prompt.rsplit('\n', 1)[-1])
    captions = ['See how the offer works.', 'What would you like to try?', 'A small detail makes the difference.', 'Make time for your next visit.']
    if payload.get('positions') and payload['positions'][0] >= len(payload.get('sequence', [])):
        captions = ['What happens after collection?', 'Bring a little colour to your table.']
    return json.dumps({'posts':[{'caption': captions[i % len(captions)]+' Version '+str(generation), 'asset_id':None}
                               for i in range(len(payload['slots']))]})
ai.editorial_response = generate

@app.get('/fixture/{persona}')
def login(persona: int):
    response = RedirectResponse('/campaigns')
    response.set_cookie('nova_session', accounts[persona][2], httponly=True)
    return response

if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app, host='127.0.0.1', port=8797, log_level='error')
