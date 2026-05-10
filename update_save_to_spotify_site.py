#!/usr/bin/env python3
"""Generate the Save to Spotify chatter tracker index page."""
from __future__ import annotations

import datetime as dt
import html
import importlib.util
import json
import pathlib
import re
import sys
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

REPO_OWNER = "nyx371"
REPO_NAME = "nyx-site-2"
TRACKED_REPO = "spotify/save-to-spotify"
REDDIT_READER = pathlib.Path("/Users/agent/.openclaw/workspace/tools/reddit_reader.py")

NEWS_QUERY = '"Save to Spotify" Spotify AI podcasts'

CURATED_SOCIAL = [
    {
        "source": "X / @mignano",
        "title": "Spotify product/startup angle; launch post with visible traction (90+ likes when first checked).",
        "url": "https://x.com/mignano/status/2052774235685208080",
        "note": "Good thread to watch for product/strategy discussion.",
    },
    {
        "source": "X / @laytoun",
        "title": "Builder/team launch excitement: agents can create Personal Podcasts and save to Spotify.",
        "url": "https://x.com/laytoun/status/2052440113502629939",
        "note": "Useful for launch context and replies from dev circle.",
    },
    {
        "source": "X / @saen_dev",
        "title": "Developer use-case chatter: AI-generated podcasts saved into Spotify library.",
        "url": "https://x.com/saen_dev/status/2052995476987768920",
        "note": "Shows agent/workflow interpretation.",
    },
    {
        "source": "X / @mediagazer",
        "title": "News syndication mention of Save to Spotify launch.",
        "url": "https://x.com/mediagazer/status/2052398317523378515",
        "note": "Useful for media pickup trail.",
    },
    {
        "source": "Hacker News",
        "title": "Spotify CLI submission; low discussion so far.",
        "url": "https://news.ycombinator.com/item?id=48062612",
        "note": "Initially 3 points / 0 comments; updated stats below when API finds it.",
    },
]

PRIMARY_LINKS = [
    ("Spotify Newsroom", "Save Your Personal Podcast to Spotify and Listen Anywhere", "https://newsroom.spotify.com/2026-05-07/personal-podcasts-launch/"),
    ("GitHub", "spotify/save-to-spotify CLI", "https://github.com/spotify/save-to-spotify"),
    ("The Verge", "OpenClaw and Claude can put your AI-generated podcasts in Spotify", "https://www.theverge.com/entertainment/925916/save-to-spotify-ai-podcasts"),
    ("TechCrunch", "Spotify wants to become the home for AI-generated personal audio", "https://techcrunch.com/2026/05/07/spotify-wants-to-become-the-home-for-ai-generated-personal-audio/"),
    ("9to5Google", "Spotify can now save Personal Podcasts with your calendar and AI agents", "https://9to5google.com/2026/05/07/spotify-personal-podcasts-ai-agents/"),
]


def fetch_json(url: str, timeout: int = 20):
    req = urllib.request.Request(url, headers={"User-Agent": "nyx-save-to-spotify-tracker/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.load(r)


def fetch_bytes(url: str, timeout: int = 20) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": "nyx-save-to-spotify-tracker/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def clean_title(title: str) -> tuple[str, str]:
    # Google News titles are often "Title - Source".
    if " - " in title:
        t, source = title.rsplit(" - ", 1)
        return t.strip(), source.strip()
    return title.strip(), ""


def google_news_items(limit: int = 12):
    q = urllib.parse.quote(NEWS_QUERY)
    url = f"https://news.google.com/rss/search?q={q}&hl=en-US&gl=US&ceid=US:en"
    try:
        root = ET.fromstring(fetch_bytes(url))
    except Exception as e:
        return [], f"Google News RSS failed: {e!r}"
    items = []
    seen = set()
    for item in root.findall(".//item"):
        raw_title = item.findtext("title") or "Untitled"
        title, source = clean_title(raw_title)
        link = item.findtext("link") or ""
        pub = item.findtext("pubDate") or ""
        key = re.sub(r"\W+", " ", title.lower()).strip()
        if key in seen:
            continue
        seen.add(key)
        items.append({"title": title, "source": source, "url": link, "published": pub})
        if len(items) >= limit:
            break
    return items, None


def github_stats():
    try:
        repo = fetch_json(f"https://api.github.com/repos/{TRACKED_REPO}")
        issues = fetch_json(f"https://api.github.com/repos/{TRACKED_REPO}/issues?state=open&per_page=10")
        return {
            "stars": repo.get("stargazers_count"),
            "forks": repo.get("forks_count"),
            "open_issues": repo.get("open_issues_count"),
            "updated_at": repo.get("updated_at"),
            "latest_open": [
                {
                    "title": i.get("title"),
                    "url": i.get("html_url"),
                    "kind": "PR" if "pull_request" in i else "Issue",
                    "created_at": i.get("created_at"),
                }
                for i in issues[:6]
            ],
        }, None
    except Exception as e:
        return None, f"GitHub API failed: {e!r}"



def reddit_hits(limit: int = 8):
    """Fetch Reddit discussion via the local public Reddit reader helper."""
    try:
        if not REDDIT_READER.exists():
            return [], f"Reddit reader missing: {REDDIT_READER}"
        spec = importlib.util.spec_from_file_location("nyx_reddit_reader", REDDIT_READER)
        if spec is None or spec.loader is None:
            return [], f"Could not load Reddit reader: {REDDIT_READER}"
        reddit_reader = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = reddit_reader
        spec.loader.exec_module(reddit_reader)
        result = reddit_reader.fetch_json(
            "/search.json",
            {
                "q": '\"Save to Spotify\"',
                "limit": limit,
                "sort": "new",
                "t": "month",
                "raw_json": 1,
            },
        )
        out = []
        for child in reddit_reader.listing_children(result.data):
            post = child.get("data", {})
            title = reddit_reader.clean(post.get("title"))
            if not title:
                continue
            created = dt.datetime.fromtimestamp(
                post.get("created_utc", 0), dt.timezone.utc
            ).strftime("%Y-%m-%d %H:%M UTC")
            out.append({
                "title": title,
                "url": reddit_reader.post_url(post.get("permalink", "")),
                "subreddit": post.get("subreddit_name_prefixed") or f"r/{post.get('subreddit', '?')}",
                "author": post.get("author") or "?",
                "score": post.get("score", 0),
                "comments": post.get("num_comments", 0),
                "created": created,
                "external_url": post.get("url") if post.get("url") and not str(post.get("url")).startswith("https://www.reddit.com") else "",
            })
        return out, None
    except BaseException as e:
        return [], f"Reddit reader failed: {e!r}"

def hn_hits():
    try:
        q = urllib.parse.quote('"Save to Spotify"')
        data = fetch_json(f"https://hn.algolia.com/api/v1/search?query={q}")
        out = []
        for h in data.get("hits", [])[:8]:
            title = h.get("title") or h.get("story_title") or "Untitled"
            url = h.get("url") or f"https://news.ycombinator.com/item?id={h.get('objectID')}"
            out.append({
                "title": title,
                "url": url,
                "points": h.get("points"),
                "comments": h.get("num_comments"),
                "created_at": h.get("created_at"),
            })
        return out, None
    except Exception as e:
        return [], f"HN API failed: {e!r}"


def esc(s) -> str:
    return html.escape(str(s or ""), quote=True)


def link(url: str, text: str) -> str:
    return f'<a href="{esc(url)}" target="_blank" rel="noopener noreferrer">{esc(text)}</a>'


def render():
    now_utc = dt.datetime.now(dt.timezone.utc)
    now_stockholm = now_utc.astimezone(dt.ZoneInfo("Europe/Stockholm")) if hasattr(dt, "ZoneInfo") else now_utc
    # Python exposes ZoneInfo from zoneinfo, not datetime, fallback below.


def main():
    from zoneinfo import ZoneInfo
    now_utc = dt.datetime.now(dt.timezone.utc)
    now_local = now_utc.astimezone(ZoneInfo("Europe/Stockholm"))

    news, news_err = google_news_items()
    gh, gh_err = github_stats()
    hn, hn_err = hn_hits()
    reddit, reddit_err = reddit_hits()
    errors = [e for e in [news_err, gh_err, hn_err, reddit_err] if e]

    gh_summary = "GitHub stats unavailable"
    if gh:
        gh_summary = f"{gh['stars']} stars · {gh['forks']} forks · {gh['open_issues']} open issues/PRs · updated {esc(gh['updated_at'])}"

    news_html = "\n".join(
        f'<li><strong>{esc(i["source"] or "News")}</strong>: {link(i["url"], i["title"])}<small>{esc(i["published"])}</small></li>'
        for i in news
    ) or "<li>No news items found this run.</li>"

    hn_html = "\n".join(
        f'<li>{link(i["url"], i["title"])} <small>{esc(i.get("points"))} points · {esc(i.get("comments"))} comments</small></li>'
        for i in hn
    ) or "<li>No Hacker News hits found this run.</li>"

    social_html = "\n".join(
        f'<li><strong>{esc(i["source"])}</strong>: {link(i["url"], i["title"])}<small>{esc(i["note"])}</small></li>'
        for i in CURATED_SOCIAL
    )

    reddit_html = "\n".join(
        f'<li><strong>{esc(i["subreddit"])}</strong>: {link(i["url"], i["title"])}<small>u/{esc(i["author"])} · {esc(i["score"])} pts · {esc(i["comments"])} comments · {esc(i["created"])}{(" · external: " + link(i["external_url"], "source")) if i.get("external_url") else ""}</small></li>'
        for i in reddit
    ) or "<li>No Reddit hits found this run.</li>"

    primary_html = "\n".join(
        f'<li><strong>{esc(src)}</strong>: {link(url, title)}</li>'
        for src, title, url in PRIMARY_LINKS
    )

    issues_html = ""
    if gh and gh.get("latest_open"):
        issues_html = "\n".join(
            f'<li><strong>{esc(i["kind"])}</strong>: {link(i["url"], i["title"])} <small>{esc(i["created_at"])}</small></li>'
            for i in gh["latest_open"]
        )
    else:
        issues_html = "<li>No open issue/PR details found.</li>"

    errors_html = ""
    if errors:
        errors_html = "<section class='card warn'><h2>Fetch notes</h2><ul>" + "".join(f"<li>{esc(e)}</li>" for e in errors) + "</ul></section>"

    html_doc = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Save to Spotify chatter tracker</title>
  <style>
    :root {{ color-scheme: dark; --bg:#080812; --card:#121326dd; --text:#f7f3ff; --muted:#bcb5d6; --line:#2c2850; --accent:#1ed760; --violet:#8d7aff; font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; }}
    body {{ margin:0; min-height:100vh; color:var(--text); background: radial-gradient(circle at top left, #263a24, transparent 28rem), radial-gradient(circle at top right, #352060, transparent 32rem), var(--bg); }}
    header {{ padding: clamp(2rem, 6vw, 5rem) clamp(1rem, 5vw, 4rem) 1rem; max-width: 1120px; margin:auto; }}
    h1 {{ font-size: clamp(2.4rem, 8vw, 6rem); letter-spacing: -0.07em; line-height: .92; margin: 0 0 1rem; }}
    .lede {{ max-width: 760px; color: var(--muted); font-size: 1.13rem; line-height: 1.6; }}
    .meta {{ display:flex; flex-wrap:wrap; gap:.7rem; margin-top:1.4rem; }}
    .pill {{ border:1px solid var(--line); background:#ffffff0a; color:var(--muted); border-radius:999px; padding:.45rem .75rem; font-size:.9rem; }}
    main {{ max-width:1120px; margin:auto; padding: 1rem clamp(1rem, 5vw, 4rem) 4rem; display:grid; gap:1rem; }}
    .grid {{ display:grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap:1rem; }}
    .card {{ border:1px solid var(--line); background:var(--card); border-radius:24px; padding:1.2rem; box-shadow: 0 20px 80px #0005; backdrop-filter: blur(16px); }}
    h2 {{ margin:.1rem 0 1rem; font-size:1.1rem; letter-spacing:-.02em; }}
    ul {{ list-style:none; padding:0; margin:0; display:grid; gap:.85rem; }}
    li {{ line-height:1.35; }}
    a {{ color:#d9fbe4; text-decoration-color:#1ed76088; text-underline-offset:3px; }}
    a:hover {{ color:white; text-decoration-color:var(--accent); }}
    small {{ display:block; color:var(--muted); margin-top:.2rem; font-size:.82rem; }}
    .bigstat {{ font-size:1.25rem; color:#d9fbe4; font-weight:700; }}
    .warn {{ border-color:#806b2a; }}
    footer {{ max-width:1120px; margin:auto; color:var(--muted); padding:0 clamp(1rem, 5vw, 4rem) 3rem; font-size:.9rem; }}
  </style>
</head>
<body>
  <header>
    <h1>Save to Spotify chatter tracker</h1>
    <p class="lede">A lightweight hourly snapshot of where people are talking about Spotify’s beta CLI for saving AI-generated personal podcasts into Spotify.</p>
    <div class="meta">
      <span class="pill">Last updated: {esc(now_local.strftime('%Y-%m-%d %H:%M %Z'))}</span>
      <span class="pill">UTC: {esc(now_utc.strftime('%Y-%m-%d %H:%M'))}</span>
      <span class="pill">Auto-refresh target: hourly</span>
    </div>
  </header>
  <main>
    <section class="card">
      <h2>Current read</h2>
      <p class="bigstat">Conversation is mostly press + Spotify/dev X + GitHub, with Reddit now tracked directly via the local reader.</p>
    </section>
    <div class="grid">
      <section class="card"><h2>Primary links</h2><ul>{primary_html}</ul></section>
      <section class="card"><h2>GitHub repo pulse</h2><p class="bigstat">{esc(gh_summary)}</p><ul>{issues_html}</ul></section>
    </div>
    <section class="card"><h2>Latest news pickup</h2><ul>{news_html}</ul></section>
    <div class="grid">
      <section class="card"><h2>Social / community places to watch</h2><ul>{social_html}</ul></section>
      <section class="card"><h2>Hacker News</h2><ul>{hn_html}</ul></section>
    </div>
    <section class="card"><h2>Reddit chatter</h2><ul>{reddit_html}</ul></section>
    {errors_html}
  </main>
  <footer>Generated by Nyx. Sources are fetched from Google News RSS, GitHub API, Hacker News Algolia API, tools/reddit_reader.py, plus curated social links found during the first sweep.</footer>
</body>
</html>
"""
    with open("index.html", "w", encoding="utf-8") as f:
        f.write(html_doc)

if __name__ == "__main__":
    main()
