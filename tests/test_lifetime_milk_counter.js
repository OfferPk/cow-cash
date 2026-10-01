const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const test = require('node:test');
const vm = require('node:vm');

const gameSource = fs.readFileSync(path.join(__dirname, '../js/game.js'), 'utf8');

class FakeClassList {
  constructor() { this.values = new Set(); }
  add(value) { this.values.add(value); }
  remove(value) { this.values.delete(value); }
  contains(value) { return this.values.has(value); }
}

class FakeElement {
  constructor(id = '') {
    this.id = id;
    this.dataset = {};
    this.style = {};
    this.classList = new FakeClassList();
    this.listeners = {};
    this.children = [];
    this.queryNodes = new Map();
    this.textContent = '';
    this.checked = false;
    this.disabled = false;
    this.isConnected = true;
  }
  addEventListener(type, callback) { this.listeners[type] = callback; }
  appendChild(child) { this.children.push(child); return child; }
  remove() { this.isConnected = false; }
  set innerHTML(value) {
    this._innerHTML = value;
    if (value === '') this.children = [];
  }
  get innerHTML() { return this._innerHTML || ''; }
  querySelector(selector) {
    if (!this.queryNodes.has(selector)) this.queryNodes.set(selector, new FakeElement(selector));
    return this.queryNodes.get(selector);
  }
  querySelectorAll(selector) { return selector === '.item' ? this.children : []; }
  getBoundingClientRect() { return { left: 0, top: 0, width: 100, height: 100 }; }
}

function startGame(savedState = null) {
  const ids = [
    'coins', 'milk', 'mps', 'totalMilk', 'perTap', 'cow', 'sellBtn',
    'sellValue', 'autoSell', 'price', 'shopList', 'saveBtn', 'resetBtn',
    'modal', 'modalTitle', 'modalBody', 'modalActions', 'toast',
  ];
  const elements = new Map(ids.map(id => [id, new FakeElement(id)]));
  elements.get('modal').classList.add('hidden');
  elements.get('toast').classList.add('hidden');

  const body = new FakeElement('body');
  const document = {
    activeElement: body,
    body,
    getElementById: id => elements.get(id),
    createElement: tag => new FakeElement(tag),
    addEventListener() {},
  };
  const localStorage = {
    getItem: () => savedState === null ? null : JSON.stringify(savedState),
    setItem() {},
    removeItem() {},
  };
  const context = {
    document,
    localStorage,
    window: { addEventListener() {} },
    performance: { now: () => 0 },
    requestAnimationFrame() {},
    setInterval() {},
    setTimeout() { return 1; },
    clearTimeout() {},
    console,
  };

  vm.runInNewContext(gameSource, context, { filename: 'game.js' });
  return elements;
}

test('shows zero on a new farm and updates the all-time total after a tap', () => {
  const elements = startGame();
  assert.equal(elements.get('totalMilk').textContent, '0');

  elements.get('cow').listeners.click({ clientX: 120, clientY: 100 });
  assert.equal(elements.get('totalMilk').textContent, '1');
});

test('loads and formats lifetime milk from an existing save', () => {
  const elements = startGame({
    coins: 0,
    milk: 0,
    totalMilk: 999.9,
    autoSell: false,
    owned: { cow: 0, machine: 0, feed: 0, barn: 0 },
    lastSaved: Date.now(),
  });

  assert.equal(elements.get('totalMilk').textContent, '999.9');
  elements.get('cow').listeners.click({ clientX: 120, clientY: 100 });
  assert.equal(elements.get('totalMilk').textContent, '1K');
});
