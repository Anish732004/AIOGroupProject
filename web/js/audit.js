/* Approval log (team decision: stored in the viewer's browser for this showcase).
   Each record carries the SHA-256 fingerprint of the previous record. Changing or deleting an earlier record breaks
   every later fingerprint, which verify() detects. A production system would write to the buyer's own database. */
(function (root) {
  'use strict';
  const KEY = 'pharmashield_audit_v1';
  const GENESIS = '0'.repeat(64);

  function canonical(v) {                      // JSON with sorted keys, so the fingerprint is reproducible
    if (v === null || typeof v !== 'object') return JSON.stringify(v);
    if (Array.isArray(v)) return '[' + v.map(canonical).join(',') + ']';
    return '{' + Object.keys(v).sort().map(function (k) { return JSON.stringify(k) + ':' + canonical(v[k]); }).join(',') + '}';
  }
  async function sha256(text) {
    const buf = await root.crypto.subtle.digest('SHA-256', new TextEncoder().encode(text));
    return Array.from(new Uint8Array(buf)).map(function (b) { return b.toString(16).padStart(2, '0'); }).join('');
  }
  function digest(rec) {
    const body = {};
    Object.keys(rec).forEach(function (k) { if (k !== 'record_hash') body[k] = rec[k]; });
    return sha256(canonical(body));
  }
  function read(store) {
    try { return JSON.parse((store || root.localStorage).getItem(KEY) || '[]'); } catch (e) { return []; }
  }
  async function append(entry, store) {
    const rows = read(store);
    const rec = Object.assign({ seq: rows.length + 1, timestamp_utc: new Date().toISOString().slice(0, 19) + 'Z' }, entry,
      { prev_hash: rows.length ? rows[rows.length - 1].record_hash : GENESIS });
    rec.record_hash = await digest(rec);
    rows.push(rec);
    (store || root.localStorage).setItem(KEY, JSON.stringify(rows));
    return rec;
  }
  async function verify(store) {
    const rows = read(store);
    let prev = GENESIS;
    for (const r of rows) {
      if (r.prev_hash !== prev) return { ok: false, message: 'Record ' + r.seq + ': the link to the previous record is broken' };
      if ((await digest(r)) !== r.record_hash) return { ok: false, message: 'Record ' + r.seq + ': contents were changed after signing' };
      prev = r.record_hash;
    }
    return { ok: true, message: rows.length + ' record' + (rows.length === 1 ? '' : 's') + ', chain intact' };
  }
  function toJsonl(store) { return read(store).map(function (r) { return JSON.stringify(r); }).join('\n') + '\n'; }
  root.PSAudit = { KEY: KEY, read: read, append: append, verify: verify, toJsonl: toJsonl };
})(typeof window !== 'undefined' ? window : globalThis);
