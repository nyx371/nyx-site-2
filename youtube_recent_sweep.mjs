#!/usr/bin/env node
/**
 * Best-effort YouTube "Recently uploaded" sweep via Chrome DevTools Protocol.
 *
 * YouTube's recent-upload chip is loaded through the web UI, so this uses the
 * existing browser session, clicks the chip, then scrolls slowly and extracts
 * visible video results. It exits cleanly if the browser is unavailable.
 */
import fs from 'node:fs/promises';

const CDP = process.env.STS_CDP_URL || 'http://127.0.0.1:18800';
const OUT = process.env.STS_YOUTUBE_SWEEP_OUT || 'youtube_recent_posts.json';
const SEARCH_URL = process.env.STS_YOUTUBE_SEARCH_URL || 'https://www.youtube.com/results?search_query=%22save+to+spotify%22';
const MAX_POSTS = Number(process.env.STS_YOUTUBE_MAX_POSTS || 40);
const SCROLLS = Number(process.env.STS_YOUTUBE_SCROLLS || 6);
const MIN_DELAY_MS = Number(process.env.STS_YOUTUBE_MIN_DELAY_MS || 1200);
const MAX_DELAY_MS = Number(process.env.STS_YOUTUBE_MAX_DELAY_MS || 2800);

const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));
const jitter = () => MIN_DELAY_MS + Math.floor(Math.random() * Math.max(1, MAX_DELAY_MS - MIN_DELAY_MS));

async function cdpJson(path, options = {}) {
  const res = await fetch(`${CDP}${path}`, options);
  if (!res.ok) throw new Error(`${path}: HTTP ${res.status}`);
  return res.json();
}

async function getTarget() {
  const tabs = await cdpJson('/json/list');
  const existing = tabs.find((t) => /https:\/\/www\.youtube\.com\/results/.test(t.url || '') && t.webSocketDebuggerUrl)
    || tabs.find((t) => /https:\/\/www\.youtube\.com\//.test(t.url || '') && t.webSocketDebuggerUrl)
    || tabs.find((t) => t.type === 'page' && t.webSocketDebuggerUrl);
  if (existing) return existing;
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

const clickRecentExpression = `(() => {
  const chip = Array.from(document.querySelectorAll('yt-chip-cloud-chip-renderer'))
    .find((el) => /Recently uploaded/i.test(el.innerText || ''));
  if (!chip) return { clicked: false, reason: 'chip not found' };
  const target = chip.querySelector('a, button, yt-formatted-string') || chip;
  target.click();
  return { clicked: true };
})()`;

const extractExpression = `(() => {
  const clean = (s) => (s || '').replace(/\s+/g, ' ').trim();
  return Array.from(document.querySelectorAll('ytd-video-renderer')).map((el) => {
    const titleEl = el.querySelector('a#video-title');
    const href = titleEl?.href || '';
    const url = href ? new URL(href, location.href) : null;
    const videoId = url?.searchParams.get('v') || '';
    const metadata = Array.from(el.querySelectorAll('#metadata-line span')).map((span) => clean(span.innerText)).filter(Boolean);
    const description = clean(el.querySelector('#description-text, .metadata-snippet-text, yt-formatted-string.metadata-snippet-text')?.innerText || '');
    return {
      title: clean(titleEl?.textContent || titleEl?.getAttribute('title') || ''),
      url: videoId ? 'https://www.youtube.com/watch?v=' + videoId : '',
      channel: clean(el.querySelector('ytd-channel-name a, #channel-info a')?.textContent || ''),
      views: metadata.find((part) => /view/i.test(part)) || '',
      published: metadata.find((part) => /ago|streamed|premiered/i.test(part)) || '',
      duration: clean(el.querySelector('ytd-thumbnail-overlay-time-status-renderer span, #overlays ytd-thumbnail-overlay-time-status-renderer')?.innerText || ''),
      snippet: description,
      query: 'browser: "save to spotify" recently uploaded',
    };
  }).filter((video) => video.url && video.title);
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
    await client.send('Runtime.evaluate', { expression: clickRecentExpression, returnByValue: true, awaitPromise: true });
    await sleep(jitter());

    const videos = new Map();
    for (let i = 0; i <= SCROLLS; i++) {
      const result = await client.send('Runtime.evaluate', { expression: extractExpression, returnByValue: true, awaitPromise: true });
      for (const video of result?.result?.value || []) {
        if (!videos.has(video.url)) videos.set(video.url, video);
      }
      if (videos.size >= MAX_POSTS) break;
      await client.send('Runtime.evaluate', { expression: `window.scrollBy(0, ${800 + Math.floor(Math.random() * 500)})`, returnByValue: true });
      await sleep(jitter());
    }

    const payload = {
      generated_at: new Date().toISOString(),
      search_url: SEARCH_URL,
      filter: 'Recently uploaded',
      posts: Array.from(videos.values()).slice(0, MAX_POSTS),
    };
    await fs.writeFile(OUT, JSON.stringify(payload, null, 2) + '\n', 'utf8');
    console.log(`Wrote ${payload.posts.length} YouTube posts to ${OUT}`);
  } catch (error) {
    console.error(`YouTube recent sweep skipped: ${error.message}`);
    process.exitCode = 0;
  } finally {
    client?.close();
  }
}

await main();
