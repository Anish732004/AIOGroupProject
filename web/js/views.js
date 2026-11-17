/* PharmaShield GCC showcase: page renderers. Each returns an HTML string built from data/snapshot.json. */
(function (PS) {
  'use strict';
  const e = PS.esc, V = {};
  const MODE_NOTE = {
    'Normal': 'Everyday priorities: compliance and on-time delivery count most.',
    'Crisis': 'A Hormuz or Gulf-airspace shock: weight moves from cost to route exposure, and every route\'s exposure is stressed by 1.5 times.',
    'Cost Focus': 'A calm-period budget focus: weight moves from route exposure to cost.'
  };
  const critShort = function (id) { return PS.criteria().find(function (c) { return c.id === id; }); };
  const place = function (f) { return [f.city, f.country === 'Unknown' ? '' : f.country].filter(Boolean).join(', '); };

  function head(eyebrow, title, text) {
    return '<header class="page-head"><span class="eyebrow">' + e(eyebrow) + '</span><h1>' + e(title) + '</h1><p>' + text + '</p></header>';
  }
  function tile(label, value, hint) {
    return '<div class="card tile"><span class="label">' + e(label) + '</span><span class="value">' + value + '</span>' +
      (hint ? '<span class="hint">' + hint + '</span>' : '') + '</div>';
  }
  function flagBadges(s, all) {
    const out = [];
    if (s.active_shortage) out.push(PS.badge('crit', 'In shortage', 'alert', 'The FDA lists an active carboplatin shortage record for this company.'));
    if (s.country_neutral) out.push(PS.badge('', 'Country: no data', 'nodata', 'The drug label does not say where it is made. Country-based marks use the middle value of the other suppliers.' + (PS.isSyn() ? ' The synthetic view does not invent this: it is a fact about one company, not an industry average.' : '')));
    if (s.factory_neutral) out.push(PS.badge('', 'Factory: no data', 'nodata', 'The factory is not named on the label, so inspection and warning-letter terms use the middle value of the other suppliers.' + (PS.isSyn() ? ' The synthetic view does not invent this: it is a fact about one company, not an industry average.' : '')));
    if (all && s.is_probation) out.push(PS.badge('', 'New supplier', 'new', 'Fewer than 5 past deliveries of its own on record. The plan gives a new supplier a capped trial share.'));
    if (synEstablished(s)) out.push(PS.badge('syn', 'Established (synthetic)', 'syn', s.syn.past_deliveries + ' past deliveries to this buyer, ' + PS.pct(100 * s.syn.on_time_rate) + ' on time: synthetic values (ranges R10, R11).'));
    return out.length ? '<span class="flags">' + out.join('') + '</span>' : '';
  }

  V.synBanner = function () {
    return '<div style="margin-bottom:18px">' + PS.banner('syn', 'syn', '<strong>Synthetic view.</strong> Inputs with no public evidence are filled with values invented within industry ranges, each marked ' +
      PS.synTag(null) + ': freight, delivery terms, past deliveries to this buyer, invoices, contracts, factory capacity and route share. FDA records, prices and country logistics scores stay real, and facts about a specific company are never invented, so "no data" stays where a drug label is silent (Fresenius\'s country, Avyxa\'s and Fresenius\'s factory). ' +
      '<a href="#/trust">See every value and its basis</a>. Choose <strong>Real data only</strong> in the side bar for the evidence-only result.') + '</div>';
  };
  function synEstablished(s) { return PS.isSyn() && s.syn && s.syn.established; }

  function rowFlags(s) { const f = flagBadges(s, false); return f ? '<div style="margin-top:6px">' + f + '</div>' : ''; }

  /* ---------- split by factory (meter list: one row per factory, share against its cap) ---------- */
  function splitList(sc, demand) {
    const rows = PS.splitByFactory(sc);
    if (!rows.length) return '<p class="muted">No supplier was selected.</p>';
    return '<div class="legend"><span><span class="sw"></span>Share of the monthly order</span>' +
      '<span><span class="sw capmark"></span>Most one factory may receive</span></div>' +
      '<div class="bars stacked">' + rows.map(function (r) {
        const share = 100 * r.vials / demand, f = r.factory;
        const others = f.names.filter(function (n) { return r.ordered.indexOf(n) < 0; });
        const sub = [place(f), 'ordered as ' + r.ordered.join(', ')].filter(Boolean).join(' · ') +
          (others.length ? ' (same factory also sells as ' + others.join(', ') + ')' : '');
        return '<div class="bar-row"><div class="name"><strong>' + e(f.label) + '</strong><span class="cellsub">' + e(sub) + '</span></div>' +
          PS.barLine(share, 100, PS.pct(share) + ' · ' + PS.num(r.vials) + ' vials',
            { cap: r.cap, tip: f.label + ': ' + PS.pct(share) + ' of the order (' + PS.num(r.vials) + ' vials). Cap for this factory: ' + PS.pct(r.cap) + '.' }) + '</div>';
      }).join('') + '</div>';
  }
  function splitStats(sc) {
    const rows = PS.splitByFactory(sc), demand = PS.data.meta.demand;
    const countries = {};
    rows.forEach(function (r) { if (r.factory.country && r.factory.country !== 'Unknown') countries[r.factory.country] = 1; });
    return { unknownCountry: rows.some(function (r) { return r.factory.country === 'Unknown'; }), factories: rows.length, countries: Object.keys(countries).length,
      largest: rows.length ? 100 * rows[0].vials / demand : 0, spot: sc.spot, backup: sc.backup, two_ok: sc.two_ok };
  }

  /* =============================================================== OVERVIEW */
  V.overview = function () {
    const d = PS.data, c = d.content, sc = PS.scenario('Normal', 1, 0), st = splitStats(sc);
    const act = PS.activeShortages(), comp = {};
    act.forEach(function (r) { comp[r.company_name] = 1; });
    const counts = {};
    PS.ledger().forEach(function (r) { counts[r.level] = (counts[r.level] || 0) + 1; });
    const x = d.models.c2.xgboost_test;
    return '<div class="hero">' +
      '<div class="hero-text"><span class="eyebrow">' + e(c.project.product) + ' · ' + e(c.project.product_note) + '</span>' +
      '<h1>' + e(c.project.tagline) + '</h1>' +
      '<p>PharmaShield checks every approved supplier of a critical medicine on five risks, ranks them, and recommends how to split the monthly order across independent factories. A person approves every order.</p>' +
      '<div class="row"><a class="btn primary" href="#/split">See the recommended order</a><a class="btn" href="#/suppliers">Compare the suppliers</a></div></div>' +
      '<div class="card"><h3>Recommended order this month</h3><p class="sub">' + PS.num(d.meta.demand) + ' vials · everyday (Normal) priorities' + (PS.isSyn() ? PS.synTag(null, 'synthetic view') : '') + '</p>' +
      '<div class="hero-figure">' + st.factories + ' factories</div>' +
      '<p class="ink2" style="margin:4px 0 16px">in ' + st.countries + ' countries' + (st.unknownCountry ? ' (plus one not stated)' : '') + ' share the order. No factory carries more than ' + PS.pct(st.largest) + ', so ' + PS.pct(st.backup) + ' is a warm backup.</p>' +
      splitList(sc, d.meta.demand) + '</div></div>' +

      (act.length ? '<div class="section">' + PS.banner('crit', 'alert', '<strong>Shortage alert.</strong> The FDA lists ' + act.length +
        ' active carboplatin shortage records from ' + Object.keys(comp).length + ' companies (snapshot of ' + e(d.meta.as_of) +
        '). <a href="#/alerts">See the alerts</a>') + '</div>' : '') +

      '<section class="section"><h2>Key findings</h2><p class="sub">What the data says, in plain words. Each finding is worked out from the numbers shown elsewhere on this site.</p>' +
      '<ol class="findings">' + V.findings().map(function (f) {
        return '<li class="card finding"><h3>' + e(f.title) + '</h3><p>' + e(f.text) + '</p><a class="small" href="' + f.link + '">' + e(f.cta) + ' →</a></li>';
      }).join('') + '</ol></section>' +

      '<div class="section grid g4">' +
      tile('Suppliers checked', d.meta.labelers_total, d.meta.rankable + ' sell finished vials and are ranked') +
      tile('Independent factories', d.meta.factories, 'behind those ' + d.meta.rankable + ' names on the box') +
      tile('Late shipments caught', PS.pct(100 * x.recall_late), 'by the delivery model, on shipments it had never seen') +
      tile('Data checks run', d.quality.checks, d.quality.errors + ' errors · ' + d.quality.quarantined_rows + ' bad rows set aside') + '</div>' +

      '<section class="section"><h2>Why this matters</h2><p class="sub">' + e(c.why_it_matters.note) + '</p><div class="grid g4">' +
      c.why_it_matters.stats.map(function (s) { return tile(s.label, e(s.value), 'Source: ' + e(s.source)); }).join('') + '</div></section>' +

      '<section class="section"><h2>How it works</h2><p class="sub">Five steps, from public data to a signed-off order.</p><div class="steps">' +
      c.how_it_works.map(function (s) {
        return '<div class="card step"><div class="k">' + e(s.step) + '</div><h3>' + e(s.title) + '</h3><p>' + e(s.text) + '</p></div>';
      }).join('') + '</div></section>' +

      '<section class="section"><h2>The five marks</h2><p class="sub">Every supplier gets five marks, each from 0 (best) to 1 (worst).</p><div class="grid g5">' +
      c.criteria.map(function (k) {
        return '<div class="card crit-card"><span class="code">' + e(k.code) + '</span><h3>' + e(k.short) + '</h3><p>' + e(k.plain) + '</p><p class="how">' + e(PS.isSyn() && k.method_synthetic ? k.method_synthetic : k.method) + '</p></div>';
      }).join('') + '</div></section>' +

      '<section class="section"><h2>Why you can trust the numbers</h2><p class="sub">' + (PS.isSyn()
        ? 'Synthetic view: inputs with no public evidence are filled from approved industry ranges and marked synthetic; every other input is the same as in the real view.'
        : 'One rule: every input is backed by a cited source, or it is openly marked "no data" and given the same neutral value for every supplier.') + '</p>' +
      '<div class="grid g4">' + PS.levels().filter(function (k) { return !PS.isSyn() || counts[k]; }).map(function (k) {
        const lv = c.evidence_levels[k];
        return tile(lv.label, counts[k] || 0, e(lv.plain));
      }).join('') + '</div>' + (PS.hasSyn() && !PS.isSyn() ? '<p class="ink2" style="margin-top:12px">A synthetic view, which fills the "no data" inputs with values invented within industry ranges, can be switched on in the side bar.</p>' : '') +
      '<p style="margin-top:14px"><a class="btn" href="#/trust">See the evidence behind every input</a></p></section>';
  };

  /* =============================================================== KEY FINDINGS (computed, never typed in) */
  V.findings = function () {
    const d = PS.data, sc = PS.scenario('Normal', 1, 0), cr = PS.scenario('Crisis', 1, 0), crit = PS.criteria();
    const vals = d.modes.Normal.values, out = [];
    const money = function (v) { return '$' + PS.num(v, v < 100 ? 2 : 0); };

    // 1. where the order goes
    const rows = PS.splitByFactory(sc), countries = {};
    rows.forEach(function (r) { if (r.factory.country !== 'Unknown') countries[r.factory.country] = 1; });
    const unknownC = rows.some(function (r) { return r.factory.country === 'Unknown'; });
    out.push({ title: 'The order is spread over ' + rows.length + ' independent factories in ' + Object.keys(countries).length + ' countries' + (unknownC ? ', plus one whose country is not stated' : ''),
      text: rows.map(function (r) { return r.factory.label + ' (' + (r.factory.country === 'Unknown' ? 'country not stated' : r.factory.country) + ') ' + PS.pct(100 * r.vials / d.meta.demand); }).join(', ') +
        '. The largest share is ' + PS.pct(100 * rows[0].vials / d.meta.demand) +
        (d.modes.Normal.established_factories === 0 ? ': with no supplier holding a delivery record of its own, the plan caps every factory at ' + PS.pct(100 * d.modes.Normal.probation_cap) + '.' : '.'),
      link: '#/split', cta: 'See the order split' });

    // 2. brand names vs factories
    const fac = PS.factories(), shared = Object.keys(fac).map(function (k) { return fac[k]; }).filter(function (g) { return g.names.length > 1; });
    if (shared.length) out.push({ title: d.meta.rankable + ' brand names, but only ' + d.meta.factories + ' factories',
      text: shared.map(function (g) { return g.label + ' makes the product sold as ' + g.names.join(', '); }).join('. ') +
        '. Splitting an order between two names from the same factory is not real dual sourcing, so the split limits each factory, not each name.',
      link: '#/compare', cta: 'Compare two suppliers' });

    // 3. the weakest supplier, and why
    let last = 0;
    sc.rank.forEach(function (r, i) { if (r > sc.rank[last]) last = i; });
    const w = d.suppliers[last], g = sc.gap[last], j = g.indexOf(Math.max.apply(null, g)), why = [];
    if (crit[j].id === 'C4_compliance_risk') {
      if (!w.factory_neutral && w.oai) why.push(w.oai + ' serious FDA inspection finding' + (w.oai > 1 ? 's' : '') + ' at its factory');
      if (w.recalls) why.push(w.recalls + ' serious injectable recall' + (w.recalls > 1 ? 's' : '') + ' in 5 years');
      if (w.worst_letter) why.push('an FDA warning letter (' + String(w.worst_letter).match(/\d{4}/)[0] + ')');
    } else { why.push('its ' + crit[j].short.toLowerCase() + ' mark of ' + vals[last][j].toFixed(2)); }
    out.push({ title: w.name + ' ranks last of ' + d.suppliers.length,
      text: PS.pct(100 * g[j]) + ' of its distance from the ideal supplier comes from ' + crit[j].short.toLowerCase() + ': ' + why.join(', ') + '.',
      link: '#/suppliers?supplier=' + encodeURIComponent(w.id), cta: 'See why' });

    // 4. price outlier
    const prices = d.suppliers.map(function (s) { return s.price_usd; }).slice().sort(function (a, b) { return a - b; });
    const med = prices[Math.floor(prices.length / 2)];
    const dear = d.suppliers.filter(function (s) { return s.price_usd > 2 * med; });
    const same = d.suppliers.filter(function (s) { return Math.abs(s.price_usd - med) < 0.01; }).length;
    dear.forEach(function (s) {
      const k = d.supplier_ids.indexOf(s.id), keys = Object.keys(d.scenarios);
      const ordered = keys.filter(function (key) { return d.scenarios[key].vials[k] > 0.5; }).length;
      const worstOn = crit.filter(function (c, j) { return vals[k][j] > 0 && vals[k][j] >= Math.max.apply(null, vals.map(function (v) { return v[j]; })); })
        .map(function (c) { return c.short.toLowerCase(); });
      out.push({ title: s.name + ' costs about ' + Math.round(s.price_usd / med) + ' times more',
        text: money(s.price_usd) + ' per vial against ' + money(med) + (PS.isSyn() ? ' (median of the generic suppliers: one official US price plus synthetic freight). ' : ' for the ' + same + ' generic suppliers, which all share one official US price. ') +
          (worstOn.length ? 'It has the worst mark of all suppliers on ' + worstOn.join(' and ') + '. ' : '') +
          (ordered ? 'It receives an order in ' + ordered + ' of the ' + keys.length + ' situations a reader can set.' :
            'It receives no order in any of the ' + keys.length + ' situations a reader can set.'),
        link: '#/suppliers?supplier=' + encodeURIComponent(s.id), cta: 'See the supplier' });
    });

    // 5. crisis
    const moved = cr.rank.filter(function (r, i) { return r !== sc.rank[i]; }).length;
    const topC = d.suppliers[cr.rank.indexOf(1)];
    out.push({ title: 'A Hormuz crisis changes the ranking' + (PS.sameSplit(cr, sc) ? ', not the order' : ' and the order'),
      text: moved + ' of ' + d.suppliers.length + ' suppliers change rank and ' + topC.name + (sc.rank[cr.rank.indexOf(1)] === 1 ? ' stays first' : ' moves to first') + ', because route exposure gains weight and cost loses it. ' +
        (PS.sameSplit(cr, sc) ? 'The recommended order stays the same, because it also weighs price and the share limits.' : 'The recommended order changes too.'),
      link: '#/split?mode=Crisis', cta: 'Try Crisis mode' });

    // 5b. natural disaster in the country with most factories
    const ctry = d.stress.outages.find(function (o) { return o.kind === 'country'; });
    const singleOk = d.stress.outages.filter(function (o) { return o.kind === 'factory'; }).every(function (o) { return PS.stressed(o.key, 'Normal', 1, 0).spot < 0.5; });
    if (ctry) {
      const hit = PS.stressed(ctry.key, 'Normal', 1, 0), worst = d.stress.outages.find(function (o) { return o.kind === 'country_worst' && o.country === ctry.country; });
      const wr = worst ? PS.stressed(worst.key, 'Normal', 1, 0) : null, money = function (v) { return '$' + PS.num(v); };
      out.push({ title: 'A disaster shutting every factory in ' + ctry.country + ' would ' + (hit.spot > 0.5 ? 'leave a supply gap' : hit.spend > sc.spend * 1.05 ? 'not stop supply, but cost far more' : 'be absorbed by the other factories'),
        text: ctry.groups.length + ' of the ' + d.meta.factories + ' factories are in ' + ctry.country + '. Without them ' +
          (hit.spot > 0.5 ? PS.num(hit.spot) + ' vials need an emergency purchase and ' : 'the order is still covered, but ') +
          'the monthly cost ' + (hit.spend > sc.spend * 1.05 ? 'rises from ' + money(sc.spend) + ' to ' + money(hit.spend) : 'barely changes (' + money(sc.spend) + ' to ' + money(hit.spend) + ')') + ', ' + PS.priceBasis() + '.' +
          (wr ? ' If the supplier whose factory country is unknown is also there, ' + (wr.spot > 0.5 ? PS.num(wr.spot) + ' vials need an emergency purchase.' : 'the order is still covered.') : '') +
          (singleOk ? ' Losing any single factory, by contrast, is fully absorbed.' : ''),
        link: '#/split?outage=' + encodeURIComponent(ctry.key), cta: 'Run the stress test' });
    }

    // 6. shortages hit the recommended suppliers too
    const ordered = d.suppliers.filter(function (s, i) { return sc.vials[i] > 0.5; });
    const short = d.suppliers.filter(function (s) { return s.active_shortage; }).length;
    const shortOrdered = ordered.filter(function (s) { return s.active_shortage; });
    out.push({ title: short + ' of ' + d.suppliers.length + ' suppliers have an active FDA shortage record',
      text: 'That includes ' + shortOrdered.length + ' of the ' + ordered.length + ' names in the recommended order (' + shortOrdered.map(function (s) { return s.name; }).join(', ') +
        '). Shortages do not change a score here; they tell the buyer to confirm supply before ordering.', link: '#/alerts', cta: 'See the alerts' });

    // 7. what the evidence can and cannot say
    if (PS.isSyn()) {
      const est = d.suppliers.filter(function (x) { return !x.is_probation; }), lr = PS.raw.synthetic.incoterm_late_rates || {};
      out.push({ title: 'In the synthetic view, invented inputs decide part of the result',
        text: est.length + ' suppliers get a synthetic delivery record (' + est.map(function (x) { return x.name; }).join(', ') + '), so the plan lets an established factory take up to ' +
          PS.pct(100 * d.modes.Normal.tier_cap) + ' and caps new ones at ' + PS.pct(100 * d.modes.Normal.probation_cap) + '. The drawn delivery term moves late-delivery risk most: in the real USAID data, ' +
          Object.keys(lr).map(function (k) { return k + ' shipments were late ' + PS.pct(100 * lr[k]) + ' of the time'; }).join(', ') + '. Compare with Real data only before relying on any synthetic result.',
        link: '#/trust', cta: 'See the synthetic values' });
      return out;
    }
    const tied = sc.S.filter(function (s) { return Math.abs(s - sc.S[sc.rank.indexOf(1)]) < 1e-6; }).length;
    out.push({ title: 'Many suppliers score alike, by design',
      text: 'Cost is 0 for ' + vals.filter(function (v) { return v[0] === 0; }).length + ' suppliers and billing has no data, so it is the same (0) for all ' + vals.length +
        ', because numbers without evidence were set to the same neutral value rather than invented. The ranking therefore rests on the FDA record, the delivery model and each country\'s logistics score.',
      link: '#/trust', cta: 'See the evidence' });
    return out;
  };

  /* =============================================================== COMPARE */
  V.compare = function () {
    const d = PS.data, s = PS.state, sc = PS.scenario(), vals = d.modes[s.mode].values, crit = PS.criteria();
    const order = d.suppliers.map(function (_, i) { return i; }).sort(function (a, b) { return sc.rank[a] - sc.rank[b] || a - b; });
    if (!s.cmpA || !PS.byId(s.cmpA)) s.cmpA = d.suppliers[order[0]].id;
    if (!s.cmpB || !PS.byId(s.cmpB) || s.cmpB === s.cmpA) s.cmpB = d.suppliers[order[order.length - 1]].id;
    const ia = d.supplier_ids.indexOf(s.cmpA), ib = d.supplier_ids.indexOf(s.cmpB), A = d.suppliers[ia], B = d.suppliers[ib];
    const pick = function (id, sel) {
      return '<select id="' + id + '" class="sel">' + order.map(function (i) {
        const x = d.suppliers[i];
        return '<option value="' + e(x.id) + '"' + (x.id === sel ? ' selected' : '') + '>#' + sc.rank[i] + ' ' + e(x.name) + '</option>';
      }).join('') + '</select>';
    };
    const better = function (a, b, lowerIsBetter) {             // the ✓ text marks the better side (not colour alone)
      if (a === b || a === null || b === null) return ['', ''];
      const aWins = lowerIsBetter ? a < b : a > b;
      return aWins ? [' <span class="win">✓ better</span>', ''] : ['', ' <span class="win">✓ better</span>'];
    };
    const row = function (label, hint, a, b, fmt, lower) {
      const w = (lower === undefined) ? ['', ''] : better(a, b, lower);
      return '<tr><th scope="row">' + e(label) + (hint ? '<span class="hint">' + e(hint) + '</span>' : '') + '</th><td>' + fmt(a, A) + w[0] + '</td><td>' + fmt(b, B) + w[1] + '</td></tr>';
    };
    const txt = function (v) { return e(v); };
    const n = function (v) { return v === null || v === undefined ? '–' : PS.num(v); };
    const markRows = crit.map(function (c, j) {
      if (PS.noData(c.id)) return row(c.short, 'no data for any supplier', 0, 0, function () { return PS.meter(0, 1, { label: 'no data', tip: c.short + ': ' + PS.NO_DATA_TIP }); });
      return row(c.short, '0 best · 1 worst', vals[ia][j], vals[ib][j], function (v) { return PS.meter(v, 1, { tip: c.short + ': ' + v.toFixed(3) }); }, true);
    }).join('');
    const sameFactory = A.factory_group === B.factory_group;
    return head('Compare', 'Two suppliers, side by side',
      'Pick any two suppliers. The situation and data setting above apply. "✓ better" marks the stronger side of each row.') +
      '<div class="grid g2"><label class="f">Supplier A' + pick('cmp-a', s.cmpA) + '</label><label class="f">Supplier B' + pick('cmp-b', s.cmpB) + '</label></div>' +
      (sameFactory ? '<div class="section">' + PS.banner('info', 'info', '<strong>Same factory.</strong> Both are made by ' + e(A.factory) + '. Ordering from both is not dual sourcing.') + '</div>' : '') +
      '<div class="section table-wrap"><table class="cmp"><thead><tr><th></th><th>' + e(A.name) + '</th><th>' + e(B.name) + '</th></tr></thead><tbody>' +
      row('Rank', 'in this situation', sc.rank[ia], sc.rank[ib], function (v) { return '<strong>' + v + '</strong> of ' + d.suppliers.length; }, true) +
      row('Overall score', 'higher is better', sc.S[ia], sc.S[ib], function (v) { return PS.meter(v, 1, { d: 3 }); }, false) +
      '<tr class="group"><th colspan="3">The five marks</th></tr>' + markRows +
      '<tr class="group"><th colspan="3">Behind the marks</th></tr>' +
      row('Factory', '', A.factory, B.factory, function (v, x) { return txt(v && v.indexOf('(') !== 0 ? v + (x.factory_city ? ', ' + x.factory_city : '') : 'Not named on the label'); }) +
      row('Made in', '', A.country, B.country, function (v) { return txt(v === 'Unknown' ? 'Not stated' : v); }) +
      row('Price per vial', PS.isSyn() ? 'official US price + synthetic freight' : 'official US price', A.price_usd, B.price_usd, function (v) { return '$' + PS.num(v, 2); }, true) +
      row('Country logistics score', 'World Bank LPI, 1 to 5, higher is better', A.lpi, B.lpi, function (v) { return PS.num(v, 1); }, false) +
      row('Serious inspection findings', 'at its factory, 5 years', A.factory_neutral ? null : A.oai, B.factory_neutral ? null : B.oai, function (v) { return v === null ? 'No data' : n(v); }, true) +
      row('Minor inspection findings', 'at its factory, 5 years', A.factory_neutral ? null : A.vai, B.factory_neutral ? null : B.vai, function (v) { return v === null ? 'No data' : n(v); }, true) +
      row('Serious injectable recalls', 'by this seller, 5 years', A.recalls, B.recalls, n, true) +
      row('Warning letter to its factory', 'in our 50-letter sample', A.worst_letter, B.worst_letter, function (v) { return txt(v ? PS.words(v) : 'None found'); }) +
      row('Own delivery history', 'past shipments on record', A.own_shipments, B.own_shipments, n) +
      (PS.isSyn() ? row('Past deliveries to this buyer', 'synthetic', A.syn.past_deliveries, B.syn.past_deliveries, function (v) { return n(v) + PS.synTag('R10'); }) +
        row('Monthly vials its factory can give us', 'synthetic', A.syn.factory_capacity_vials, B.syn.factory_capacity_vials, function (v) { return n(v) + PS.synTag('R8'); }) : '') +
      row('Active FDA shortage', '', A.active_shortage, B.active_shortage, function (v) { return v ? PS.badge('crit', 'Yes', 'alert') : 'No'; }) +
      row('Share of 2025 US Medicaid volume', PS.isSyn() ? 'real data; picks the established suppliers and scales capacity in the synthetic view' : 'information only, not scored', A.medicaid_share_pct, B.medicaid_share_pct, function (v) { return v === null || v === undefined ? 'Not in the data' : PS.num(v, 1) + '%'; }) +
      '</tbody></table></div>' +
      '<p class="section"><a class="btn" href="#/suppliers?supplier=' + encodeURIComponent(A.id) + '">Details for ' + e(A.name) + '</a> <a class="btn" href="#/suppliers?supplier=' + encodeURIComponent(B.id) + '">Details for ' + e(B.name) + '</a></p>';
  };

  /* =============================================================== CONTROLS (suppliers + split pages) */
  V.controls = function (page) {
    const s = PS.state, m = PS.data.meta;
    return '<div class="controls"><div class="controls-row">' +
      '<div class="ctl"><span class="lab">Situation</span><div class="seg" role="group" aria-label="Situation">' +
      m.modes.map(function (md) {
        return '<button type="button" data-mode="' + e(md) + '" aria-pressed="' + (s.mode === md) + '">' + e(md) + '</button>';
      }).join('') + '</div></div>' +
      '<details class="adv ctl"' + (s.ent > 0 ? ' open' : '') + '><summary>Advanced</summary>' +
      '<label class="lab" for="ent">Let the data adjust the weights: <span id="ent-val">' + Math.round(100 * s.ent) + '%</span></label>' +
      '<input id="ent" type="range" min="0" max="0.5" step="0.1" value="' + s.ent + '">' +
      '<div class="range-ends"><span>Board only</span><span>Half data</span></div></details>' +
      '</div><p class="mode-note" id="mode-note">' + e(MODE_NOTE[s.mode]) + '</p></div>';
  };

  /* =============================================================== SUPPLIERS */
  V.suppliers = function () {
    const d = PS.data, s = PS.state, sc = PS.scenario(), base = PS.scenario('Normal'), vals = d.modes[s.mode].values;
    const order = d.suppliers.map(function (_, i) { return i; }).sort(function (a, b) { return sc.rank[a] - sc.rank[b] || sc.S[b] - sc.S[a] || a - b; });
    if (!s.supplier || !PS.byId(s.supplier)) s.supplier = d.suppliers[order[0]].id;
    const crit = PS.criteria();
    const rows = order.map(function (i) {
      const sp = d.suppliers[i], dr = base.rank[i] - sc.rank[i];
      const delta = s.mode === 'Normal' ? '' : '<span class="delta">' + (dr > 0 ? '▲ up ' + dr : dr < 0 ? '▼ down ' + (-dr) : 'no change') + ' vs Normal</span>';
      return '<tr class="click' + (sp.id === s.supplier ? ' sel' : '') + '" data-supplier="' + e(sp.id) + '" tabindex="0" aria-label="Show details for ' + e(sp.name) + '">' +
        '<td class="num"><strong>' + sc.rank[i] + '</strong></td>' +
        '<td class="col-supplier"><strong>' + e(sp.name) + '</strong><span class="cellsub">' + e((sp.factory && sp.factory.indexOf('(') !== 0 ? 'Made by ' + sp.factory : 'Factory not named on the label') +
          ' · ' + (sp.country === 'Unknown' ? 'country not stated' : sp.country)) + '</span>' + delta + rowFlags(sp) + '</td>' +
        '<td>' + PS.meter(sc.S[i], 1, { d: 3, tip: sp.name + ': overall score ' + sc.S[i].toFixed(3) + ' (1 = the ideal supplier).' }) + '</td>' +
        crit.map(function (c, j) { return '<td>' + (PS.noData(c.id) ? PS.meter(0, 1, { label: 'no data', tip: c.short + ': ' + PS.NO_DATA_TIP }) : PS.meter(vals[i][j], 1, { tip: sp.name + ' · ' + c.short + ': ' + vals[i][j].toFixed(3) + ' (0 best, 1 worst).' + (PS.isSyn() && c.id === 'C3_price_integrity' && sp.is_probation ? ' New supplier: no invoices with this buyer yet, so the plan gives 0.' : '') })) + '</td>'; }).join('') +
        '</tr>';
    }).join('');
    return head('Suppliers', 'Who can supply it, and how each one scores',
      d.meta.rankable + ' companies sell finished carboplatin vials. They are ranked for the situation chosen above. Select a row to see why a supplier scored as it did.') +
      (function () {
        const est = d.suppliers.filter(function (x) { return !x.is_probation; });
        if (!est.length) return PS.banner('info', 'new', 'All ' + d.meta.rankable + ' are <strong>new suppliers</strong>: none has 5 or more past deliveries of its own on record. There is no billing data for any of them, so their billing mark is the same (0) for all, the plan\'s rule for new suppliers. It therefore has no effect on the ranking.');
        return PS.banner('syn', 'syn', '<strong>' + est.length + ' established suppliers</strong> (' + est.map(function (x) { return e(x.name); }).join(', ') + ') have a synthetic delivery record with this buyer ' + PS.synTag('R10') +
          '. Their billing mark comes from the billing model run on their synthetic invoices; the other ' + (d.suppliers.length - est.length) + ' are new suppliers and keep the plan\'s billing mark of 0.');
      })() +
      '<div class="section table-wrap"><table><thead><tr><th>#</th><th>Supplier</th>' +
      '<th data-tip="How close the supplier is to an ideal one that is best on every mark. Higher is better." tabindex="0">Overall score<span class="hint">higher is better</span></th>' +
      crit.map(function (c) { return '<th data-tip="' + e(c.plain) + '" tabindex="0">' + e(c.short) + '<span class="hint">0 best · 1 worst</span></th>'; }).join('') +
      '</tr></thead><tbody>' + rows + '</tbody></table></div>' +
      '<div id="detail" class="section">' + supplierDetail(PS.byId(s.supplier), sc, vals) + '</div>' +
      '<section class="section"><h2>Not ranked</h2><p class="sub">' + d.excluded.length + ' more companies are registered for carboplatin but sell only the raw ingredient, so they cannot supply hospital vials.</p>' +
      '<p class="ink2">' + d.excluded.map(function (x) { return e(x.name); }).join(' · ') + '</p></section>';
  };

  function supplierDetail(sp, sc, vals) {
    const d = PS.data, i = d.supplier_ids.indexOf(sp.id), crit = PS.criteria();
    const maxAbs = Math.max.apply(null, sp.reasons.map(function (r) { return Math.abs(r.shap_log_odds); }).concat([0.0001]));
    const hasShap = sp.reasons.some(function (r) { return Math.abs(r.shap_log_odds) > 0; });
    const reasons = hasShap ? '<div class="legend"><span><span class="sw"></span>Lowers the risk</span><span><span class="sw neg"></span>Raises the risk</span></div>' +
      '<div class="stack" style="gap:12px">' + sp.reasons.map(function (r) {
        const w = (50 * Math.abs(r.shap_log_odds) / maxAbs).toFixed(1), up = r.shap_log_odds > 0;
        return '<div class="div-row"><div><strong>' + e(r.feature) + '</strong><span class="cellsub">' + e(r.value) + '</span></div>' +
          '<div class="div-plot" tabindex="0" data-tip="' + e(r.feature + ' ' + r.effect + ' (strength ' + Math.abs(r.shap_log_odds).toFixed(2) + ').') + '">' +
          '<span class="b ' + (up ? 'pos' : 'negv') + '" style="width:' + w + '%"></span></div></div>';
      }).join('') + '</div>'
      : '<p class="ink2">' + e(sp.reasons[0] ? sp.reasons[0].effect : 'No explanation available.') + '</p>';
    const gaps = sc.gap[i], anyGap = gaps.some(function (g) { return g > 0; });
    const ev = sp.evidence || {};
    return '<h2>' + e(sp.name) + '</h2><p class="sub ink2" style="margin:4px 0 14px">Rank ' + sc.rank[i] + ' of ' + d.suppliers.length +
      ' · overall score ' + sc.S[i].toFixed(3) + ' · price ' + (sp.price_usd ? '$' + PS.num(sp.price_usd, 2) + ' per vial' : 'n/a') + '</p>' +
      '<div style="margin-bottom:14px">' + flagBadges(sp, true) + '</div>' +
      '<div class="grid g3">' +
      '<div class="card"><h3>Why this late-delivery mark (' + vals[i][1].toFixed(3) + ')</h3><p class="sub">The three things that moved the model\'s estimate most.</p>' + reasons +
      '<p class="small muted" style="margin-top:12px">' + e(sp.own_shipments > 0 ? sp.own_shipments + ' past shipment(s) of its own on record.' : 'No past shipments of its own on record.') + ' ' +
      (PS.isSyn() && sp.syn ? 'Shipping details are synthetic (see below). ' + (sp.syn.past_deliveries ? sp.syn.past_deliveries + ' past deliveries to this buyer, ' + PS.pct(100 * sp.syn.on_time_rate) + ' on time' + PS.synTag('R10, R11') : 'No deliveries to this buyer yet.') :
        e(sp.shipment_profile ? 'Shipping details for UAE orders are unknown, so the estimate is averaged over ' + sp.shipment_profile + '.' : '')) + '</p></div>' +

      '<div class="card"><h3>Compliance record (' + vals[i][3].toFixed(3) + ')</h3><p class="sub">Counted for the factory that makes this product.</p>' +
      '<dl class="kv"><dt>Factory</dt><dd>' + e(sp.factory && sp.factory.indexOf('(') !== 0 ? sp.factory : 'Not named on the label') + (sp.factory_city ? ', ' + e(sp.factory_city) : '') + '</dd>' +
      '<dt>Serious inspection findings, 5 yrs</dt><dd>' + (sp.factory_neutral ? 'No data (neutral)' : sp.oai) + '</dd>' +
      '<dt>Minor inspection findings, 5 yrs</dt><dd>' + (sp.factory_neutral ? 'No data (neutral)' : sp.vai) + '</dd>' +
      '<dt>Serious injectable recalls by this seller, 5 yrs</dt><dd>' + sp.recalls + '</dd>' +
      '<dt>Warning letter to this factory</dt><dd>' + e(PS.words(sp.worst_letter) || 'None in our 50-letter sample') + '</dd>' +
      '<dt>Contract</dt><dd>' + (PS.isSyn() && sp.syn ? 'Risk ' + sp.syn.contract_risk.toFixed(2) + ', counts 20%' + PS.synTag('R6', 'synthetic contract') : 'Not scored') + '</dd></dl>' +
      (sp.note ? '<div style="margin-top:12px">' + PS.banner('warn', 'warn', '<strong>Note, not scored.</strong> ' + e(sp.note.replace(/\s*Not scored.*$/, ''))) + '</div>' : '') + '</div>' +

      '<div class="card"><h3>Where it loses ground</h3><p class="sub">How the gap to an ideal supplier splits across the five marks.</p>' +
      (anyGap ? '<div class="bars">' + crit.map(function (c, j) {
        return '<div class="bar-row"><div class="name">' + e(c.short) + '</div>' + PS.barLine(100 * gaps[j], 100, PS.pct(100 * gaps[j]),
          { tip: PS.pct(100 * gaps[j]) + ' of this supplier\'s gap to the ideal comes from ' + c.short.toLowerCase() + '.' }) + '</div>';
      }).join('') + '</div>' : '<p class="ink2">This supplier is the best on every mark in this situation.</p>') + '</div></div>' +

      '<div class="card section"><h3>Cost and route (' + vals[i][0].toFixed(2) + ' and ' + vals[i][4].toFixed(2) + ')</h3><p class="sub">What the cost and route-exposure marks are made of.</p><dl class="kv">' +
      '<dt>Price per vial</dt><dd>$' + PS.num(sp.price_usd, 2) + (PS.isSyn() && sp.syn ? ' (official US price + $' + PS.num(sp.syn.freight_usd_per_vial, 2) + ' synthetic freight' + PS.synTag(sp.syn.freight_rate_range) + ')' : ' (official US price; freight has no data)') + '</dd>' +
      '<dt>Country logistics score</dt><dd>' + PS.num(sp.lpi, 1) + ' of 5 (World Bank Logistics Performance Index' + (sp.country_neutral ? ', middle value of the others because the country is not stated' : ', ' + e(sp.country)) + ')</dd>' +
      '<dt>Share of cargo exposed to Hormuz or Gulf airspace</dt><dd>' + (PS.isSyn() && sp.syn ? PS.num(sp.syn.hormuz_air_share, 2) + PS.synTag('R9') : PS.num(sp.hormuz, 2) + ' (UAE port volumes, the same for every origin)') + '</dd>' +
      '<dt>Route exposure in Crisis mode</dt><dd>' + PS.num(sp.c5_crisis, 2) + ' (exposure stressed 1.5 times, capped at 1)</dd></dl></div>' +
      '<div class="card section"><h3>Evidence: where it is made</h3><p class="sub">Taken from the official drug label' + (ev.label_version ? ' (' + e(ev.label_version) + ')' : '') + '.</p>' +
      '<blockquote>' + e(ev.quote || 'No statement found.') + '</blockquote>' +
      '<p class="small ink2" style="margin-top:10px">' + e(ev.note || '') + '</p>' +
      (ev.fei_evidence && sp.factory_fei ? '<p class="small ink2" style="margin-top:6px">FDA factory number ' + e(sp.factory_fei) + '. ' + e(ev.fei_evidence) + '</p>' : '') +
      ((ev.label_urls || []).length ? '<p class="small" style="margin-top:8px">' + ev.label_urls.map(function (u, n) {
        return '<a href="' + e(u) + '" target="_blank" rel="noopener">Open the label on DailyMed' + (ev.label_urls.length > 1 ? ' (' + (n + 1) + ')' : '') + '</a>';
      }).join(' · ') + '</p>' : '') +
      (sp.medicaid_share_pct !== null && sp.medicaid_share_pct !== undefined ? '<p class="small muted" style="margin-top:8px">' + (PS.isSyn() ? 'Real data, used to scale the synthetic capacity and to pick the established suppliers: ' : 'Information only, not scored: ') +
        PS.num(sp.medicaid_share_pct, 1) + '% of 2025 US Medicaid carboplatin volume.</p>' : '') + '</div>' +
      (PS.isSyn() && sp.syn ? synCard(sp) : '');
  }

  function synCard(sp) {
    const y = sp.syn, t = PS.synTag;
    const row = function (k, v, rid) { return '<dt>' + e(k) + '</dt><dd>' + v + t(rid) + '</dd>'; };
    return '<div class="card section"><h3>Synthetic inputs for this supplier</h3><p class="sub">Invented within the approved ranges (fixed seed), because no public data exists. Range ids refer to the table on Evidence &amp; trust.</p>' +
      '<div class="grid g2"><dl class="kv">' +
      row('Shipping', 'by ' + e(y.shipment_mode) + ', terms ' + e(y.vendor_inco_term), 'R1, R2') +
      row('Typical shipment', PS.num(y.shipment_vials) + ' vials, ' + PS.num(y.shipment_weight_kg) + ' kg', 'R3, R4') +
      row('Air freight', '$' + PS.num(y.freight_rate_usd_per_kg, 2) + ' per kg = $' + PS.num(y.freight_usd_per_vial, 2) + ' per vial', y.freight_rate_range) +
      row('Share of cargo exposed to Hormuz or Gulf airspace', PS.num(y.hormuz_air_share, 2), 'R9') + '</dl><dl class="kv">' +
      row('Monthly vials this factory can give us', PS.num(y.factory_capacity_vials), 'R8') +
      row('Past deliveries to this buyer', y.past_deliveries ? y.past_deliveries + ' (' + PS.pct(100 * y.on_time_rate) + ' on time)' : '0 (new supplier)', 'R10, R11') +
      row('Invoice error rate used to make its invoices', y.invoice_error_rate ? PS.pct(100 * y.invoice_error_rate, 1) : 'no invoices (new supplier)', 'R7') +
      row('Contract risk (from its synthetic contract)', y.contract_risk.toFixed(2), 'R6') + '</dl></div></div>';
  }

  /* =============================================================== ORDER SPLIT */
  V.split = function () {
    const d = PS.data, s = PS.state, sc = PS.stressed(), st = splitStats(sc), mode = d.modes[s.mode], crit = PS.criteria();
    const notes = [];
    if (s.outage && s.outage !== 'none') notes.push(disasterNote(s.outage));
    if (sc.spot > 0.5) notes.push(PS.banner('crit', 'alert', '<strong>Emergency purchase needed.</strong> The approved suppliers cannot cover ' + PS.num(sc.spot) + ' vials under the rules.'));
    if (s.mode !== 'Normal') {
      const base = PS.scenario('Normal'), same = PS.sameSplit(sc, base);
      const moved = sc.rank.filter(function (r, i) { return r !== base.rank[i]; }).length;
      const top = d.suppliers[sc.rank.indexOf(1)];
      notes.push(PS.banner('info', 'info', (same ? '<strong>Same order as in Normal mode.</strong> ' : '<strong>The order changes compared with Normal mode.</strong> ') +
        (moved ? 'The ranking does change: ' + moved + ' of ' + sc.rank.length + ' suppliers move, and ' + e(top.name) + ' ranks first.' : 'The ranking is unchanged as well.') +
        (same && moved ? ' The split stays the same because it also weighs price and the share limits, not the ranking alone.' : '')));
    }
    {                                                    // a top-ranked supplier that receives nothing needs an explanation
      const facV = {}, prices = d.suppliers.map(function (x) { return x.price_usd; }).sort(function (a, b) { return a - b; });
      const med = prices[Math.floor(prices.length / 2)];
      d.suppliers.forEach(function (sp, i) { facV[sp.factory_group] = (facV[sp.factory_group] || 0) + sc.vials[i]; });
      d.suppliers.forEach(function (sp, i) {
        if (sc.rank[i] !== 1 || facV[sp.factory_group] > 0.5) return;
        if (sc.outage && PS.outage(sc.outage).groups.indexOf(sp.factory_group) >= 0) return;   // explained by the disaster note
        notes.push(PS.banner('warn', 'warn', sp.price_usd > 2 * med
          ? '<strong>' + e(sp.name) + ' ranks first but receives no order.</strong> At $' + PS.num(sp.price_usd) + ' per vial it costs about ' + Math.round(sp.price_usd / med) +
            ' times the other suppliers ($' + PS.num(med, 2) + '). The ranking in this situation gives cost little or no weight, but the order split still weighs price.'
          : '<strong>' + e(sp.name) + ' ranks first but receives no order</strong> because of the share limits.'));
      });
    }
    if (mode.established_factories > 0) notes.push(PS.banner('syn', 'syn', mode.established_factories + ' factories have an established supplier (synthetic delivery records' + PS.synTag('R10') + '), so the plan lets each take up to ' + PS.pct(100 * mode.tier_cap) +
      ' and caps each new supplier at ' + PS.pct(100 * mode.probation_cap) + ' (at least 5% if chosen). Each factory is also limited by the vials it can give us each month' + PS.synTag('R8') + '.'));
    if (mode.established_factories === 0) notes.push(PS.banner('', 'new', 'All suppliers are new, so the plan caps each <strong>factory</strong> at ' + PS.pct(100 * mode.probation_cap) + ' and a chosen supplier gets at least 5%. A supplier with its own delivery record could receive up to ' + PS.pct(100 * mode.tier_cap) + '.'));

    const changed = sc.w.some(function (w, j) { return Math.abs(w - d.modes.Normal.ahp[j]) > 1e-6; });
    const weights = '<div class="legend"><span><span class="sw"></span>Weight used now</span>' + (changed ? '<span><span class="sw context"></span>Board\'s everyday weight</span>' : '') + '</div><div class="bars">' +
      crit.map(function (c, j) {
        return '<div class="bar-row"><div class="name">' + e(c.short) + '</div><div class="pair">' +
          PS.barLine(100 * sc.w[j], 50, PS.pct(100 * sc.w[j], 1) + (PS.noData(c.id) ? ' · no effect' : ''), { tip: PS.noData(c.id) ? c.short + ' has ' + PS.pct(100 * sc.w[j], 1) + ' weight, but ' + PS.NO_DATA_TIP.charAt(0).toLowerCase() + PS.NO_DATA_TIP.slice(1) : c.short + ' counts for ' + PS.pct(100 * sc.w[j], 1) + ' of the ranking in this situation.' }) +
          (changed ? PS.barLine(100 * d.modes.Normal.ahp[j], 50, PS.pct(100 * d.modes.Normal.ahp[j], 1), { context: true, tip: 'Board\'s everyday weight for ' + c.short.toLowerCase() + ': ' + PS.pct(100 * d.modes.Normal.ahp[j], 1) + '.' }) : '') +
          '</div></div>';
      }).join('') + '</div>';

    const order = d.suppliers.map(function (_, i) { return i; }).sort(function (a, b) { return sc.rank[a] - sc.rank[b] || a - b; });
    const byMode = d.meta.modes.map(function (md) { return PS.scenario(md); });
    const modeTable = '<div class="table-wrap"><table><thead><tr><th>Supplier</th>' + d.meta.modes.map(function (md) {
      return '<th class="num">' + e(md) + (md === s.mode ? ' (shown)' : '') + '</th>';
    }).join('') + '</tr></thead><tbody>' + order.map(function (i) {
      return '<tr><td>' + e(d.suppliers[i].name) + '</td>' + byMode.map(function (m2, k) {
        const cur = d.meta.modes[k] === s.mode;
        return '<td class="num">' + (cur ? '<strong>' : '') + m2.S[i].toFixed(3) + (cur ? '</strong>' : '') + '<span class="cellsub">rank ' + m2.rank[i] + '</span></td>';
      }).join('') + '</tr>';
    }).join('') + '</tbody></table></div>';

    return head('Order split', 'How to split this month\'s order',
      'The split spreads ' + PS.num(d.meta.demand) + ' vials across independent factories, favouring higher-ranked suppliers while obeying the plan\'s share limits. Change the situation above to see it respond.') +
      stressPicker() +
      '<div class="stack">' + notes.join('') + '</div>' +
      '<div class="section grid g4">' + tile('Factories in the order', st.factories, st.two_ok ? 'meets the Tier 1 rule of at least 2 suppliers' : 'below the Tier 1 rule of at least 2 suppliers') +
      tile('Countries', st.countries, st.unknownCountry ? 'plus one factory whose country is not stated' : '') +
      '<div class="card tile" data-tip="Warm-backup share: the part of this month\'s order placed with factories other than the main one. That supply is already approved and shipping, so it can be scaled up at once if the main factory fails." tabindex="0"><span class="label">Warm-backup share</span><span class="value">' + PS.pct(st.backup) +
        '</span><span class="hint">of the order is with factories other than the main one (largest single factory: ' + PS.pct(st.largest) + ')</span></div>' +
      tile('Emergency purchase', PS.num(st.spot) + ' vials', 'outside the approved suppliers') + '</div>' +
      '<div class="section grid g-main"><div class="card"><h3>Recommended split, by factory</h3><p class="sub">Several names on the box can be one factory, so limits apply to the factory.</p>' + splitList(sc, d.meta.demand) + '</div>' +
      '<div class="card"><h3>What counts, and how much</h3><p class="sub">The weights behind the ranking in this situation.</p>' + weights +
      '<p class="small muted" style="margin-top:12px">Consistency check on the board\'s weights: ' + d.meta.ahp_consistency.CR + ' (must stay below 0.10).</p></div></div>' +
      '<section class="section"><h2>Scores in each situation</h2><p class="sub">Overall score (higher is better) and rank in each situation.</p>' + modeTable + '</section>' +
      '<section class="section"><h2>Approve and log</h2><p class="sub">Nothing is ordered until a person signs off. Each record is fingerprinted and chained to the one before it, so later changes can be detected.</p>' +
      '<div class="grid g-main"><form class="card stack" id="approve-form" novalidate>' +
      '<label class="f">Your initials or staff ID (no full names)<input type="text" id="ap-who" maxlength="12" autocomplete="off"></label>' +
      '<div class="f" role="group" aria-label="Decision"><span>Decision</span><div class="radio-row">' +
      ['Approve as recommended', 'Approve with changes', 'Reject'].map(function (o, n) {
        return '<label><input type="radio" name="ap-decision" value="' + e(o) + '"' + (n === 0 ? ' checked' : '') + '> ' + e(o) + '</label>';
      }).join('') + '</div></div>' +
      '<label class="f">Reason (required when you change or reject)<textarea id="ap-reason" maxlength="500"></textarea></label>' +
      '<p class="err" id="ap-err" role="alert" hidden></p>' +
      '<div class="row"><button class="btn primary" type="submit">Sign and log</button><span class="small muted">Demo storage: saved in this browser only. A live system would write to the buyer\'s own database.</span></div></form>' +
      '<div class="card" id="audit-box"><h3>Approval log</h3><p class="sub muted">Loading…</p></div></div></section>';
  };

  function stressPicker() {
    const s = PS.state, opts = PS.data.stress.outages.filter(function (o) { return o.kind !== 'country_worst'; });
    return '<div class="card" style="margin-bottom:16px"><h3>Stress test: a natural disaster</h3>' +
      '<p class="sub">A flood, cyclone or earthquake can shut a factory or a whole region. Choose what goes offline; the order split re-solves. Supplier scores do not change, because a disaster says nothing about quality.</p>' +
      '<label class="f" style="max-width:560px">What goes offline<select id="outage" class="sel"><option value="none"' + (s.outage === 'none' ? ' selected' : '') + '>Nothing (no disaster)</option>' +
      opts.map(function (o) { return '<option value="' + e(o.key) + '"' + (o.key === s.outage ? ' selected' : '') + '>' + e(PS.outageLabel(o)) + '</option>'; }).join('') +
      '</select></label></div>';
  }
  function disasterNote(key) {
    const d = PS.data, o = PS.outage(key), base = PS.scenario(), hit = PS.stressed(key), fac = PS.factories();
    const tot = function (sc) { const t = {}; d.suppliers.forEach(function (sp, i) { t[sp.factory_group] = (t[sp.factory_group] || 0) + sc.vials[i]; }); return t; };
    const b = tot(base), h = tot(hit);
    const gained = Object.keys(h).filter(function (g) { return h[g] > (b[g] || 0) + 0.5; }).map(function (g) { return fac[g].label + ' (+' + PS.num(h[g] - (b[g] || 0)) + ' vials)'; });
    const lost = Object.keys(b).filter(function (g) { return b[g] > 0.5 && o.groups.indexOf(g) >= 0; }).map(function (g) { return fac[g].label; });
    const money = function (v) { return '$' + PS.num(v); };
    const cost = Math.abs(hit.spend - base.spend) < 1 ? 'The monthly cost does not change' :
      'The monthly cost of the order rises from ' + money(base.spend) + ' to ' + money(hit.spend) + ' (' + (hit.spend / base.spend).toFixed(1) + ' times)';
    let html = '<strong>' + e(PS.outageLabel(o)) + ' offline.</strong> ' +
      (lost.length ? 'The recommended order loses ' + e(lost.join(', ')) + '. ' : 'None of these factories was in the recommended order. ') +
      (gained.length ? 'Taking over: ' + e(gained.join(', ')) + '. ' : '') +
      (hit.spot > 0.5 ? '<strong>' + PS.num(hit.spot) + ' vials cannot be supplied by any approved supplier</strong> and must be bought in an emergency. ' : 'The order is still fully covered by approved suppliers. ') +
      cost + ', ' + PS.priceBasis() + ' (a stand-in for tender prices).';
    const worst = d.stress.outages.find(function (x) { return x.kind === 'country_worst' && x.country === o.country; });
    if (o.kind === 'country' && worst) {
      const wr = PS.stressed(worst.key), unk = worst.groups.filter(function (g) { return o.groups.indexOf(g) < 0; }).map(function (g) { return fac[g].names.join(', '); });
      html += '<br><br><strong>Caveat:</strong> ' + e(unk.join(', ')) + ' does not state its factory\'s country, so it is not taken offline here. If its factory is also in ' + e(o.country) + ': ' +
        (wr.spot > 0.5 ? PS.num(wr.spot) + ' vials must be bought in an emergency' : 'the order is still covered') + ' and the monthly cost becomes ' + money(wr.spend) + '.';
    }
    return PS.banner(hit.spot > 0.5 ? 'crit' : 'warn', hit.spot > 0.5 ? 'alert' : 'warn', html);
  }

  V.auditBox = function (rows, check) {
    if (!rows.length) return '<h3>Approval log</h3><p class="sub">No approvals yet in this browser.</p>';
    return '<h3>Approval log</h3><div style="margin:8px 0 12px">' + PS.banner(check.ok ? 'good' : 'crit', check.ok ? 'good' : 'alert',
      '<strong>' + (check.ok ? 'Log verified.' : 'Log has been altered.') + '</strong> ' + e(check.message)) + '</div>' +
      '<div class="table-wrap"><table><thead><tr><th>#</th><th>When (UTC)</th><th>Who</th><th>Decision</th><th>Situation</th><th>Fingerprint</th></tr></thead><tbody>' +
      rows.slice().reverse().map(function (r) {
        return '<tr><td class="num">' + r.seq + '</td><td class="nowrap">' + e(String(r.timestamp_utc).replace('T', ' ').replace('Z', '')) + '</td><td>' + e(r.approver) + '</td><td>' + e(r.decision) +
          (r.reason ? '<span class="cellsub">' + e(r.reason) + '</span>' : '') + '</td><td>' + e(r.mode) + '<span class="cellsub">' + (r.stress_test && r.stress_test !== 'none' ? 'stress test: ' + e(r.stress_test) : 'no disaster') + '</span></td><td class="mono">' + e(String(r.record_hash).slice(0, 12)) + '…</td></tr>';
      }).join('') + '</tbody></table></div><p style="margin-top:12px"><button class="btn small-btn" type="button" id="audit-download">Download the log</button></p>';
  };

  /* =============================================================== ALERTS */
  V.alerts = function () {
    const d = PS.data, act = PS.activeShortages(), by = {};
    act.forEach(function (r) { by[r.company_name] = (by[r.company_name] || 0) + 1; });
    const comp = Object.keys(by).map(function (k) { return [k, by[k]]; }).sort(function (a, b) { return b[1] - a[1]; });
    const hit = d.suppliers.filter(function (s) { return s.active_shortage; }).length;
    const mx = comp.length ? comp[0][1] : 1, omx = d.alerts.oncology_by_molecule.length ? d.alerts.oncology_by_molecule[0].records : 1;
    return head('Alerts', 'Shortage alerts from the US drug regulator',
      'The FDA publishes which medicines are in short supply and which companies are affected. A shortage record does not change a supplier\'s score here; it is a warning for the buyer.') +
      (act.length ? PS.banner('crit', 'alert', '<strong>' + act.length + ' active carboplatin shortage records</strong> from ' + comp.length + ' companies, in the snapshot of ' + e(d.meta.as_of) + '.')
        : PS.banner('good', 'good', 'No active carboplatin shortage records in the snapshot of ' + e(d.meta.as_of) + '.')) +
      '<div class="section grid g3">' + tile('Active records', act.length, 'for carboplatin') + tile('Our ranked suppliers affected', hit + ' of ' + d.suppliers.length) +
      tile('Cancer medicines in shortage', d.alerts.oncology_total, 'records across ' + d.alerts.oncology_by_molecule.length + ' medicines') + '</div>' +
      '<div class="section card"><h3>Check the FDA right now</h3><p class="sub">Asks the FDA\'s public database directly from your browser.</p>' +
      '<div class="row"><button class="btn primary" type="button" id="live-check">Check now</button><span id="live-result" class="ink2" role="status"></span></div></div>' +
      '<div class="section grid g2"><div class="card"><h3>Active carboplatin records, by company</h3><p class="sub">One record is one product size in shortage.</p><div class="bars">' +
      comp.map(function (c) { return '<div class="bar-row"><div class="name">' + e(c[0]) + '</div>' + PS.barLine(c[1], mx, String(c[1]), { tip: c[0] + ': ' + c[1] + ' active record(s).' }) + '</div>'; }).join('') + '</div></div>' +
      '<div class="card"><h3>Cancer medicines in shortage</h3><p class="sub">Current FDA records, by medicine.</p><div class="bars">' +
      d.alerts.oncology_by_molecule.map(function (m) { return '<div class="bar-row"><div class="name">' + e(m.molecule) + '</div>' + PS.barLine(m.records, omx, String(m.records), { tip: m.molecule + ': ' + m.records + ' record(s).' }) + '</div>'; }).join('') + '</div></div></div>' +
      '<section class="section"><h2>All carboplatin records</h2><div class="table-wrap"><table><thead><tr><th>Company</th><th>Product</th><th>Availability</th><th>Reason given</th><th>Updated</th></tr></thead><tbody>' +
      d.alerts.sku.map(function (r) {
        return '<tr><td>' + e(r.company_name) + '</td><td>' + e(r.presentation || '') + '</td><td>' + e(r.availability || r.status || '') + '</td><td>' + e(r.shortage_reason || 'Not given') + '</td><td class="nowrap">' + e(String(r.update_date || '').slice(0, 10)) + '</td></tr>';
      }).join('') + '</tbody></table></div></section>';
  };

  /* =============================================================== DOCUMENTS */
  V.documents = function (showAll) {
    const d = PS.data.documents, letters = showAll ? d.letters : d.letters.slice(0, 12);
    const cls = Object.keys(d.classifier).map(function (k) { return [k, d.classifier[k]]; });
    return head('Documents', 'Reading regulator letters and contracts',
      'The system reads FDA warning letters to recognise what kind of failure each one describes, and it can pull the key terms out of a supply contract.') +
      '<section class="section"><h2>FDA warning letters</h2><p class="sub">50 hand-picked letters were read. A supplier with no letter here has none in our sample; it may still have one elsewhere.</p>' +
      '<div class="grid g-main"><div class="card"><h3>What the reader looks for</h3><p class="sub">Tested on letters it had not seen. 0.5 is guessing, 1.0 is perfect.</p><div class="bars">' +
      cls.map(function (c) {
        const auc = c[1].oof_roc_auc;
        return '<div class="bar-row"><div class="name">' + e(PS.cap(c[0])) + '<span class="cellsub">' + c[1].positives + ' of ' + c[1].letters + ' letters</span></div>' +
          (auc !== undefined ? PS.barLine(auc, 1, auc.toFixed(2), { tip: PS.cap(c[0]) + ': recognition quality ' + auc.toFixed(2) + ' on unseen letters.' }) : '<span class="small muted">' + e(c[1].method) + '</span>') + '</div>';
      }).join('') + '</div></div>' +
      '<div class="card"><h3>How serious each kind counts</h3><p class="sub">A team setting, not data.</p><dl class="kv">' +
      Object.keys(d.severity_weights).map(function (k) { return '<dt>' + e(PS.cap(k)) + '</dt><dd>' + d.severity_weights[k] + '</dd>'; }).join('') + '</dl>' +
      '<p class="small muted" style="margin-top:12px">The answer key comes from the regulations each letter cites, not from human labelling. The weakest class, quality unit, is cited by nearly every letter.</p></div></div>' +
      '<div class="table-wrap" style="margin-top:16px"><table><thead><tr><th>Company</th><th>Date</th><th>Main failure</th><th>Seriousness</th><th>Source</th></tr></thead><tbody>' +
      letters.map(function (l) {
        return '<tr><td>' + e(l.company_name) + '</td><td class="nowrap">' + e(String(l.letter_date).slice(0, 10)) + '</td><td>' + e(PS.cap(l.top_violation)) + '</td><td>' +
          PS.meter(l.letter_severity, 1, { tip: l.company_name + ': seriousness ' + Number(l.letter_severity).toFixed(2) + ' of 1.' }) + '</td><td>' +
          (l.source_url ? '<a href="' + e(l.source_url) + '" target="_blank" rel="noopener">FDA letter</a>' : '') + '</td></tr>';
      }).join('') + '</tbody></table></div>' +
      '<p style="margin-top:10px"><button class="btn small-btn" type="button" id="letters-toggle">' + (showAll ? 'Show fewer' : 'Show all ' + d.letters.length + ' letters') + '</button></p></section>' +

      '<section class="section"><h2>Contract reader</h2>' + (PS.isSyn() ? PS.banner('syn', 'syn', '<strong>Synthetic view: these contracts are scored.</strong> The 11 contracts were invented for testing; here their risk counts for 20% of the compliance mark' + PS.synTag('R6') + '. In the real view they are not scored.')
        : PS.banner('warn', 'warn', '<strong>Demo only.</strong> The 11 contracts below were invented for testing, so their results are not part of any supplier\'s score.')) +
      '<div class="table-wrap" style="margin-top:14px"><table><thead><tr><th>Contract with</th><th>If Hormuz closes</th><th>Delivery promise</th><th>Late delivery</th><th>Locks the buyer in?</th></tr></thead><tbody>' +
      d.contracts.map(function (c) {
        return '<tr><td>' + e(c.supplier_name) + '</td><td>' + e(PSContract.plain(c.force_majeure)) + '</td><td class="nowrap">' + e(c.lead_time_days) + ' days</td><td>' + e(PSContract.plain(c.late_delivery_penalty)) + '</td><td>' +
          (c.exclusive_share_pct ? 'Yes, at least ' + e(c.exclusive_share_pct) + '% must be bought here' : 'No') + '</td></tr>';
      }).join('') + '</tbody></table></div>' +
      '<div class="card" style="margin-top:16px"><h3>Try it</h3><p class="sub">Paste contract text with numbered sections such as "8. FORCE MAJEURE 8.1 …". It is read in your browser and sent nowhere.</p>' +
      '<textarea id="contract-try" aria-label="Contract text" placeholder="2. FORECASTS, ORDERS AND LEAD TIME 2.2 … within 45 calendar days … 8. FORCE MAJEURE 8.1 …"></textarea><div id="contract-out" style="margin-top:12px"></div></div></section>';
  };
  V.contractResult = function (r) {
    return '<dl class="kv"><dt>If Hormuz closes</dt><dd>' + e(PSContract.plain(r.force_majeure.category)) + '</dd>' +
      '<dt>Delivery promise</dt><dd>' + (r.lead_time.days === null ? 'Not found' : r.lead_time.days + ' days') + '</dd>' +
      '<dt>Late delivery</dt><dd>' + e(PSContract.plain(r.late_delivery_penalty.category)) + '</dd>' +
      '<dt>Locks the buyer in?</dt><dd>' + (r.single_source.risk ? 'Yes' + (r.single_source.exclusive_share_pct ? ', at least ' + r.single_source.exclusive_share_pct + '%' : '') : 'No') + '</dd>' +
      '<dt>Overall contract risk</dt><dd>' + r.contract_risk.toFixed(2) + ' of 1</dd></dl>';
  };

  /* =============================================================== MODELS */
  /* late-delivery mark per supplier in each view: the model is the same, the inputs differ */
  function delivery_by_supplier() {
    const real = PS.raw.suppliers, syn = PS.raw.synthetic.suppliers;
    const rows = real.map(function (r, i) {
      const y = syn[i], a = r.marks.C2_delivery_risk, b = y.marks.C2_delivery_risk, d = b - a;
      const cur = PS.isSyn() ? y : r, top = cur.reasons && cur.reasons[0];
      return '<tr><td><strong>' + e(r.name) + '</strong></td><td class="num">' + a.toFixed(3) + '</td><td class="num">' + b.toFixed(3) + '</td>' +
        '<td class="num">' + (Math.abs(d) < 0.0005 ? 'same' : (d > 0 ? '+' : '') + d.toFixed(3)) + '</td>' +
        '<td class="ink2">' + (top ? e(top.feature + ': ' + top.value) : '') + '</td></tr>';
    }).join('');
    return '<div class="card" style="margin-top:16px"><h3>What the model predicts for each supplier, in both views</h3>' +
      '<p class="sub">Late-delivery mark, 0 best to 1 worst. Same model, different inputs: the real view averages over real shipments from the factory\'s country; the synthetic view uses each supplier\'s own synthetic shipping terms and delivery record ' + PS.synTag('R1-R4, R10, R11') + '.</p>' +
      '<div class="table-wrap"><table><thead><tr><th>Supplier</th><th>Real view</th><th>Synthetic view</th><th>Change</th><th>Biggest driver in the view you are looking at</th></tr></thead><tbody>' + rows + '</tbody></table></div></div>';
  }

  V.models = function () {
    const m = PS.data.models, x = m.c2.xgboost_test, b = m.c2.logistic_regression_test;
    const metrics = [['Overall quality', 'roc_auc', '0.5 is guessing, 1.0 is perfect'], ['Late shipments caught', 'recall_late', 'share of truly late shipments that were flagged'],
      ['Flags that were right', 'precision_late', 'share of flagged shipments that really were late']];
    const imp = Object.keys(m.c2.global_feature_importance_mean_abs_shap).map(function (k) { return [k, m.c2.global_feature_importance_mean_abs_shap[k]]; }), imx = imp[0][1];
    const cm = x.confusion_matrix, late = cm.tp + cm.fn, ontime = cm.tn + cm.fp;
    return head('Models', 'How good are the predictions?',
      'Two models do the predicting. Both are tested the honest way: on data they were not allowed to see while learning.') +
      '<section class="section"><h2>Late-delivery model</h2>' + (PS.hasSyn() ? PS.banner('info', 'info', '<strong>The scores below are the same in both views, on purpose.</strong> The model is trained and tested only on real shipments (2006 to 2015); the synthetic view never trains it. What the synthetic view changes is the <em>input</em>: each supplier\'s own shipping terms and delivery record. Its effect on each supplier\'s late-delivery mark is in the table at the end of this section.') : '') + '<p class="sub">It learned from ' + PS.num(m.c2.train_rows) + ' shipments up to 2013 and was tested on ' + PS.num(m.c2.test_rows) +
      ' later shipments (2014 to 2015), of which ' + PS.pct(100 * m.c2.test_late_rate) + ' were late.</p>' +
      '<div class="grid g-main"><div class="card"><h3>Against a simple baseline</h3><p class="sub">A complex model must beat a simple one to earn its place.</p>' +
      '<div class="legend"><span><span class="sw"></span>XGBoost (used)</span><span><span class="sw context"></span>Simple baseline (logistic regression)</span></div><div class="bars">' +
      metrics.map(function (k) {
        return '<div class="bar-row"><div class="name">' + e(k[0]) + '<span class="cellsub">' + e(k[2]) + '</span></div><div class="pair">' +
          PS.barLine(x[k[1]], 1, x[k[1]].toFixed(2), { tip: 'XGBoost, ' + k[0].toLowerCase() + ': ' + x[k[1]].toFixed(3) }) +
          PS.barLine(b[k[1]], 1, b[k[1]].toFixed(2), { context: true, tip: 'Baseline, ' + k[0].toLowerCase() + ': ' + b[k[1]].toFixed(3) }) + '</div></div>';
      }).join('') + '</div><p class="small muted" style="margin-top:12px">The model is tuned to catch late shipments, which costs false alarms: it beats the baseline on quality and on shipments caught, and loses on how often a flag is right.</p></div>' +
      '<div class="card"><h3>In plain numbers</h3><p class="sub">On the ' + PS.num(m.c2.test_rows) + ' test shipments.</p><dl class="kv">' +
      '<dt>Late shipments caught</dt><dd>' + PS.num(cm.tp) + ' of ' + PS.num(late) + '</dd><dt>Late shipments missed</dt><dd>' + PS.num(cm.fn) + '</dd>' +
      '<dt>False alarms</dt><dd>' + PS.num(cm.fp) + ' of ' + PS.num(ontime) + ' on-time shipments</dd><dt>Correctly left alone</dt><dd>' + PS.num(cm.tn) + '</dd></dl></div></div>' +
      '<div class="card" style="margin-top:16px"><h3>What the model relies on most</h3><p class="sub">Average pull on the prediction, across the test shipments.</p><div class="bars">' +
      imp.map(function (k) { return '<div class="bar-row"><div class="name">' + e(k[0]) + '</div>' + PS.barLine(k[1], imx, k[1].toFixed(2), { tip: k[0] + ': average pull ' + k[1].toFixed(3) }) + '</div>'; }).join('') + '</div>' +
      '<p class="small muted" style="margin-top:12px">It learned from HIV-medicine shipments between 2006 and 2015, so it captures how shipping behaves in general, not cancer-medicine supply to the Gulf. ' + (PS.isSyn() ? 'In the synthetic view each supplier gets its own synthetic shipping terms and delivery record, so the marks differ more.' : 'Suppliers whose factories are in the same country, with no delivery history of their own, get the same mark.') + '</p></div>' +
      (PS.hasSyn() ? delivery_by_supplier() : '') + '</section>' +

      '<section class="section"><h2>Billing-oddity model</h2><p class="sub">It looks at each invoice line\'s unit price, freight share and value, and flags the oddest 5% within each product group.</p>' +
      '<div class="grid g3">' + tile('Invoice lines checked', PS.num(m.c3.lines_scored), 'of ' + PS.num(m.c3.lines_total) + '; the rest have no freight figure') +
      tile('Lines flagged', PS.num(m.c3.lines_flagged)) + (PS.isSyn() ? tile('Used in the synthetic view', PS.num(PS.raw.synthetic.summary.c3_invoice_lines) + PS.synTag('R7'), 'synthetic invoice lines of the established suppliers; ' + PS.raw.synthetic.summary.c3_injected_errors_caught + ' of ' + PS.raw.synthetic.summary.c3_injected_errors + ' planted errors caught') :
        tile('Used in today\'s ranking', '0', 'no ranked supplier has invoice history of its own')) + '</div>' +
      '<h3 style="margin:18px 0 10px">Three flagged lines from the historical data</h3><div class="grid g3">' +
      m.c3.examples.map(function (x2) {
        return '<div class="card"><h3>' + e(x2.vendor) + '</h3><p class="sub">Product group ' + e(x2.product_group) + '</p><p class="ink2">' + e(x2.why_flagged) + '</p></div>';
      }).join('') + '</div></section>';
  };

  /* =============================================================== EVIDENCE & TRUST */
  function synSection() {
    const y = PS.raw.synthetic, sm = y.summary;
    return '<section class="section"><h2>The synthetic view: every invented value and its basis</h2><p class="sub">Asked for by the course professor for inputs with no public evidence. The real view never uses these. Each value is drawn once from its range with a fixed seed, so every run gives the same numbers; the models are not trained on them.</p>' +
      '<div class="table-wrap"><table><thead><tr><th>Range</th><th>What is invented</th><th>Applies to</th><th>Range used</th><th>Basis</th></tr></thead><tbody>' +
      y.ranges.map(function (r) {
        const dp = function (v) { return Number.isInteger(v) ? 0 : 2; };
        const rng = r.low !== null && r.low !== undefined ? PS.num(r.low, dp(r.low)) + ' to ' + PS.num(r.high, dp(r.high)) + ' ' + PS.words(r.unit) : e(r.how_drawn);
        const src = String(r.source || '').split(';').map(function (x) { x = x.trim(); return /^https?:/.test(x) ? '<a href="' + e(x) + '" target="_blank" rel="noopener">source</a>' : e(x); }).join(' · ');
        return '<tr><td>' + PS.synTag(r.id, r.id) + '</td><td><strong>' + e(r.item) + '</strong></td><td>' + e(r.applies_to) + '</td><td>' + rng + '</td><td class="ink2">' + e(r.basis) + '<span class="cellsub">' + src + '</span></td></tr>';
      }).join('') + '</tbody></table></div>' +
      '<p class="ink2" style="margin-top:12px">Check on the billing model: ' + sm.c3_injected_errors + ' invoice errors were planted in ' + PS.num(sm.c3_invoice_lines) + ' synthetic invoice lines, and the model flagged ' +
      sm.c3_injected_errors_caught + ' of them (' + sm.c3_flagged + ' lines flagged in total). The late-delivery model is unchanged (test score ' + sm.c2_model_test_roc_auc_unchanged.toFixed(3) + ').</p></section>';
  }

  V.trust = function () {
    const d = PS.data, c = d.content, lv = c.evidence_levels, icon = PS.LEVEL_ICON, ledger = PS.ledger();
    return head('Evidence & trust', 'What every number rests on',
      PS.isSyn() ? 'Synthetic view: every input with no public evidence is filled with a value invented within an approved industry range and marked synthetic; the ranges and their sources are listed below. Everything else is the same as in the real view.'
        : 'One rule runs through the whole system: an input is either backed by a cited source, or openly marked "no data" and given the same neutral value for every supplier, so it cannot tilt the ranking.') +
      '<div class="grid g4">' + PS.levels().filter(function (k) { return !PS.isSyn() || ledger.some(function (r) { return r.level === k; }); }).map(function (k) {
        const n = ledger.filter(function (r) { return r.level === k; }).length;
        return '<div class="card tile"><span>' + PS.badge('level-' + k, lv[k].label, icon[k]) + '</span><span class="value">' + n + '</span><span class="hint">' + e(lv[k].plain) + '</span></div>';
      }).join('') + '</div>' +
      '<section class="section"><h2>Every input, and its evidence</h2>' + (PS.isSyn() ? '<p class="sub">Rows marked Synthetic are filled from the ranges in the next table; in the real view the same rows read "no data" or "stand-in".</p>' : '') + '<div class="table-wrap"><table><thead><tr><th>Input</th><th>Feeds</th><th>Evidence</th><th>Source</th><th>What it means here</th></tr></thead><tbody>' +
      ledger.map(function (r) {
        return '<tr><td><strong>' + e(r.input) + '</strong></td><td>' + e(r.feeds) + '</td><td>' + PS.badge('level-' + r.level, lv[r.level].label, icon[r.level]) + '</td><td>' + e(r.source) + '</td><td class="ink2">' + e(r.note) + '</td></tr>';
      }).join('') + '</tbody></table></div></section>' +
      (PS.hasSyn() ? synSection() : '') +
      '<section class="section"><h2>Where this differs from the project plan, and why</h2><p class="sub">Every deliberate difference, so the plan, this site and the slides never silently disagree.</p>' +
      '<div class="table-wrap"><table><thead><tr><th>The plan says</th><th>Real view</th><th>Synthetic view</th><th>Why</th></tr></thead><tbody>' +
      c.plan_differences.map(function (r) { return '<tr><td>' + e(r.plan) + '</td><td><strong>' + e(r.here) + '</strong></td><td>' + e(r.synthetic) + '</td><td class="ink2">' + e(r.why) + '</td></tr>'; }).join('') +
      '</tbody></table></div></section>' +
      '<div class="section grid g2"><div class="card"><h3>Known limits</h3><p class="sub">What this prototype cannot claim.</p><ul class="ink2" style="margin:0;padding-left:18px">' +
      c.limits.map(function (l) { return '<li style="margin-bottom:8px">' + e(l) + '</li>'; }).join('') + '</ul></div>' +
      '<div class="card"><h3>How it is governed</h3><p class="sub">The rules the system follows.</p><dl class="stack" style="gap:10px;margin:0">' +
      c.governance.map(function (g) { return '<div><dt style="font-weight:650">' + e(g.title) + '</dt><dd class="ink2" style="margin:0">' + e(g.text) + '</dd></div>'; }).join('') + '</dl></div></div>' +
      '<section class="section"><h2>Data sources in this snapshot</h2><p class="sub">Snapshot of ' + e(d.meta.as_of) + ': ' + d.quality.checks + ' quality checks, ' + d.quality.errors + ' errors, ' + d.quality.warnings + ' warnings, ' + d.quality.quarantined_rows + ' bad rows set aside.</p>' +
      '<div class="table-wrap"><table><thead><tr><th>Source</th><th>Status</th><th class="num">Rows</th><th>Pipeline note</th></tr></thead><tbody>' +
      d.sources.map(function (s) {
        const ok = s.status === 'OK';
        return '<tr><td>' + e(s.label) + '</td><td>' + PS.badge(ok ? 'good' : '', ok ? 'Loaded' : PS.cap(String(s.status).toLowerCase()), ok ? 'good' : 'nodata') + '</td><td class="num">' + (s.rows === undefined || s.rows === null ? '–' : PS.num(s.rows)) + '</td><td class="ink2">' + e(s.note || '') + '</td></tr>';
      }).join('') + '</tbody></table></div><p class="small muted" style="margin-top:10px">Fingerprint of the score table behind this site: <span class="mono">' + e(d.meta.matrix_sha256.slice(0, 24)) + '…</span></p></section>';
  };

  /* =============================================================== GLOSSARY */
  V.glossary = function () {
    return head('Glossary', 'Plain-English meanings',
      PS.data.glossary.length + ' terms from shipping, medicines, buying and AI, each in one line.') +
      '<label class="f" style="max-width:420px">Search<input type="search" id="gloss-search" placeholder="Try: OAI, landed cost, recall" autocomplete="off"></label>' +
      '<div id="gloss-out" class="section">' + V.glossaryList('') + '</div>';
  };
  V.glossaryList = function (q) {
    q = String(q || '').trim().toLowerCase();
    const items = PS.data.glossary.filter(function (g) { return !q || (g.term + ' ' + g.meaning).toLowerCase().indexOf(q) >= 0; });
    if (!items.length) return '<p class="muted">No term matches "' + e(q) + '".</p>';
    const groups = {};
    items.forEach(function (g) { (groups[g.section] = groups[g.section] || []).push(g); });
    return Object.keys(groups).map(function (k) {
      return '<section class="section"><h2>' + e(k) + '</h2><dl class="gloss-list">' + groups[k].map(function (g) {
        return '<div class="gloss-item"><dt>' + e(g.term) + '</dt><dd>' + e(g.meaning) + '</dd></div>';
      }).join('') + '</dl></section>';
    }).join('');
  };

  PS.views = V;
})(window.PS);
