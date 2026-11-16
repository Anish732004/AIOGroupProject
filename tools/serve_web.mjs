// Serves web/ locally WITH the headers from vercel.json, so the security policy is tested exactly as deployed.
//   node tools/serve_web.mjs            -> http://127.0.0.1:8766/
import { createServer } from 'node:http';
import { readFile } from 'node:fs/promises';
import { readFileSync } from 'node:fs';
import { join, extname, normalize, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';
const root = join(dirname(fileURLToPath(import.meta.url)), '..');
const web = join(root, 'web'), cfg = JSON.parse(readFileSync(join(root, 'vercel.json'), 'utf8'));
const TYPES = { '.html': 'text/html; charset=utf-8', '.js': 'text/javascript; charset=utf-8', '.css': 'text/css; charset=utf-8', '.json': 'application/json', '.svg': 'image/svg+xml', '.png': 'image/png' };
const PORT = Number(process.env.PORT || 8766);
createServer(async (req, res) => {
  const path = decodeURIComponent(new URL(req.url, 'http://x').pathname);
  const file = normalize(join(web, path === '/' ? 'index.html' : path));
  if (!file.startsWith(web)) { res.writeHead(403).end(); return; }
  for (const rule of cfg.headers) {
    if (new RegExp('^' + rule.source.replace('(.*)', '.*') + '$').test(path)) for (const h of rule.headers) res.setHeader(h.key, h.value);
  }
  try { const body = await readFile(file); res.writeHead(200, { 'Content-Type': TYPES[extname(file)] || 'application/octet-stream' }).end(body); }
  catch { res.writeHead(404).end('not found'); }
}).listen(PORT, '127.0.0.1', () => console.log(`serving web/ with vercel.json headers on http://127.0.0.1:${PORT}/`));
