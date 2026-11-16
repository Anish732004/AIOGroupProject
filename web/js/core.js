/* PharmaShield GCC showcase: shared state and helpers. The site only LOOKS UP results that the Python pipeline
   computed (data/snapshot.json). It never recomputes a score, so its numbers match the pipeline exactly. */
window.PS = (function () {
  'use strict';
  const PS = { data: null, state: { mode: 'Normal', lam: 1, ent: 0, supplier: null, outage: 'none' } };

  PS.esc = function (v) {
    return String(v === null || v === undefined ? '' : v)
      .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;').replace(/'/g, '&#39;');
  };
  PS.num = function (v, d) {
    if (v === null || v === undefined || isNaN(v)) return '–';
    return Number(v).toLocaleString('en-US', { minimumFractionDigits: d || 0, maximumFractionDigits: d || 0 });
  };
  PS.pct = function (v, d) { return PS.num(v, d || 0) + '%'; };
  PS.words = function (s) { return String(s || '').replace(/_/g, ' '); };
  PS.cap = function (s) { s = PS.words(s); return s.charAt(0).toUpperCase() + s.slice(1); };

  /* ---- icons (status colours never appear without one of these plus a label) ---- */
  const ICONS = {
    alert: '<path d="M8 1.5l7 12.5H1z" fill="var(--crit)"/><path d="M8 6v4" stroke="#fff" stroke-width="1.6" stroke-linecap="round"/><circle cx="8" cy="12" r=".9" fill="#fff"/>',
    warn: '<circle cx="8" cy="8" r="7" fill="var(--warn)"/><path d="M8 4.2v4.6" stroke="#0b0b0b" stroke-width="1.6" stroke-linecap="round"/><circle cx="8" cy="11.4" r=".9" fill="#0b0b0b"/>',
    good: '<circle cx="8" cy="8" r="7" fill="var(--good)"/><path d="M4.8 8.2l2.2 2.2 4.2-4.6" stroke="#fff" stroke-width="1.6" fill="none" stroke-linecap="round" stroke-linejoin="round"/>',
    info: '<circle cx="8" cy="8" r="7" fill="var(--accent)"/><path d="M8 7.2v4" stroke="#fff" stroke-width="1.6" stroke-linecap="round"/><circle cx="8" cy="4.8" r=".9" fill="#fff"/>',
    nodata: '<circle cx="8" cy="8" r="6.2" fill="none" stroke="var(--muted)" stroke-width="1.6"/><path d="M5 8h6" stroke="var(--muted)" stroke-width="1.6" stroke-linecap="round"/>',
    'new': '<circle cx="8" cy="8" r="7" fill="var(--accent)"/><path d="M8 4.4v7.2M4.4 8h7.2" stroke="#fff" stroke-width="1.6" stroke-linecap="round"/>',
    gear: '<circle cx="8" cy="8" r="7" fill="var(--accent)"/><circle cx="8" cy="8" r="2.4" fill="#fff"/>'
  };
  PS.icon = function (name) {
    return '<svg class="ic" viewBox="0 0 16 16" aria-hidden="true">' + (ICONS[name] || ICONS.info) + '</svg>';
  };
  PS.badge = function (kind, label, icon, tip) {
    return '<span class="badge ' + kind + '"' + (tip ? ' data-tip="' + PS.esc(tip) + '" tabindex="0"' : '') + '>' +
      PS.icon(icon) + PS.esc(label) + '</span>';
  };
  PS.banner = function (kind, icon, html) {
    return '<div class="banner ' + kind + '" role="status">' + PS.icon(icon) + '<div>' + html + '</div></div>';
  };

  /* ---- marks ---- */
  /* a mark is "no data" when every supplier has the same value (e.g. billing: no supplier has its own invoices) */
  PS.noData = function (cid) {
    const v = PS.data.suppliers.map(function (s) { return s.marks[cid]; });
    return v.every(function (x) { return Math.abs(x - v[0]) < 1e-12; });
  };
  PS.NO_DATA_TIP = 'No data: the same value for every supplier, so it has no effect on the ranking.';
  PS.meter = function (v, max, opts) {
    opts = opts || {};
    const w = Math.max(0, Math.min(100, 100 * (v || 0) / (max || 1)));
    const label = opts.label !== undefined ? opts.label : PS.num(v, opts.d === undefined ? 2 : opts.d);
    return '<div class="meter' + (opts.context ? ' context' : '') + '"' +
      (opts.tip ? ' data-tip="' + PS.esc(opts.tip) + '" tabindex="0"' : '') + '>' +
      '<div class="track"><div class="fill" style="width:' + w.toFixed(1) + '%"></div></div>' +
      '<span class="v">' + PS.esc(label) + '</span></div>';
  };
  /* one horizontal bar on a shared scale; value printed at the tip */
  PS.barLine = function (v, max, label, opts) {
    opts = opts || {};
    const w = Math.max(0, Math.min(100, 100 * (v || 0) / (max || 1)));
    const cap = opts.cap !== undefined ? '<span class="cap" style="left:calc(' + (100 * opts.cap / max).toFixed(1) + '% - 1px)"></span>' : '';
    return '<div class="bar-line"' + (opts.tip ? ' data-tip="' + PS.esc(opts.tip) + '" tabindex="0"' : '') + '>' +
      '<div class="plot"><span class="b' + (opts.context ? ' context' : '') + '" style="width:' + w.toFixed(1) + '%"></span>' + cap + '</div>' +
      '<span class="val">' + PS.esc(label) + '</span></div>';
  };

  /* ---- scenario lookup ---- */
  PS.key = function (mode, lam, ent) {
    return mode + '|' + Number(lam).toFixed(2) + '|' + Number(ent).toFixed(1);
  };
  PS.scenario = function (mode, lam, ent) {
    const s = PS.state;
    return PS.data.scenarios[PS.key(mode || s.mode, lam === undefined ? s.lam : lam, ent === undefined ? s.ent : ent)];
  };
  /* stress test (natural disaster): same ranking, order split re-solved with some factories offline */
  PS.outage = function (key) { return (PS.data.stress.outages || []).find(function (o) { return o.key === key; }); };
  PS.stressed = function (key, mode, lam, ent) {
    const base = PS.scenario(mode, lam, ent), s = PS.state;
    key = key === undefined ? s.outage : key;
    if (!key || key === 'none') return base;
    const r = PS.data.stress.results[key][PS.key(mode || s.mode, lam === undefined ? s.lam : lam, ent === undefined ? s.ent : ent)];
    return Object.assign({}, base, { vials: r.vials, spot: r.spot, spend: r.spend, status: r.status, outage: key });
  };
  PS.outageLabel = function (o) {
    if (!o) return 'None';
    if (o.kind === 'country' || o.kind === 'country_worst') {
      const n = o.groups.length;
      return 'Every factory in ' + o.country + ' (' + n + ' of ' + PS.data.meta.factories + ')' + (o.kind === 'country_worst' ? ', plus factories in an unknown country' : '');
    }
    const f = PS.factories()[o.groups[0]];
    return f.label + (f.city ? ', ' + f.city : '') + (f.country && f.country !== 'Unknown' ? ' (' + f.country + ')' : ' (country not stated)');
  };
  PS.suppliers = function () { return PS.data.suppliers; };
  PS.byId = function (id) { return PS.data.suppliers.find(function (x) { return x.id === id; }); };
  PS.criteria = function () { return PS.data.content.criteria; };

  /* factories: several names on the box can be one factory */
  PS.factories = function () {
    const map = {};
    PS.data.suppliers.forEach(function (s) {
      const g = map[s.factory_group] || (map[s.factory_group] = { id: s.factory_group, names: [], country: s.country });
      g.names.push(s.name);
      g.known = !!s.factory_fei || (s.factory && s.factory.indexOf('(') !== 0);
      g.label = (s.factory && s.factory.indexOf('(') !== 0) ? s.factory : g.names[0] + '\'s factory (not named on the label)';
      g.city = s.factory_city || '';
    });
    return map;
  };
  PS.splitByFactory = function (sc) {
    const fac = PS.factories(), rows = {};
    PS.data.suppliers.forEach(function (s, i) {
      const v = sc.vials[i];
      if (v <= 0.5) return;
      const r = rows[s.factory_group] || (rows[s.factory_group] = {
        factory: fac[s.factory_group], vials: 0, cap: sc.cap_pct[i], ordered: [], bestS: 0 });
      r.vials += v; r.ordered.push(s.name); r.bestS = Math.max(r.bestS, sc.S[i]);
    });
    return Object.keys(rows).map(function (k) { return rows[k]; })
      .sort(function (a, b) { return b.vials - a.vials || b.bestS - a.bestS; });
  };
  PS.sameSplit = function (a, b) {
    return a.vials.every(function (v, i) { return Math.abs(v - b.vials[i]) < 0.5; });
  };
  PS.activeShortages = function () { return PS.data.alerts.sku.filter(function (r) { return r.is_active; }); };

  /* ---- live FDA check: latest row per company + package, then the same 'active' rule as the pipeline ---- */
  PS.countActive = function (results) {
    const latest = {};
    results.forEach(function (r) {
      const k = [String(r.company_name || '').trim().toLowerCase(), r.package_ndc || '', r.presentation || ''].join('|');
      const t = Date.parse(r.update_date) || 0;
      if (!latest[k] || t > latest[k].t) latest[k] = { t: t, r: r };
    });
    const rows = Object.keys(latest).map(function (k) { return latest[k].r; });
    const active = rows.filter(function (r) {
      const st = String(r.status || '').toLowerCase();
      return st !== 'resolved' && (st === 'current' || st === 'to be discontinued' || /unavailable|limited/i.test(r.availability || ''));
    });
    const companies = {};
    active.forEach(function (r) { companies[r.company_name] = 1; });
    return { records: rows.length, active: active.length, companies: Object.keys(companies).length };
  };

  /* ---- tooltip: enhances, never the only way to read a value (values are printed too) ---- */
  PS.initTips = function () {
    const tip = document.getElementById('tip');
    function show(el) {
      const t = el.getAttribute('data-tip');
      if (!t) return;
      tip.textContent = t; tip.hidden = false;
      const r = el.getBoundingClientRect(), tw = tip.offsetWidth, th = tip.offsetHeight;
      let x = r.left + r.width / 2 - tw / 2, y = r.top - th - 8;
      x = Math.max(8, Math.min(x, window.innerWidth - tw - 8));
      if (y < 8) y = r.bottom + 8;
      tip.style.left = x + 'px'; tip.style.top = y + 'px';
    }
    function hide() { tip.hidden = true; }
    document.addEventListener('mouseover', function (e) { const el = e.target.closest('[data-tip]'); if (el) show(el); else hide(); });
    document.addEventListener('focusin', function (e) { const el = e.target.closest('[data-tip]'); if (el) show(el); });
    document.addEventListener('focusout', hide);
    document.addEventListener('scroll', hide, true);
  };

  PS.load = function () {
    return fetch('data/snapshot.json', { cache: 'no-cache' }).then(function (r) {
      if (!r.ok) throw new Error('snapshot not found (' + r.status + ')');
      return r.json();
    }).then(function (d) { PS.data = d; return d; });
  };
  return PS;
})();
