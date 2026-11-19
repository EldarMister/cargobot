// Run with: node --test tests/test_web_upload.cjs
// Exercise the real form handlers with Android-like one-shot file handles.
const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

function panel() {
  const elements = new Map();
  const requests = [];
  function element(selector) {
    if (!elements.has(selector)) elements.set(selector, {
      value: '', options: [], listeners: {}, disabled: false,
      classList: { add() {}, remove() {}, toggle() {} },
      setAttribute() {}, reset() {},
      querySelector: () => element(`${selector} [type=submit]`),
      addEventListener(type, fn) { this.listeners[type] = fn; },
      showModal() { this.open = true; },
      close() { this.open = false; this.listeners.close?.(); },
    });
    return elements.get(selector);
  }
  const context = vm.createContext({
    Blob, URLSearchParams, Error, console, queueMicrotask,
    location: { search: '', hostname: 'test' },
    window: { AdminI18n: { t: key => key, applyStatic() {} }, scrollTo() {} },
    document: { querySelector: element, querySelectorAll: () => [], addEventListener() {} },
    setTimeout(fn) { fn(); }, clearTimeout() {},
    FormData: class extends FormData {
      constructor(form) {
        super();
        if (form) {
          this.set('file', form.original);
          this.set('selected_status', 'CHINA_WAREHOUSE');
          this.set('target_import_id', '');
          this.set('transit_days', '12');
        }
      }
    },
    FileReader: class {
      readAsArrayBuffer(file) {
        file.reads += 1;
        const finish = () => {
          if (file.unreadable) this.onerror();
          else { this.result = file.bytes; this.onload(); }
        };
        if (file.hold) file.finish = finish;
        else queueMicrotask(finish);
      }
    },
    async fetch(url, options) {
      requests.push({ url, options });
      return new Response(JSON.stringify(url.endsWith('/analyze')
        ? { duplicate: null, suggestion: null } : { id: 1, created: 1, updated: 0 }));
    },
  });
  vm.runInContext(fs.readFileSync(path.join(__dirname, '../app/web/static/app.js'), 'utf8'), context);
  vm.runInContext('loadImports = loadParcels = loadDashboard = async () => {};', context);
  return {
    context, element, requests,
    select(file) {
      element('#import-form').original = file;
      return element('#excel-file').listeners.change({ target: { files: [file] } });
    },
    submit() {
      return element('#import-form').listeners.submit({
        preventDefault() {}, target: element('#import-form'),
      });
    },
    state: () => vm.runInContext('state', context),
  };
}

function androidFile(name = '糖宝.xls1.xls', bytes = new Uint8Array([1, 2, 3])) {
  const file = new File([bytes], name);
  file.bytes = bytes.buffer;
  file.reads = 0;
  // Accessing these is enough to break some Android content providers.
  for (const property of ['size', 'lastModified']) {
    Object.defineProperty(file, property, { get() { throw new Error(`Unsafe ${property} access`); } });
  }
  return file;
}

test('analysis and import send a memory copy without reading Android file metadata', async () => {
  const p = panel();
  const file = androidFile();
  await p.select(file);
  assert.equal(p.requests.length, 1);
  file.unreadable = true; // Provider access is lost after selecting the file.
  await p.submit();
  assert.equal(file.reads, 1);
  assert.deepEqual(p.requests.map(r => r.url), ['/api/imports/analyze', '/api/imports']);
  for (const request of p.requests) {
    const uploaded = request.options.body.get('file');
    assert.notEqual(uploaded, file);
    assert.equal(uploaded.name, file.name);
    assert.deepEqual(new Uint8Array(await uploaded.arrayBuffer()), new Uint8Array(file.bytes));
  }
  assert.equal(p.requests[1].options.body.get('selected_status'), 'CHINA_WAREHOUSE');
});

test('network retry reuses captured bytes after source access is lost', async () => {
  const p = panel();
  const file = androidFile();
  await p.select(file);
  const successfulFetch = p.context.fetch;
  let attempts = 0;
  p.context.fetch = async (...args) => {
    if (attempts++ === 0) {
      file.unreadable = true;
      throw new TypeError('Failed to fetch');
    }
    return successfulFetch(...args);
  };
  await p.submit();
  assert.equal(attempts, 2);
  assert.equal(file.reads, 1);
  assert.equal(p.requests[1].url, '/api/imports');
  assert.deepEqual(new Uint8Array(await p.requests[1].options.body.get('file').arrayBuffer()),
    new Uint8Array(file.bytes));
});

test('unreadable file shows a local read error and prevents submission', async () => {
  const p = panel();
  const file = androidFile();
  file.unreadable = true;
  await p.select(file);
  await p.submit();
  assert.equal(p.requests.length, 0);
  assert.equal(p.state().importFileError, true);
  assert.equal(p.element('#import-form [type=submit]').disabled, true);
  assert.match(p.element('#import-analysis').textContent, /Загрузки/);
});

test('submission waits for reading and obsolete file reads cannot replace a new selection', async () => {
  const p = panel();
  const oldFile = androidFile('old.xls');
  oldFile.hold = true;
  const pending = p.select(oldFile);
  assert.equal(oldFile.reads, 1); // Reading starts before the first async boundary.
  await p.submit();
  assert.equal(p.requests.length, 0);
  const newFile = androidFile('new.xlsx');
  await p.select(newFile);
  oldFile.finish();
  await pending;
  assert.equal(p.state().importFile.name, 'new.xlsx');
  assert.equal(p.requests.length, 1);
});

test('closing dialog while reading discards the completed read', async () => {
  const p = panel();
  const file = androidFile();
  file.hold = true;
  const pending = p.select(file);
  p.element('#import-sheet').close();
  file.finish();
  await pending;
  assert.equal(p.state().importFile, null);
  assert.equal(p.requests.length, 0);
});

test('empty and oversized captured files are rejected before any network request', async () => {
  for (const length of [0, 20 * 1024 * 1024 + 1]) {
    const p = panel();
    await p.select(androidFile('cargo.xls', new Uint8Array(length)));
    await p.submit();
    assert.equal(p.requests.length, 0);
    assert.equal(p.element('#import-form [type=submit]').disabled, true);
    assert.equal(p.state().importFileError, true);
  }
});

test('client message sends to the shown recipient once despite double submission', async () => {
  const p = panel();
  vm.runInContext("openClientMessage({id:7,client_code:'H-853',full_name:'Клиент',telegram_id:123456});", p.context);
  assert.match(p.element('#client-message-recipient').textContent, /H-853/);
  assert.match(p.element('#client-message-text').value, /H-853/);
  p.element('#client-message-text').value = 'Ваш груз <прибыл> & ждёт вас';
  let complete;
  p.context.fetch = (url, options) => {
    p.requests.push({url, options});
    return new Promise(resolve => { complete = resolve; });
  };
  const event = {preventDefault() {}, target:p.element('#client-message-form')};
  const first = p.element('#client-message-form').listeners.submit(event);
  await p.element('#client-message-form').listeners.submit(event);
  assert.equal(p.requests.length, 1);
  assert.equal(p.element('#client-message-form [type=submit]').disabled, true);
  assert.equal(p.requests[0].url, '/api/clients/7/messages');
  assert.deepEqual(JSON.parse(p.requests[0].options.body), {
    text:'Ваш груз <прибыл> & ждёт вас', expected_telegram_id:123456,
  });
  complete(new Response(JSON.stringify({ok:true,message_id:42})));
  await first;
  assert.equal(p.element('#client-message-sheet').open, false);
});

test('message network failure keeps draft and does not automatically resend', async () => {
  const p = panel();
  vm.runInContext("openClientMessage({id:7,client_code:'H-853',full_name:'Клиент',telegram_id:123456});", p.context);
  p.element('#client-message-text').value = 'Личное сообщение';
  p.context.fetch = async () => { p.requests.push({}); throw new TypeError('Lost response'); };
  await p.element('#client-message-form').listeners.submit({preventDefault() {},target:p.element('#client-message-form')});
  assert.equal(p.requests.length, 1);
  assert.equal(p.element('#client-message-sheet').open, true);
  assert.equal(p.element('#client-message-text').value, 'Личное сообщение');
  assert.match(p.element('#client-message-error').textContent, /Перед повтором уточните/);
  assert.equal(p.element('#client-message-error').hidden, false);
});
