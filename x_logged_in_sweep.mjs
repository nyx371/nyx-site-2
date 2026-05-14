#!/usr/bin/env node
/**
 * Best-effort logged-in X search sweep via Chrome DevTools Protocol.
 *
 * This uses the already-running OpenClaw-managed browser session, so it can read
 * the logged-in X web UI without the paid X API. It intentionally browses slowly
 * (small randomized pauses between scrolls) to keep load low and reduce UI
 * brittleness. If the browser/session is unavailable, the script exits cleanly
 * and leaves the previous cache in place.
 */
import fs from 'node:fs/promises';

const CDP = process.env.STS_CDP_URL || 'http://127.0.0.1:18800';
const OUT = process.env.STS_X_SWEEP_OUT || 'x_logged_in_posts.json';
const SEARCH_URL = process.env.STS_X_SEARCH_URL || 'https://x.com/search?q=%22save-to-spotify%22&src=typed_query&f=live';
const MAX_POSTS = Number(process.env.STS_X_MAX_POSTS || 60);
const SCROLLS = Number(process.env.STS_X_SCROLLS || 10);
const MIN_DELAY_MS = Number(process.env.STS_X_MIN_DELAY_MS || 1800);
const MAX_DELAY_MS = Number(process.env.STS_X_MAX_DELAY_MS || 4200);

const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));
const jitter = () => MIN_DELAY_MS + Math.floor(Math.random() * Math.max(1, MAX_DELAY_MS - MIN_DELAY_MS));

async function cdpJson(path, options = {}) {
  const res = await fetch(`${CDP}${path}`, options);
  if (!res.ok) throw new Error(`${path}: HTTP ${res.status}`);
  return res.json();
}

async function getTarget() {
  const tabs = await cdpJson('/json/list');
  const existing = tabs.find((t) => /https:\/\/x\.com\/search/.test(t.url || '') && t.webSocketDebuggerUrl)
    || tabs.find((t) => /https:\/\/x\.com\//.test(t.url || '') && t.webSocketDebuggerUrl)
    || tabs.find((t) => t.type === 'page' && t.webSocketDebuggerUrl);
  if (existing) return existing;

  // Chrome's /json/new endpoint is PUT in newer builds.
  return cdpJson(`/json/new?${encodeURIComponent(SEARCH_URL)}`, { method: 'PUT' });
}

function connect(wsUrl) {
  const ws = new WebSocket(wsUrl);
  let nextId = 1;
  const pending = new Map();
  ws.addEventListener('message', (event) => {
    const message = JSON.parse(event.data);
    if (message.id && pending.has(message.id)) {
      const { resolve, reject } = pending.get(message.id);
      pending.delete(message.id);
      message.error ? reject(new Error(JSON.stringify(message.error))) : resolve(message.result);
    }
  });
  return new Promise((resolve, reject) => {
    ws.addEventListener('open', () => {
      resolve({
        send(method, params = {}) {
          const id = nextId++;
          ws.send(JSON.stringify({ id, method, params }));
          return new Promise((resolve, reject) => pending.set(id, { resolve, reject }));
        },
        close() { ws.close(); },
      });
    });
    ws.addEventListener('error', reject);
  });
}

const extractExpression = `(() => {
  const clean = (s) => (s || '').replace(/\\s+/g, ' ').trim();
  const statusHref = (article) => Array.from(article.querySelectorAll('a[href*="/status/"]'))
    .map((a) => a.href)
    .find((href) => /\\/status\\/\\d+/.test(href)) || '';
  const canonical = (href) => {
    const match = href.match(/^https?:\\/\\/(?:mobile\\.)?(?:twitter|x)\\.com\\/([^/?#]+)\\/status\\/(\\d+)/);
    return match ? 'https://x.com/' + match[1] + '/status/' + match[2] : '';
  };
  const metricText = (article) => Array.from(article.querySelectorAll('[aria-label]'))
    .map((el) => el.getAttribute('aria-label') || '')
    .find((label) => /(?:repl|repost|quote|like|bookmark|view)/i.test(label) && /view/i.test(label)) || '';
  const titleFromText = (text) => {
    const lines = text.split('\\n').map((line) => line.trim()).filter(Boolean);
    const atIndex = lines.findIndex((line) => /^@/.test(line));
    let body = lines.slice(Math.max(0, atIndex + 2)).filter((line) => !/^·$/.test(line) && !/^Show more$/i.test(line));
    body = body.filter((line) => !/^\\d+(?:\\.\\d+)?[KkMm]?$/.test(line));
    body = body.filter((line) => !/^(?:\\d+[smhdw]|May \\d{1,2}|Jan \\d{1,2}|Feb \\d{1,2}|Mar \\d{1,2}|Apr \\d{1,2}|Jun \\d{1,2}|Jul \\d{1,2}|Aug \\d{1,2}|Sep \\d{1,2}|Oct \\d{1,2}|Nov \\d{1,2}|Dec \\d{1,2})$/i.test(line));
    return clean(body.slice(0, 6).join(' ')).slice(0, 240) || clean(text).slice(0, 240);
  };
  return Array.from(document.querySelectorAll('article')).map((article) => {
    const url = canonical(statusHref(article));
    const text = article.innerText || '';
    const handle = (url.match(/x\\.com\\/([^/]+)\\/status/) || [])[1] || '';
    return {
      source: handle ? 'X / @' + handle : 'X',
      title: titleFromText(text),
      url,
      published_at: article.querySelector('time')?.getAttribute('datetime') || '',
      metrics: metricText(article).replace(/, /g, ' · '),
      note: 'Found via logged-in X live search for save-to-spotify.',
    };
  }).filter((post) => post.url);
})()`;

async function main() {
  let client;
  try {
    const target = await getTarget();
    if (!target?.webSocketDebuggerUrl) throw new Error('No CDP page target with webSocketDebuggerUrl');
    client = await connect(target.webSocketDebuggerUrl);
    await client.send('Page.enable');
    await client.send('Runtime.enable');
    await client.send('Page.navigate', { url: SEARCH_URL });
    await sleep(jitter());

    const posts = new Map();
    for (let i = 0; i <= SCROLLS; i++) {
      const result = await client.send('Runtime.evaluate', { expression: extractExpression, returnByValue: true, awaitPromise: true });
      for (const post of result?.result?.value || []) {
        if (!posts.has(post.url)) posts.set(post.url, post);
      }
      if (posts.size >= MAX_POSTS) break;
      await client.send('Runtime.evaluate', { expression: `window.scrollBy(0, ${700 + Math.floor(Math.random() * 500)})`, returnByValue: true });
      await sleep(jitter());
    }

    const payload = {
      generated_at: new Date().toISOString(),
      search_url: SEARCH_URL,
      posts: Array.from(posts.values()).slice(0, MAX_POSTS),
    };
    await fs.writeFile(OUT, JSON.stringify(payload, null, 2) + '\n', 'utf8');
    console.log(`Wrote ${payload.posts.length} X posts to ${OUT}`);
  } catch (error) {
    console.error(`X logged-in sweep skipped: ${error.message}`);
    process.exitCode = 0;
  } finally {
    client?.close();
  }
}

await main();
