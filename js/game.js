/* Cow Cash: a tiny idle clicker. Virtual coins only. MIT License. */
(function () {
  'use strict';

  const SAVE_KEY = 'cowCashSave.v1';
  const AUTOSAVE_MS = 10000;
  const OFFLINE_CAP_SEC = 2 * 60 * 60; // 2 hours
  const COST_SCALE = 1.15;
  const BASE_PRICE = 1;          // coins per milk
  const BASE_CAPACITY = 100;     // barn milk storage

  const ITEMS = [
    { id: 'cow',     icon: '🐄', name: 'Extra Cow',       baseCost: 15,
      desc: s => `+1 milk/sec each (you make ${fmt(cowMps(s))}/sec)` },
    { id: 'machine', icon: '⚙️', name: 'Milking Machine', baseCost: 50,
      desc: s => `Tap multiplier: x${tapMultiplier(s)} → x${tapMultiplier(s) + 1}` },
    { id: 'feed',    icon: '🌾', name: 'Better Feed',     baseCost: 120,
      desc: s => `+50% milk from everything (now x${feedMultiplier(s).toFixed(1)})` },
    { id: 'barn',    icon: '🏠', name: 'Bigger Barn',     baseCost: 250,
      desc: s => `Doubles storage (${fmt(capacity(s))} milk) and +10% sell price` },
  ];

  const defaultState = () => ({
    coins: 0, milk: 0, totalMilk: 0, autoSell: false,
    owned: { cow: 0, machine: 0, feed: 0, barn: 0 },
    lastSaved: Date.now(),
  });

  let state = defaultState();

  // ---------- Formulas ----------
  function feedMultiplier(s) { return 1 + 0.5 * s.owned.feed; }
  function tapMultiplier(s) { return 1 + s.owned.machine; }
  function perTap(s) { return tapMultiplier(s) * feedMultiplier(s); }
  function cowMps(s) { return s.owned.cow * feedMultiplier(s); }
  function capacity(s) { return BASE_CAPACITY * Math.pow(2, s.owned.barn); }
  function price(s) { return BASE_PRICE * (1 + 0.1 * s.owned.barn); }
  function cost(item, s) { return Math.ceil(item.baseCost * Math.pow(COST_SCALE, s.owned[item.id])); }

  // ---------- Formatting ----------
  const SUFFIXES = ['', 'K', 'M', 'B', 'T', 'Qa', 'Qi', 'Sx', 'Sp', 'Oc', 'No', 'Dc'];
  function fmt(n) {
    if (!isFinite(n)) return '∞';
    if (n < 1000) return (Math.round(n * 10) / 10).toLocaleString();
    const tier = Math.min(Math.floor(Math.log10(n) / 3), SUFFIXES.length - 1);
    return (n / Math.pow(1000, tier)).toFixed(2).replace(/\.?0+$/, '') + SUFFIXES[tier];
  }
  function fmtTime(sec) {
    const h = Math.floor(sec / 3600), m = Math.floor((sec % 3600) / 60), s = Math.floor(sec % 60);
    return [h ? h + 'h' : '', m ? m + 'm' : '', !h && s ? s + 's' : ''].filter(Boolean).join(' ') || '0s';
  }

  // ---------- DOM ----------
  const $ = id => document.getElementById(id);
  const el = {
    coins: $('coins'), milk: $('milk'), milkCapacity: $('milkCapacity'), mps: $('mps'), totalMilk: $('totalMilk'), perTap: $('perTap'),
    cow: $('cow'), sellBtn: $('sellBtn'), sellValue: $('sellValue'), autoSell: $('autoSell'),
    price: $('price'), shopList: $('shopList'), saveBtn: $('saveBtn'), resetBtn: $('resetBtn'),
    modal: $('modal'), modalTitle: $('modalTitle'), modalBody: $('modalBody'),
    modalActions: $('modalActions'), toast: $('toast'),
  };

  // ---------- Core actions ----------
  function addMilk(amount) {
    const cap = capacity(state);
    const room = Math.max(0, cap - state.milk);
    const added = Math.min(room, amount);
    state.milk += added;
    state.totalMilk += added;
    if (state.autoSell) sellAll();
    return added;
  }
  function sellAll() {
    if (state.milk <= 0) return 0;
    const earned = state.milk * price(state);
    state.coins += earned;
    state.milk = 0;
    return earned;
  }
  function buy(item) {
    const c = cost(item, state);
    if (state.coins < c) return;
    state.coins -= c;
    state.owned[item.id]++;
    renderShop();
    render();
  }

  // ---------- Tap ----------
  function tap(ev) {
    const gained = perTap(state);
    const added = addMilk(gained);
    let x, y;
    if (ev && ev.clientX) { x = ev.clientX; y = ev.clientY; }
    else { const r = el.cow.getBoundingClientRect(); x = r.left + r.width / 2; y = r.top + r.height / 3; }
    floatText(added > 0 ? `+${fmt(added)} 🥛` : 'Barn full!', x, y);
    el.cow.classList.add('pressed');
    setTimeout(() => el.cow.classList.remove('pressed'), 80);
    render();
  }
  function floatText(text, x, y) {
    const f = document.createElement('div');
    f.className = 'float';
    f.textContent = text;
    f.style.left = (x + (Math.random() * 40 - 20)) + 'px';
    f.style.top = (y - 20) + 'px';
    document.body.appendChild(f);
    setTimeout(() => f.remove(), 900);
  }

  // ---------- Rendering ----------
  function renderShop() {
    el.shopList.innerHTML = '';
    ITEMS.forEach(item => {
      const b = document.createElement('button');
      b.className = 'item';
      b.dataset.id = item.id;
      b.innerHTML = `
        <span class="icon">${item.icon}</span>
        <span class="info"><div class="name">${item.name}</div><div class="desc"></div></span>
        <span class="meta"><div class="cost"></div><div class="owned"></div></span>`;
      b.addEventListener('click', () => buy(item));
      el.shopList.appendChild(b);
    });
    render();
  }
  function render() {
    el.coins.textContent = fmt(state.coins);
    const storageCapacity = capacity(state);
    el.milk.textContent = `${fmt(state.milk)} / ${fmt(storageCapacity)}`;
    el.milkCapacity.max = storageCapacity;
    el.milkCapacity.value = Math.min(Math.max(state.milk, 0), storageCapacity);
    const barnFull = state.milk >= storageCapacity;
    const barnNearlyFull = !barnFull && state.milk >= storageCapacity * 0.8;
    el.milkCapacity.classList.toggle('is-near-full', barnNearlyFull);
    el.milkCapacity.classList.toggle('is-full', barnFull);
    const status = barnFull ? ', barn full' : barnNearlyFull ? ', barn nearly full' : '';
    el.milkCapacity.setAttribute('aria-valuetext', `${fmt(state.milk)} of ${fmt(storageCapacity)} milk${status}`);
    el.mps.textContent = fmt(cowMps(state));
    el.totalMilk.textContent = fmt(state.totalMilk);
    el.perTap.textContent = fmt(perTap(state));
    el.price.textContent = fmt(price(state));
    el.sellValue.textContent = fmt(state.milk * price(state));
    el.sellBtn.disabled = state.milk <= 0;
    el.autoSell.checked = state.autoSell;
    el.shopList.querySelectorAll('.item').forEach(b => {
      const item = ITEMS.find(i => i.id === b.dataset.id);
      const c = cost(item, state);
      b.querySelector('.desc').textContent = item.desc(state);
      b.querySelector('.cost').textContent = `${fmt(c)} 🪙`;
      b.querySelector('.owned').textContent = `Owned: ${state.owned[item.id]}`;
      b.disabled = state.coins < c;
    });
  }

  // ---------- Modal / toast ----------
  let modalOpener = null;
  function showModal(title, body, actions) {
    const activeElement = document.activeElement;
    modalOpener = activeElement && activeElement !== document.body ? activeElement : null;
    el.modalTitle.textContent = title;
    el.modalBody.textContent = body;
    el.modalActions.innerHTML = '';
    actions.forEach(a => {
      const b = document.createElement('button');
      b.className = 'btn ' + (a.cls || '');
      b.textContent = a.label;
      b.addEventListener('click', () => { hideModal(); a.onClick && a.onClick(); });
      el.modalActions.appendChild(b);
    });
    el.modal.classList.remove('hidden');
    const firstAction = el.modalActions.querySelector('button:not(:disabled)');
    if (firstAction) firstAction.focus();
  }
  function hideModal() {
    el.modal.classList.add('hidden');
    if (modalOpener && modalOpener.isConnected) modalOpener.focus();
    modalOpener = null;
  }
  let toastTimer;
  function toast(msg) {
    el.toast.textContent = msg;
    el.toast.classList.remove('hidden');
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => el.toast.classList.add('hidden'), 1600);
  }

  // ---------- Save / load ----------
  function save(showToast) {
    state.lastSaved = Date.now();
    try {
      localStorage.setItem(SAVE_KEY, JSON.stringify(state));
      if (showToast) toast('Game saved 💾');
    } catch (e) { if (showToast) toast('Could not save (storage unavailable)'); }
  }
  function load() {
    try {
      const raw = localStorage.getItem(SAVE_KEY);
      if (!raw) return false;
      const data = JSON.parse(raw);
      const d = defaultState();
      state = Object.assign(d, data, { owned: Object.assign(d.owned, data.owned || {}) });
      ['coins', 'milk', 'totalMilk'].forEach(k => { if (!isFinite(state[k]) || state[k] < 0) state[k] = 0; });
      return true;
    } catch (e) { return false; }
  }
  function applyOffline() {
    const now = Date.now();
    const elapsed = Math.max(0, (now - (state.lastSaved || now)) / 1000);
    const secs = Math.min(elapsed, OFFLINE_CAP_SEC);
    const mps = cowMps(state);
    if (secs < 30 || mps <= 0) return;
    // Offline milk is sold automatically so nothing is lost to barn capacity.
    const milk = mps * secs;
    const coins = milk * price(state);
    state.coins += coins;
    state.totalMilk += milk;
    const capped = elapsed > OFFLINE_CAP_SEC ? ' (capped at 2h)' : '';
    showModal('Welcome back! 🐄',
      `You were away for ${fmtTime(elapsed)}${capped}. Your cows made ${fmt(milk)} milk, sold for ${fmt(coins)} coins.`,
      [{ label: 'Collect', cls: 'primary' }]);
  }
  function resetGame() {
    showModal('Reset your farm?', 'This wipes all coins, milk and upgrades. This cannot be undone.', [
      { label: 'Cancel' },
      { label: 'Yes, reset', cls: 'danger', onClick: () => {
        state = defaultState();
        try { localStorage.removeItem(SAVE_KEY); } catch (e) {}
        renderShop();
        toast('Farm reset');
      } },
    ]);
  }

  // ---------- Loop ----------
  let last = performance.now();
  let renderAcc = 0;
  function loop(now) {
    const dt = Math.min(1, (now - last) / 1000);
    last = now;
    const mps = cowMps(state);
    if (mps > 0) addMilk(mps * dt);
    renderAcc += dt;
    if (renderAcc >= 0.1) { renderAcc = 0; render(); }
    requestAnimationFrame(loop);
  }

  // ---------- Wire up ----------
  el.cow.addEventListener('click', tap);
  el.sellBtn.addEventListener('click', () => {
    const earned = sellAll();
    if (earned > 0) {
      const r = el.sellBtn.getBoundingClientRect();
      floatText(`+${fmt(earned)} 🪙`, r.left + r.width / 2, r.top);
    }
    render();
  });
  el.autoSell.addEventListener('change', () => { state.autoSell = el.autoSell.checked; if (state.autoSell) sellAll(); render(); });
  el.saveBtn.addEventListener('click', () => save(true));
  el.resetBtn.addEventListener('click', resetGame);
  document.addEventListener('keydown', e => {
    if (el.modal.classList.contains('hidden')) return;
    if (e.key === 'Escape') {
      e.preventDefault();
      hideModal();
      return;
    }
    if (e.key !== 'Tab') return;
    const actions = Array.from(el.modalActions.querySelectorAll('button:not(:disabled)'));
    if (!actions.length) {
      e.preventDefault();
      return;
    }
    const first = actions[0];
    const last = actions[actions.length - 1];
    const focusIsOutside = !el.modal.contains(document.activeElement);
    if (e.shiftKey && (document.activeElement === first || focusIsOutside)) {
      e.preventDefault();
      last.focus();
    } else if (!e.shiftKey && (document.activeElement === last || focusIsOutside)) {
      e.preventDefault();
      first.focus();
    }
  });
  document.addEventListener('visibilitychange', () => { if (document.hidden) save(); });
  window.addEventListener('beforeunload', () => save());

  load();
  renderShop();
  applyOffline();
  render();
  setInterval(() => save(), AUTOSAVE_MS);
  requestAnimationFrame(loop);
})();
