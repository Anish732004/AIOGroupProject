// Checks for the Vercel showcase's browser-side logic.  Run:  node tools/test_web.mjs
import { readFileSync, readdirSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import vm from 'node:vm';
import assert from 'node:assert/strict';

const root = join(dirname(fileURLToPath(import.meta.url)), '..');
globalThis.window = globalThis;
for (const f of ['core.js', 'contract.js', 'audit.js']) vm.runInThisContext(readFileSync(join(root, 'web/js', f), 'utf8'), { filename: f });
const snap = JSON.parse(readFileSync(join(root, 'web/data/snapshot.json'), 'utf8'));
let n = 0;
const ok = (name) => { n++; console.log('  ok  ' + name); };

// 1. snapshot: every scenario the controls can reach exists, and each split adds up to the demand
const m = snap.meta;
for (const mode of m.modes) for (const lam of m.lambdas) for (const ent of m.entropy_shares) {
  const sc = snap.scenarios[PS.key(mode, lam, ent)];
  assert.ok(sc, 'missing scenario ' + PS.key(mode, lam, ent));
  assert.equal(sc.status, 'Optimal');
  assert.equal(sc.S.length, snap.suppliers.length);
  assert.ok(Math.abs(sc.vials.reduce((a, b) => a + b, 0) + sc.spot - m.demand) < 0.6, 'split does not add up');
  assert.ok(Math.abs(sc.w.reduce((a, b) => a + b, 0) - 1) < 1e-3, 'weights do not sum to 1');
  sc.vials.forEach((v, i) => assert.ok(v <= m.demand * sc.cap_pct[i] / 100 + 0.6, 'cap broken'));
}
ok(Object.keys(snap.scenarios).length + ' scenarios present, splits add up to demand, weights sum to 1, caps respected');
assert.equal(snap.supplier_ids.length, new Set(snap.supplier_ids).size);
assert.ok(!/\/Users\/|\/private\/tmp|[\w.+-]+@[\w-]+\.[\w.-]+/.test(JSON.stringify(snap)), 'local path or e-mail in snapshot');
ok('no local paths or e-mail addresses in the snapshot');

// 2. contract reader: the JavaScript port gives the same answers as the Python extractor
const dir = join(root, 'layer1_ingestion/data/manual/contracts');
const expected = Object.fromEntries(snap.documents.contracts.map((c) => [c.supplier_name, c]));
let checked = 0;
for (const f of readdirSync(dir).filter((x) => x.endsWith('.txt'))) {
  const text = readFileSync(join(dir, f), 'utf8');
  const r = PSContract.read(text);
  const name = /made between (.+?) \(the "Supplier"\)/.exec(text.split(/\s+/).join(' '))[1];
  const e = expected[name];
  assert.ok(e, 'no Python result for ' + name);
  assert.equal(r.force_majeure.category, e.force_majeure, f);
  assert.equal(r.lead_time.days, e.lead_time_days, f);
  assert.equal(r.late_delivery_penalty.category, e.late_delivery_penalty, f);
  assert.equal(r.single_source.exclusive_share_pct, e.exclusive_share_pct, f);
  assert.ok(Math.abs(r.contract_risk - e.contract_risk) < 1e-4, f + ' risk ' + r.contract_risk + ' vs ' + e.contract_risk);
  checked++;
}
assert.equal(checked, snap.documents.contracts.length);
ok('contract reader matches the Python extractor on all ' + checked + ' demo contracts');

// 3. approval log: chained fingerprints, tampering is detected
const mem = { v: null, getItem() { return this.v; }, setItem(_k, v) { this.v = v; } };
await PSAudit.append({ approver: 'AB', decision: 'Approve as recommended', mode: 'Normal' }, mem);
await PSAudit.append({ approver: 'CD', decision: 'Reject', reason: 'test', mode: 'Crisis' }, mem);
assert.deepEqual((await PSAudit.verify(mem)).ok, true);
const rows = JSON.parse(mem.v);
assert.equal(rows[1].prev_hash, rows[0].record_hash);
rows[0].decision = 'Reject'; mem.v = JSON.stringify(rows);
assert.equal((await PSAudit.verify(mem)).ok, false);
rows[0].decision = 'Approve as recommended'; rows.shift(); mem.v = JSON.stringify(rows);
assert.equal((await PSAudit.verify(mem)).ok, false);
ok('approval log verifies, and detects an edited record and a deleted record');

// 4. live-check counting rule gives the pipeline's count on the pipeline's own rows
const c = PS.countActive(snap.alerts.sku.map((r) => ({ ...r, package_ndc: r.presentation })));
assert.equal(c.active, snap.alerts.sku.filter((r) => r.is_active).length);
ok('shortage "active" rule matches the pipeline on the snapshot rows (' + c.active + ' active)');
// 5. the security policy in vercel.json allows exactly the inline script in index.html (else the site breaks on Vercel)
const { createHash } = await import('node:crypto');
const html = readFileSync(join(root, 'web/index.html'), 'utf8');
const inline = [...html.matchAll(/<script>([\s\S]*?)<\/script>/g)].map((x) => "'sha256-" + createHash('sha256').update(x[1]).digest('base64') + "'");
const csp = JSON.parse(readFileSync(join(root, 'vercel.json'), 'utf8')).headers[0].headers.find((h) => h.key === 'Content-Security-Policy').value;
for (const h of inline) assert.ok(csp.includes(h), 'index.html inline script changed: put ' + h + ' into the CSP in vercel.json');
assert.ok(csp.includes('https://api.fda.gov'), 'the live FDA check needs connect-src https://api.fda.gov');
ok('vercel.json security policy matches the inline script (' + inline.length + ') and allows the FDA API');
console.log(n + ' checks passed');
