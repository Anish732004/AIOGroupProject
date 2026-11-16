/* PharmaShield GCC showcase: navigation, controls and events. */
(function (PS) {
  'use strict';
  const ROUTES = [
    ['', 'Overview', 'overview'], ['suppliers', 'Suppliers', 'suppliers'], ['compare', 'Compare', 'compare'], ['split', 'Order split', 'split'],
    ['alerts', 'Alerts', 'alerts'], ['documents', 'Documents', 'documents'], ['models', 'Models', 'models'],
    ['trust', 'Evidence & trust', 'trust'], ['glossary', 'Glossary', 'glossary']
  ];
  const WITH_CONTROLS = { suppliers: 1, compare: 1, split: 1 };
  const view = document.getElementById('view'), controls = document.getElementById('controls');
  let lettersAll = false;

  function route() {
    const h = (location.hash || '#/').replace(/^#\/?/, '').split('?')[0];
    return ROUTES.find(function (r) { return r[0] === h; }) || ROUTES[0];
  }
  function renderNav() {
    const cur = route()[0], alerts = PS.activeShortages().length > 0;
    document.getElementById('nav').innerHTML = ROUTES.map(function (r, i) {
      return '<a href="#/' + r[0] + '"' + (r[0] === cur ? ' aria-current="page"' : '') + '><span class="n">' + (i + 1) + '</span>' + PS.esc(r[1]) +
        (r[0] === 'alerts' && alerts ? '<span class="alert-dot" title="Active shortage records"></span>' : '') + '</a>';
    }).join('');
  }
  function renderViewToggle() {
    const box = document.getElementById('view-toggle');
    if (!PS.hasSyn()) { box.innerHTML = ''; return; }
    box.innerHTML = '<span class="small muted" id="view-lab">Data shown</span><div class="seg" role="group" aria-labelledby="view-lab">' +
      [['real', 'Real data only'], ['synthetic', 'With synthetic data']].map(function (v) {
        return '<button type="button" data-view="' + v[0] + '" aria-pressed="' + (PS.state.view === v[0]) + '">' + v[1] + '</button>';
      }).join('') + '</div>';
  }
  function renderControls(force) {
    const need = WITH_CONTROLS[route()[2]];
    if (!need) { controls.innerHTML = ''; return; }
    if (force || !controls.firstChild) { controls.innerHTML = PS.views.controls(); return; }
    const s = PS.state;                                    // update in place so a slider keeps focus while dragged
    controls.querySelectorAll('[data-mode]').forEach(function (b) { b.setAttribute('aria-pressed', String(b.getAttribute('data-mode') === s.mode)); });
    document.getElementById('lam-val').textContent = s.lam.toFixed(2);
    document.getElementById('ent-val').textContent = Math.round(100 * s.ent) + '%';
    document.getElementById('mode-note').textContent = controls.querySelector('[data-mode][aria-pressed="true"]') ? MODE_NOTES[s.mode] : '';
  }
  const MODE_NOTES = {
    'Normal': 'Everyday priorities: compliance and on-time delivery count most.',
    'Crisis': 'A Hormuz or Gulf-airspace shock: weight moves from cost to route exposure, and every route\'s exposure is stressed by 1.5 times.',
    'Cost Focus': 'A calm-period budget focus: weight moves from route exposure to cost.'
  };
  function renderView() {
    const r = route();
    view.innerHTML = (PS.isSyn() ? PS.views.synBanner() : '') + (r[2] === 'documents' ? PS.views.documents(lettersAll) : PS.views[r[2]]());
    document.title = r[1] + ' · PharmaShield GCC';
    if (r[2] === 'split') refreshAudit();
  }
  /* links can carry a situation, e.g. #/split?mode=Crisis&dial=1.5&data=0.2 (handy for a presentation) */
  function applyLinkSettings() {
    const q = new URLSearchParams((location.hash.split('?')[1] || '')), m = PS.data.meta, s = PS.state;
    if (q.get('view') === 'synthetic' || q.get('view') === 'real') PS.setView(q.get('view'));
    const mode = q.get('mode'), dial = parseFloat(q.get('dial')), data = parseFloat(q.get('data'));
    if (mode && m.modes.indexOf(mode) >= 0) s.mode = mode;
    if (m.lambdas.indexOf(dial) >= 0) s.lam = dial;
    if (m.entropy_shares.indexOf(data) >= 0) s.ent = data;
    if (q.get('supplier') && PS.byId(q.get('supplier'))) s.supplier = q.get('supplier');
    if (q.get('a') && PS.byId(q.get('a'))) s.cmpA = q.get('a');
    if (q.get('outage') && (q.get('outage') === 'none' || PS.outage(q.get('outage')))) s.outage = q.get('outage');
    if (q.get('b') && PS.byId(q.get('b'))) s.cmpB = q.get('b');
  }
  function render(navigated) {
    if (navigated) applyLinkSettings();
    renderNav(); renderViewToggle(); renderControls(navigated); renderView();
    if (navigated) { window.scrollTo(0, 0); }
  }

  /* ---------- approval log ---------- */
  async function refreshAudit() {
    const box = document.getElementById('audit-box');
    if (!box) return;
    try {
      const rows = PSAudit.read(), check = await PSAudit.verify();
      box.innerHTML = PS.views.auditBox(rows, check);
    } catch (err) {
      box.innerHTML = '<h3>Approval log</h3><p class="sub">The log is unavailable in this browser (' + PS.esc(err.message) + ').</p>';
    }
  }
  async function submitApproval(form) {
    const who = form.querySelector('#ap-who').value.trim(), reason = form.querySelector('#ap-reason').value.trim();
    const decision = form.querySelector('input[name="ap-decision"]:checked').value, err = form.querySelector('#ap-err');
    const fail = function (m) { err.textContent = m; err.hidden = false; };
    if (!who) return fail('Enter your initials or staff ID.');
    if (decision !== 'Approve as recommended' && !reason) return fail('Give a reason when you change or reject the recommendation.');
    err.hidden = true;
    const d = PS.data, s = PS.state, sc = PS.stressed(), split = {}, weights = {};
    d.suppliers.forEach(function (sp, i) { if (sc.vials[i] > 0.5) split[sp.name] = sc.vials[i]; });
    PS.criteria().forEach(function (c, j) { weights[c.short] = sc.w[j]; });
    try {
      await PSAudit.append({ approver: who, decision: decision, reason: reason, data_view: s.view, mode: s.mode, risk_dial: s.lam, entropy_share: s.ent,
        demand_vials: d.meta.demand, split_vials: split,
        stress_test: s.outage && s.outage !== 'none' ? PS.outageLabel(PS.outage(s.outage)) + ' offline' : 'none', emergency_purchase_vials: sc.spot, weights: weights,
        snapshot_as_of: d.meta.as_of, score_table_sha256: d.meta.matrix_sha256 });
      form.reset();
      await refreshAudit();
    } catch (e2) { fail('Could not save the approval in this browser: ' + e2.message); }
  }
  function downloadAudit() {
    const a = document.createElement('a');
    a.href = URL.createObjectURL(new Blob([PSAudit.toJsonl()], { type: 'application/json' }));
    a.download = 'pharmashield_approval_log.jsonl';
    document.body.appendChild(a); a.click(); a.remove();
    setTimeout(function () { URL.revokeObjectURL(a.href); }, 1000);
  }

  /* ---------- live FDA check (public API, called from the browser; no personal data is sent) ---------- */
  async function liveCheck(btn) {
    const out = document.getElementById('live-result');
    btn.disabled = true; out.textContent = 'Asking the FDA…';
    try {
      const res = await fetch('https://api.fda.gov/drug/shortages.json?search=generic_name:carboplatin&limit=1000');
      if (res.status === 404) { out.textContent = 'The FDA lists no carboplatin shortage records right now.'; return; }
      if (!res.ok) throw new Error('the FDA service answered ' + res.status);
      const j = await res.json(), c = PS.countActive(j.results || []);
      out.textContent = 'Right now: ' + c.active + ' active record(s) from ' + c.companies + ' compan' + (c.companies === 1 ? 'y' : 'ies') +
        ' (FDA data last updated ' + ((j.meta && j.meta.last_updated) || 'n/a') + '). The snapshot of ' + PS.data.meta.as_of + ' had ' + PS.activeShortages().length + '.';
    } catch (err) {
      out.textContent = 'The live check did not work (' + err.message + '). The snapshot below is still valid.';
    } finally { btn.disabled = false; }
  }

  /* ---------- events ---------- */
  document.addEventListener('click', function (ev) {
    const t = ev.target;
    const dv = t.closest('[data-view]');
    if (dv) { PS.setView(dv.getAttribute('data-view')); renderViewToggle(); renderControls(true); renderView(); return; }
    const mode = t.closest('[data-mode]');
    if (mode) { PS.state.mode = mode.getAttribute('data-mode'); renderControls(false); renderView(); return; }
    const row = t.closest('tr[data-supplier]');
    if (row && !t.closest('a')) { selectSupplier(row.getAttribute('data-supplier')); return; }
    if (t.closest('#letters-toggle')) { lettersAll = !lettersAll; renderView(); return; }
    if (t.closest('#live-check')) { liveCheck(t.closest('#live-check')); return; }
    if (t.closest('#audit-download')) { downloadAudit(); return; }
    if (t.closest('#theme-toggle')) {
      const dark = (document.documentElement.getAttribute('data-theme') || (matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light')) === 'dark';
      const next = dark ? 'light' : 'dark';
      document.documentElement.setAttribute('data-theme', next);
      try { localStorage.setItem('pharmashield_theme', next); } catch (e) { /* private mode */ }
    }
  });
  function selectSupplier(id) {
    PS.state.supplier = id; renderView();
    const det = document.getElementById('detail');
    if (det) det.scrollIntoView({ behavior: 'smooth', block: 'start' });
  }
  document.addEventListener('keydown', function (ev) {
    const row = ev.target.closest && ev.target.closest('tr[data-supplier]');
    if (row && (ev.key === 'Enter' || ev.key === ' ')) { ev.preventDefault(); selectSupplier(row.getAttribute('data-supplier')); }
  });
  document.addEventListener('input', function (ev) {
    const t = ev.target;
    if (t.id === 'lam') { PS.state.lam = parseFloat(t.value); renderControls(false); renderView(); }
    else if (t.id === 'ent') { PS.state.ent = parseFloat(t.value); renderControls(false); renderView(); }
    else if (t.id === 'gloss-search') { document.getElementById('gloss-out').innerHTML = PS.views.glossaryList(t.value); }
    else if (t.id === 'contract-try') {
      const out = document.getElementById('contract-out');
      out.innerHTML = t.value.trim().length > 40 ? PS.views.contractResult(PSContract.read(t.value)) : '';
    }
  });
  document.addEventListener('change', function (ev) {
    const t = ev.target;
    if (t.id === 'outage') { PS.state.outage = t.value; renderView(); return; }
    if (t.id === 'cmp-a' || t.id === 'cmp-b') {
      PS.state[t.id === 'cmp-a' ? 'cmpA' : 'cmpB'] = t.value;
      if (PS.state.cmpA === PS.state.cmpB) {                  // never compare a supplier with itself: swap the other one
        const other = PS.data.supplier_ids.find(function (x) { return x !== t.value; });
        PS.state[t.id === 'cmp-a' ? 'cmpB' : 'cmpA'] = other;
      }
      renderView();
    }
  });
  document.addEventListener('submit', function (ev) {
    if (ev.target.id === 'approve-form') { ev.preventDefault(); submitApproval(ev.target); }
  });
  window.addEventListener('hashchange', function () { render(true); });

  PS.load().then(function () {
    const m = PS.data.meta;
    document.getElementById('snapshot-note').textContent = 'Data snapshot: ' + m.as_of;
    PS.initTips(); render(true);
  }).catch(function (err) {
    view.innerHTML = '<div class="pad"><h1>The data snapshot could not be loaded</h1><p class="muted" style="margin-top:8px">' + PS.esc(err.message) +
      '. Run <code>python tools/export_web_snapshot.py</code> and serve the <code>web</code> folder.</p></div>';
  });
})(window.PS);
