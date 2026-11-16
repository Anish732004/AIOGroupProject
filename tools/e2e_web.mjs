// End-to-end check of the showcase in headless Chrome, over the DevTools protocol (no packages; Node 22+).
//   node tools/serve_web.mjs &          (serves web/ with the vercel.json security headers)
//   node tools/e2e_web.mjs              (CHROME=/path/to/chrome to override; BASE=... to test a deployed URL)
import { spawn } from 'node:child_process';
import { readFileSync } from 'node:fs';
import { mkdtempSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join as pjoin, dirname as pdir } from 'node:path';
import { fileURLToPath as f2p } from 'node:url';
const ROOT = pjoin(pdir(f2p(import.meta.url)), '..');
const BASE = process.env.BASE || 'http://127.0.0.1:8766/', PORT = 9333, PROFILE = mkdtempSync(pjoin(tmpdir(), 'ps-e2e-'));
const CHROME = process.env.CHROME || '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome';
const chrome = spawn(CHROME,
  ['--headless=new', '--disable-gpu', `--remote-debugging-port=${PORT}`, `--user-data-dir=${PROFILE}`, '--disk-cache-size=1', '--window-size=1440,1000', 'about:blank'], { stdio: 'ignore' });
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
let target;
for (let i = 0; i < 40 && !target; i++) { await sleep(250); try { target = (await (await fetch(`http://127.0.0.1:${PORT}/json`)).json()).find((t) => t.type === 'page'); } catch {} }
const ws = new WebSocket(target.webSocketDebuggerUrl);
await new Promise((r) => (ws.onopen = r));
let id = 0; const pending = new Map(), problems = [];
ws.onmessage = (m) => {
  const d = JSON.parse(m.data);
  if (d.id && pending.has(d.id)) { pending.get(d.id)(d); pending.delete(d.id); }
  if (d.method === 'Runtime.exceptionThrown') problems.push('EXCEPTION ' + (d.params.exceptionDetails.exception?.description || d.params.exceptionDetails.text));
  if (d.method === 'Log.entryAdded' && d.params.entry.level === 'error') problems.push('LOG ' + d.params.entry.text + ' ' + (d.params.entry.url || ''));
  if (d.method === 'Runtime.consoleAPICalled' && d.params.type === 'error') problems.push('CONSOLE ' + d.params.args.map((a) => a.value || a.description).join(' '));
};
const send = (method, params = {}) => new Promise((r) => { const n = ++id; pending.set(n, r); ws.send(JSON.stringify({ id: n, method, params })); });
const ev = async (expr0) => { const expr = /^\s*const /.test(expr0) ? '(() => {' + expr0 + '})()' : expr0; const r = await send('Runtime.evaluate', { expression: expr, awaitPromise: true, returnByValue: true }); if (r.result.exceptionDetails) throw new Error('eval failed: ' + expr + ' -> ' + JSON.stringify(r.result.exceptionDetails.exception?.description)); return r.result.result.value; };
const go = async (hash) => { await ev(`location.hash = ${JSON.stringify(hash)}`); await sleep(250); };
let n = 0; const fails = [];
const check = (name, cond, extra = '') => { n++; if (cond) console.log('  ok   ' + name); else { fails.push(name); console.log('  FAIL ' + name + ' ' + extra); } };
await send('Runtime.enable'); await send('Log.enable'); await send('Page.enable');
await send('Page.navigate', { url: BASE + '#/' }); await sleep(1500);

// every page renders something and has a heading
for (const [hash, text] of [['#/', 'Choosing medicine suppliers'], ['#/suppliers', 'Who can supply it'], ['#/split', 'How to split'], ['#/alerts', 'Shortage alerts'],
  ['#/compare', 'Two suppliers, side by side'], ['#/documents', 'Reading regulator letters'], ['#/models', 'How good are the predictions'], ['#/trust', 'What every number rests on'], ['#/glossary', 'Plain-English meanings']]) {
  await go(hash);
  check('page ' + hash + ' renders', (await ev('document.querySelector("#view h1")?.textContent || ""')).includes(text));
}
check('nav marks the current page', (await ev('document.querySelector("#nav a[aria-current]").textContent')).includes('Glossary'));

// overview: key findings are computed from the data
await go('#/');
check('7 key findings are shown', (await ev('document.querySelectorAll(".finding").length')) === 7);
check('findings name the last-ranked supplier and its reason', (await ev('document.querySelector(".findings").textContent')).includes('ranks last') && (await ev('document.querySelector(".findings").textContent')).includes('compliance'));
check('every finding links to its evidence page', await ev('[...document.querySelectorAll(".finding a")].every(a => a.getAttribute("href").startsWith("#/"))'));

// compare: two pickers, same-factory notice, never the same supplier twice
await go('#/compare');
check('compare shows both suppliers', (await ev('document.querySelectorAll("table.cmp thead th").length')) === 3);
check('"better" marks appear for the default pair (best vs last)', (await ev('document.querySelectorAll(".win").length')) >= 3);
await ev('const a = document.getElementById("cmp-a"); a.value = "GLAND PHARMA"; a.dispatchEvent(new Event("change", { bubbles: true }))'); await sleep(100);
await ev('const b = document.getElementById("cmp-b"); b.value = "BPI LABS"; b.dispatchEvent(new Event("change", { bubbles: true }))'); await sleep(100);
check('same-factory notice appears for Gland vs BPI', (await ev('document.getElementById("view").textContent')).includes('Same factory'));
check('identical suppliers get no "better" marks on scores', (await ev('[...document.querySelectorAll("table.cmp tbody tr")].slice(0, 7).filter(r => r.querySelector(".win")).length')) === 0);
await ev('const b = document.getElementById("cmp-b"); b.value = "GLAND PHARMA"; b.dispatchEvent(new Event("change", { bubbles: true }))'); await sleep(100);
check('picking the same supplier twice is prevented', await ev('document.getElementById("cmp-a").value !== document.getElementById("cmp-b").value'));
await go('#/compare?a=APOTEX&b=TEYRO LABS');
check('compare link opens a chosen pair', await ev('document.getElementById("cmp-a").value === "APOTEX" && document.getElementById("cmp-b").value === "TEYRO LABS"'));

// suppliers: situation button, ranking, detail
await go('#/suppliers');
const firstNormal = await ev('document.querySelector("tr[data-supplier] strong + strong, tr[data-supplier] td.col-supplier strong").textContent');
await ev('document.querySelector("[data-mode=Crisis]").click()'); await sleep(150);
const firstCrisis = await ev('document.querySelector("tr[data-supplier] td.col-supplier strong").textContent');
check('Crisis button re-ranks (first: ' + firstNormal + ' -> ' + firstCrisis + ')', firstCrisis.includes('AVYXA') && !firstNormal.includes('AVYXA'));
check('situation note updates', (await ev('document.getElementById("mode-note").textContent')).includes('Hormuz'));
check('pressed state moves', await ev('document.querySelector("[data-mode=Crisis]").getAttribute("aria-pressed") === "true" && document.querySelector("[data-mode=Normal]").getAttribute("aria-pressed") === "false"'));
await ev('document.querySelector("tr[data-supplier=\\"ACCORD HEALTHCARE\\"]").click()'); await sleep(200);
check('clicking a row opens its detail', (await ev('document.querySelector("#detail h2").textContent')).includes('Accord'));
check('detail shows label evidence', (await ev('document.querySelector("#detail blockquote").textContent')).includes('Intas'));
await ev('const r = document.querySelector("tr[data-supplier=\\"HOSPIRA\\"]"); r.focus(); r.dispatchEvent(new KeyboardEvent("keydown", { key: "Enter", bubbles: true }))'); await sleep(200);
check('keyboard Enter opens a detail', (await ev('document.querySelector("#detail h2").textContent')).includes('Hospira'));

// split: situation carries over, dial, notes
await go('#/split');
check('situation carries across pages', await ev('document.querySelector("[data-mode=Crisis]").getAttribute("aria-pressed") === "true"'));
check('Crisis explanation is shown', (await ev('document.getElementById("view").textContent')).includes('ranks first but receives no order'));
await ev('const s = document.getElementById("lam"); s.value = "0"; s.dispatchEvent(new Event("input", { bubbles: true }))'); await sleep(150);
check('dial at 0 warns that risk is ignored', (await ev('document.getElementById("view").textContent')).includes('risk dial is at 0'));
check('dial label updates', (await ev('document.getElementById("lam-val").textContent')) === '0.00');
check('slider element survives re-render', await ev('!!document.getElementById("lam") && document.getElementById("lam").value === "0"'));
await ev('const s = document.getElementById("lam"); s.value = "1"; s.dispatchEvent(new Event("input", { bubbles: true })); document.querySelector("[data-mode=Normal]").click()'); await sleep(150);
check('split shows 4 factories in Normal', (await ev('document.querySelectorAll(".bars.stacked .bar-row").length')) === 4);
await ev('const s = document.getElementById("ent"); s.value = "0.5"; s.dispatchEvent(new Event("input", { bubbles: true }))'); await sleep(150);
check('data-weight slider changes the weights shown', (await ev('document.getElementById("view").textContent')).includes("Board's everyday weight"));
await ev('const s = document.getElementById("ent"); s.value = "0"; s.dispatchEvent(new Event("input", { bubbles: true }))'); await sleep(150);

// approval: validation, log, verification, tamper detection
await ev('localStorage.removeItem("pharmashield_audit_v1")'); await go('#/'); await go('#/split');
await ev('document.querySelector("#approve-form button[type=submit]").click()'); await sleep(200);
check('approval without initials is refused', (await ev('document.getElementById("ap-err").textContent')).includes('initials'));
await ev('document.getElementById("ap-who").value = "AB"; document.querySelector("input[name=ap-decision][value=Reject]").checked = true; document.querySelector("#approve-form button[type=submit]").click()'); await sleep(200);
check('rejecting without a reason is refused', (await ev('document.getElementById("ap-err").textContent')).includes('reason'));
await ev('document.getElementById("ap-reason").value = "Price too high this month"; document.querySelector("#approve-form button[type=submit]").click()'); await sleep(500);
await ev('document.getElementById("ap-who").value = "CD"; document.querySelector("#approve-form button[type=submit]").click()'); await sleep(500);
check('two approvals are logged', (await ev('document.querySelectorAll("#audit-box tbody tr").length')) === 2);
check('log verifies', (await ev('document.getElementById("audit-box").textContent')).includes('Log verified'));
check('log record holds the split and the score-table fingerprint', await ev('(() => { const r = JSON.parse(localStorage.getItem("pharmashield_audit_v1"))[1]; return Object.keys(r.split_vials).length === 4 && r.score_table_sha256.length === 64 && r.prev_hash.length === 64; })()'));
await ev('(() => { const r = JSON.parse(localStorage.getItem("pharmashield_audit_v1")); r[0].decision = "Approve as recommended"; localStorage.setItem("pharmashield_audit_v1", JSON.stringify(r)); })()');
await go('#/'); await go('#/split'); await sleep(400);
check('an edited log is detected', (await ev('document.getElementById("audit-box").textContent')).includes('Log has been altered'));
await ev('localStorage.removeItem("pharmashield_audit_v1")');

// documents: contract reader, letters toggle
await go('#/documents');
const contract = readFileSync(pjoin(ROOT, 'layer1_ingestion/data/manual/contracts/eugia_us_llc_msa.txt'), 'utf8');
await ev(`const t = document.getElementById("contract-try"); t.value = ${JSON.stringify(contract)}; t.dispatchEvent(new Event("input", { bubbles: true }))`); await sleep(150);
const out = await ev('document.getElementById("contract-out").textContent');
check('contract reader reads a pasted contract', out.includes('75 days') && out.includes('at least 80%') && out.includes('0.94'), out.slice(0, 200));
await ev('document.getElementById("letters-toggle").click()'); await sleep(150);
check('"show all letters" shows 50', (await ev('document.querySelectorAll("#view table")[0].querySelectorAll("tbody tr").length')) === 50);

// glossary search
await go('#/glossary');
const all = await ev('document.querySelectorAll(".gloss-item").length');
await ev('const g = document.getElementById("gloss-search"); g.value = "OAI"; g.dispatchEvent(new Event("input", { bubbles: true }))'); await sleep(100);
const some = await ev('document.querySelectorAll(".gloss-item").length');
check(`glossary search narrows the list (${all} -> ${some})`, some > 0 && some < all && (await ev('document.getElementById("gloss-out").textContent')).includes('OAI'));
check('search box keeps focus-able state', await ev('document.getElementById("gloss-search").value === "OAI"'));

// theme toggle, deep link
await ev('document.getElementById("theme-toggle").click()');
const t1 = await ev('document.documentElement.getAttribute("data-theme")');
await ev('document.getElementById("theme-toggle").click()');
const t2 = await ev('document.documentElement.getAttribute("data-theme")');
check(`theme toggle switches (${t1} -> ${t2})`, t1 !== t2 && ['dark', 'light'].includes(t1) && ['dark', 'light'].includes(t2));
await go('#/split?mode=Cost Focus&dial=2');
check('links can carry a situation', await ev('PS.state.mode === "Cost Focus" && PS.state.lam === 2'));

// live FDA check (needs the internet)
await go('#/alerts');
await ev('document.getElementById("live-check").click()');
let live = ''; for (let i = 0; i < 40; i++) { await sleep(500); live = await ev('document.getElementById("live-result").textContent'); if (live && !live.includes('Asking')) break; }
check('live FDA check answers: "' + live.slice(0, 110) + '"', live.includes('Right now:'));

const real = problems.filter((p) => !p.includes('favicon'));
check('no JavaScript errors or failed requests (' + real.length + ')', real.length === 0, real.join(' | '));
console.log(`${n - fails.length} of ${n} checks passed`);
ws.close(); chrome.kill();
process.exit(fails.length ? 1 : 0);
