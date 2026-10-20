const {test} = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');

function setup({action = '/verify-email', reply, valid = true} = {}) {
  const requests = [], navigation = [], listeners = {}, attributes = {};
  const button = {disabled: false}, message = {textContent: ''};
  const fields = {token: 'synthetic-one-use', password: 'synthetic-test-only'};
  const form = {
    action, method: 'post', fields,
    reportValidity: () => valid,
    querySelector: selector => selector.includes('button') ? button : message,
    addEventListener: (name, listener) => { listeners[name] = listener; },
    setAttribute: (name, value) => { attributes[name] = value; },
    removeAttribute: name => { delete attributes[name]; },
  };
  const context = {
    URL,
    FormData: class { constructor(source) { this.values = {...source.fields}; } },
    location: {
      href: 'https://zova.example/verify-email',
      origin: 'https://zova.example',
      assign: url => navigation.push(url),
    },
    document: {querySelectorAll: () => [form]},
    fetch: async (url, options) => {
      requests.push({url, options});
      return reply ? await reply() : {ok: true, url: 'https://zova.example/account?saved=verified'};
    },
  };
  vm.createContext(context);
  vm.runInContext(fs.readFileSync('nova/static/security-forms.js', 'utf8'), context);
  return {
    requests, navigation, button, message, fields, attributes,
    submit: () => listeners.submit({preventDefault() {}}),
  };
}

test('private security forms retain Origin without sending a Referer or widening cookie scope', async () => {
  const t = setup();
  await t.submit();
  assert.equal(t.requests.length, 1);
  const {url, options} = t.requests[0];
  assert.equal(url, 'https://zova.example/verify-email');
  assert.equal(options.method, 'POST');
  assert.equal(options.mode, 'cors');
  assert.equal(options.referrerPolicy, 'no-referrer');
  assert.equal(options.credentials, 'same-origin');
  assert.equal(options.body.values.token, 'synthetic-one-use');
  assert.deepEqual(t.navigation, ['https://zova.example/account?saved=verified']);
  assert.equal(t.button.disabled, true);
});

test('a pending or completed submission cannot dispatch twice', async () => {
  let finish;
  const t = setup({reply: () => new Promise(resolve => { finish = resolve; })});
  const first = t.submit();
  await t.submit();
  assert.equal(t.requests.length, 1);
  assert.equal(t.attributes['aria-busy'], 'true');
  finish({ok: true, url: 'https://zova.example/account'});
  await first;
  await t.submit();
  assert.equal(t.requests.length, 1);
});

test('a failed response keeps input, shows text safely and allows a deliberate retry', async () => {
  let fails = true;
  const t = setup({reply: async () => fails
    ? {ok: false, json: async () => ({detail: 'This link expired or was already used.'})}
    : {ok: true, url: 'https://zova.example/account'}});
  await t.submit();
  assert.equal(t.fields.token, 'synthetic-one-use');
  assert.equal(t.fields.password, 'synthetic-test-only');
  assert.equal(t.message.textContent, 'This link expired or was already used.');
  assert.equal(t.button.disabled, false);
  assert.equal(t.attributes['aria-busy'], undefined);
  assert.deepEqual(t.navigation, []);
  fails = false;
  await t.submit();
  assert.equal(t.requests.length, 2);
});

test('network errors preserve input without exposing diagnostic data or retrying automatically', async () => {
  const t = setup({reply: async () => { throw new Error('private diagnostic'); }});
  await t.submit();
  assert.match(t.message.textContent, /entries are still here/);
  assert.doesNotMatch(t.message.textContent, /private diagnostic/);
  assert.equal(t.requests.length, 1);
  assert.equal(t.button.disabled, false);
  assert.equal(t.fields.password, 'synthetic-test-only');
});

test('rejects invalid forms and off-site form actions, and refuses off-site navigation', async () => {
  for (const options of [{valid: false}, {action: 'https://other.example/collect'}]) {
    const t = setup(options);
    await t.submit();
    assert.equal(t.requests.length, 0);
    assert.deepEqual(t.navigation, []);
  }
  const t = setup({reply: async () => ({ok: true, url: 'https://other.example/continue'})});
  await t.submit();
  assert.deepEqual(t.navigation, []);
  assert.equal(t.button.disabled, false);
});
