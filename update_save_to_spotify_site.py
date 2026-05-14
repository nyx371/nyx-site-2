#!/usr/bin/env python3
"""Generate the Save to Spotify chatter tracker index page."""
from __future__ import annotations

import datetime as dt
import email.utils
import hashlib
import html
import importlib.util
import json
import pathlib
import re
import subprocess
import sys
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

REPO_OWNER = "nyx371"
REPO_NAME = "sts-snapshot"
TRACKED_REPO = "spotify/save-to-spotify"
REDDIT_READER = pathlib.Path("/Users/agent/.openclaw/workspace/tools/reddit_reader.py")
SEEN_STATE_PATH = pathlib.Path("seen_save_to_spotify_posts.json")
REMOVE_LIST_PATH = pathlib.Path("remove_list.txt")
X_LOGGED_IN_POSTS_PATH = pathlib.Path("x_logged_in_posts.json")
X_LOGGED_IN_SWEEP_SCRIPT = pathlib.Path("x_logged_in_sweep.mjs")
YOUTUBE_RECENT_POSTS_PATH = pathlib.Path("youtube_recent_posts.json")
YOUTUBE_RECENT_SWEEP_SCRIPT = pathlib.Path("youtube_recent_sweep.mjs")
MIN_MEDIA_DATE = dt.datetime(2026, 5, 7, tzinfo=dt.timezone.utc)

SEARCH_TERMS = [
    '"Save to Spotify"',
    '"save-to-spotify"',
]
NEWS_QUERY = '("Save to Spotify" OR "save-to-spotify") Spotify AI podcasts'
YOUTUBE_QUERIES = [
    '"save to spotify"',
    '"save-to-spotify"',
    '"Save AI Podcasts to Spotify"',
    '"Save to Spotify" Spotify AI podcast',
    '"Save to Spotify" Claude Code OpenClaw Codex',
    'OpenClaw Claude Spotify podcast',
    '"Spotify Personal Podcasts" "AI agents"',
]
X_SEARCH_QUERIES = [
    'site:x.com "Save to Spotify" Spotify',
    'site:x.com "save-to-spotify"',
    'site:x.com "Personal Podcasts" Spotify',
    'site:x.com "personal-podcasts-launch"',
    'site:x.com "github.com/spotify/save-to-spotify"',
    'site:x.com "newsroom.spotify.com/2026/05/07/personal-podcasts-launch"',
    'site:twitter.com "Save to Spotify" Spotify',
    'site:twitter.com "save-to-spotify"',
]
CLAWHUB_URL = "https://clawhub.ai/spotify/save-to-spotify"

CURATED_SOCIAL = [
    {
        "source": "X / @ArtinBogdanov",
        "title": "Launching sun-to-spotify after seeing Save to Spotify: a Spotify skill for private podcasts.",
        "url": "https://x.com/ArtinBogdanov/status/2054970126684864841",
        "note": "Found via logged-in X live search for save-to-spotify.",
        "metrics": "3 replies · 2 reposts · 14 likes · 3 bookmarks · 178 views",
    },
    {
        "source": "X / @InnerGNas",
        "title": "Save to Spotify GitHub share: command-line tool for saving audio content to Spotify.",
        "url": "https://x.com/InnerGNas/status/2054619124391682310",
        "note": "Found via logged-in X live search for save-to-spotify.",
        "metrics": "2 likes · 35 views",
    },
    {
        "source": "X / @princedoesai",
        "title": "Spotify launched Personal Podcasts: Save to Spotify for desktop agents like OpenClaw, Claude Code, and Codex.",
        "url": "https://x.com/princedoesai/status/2054169176961646615",
        "note": "Found via logged-in X live search for save-to-spotify.",
        "metrics": "143 views",
    },
    {
        "source": "X / @richeholmes",
        "title": "Spotify released a command-line interface tool called Save to Spotify.",
        "url": "https://x.com/richeholmes/status/2054149614601711777",
        "note": "Found via logged-in X live search for save-to-spotify.",
        "metrics": "1 like · 117 views",
    },
    {
        "source": "X / @DriftNote_",
        "title": "Spotify is testing Save to Spotify for AI tools to create personal podcasts.",
        "url": "https://x.com/DriftNote_/status/2054138230103228837",
        "note": "Found via logged-in X live search for save-to-spotify.",
        "metrics": "1 reply · 1 repost · 47 views",
    },
    {
        "source": "X / @shela_tw",
        "title": "Hermes workflow uses Spotify’s Save to Spotify tool as the publishing layer.",
        "url": "https://x.com/shela_tw/status/2053833151047205061",
        "note": "Found via logged-in X live search for save-to-spotify.",
        "metrics": "1 reply · 16 likes · 354 views",
    },
    {
        "source": "X / @Medvidekpu",
        "title": "Newsletter mention including Save to Spotify.",
        "url": "https://x.com/Medvidekpu/status/2053796874012819502",
        "note": "Found via logged-in X live search for save-to-spotify.",
        "metrics": "341 views",
    },
    {
        "source": "X / @YEB_TO",
        "title": "Spotify launches Save to Spotify beta tool that turns AI agents into personal podcast producers.",
        "url": "https://x.com/YEB_TO/status/2053788452429131805",
        "note": "Found via logged-in X live search for save-to-spotify.",
        "metrics": "1 like · 60 views",
    },
    {
        "source": "X / @365tipu",
        "title": "Newsletter mention including Save to Spotify.",
        "url": "https://x.com/365tipu/status/2053771865882034180",
        "note": "Found via logged-in X live search for save-to-spotify.",
        "metrics": "208 views",
    },
    {
        "source": "X / @AIsyuuekika",
        "title": "Japanese mention: Spotify announced Save to Spotify voice content management tool.",
        "url": "https://x.com/AIsyuuekika/status/2053333526117032060",
        "note": "Found via logged-in X live search for save-to-spotify.",
        "metrics": "63 views",
    },
    {
        "source": "X / @ChekosWH",
        "title": "Using ElevenLabs and save-to-spotify for weekly audio summaries.",
        "url": "https://x.com/ChekosWH/status/2053191057874235655",
        "note": "Found via logged-in X live search for save-to-spotify.",
        "metrics": "3 likes · 1 bookmark · 148 views",
    },
    {
        "source": "X / @brainpercent",
        "title": "Hebrew post: Save to Spotify lets AI agents save podcasts directly to a user library.",
        "url": "https://x.com/brainpercent/status/2053134284643250187",
        "note": "Found via logged-in X live search for save-to-spotify.",
        "metrics": "1 reply · 41 views",
    },
    {
        "source": "X / @sozo_museum",
        "title": "Japanese media share: Spotify releases CLI tool Save to Spotify for AI-generated audio content.",
        "url": "https://x.com/sozo_museum/status/2053106199810453943",
        "note": "Found via logged-in X live search for save-to-spotify.",
        "metrics": "2 likes · 2 bookmarks · 151 views",
    },
    {
        "source": "X / @BlogNT",
        "title": "French mention: Spotify launches Save to Spotify for personal podcasts.",
        "url": "https://x.com/BlogNT/status/2053035248657510782",
        "note": "Found via logged-in X live search for save-to-spotify.",
        "metrics": "2 likes · 95 views",
    },
    {
        "source": "X / @connordavis_ai",
        "title": "Save to Spotify makes Claude Code a podcast distribution channel.",
        "url": "https://x.com/connordavis_ai/status/2052948272638283850",
        "note": "Found via logged-in X live search for save-to-spotify.",
        "metrics": "1 repost · 2 bookmarks · 177 views",
    },
    {
        "source": "X / @ArtinBogdanov",
        "title": "Reply to GustavS: Sun pairs with Save-to-Spotify CLI for higher-quality personal podcasts.",
        "url": "https://x.com/ArtinBogdanov/status/2052908832314233193",
        "note": "Found via logged-in X live search for save-to-spotify.",
        "metrics": "2 replies · 1 repost · 9 likes · 3 bookmarks · 552 views",
    },
    {
        "source": "X / @Intellectualins",
        "title": "Spotify has launched a new command-line tool called “Save to Spotify”.",
        "url": "https://x.com/Intellectualins/status/2053407194322813179",
        "note": "Found via Google site:x.com sweep for Save to Spotify.",
        "metrics": "70 views",
    },
    {
        "source": "X / @kallepersson",
        "title": "Launch post: proud of launching Save to Spotify together with the team.",
        "url": "https://x.com/kallepersson/status/2052439008316096798",
        "note": "Found via Google site:x.com sweep for Save to Spotify.",
        "metrics": "2 replies · 2 reposts · 8 likes · 470 views",
    },
    {
        "source": "X / @laytoun",
        "title": "Save to Spotify works seamlessly with Codex, Claude Code, or any agent.",
        "url": "https://x.com/laytoun/status/2054623407975620937",
        "note": "Found via Google site:x.com sweep for Save to Spotify; refreshed via logged-in X live search.",
        "metrics": "6 likes · 1 bookmark · 810 views",
    },
    {
        "source": "X / @Techmeme",
        "title": "Techmeme: Spotify launches Save to Spotify for AI-generated podcasts.",
        "url": "https://x.com/Techmeme/status/2052398586709881106",
        "note": "Found via Google site:x.com sweep for Save to Spotify.",
        "metrics": "5 likes · 3 bookmarks · 1,811 views",
    },
    {
        "source": "X / @GustavS",
        "title": "Spotify launch/share post linking the save-to-spotify GitHub repo.",
        "url": "https://x.com/GustavS/status/2052437581946618009",
        "note": "Found via Google site:x.com sweep for Save to Spotify.",
        "metrics": "1 reply · 2 reposts · 22 likes · 35 bookmarks · 2,736 views",
    },
    {
        "source": "X / @mignano",
        "title": "Spotify product/startup angle; launch post with visible traction (90+ likes when first checked).",
        "url": "https://x.com/mignano/status/2052774235685208080",
        "note": "Good thread to watch for product/strategy discussion.",
        "metrics": "7 replies · 2 reposts · 103 likes · 72 bookmarks · 32,997 views",
    },
    {
        "source": "X / @laytoun",
        "title": "Builder/team launch excitement: agents can create Personal Podcasts and save to Spotify.",
        "url": "https://x.com/laytoun/status/2052440113502629939",
        "note": "Useful for launch context and replies from dev circle.",
        "metrics": "3 replies · 17 likes · 3 bookmarks · 1,091 views",
    },
    {
        "source": "X / @saen_dev",
        "title": "Developer use-case chatter: AI-generated podcasts saved into Spotify library.",
        "url": "https://x.com/saen_dev/status/2052995476987768920",
        "note": "Shows agent/workflow interpretation.",
        "metrics": "31 views",
    },
    {
        "source": "X / @mediagazer",
        "title": "News syndication mention of Save to Spotify launch.",
        "url": "https://x.com/mediagazer/status/2052398317523378515",
        "note": "Useful for media pickup trail.",
        "metrics": "1 like · 365 views",
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


def _strip_html(text: str) -> str:
    text = re.sub(r"<!--.*?-->", "", text, flags=re.S)
    text = re.sub(r"<[^>]+>", " ", text)
    return html.unescape(re.sub(r"\s+", " ", text).strip())


def clawhub_stats():
    """Fetch public ClawHub stats from the skill detail page.

    ClawHub changed from a hero stats row to sidebar/actions markup. Prefer the
    server-rendered data blob, then fall back to visible sidebar/action labels.
    """
    try:
        doc = fetch_bytes(CLAWHUB_URL).decode("utf-8", errors="replace")
        title = _strip_html((re.search(r"<h1[^>]*>(.*?)</h1>", doc, re.S) or [None, "Save To Spotify"])[1])
        stats = {"url": CLAWHUB_URL, "title": title}

        data_match = re.search(r"stats:\$R\[\d+\]=\{([^}]+)\}", doc)
        if data_match:
            for key, value in re.findall(r"(stars|downloads|versions):([0-9]+)", data_match.group(1)):
                stats[key] = value

        version_match = re.search(r"version=([0-9][^&\"]+)", doc)
        if not version_match:
            version_match = re.search(r'<dt class="sidebar-metadata-label">Current version</dt>\s*<dd class="sidebar-metadata-value">v?([^<]+)</dd>', doc, re.S)
        if version_match:
            stats["version"] = html.unescape(version_match.group(1)).strip()

        license_match = re.search(r'<dt class="sidebar-metadata-label">License</dt>\s*<dd class="sidebar-metadata-value">([^<]+)</dd>', doc, re.S)
        if license_match:
            stats["license"] = _strip_html(license_match.group(1))

        updated_match = re.search(r'<dt class="sidebar-metadata-label">Last updated</dt>\s*<dd class="sidebar-metadata-value">([^<]+)</dd>', doc, re.S)
        if updated_match:
            stats["updated"] = _strip_html(updated_match.group(1))

        # Fallbacks for values shown in action buttons if the data blob moves.
        if "stars" not in stats:
            star_match = re.search(r'aria-label="Star skill"[^>]*>.*?<span class="skill-action-count">([^<]+)</span>', doc, re.S)
            if star_match:
                stats["stars"] = _strip_html(star_match.group(1))
        if "downloads" not in stats:
            download_match = re.search(r'Download zip</a>.*?<span class="skill-action-count">([^<]+)</span>', doc, re.S)
            if download_match:
                stats["downloads"] = _strip_html(download_match.group(1))
        if "versions" not in stats:
            versions_match = re.search(r'<dt class="sidebar-metadata-label">Versions</dt>\s*<dd class="sidebar-metadata-value">([^<]+)</dd>', doc, re.S)
            if versions_match:
                stats["versions"] = _strip_html(versions_match.group(1))

        required = {"stars", "downloads", "versions"}
        if not required.intersection(stats):
            return None, "ClawHub stats not found in current page markup"
        return stats, None
    except Exception as e:
        return None, f"ClawHub stats fetch failed: {e!r}"


def reddit_hits(limit: int = 100):
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
        out = []
        seen_urls = set()
        for term in SEARCH_TERMS:
            params = {
                "q": term,
                "limit": limit,
                "sort": "new",
                "t": "month",
                "raw_json": 1,
            }
            delays = [2, 5, 10]
            last_error = None
            for attempt in range(len(delays) + 1):
                try:
                    result = reddit_reader.fetch_json("/search.json", params)
                    break
                except BaseException as e:
                    last_error = e
                    if "HTTP 403 from Reddit" not in str(e) or attempt >= len(delays):
                        raise
                    time.sleep(delays[attempt])
            else:
                raise last_error or RuntimeError("Reddit reader failed without an error")
            for child in reddit_reader.listing_children(result.data):
                post = child.get("data", {})
                title = reddit_reader.clean(post.get("title"))
                if not title:
                    continue
                url = reddit_reader.post_url(post.get("permalink", ""))
                if url in seen_urls:
                    continue
                seen_urls.add(url)
                created_dt = dt.datetime.fromtimestamp(
                    post.get("created_utc", 0), dt.timezone.utc
                )
                created = created_dt.strftime("%Y-%m-%d %H:%M UTC")
                out.append({
                    "title": title,
                    "url": url,
                    "subreddit": post.get("subreddit_name_prefixed") or f"r/{post.get('subreddit', '?')}",
                    "author": post.get("author") or "?",
                    "score": post.get("score", 0),
                    "comments": post.get("num_comments", 0),
                    "created": created,
                    "created_at": created_dt.isoformat(),
                    "external_url": post.get("url") if post.get("url") and not str(post.get("url")).startswith("https://www.reddit.com") else "",
                    "query": term,
                })
                if len(out) >= limit:
                    return out, None
        return out, None
    except BaseException as e:
        return [], f"Reddit reader failed: {e!r}"


def _strip_tags(value: str) -> str:
    value = re.sub(r"(?is)<(script|style).*?>.*?</\\1>", " ", value or "")
    value = re.sub(r"<[^>]+>", " ", value)
    return re.sub(r"\\s+", " ", html.unescape(value)).strip()


def _normalize_search_result_url(url: str) -> str:
    url = html.unescape(str(url or "").strip())
    if not url:
        return ""
    parsed = urllib.parse.urlparse(url)
    if parsed.netloc.endswith("duckduckgo.com") and parsed.path.startswith("/l/"):
        qs = urllib.parse.parse_qs(parsed.query)
        if qs.get("uddg"):
            return qs["uddg"][0]
    if parsed.netloc.endswith("google.com") and parsed.path == "/url":
        qs = urllib.parse.parse_qs(parsed.query)
        if qs.get("q"):
            return qs["q"][0]
    if parsed.netloc.endswith("bing.com") and parsed.path.startswith("/ck/a"):
        qs = urllib.parse.parse_qs(parsed.query)
        for key in ("u", "r"):
            if qs.get(key):
                candidate = qs[key][0]
                # Bing sometimes base64-url encodes target URLs with a leading "a1".
                if candidate.startswith("a1"):
                    try:
                        import base64
                        padded = candidate[2:] + "=" * (-len(candidate[2:]) % 4)
                        return base64.urlsafe_b64decode(padded).decode("utf-8", errors="replace")
                    except Exception:
                        pass
                return candidate
    return url


def _canonical_x_status_url(url: str) -> str:
    url = _normalize_search_result_url(url)
    match = re.search(r"https?://(?:mobile\\.)?(?:twitter|x)\\.com/([^/?#]+)/status/(\\d+)", url)
    if not match:
        return ""
    handle, status_id = match.groups()
    return f"https://x.com/{handle}/status/{status_id}"


def _first_metric(text: str, label: str) -> str:
    match = re.search(rf"(?<!\w)([\d][\d,\.]*\s*[KkMm]?\+?)\s+{label}s?\b", text or "", re.I)
    if not match:
        return ""
    value = re.sub(r"\s+", "", match.group(1))
    suffix = label if value in {"1", "1.0"} else f"{label}s"
    return f"{value} {suffix}"


def extract_social_metrics(text: str) -> str:
    text = _strip_tags(text)
    metrics = []
    for label in ("reply", "repost", "quote", "like", "bookmark", "view"):
        metric = _first_metric(text, label)
        if metric:
            metrics.append(metric)
    return " · ".join(dict.fromkeys(metrics))


def metric_label(value: str, singular: str, plural: str | None = None) -> str:
    plural = plural or f"{singular}s"
    normalized = str(value or "").strip().replace(",", "")
    return singular if normalized in {"1", "1.0"} else plural


def x_search_hits(limit: int = 80):
    """Best-effort X discovery using public search-engine result pages.

    This is intentionally not described as complete: search engines may rank, omit,
    de-index, challenge, or lag X content. Curated X links below remain as overrides.
    """
    out = []
    seen_urls = set()
    errors = []
    headers = {
        "User-Agent": "Mozilla/5.0 (compatible; nyx-save-to-spotify-tracker/1.0)",
        "Accept-Language": "en-US,en;q=0.9",
    }

    def add_hit(url: str, title: str, snippet: str, engine: str, query: str):
        status_url = _canonical_x_status_url(url)
        if not status_url or status_url in seen_urls:
            return
        seen_urls.add(status_url)
        source = "X / @" + urllib.parse.urlparse(status_url).path.strip("/").split("/", 1)[0]
        title = _strip_tags(title) or snippet or status_url
        snippet = _strip_tags(snippet)
        metrics = extract_social_metrics(f"{title} {snippet}")
        published_at = x_status_datetime(status_url)
        out.append({
            "source": source,
            "title": title,
            "url": status_url,
            "note": f"Search sweep: {engine}; query: {query}" + (f" · {snippet}" if snippet and snippet != title else ""),
            "metrics": metrics,
            "published_at": published_at.isoformat() if published_at else None,
            "query": query,
            "engine": engine,
        })

    for query in X_SEARCH_QUERIES:
        q = urllib.parse.quote_plus(query)
        search_pages = [
            ("Google", f"https://www.google.com/search?q={q}"),
            ("Bing", f"https://www.bing.com/search?q={q}"),
            ("DuckDuckGo", f"https://duckduckgo.com/html/?q={q}"),
            ("Yahoo", f"https://search.yahoo.com/search?p={q}"),
        ]
        for engine, search_url in search_pages:
            try:
                req = urllib.request.Request(search_url, headers=headers)
                with urllib.request.urlopen(req, timeout=20) as r:
                    doc = r.read().decode("utf-8", errors="replace")
                if "duckduckgo.com/anomaly" in doc or "challenge-form" in doc:
                    errors.append(f"{engine}: bot-detection challenge for {query}")
                    continue
                before = len(out)
                # Generic pass: any visible status URL in the result page.
                for m in re.finditer(r"https?://(?:mobile\\.)?(?:twitter|x)\\.com/[^\\s'\"<>]+/status/\\d+[^\\s'\"<>]*", doc):
                    add_hit(m.group(0), "", "", engine, query)
                # DuckDuckGo result blocks.
                for m in re.finditer(r'(?is)<a[^>]+class="[^"]*result__a[^"]*"[^>]+href="([^"]+)"[^>]*>(.*?)</a>(.*?)(?=<a[^>]+class="[^"]*result__a|</body>)', doc):
                    add_hit(m.group(1), m.group(2), m.group(3), engine, query)
                # Bing/Yahoo/Google-ish anchors. Keep it conservative: only x/twitter status targets survive.
                for m in re.finditer(r'(?is)<a[^>]+href="([^"]+)"[^>]*>(.*?)</a>', doc):
                    add_hit(m.group(1), m.group(2), "", engine, query)
                if len(out) == before and engine in {"Google", "Bing", "Yahoo"}:
                    # Not an error by itself, but useful when auditing coverage.
                    pass
                if len(out) >= limit:
                    return out[:limit], ("; ".join(dict.fromkeys(errors)) if errors else None)
                time.sleep(0.2)
            except Exception as e:
                errors.append(f"{engine}: {query}: {e!r}")
    return out[:limit], ("; ".join(dict.fromkeys(errors)) if errors else None)


def _extract_yt_initial_data(doc: str):
    marker = "var ytInitialData = "
    start = doc.find(marker)
    if start == -1:
        marker = "ytInitialData = "
        start = doc.find(marker)
    if start == -1:
        return None
    start = doc.find("{", start)
    if start == -1:
        return None
    depth = 0
    in_string = False
    escape = False
    for idx in range(start, len(doc)):
        ch = doc[idx]
        if in_string:
            if escape:
                escape = False
            elif ch == "\\":
                escape = True
            elif ch == '"':
                in_string = False
            continue
        if ch == '"':
            in_string = True
        elif ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return json.loads(doc[start:idx + 1])
    return None


def _yt_text(value) -> str:
    if not value:
        return ""
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        if value.get("simpleText"):
            return str(value["simpleText"])
        runs = value.get("runs") or []
        return "".join(str(run.get("text") or "") for run in runs)
    return ""


def _walk_dicts(value):
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from _walk_dicts(child)
    elif isinstance(value, list):
        for child in value:
            yield from _walk_dicts(child)


def _yt_snippet(video: dict) -> str:
    parts = [
        _yt_text(video.get("descriptionSnippet")),
        _yt_text(video.get("detailedMetadataSnippets")),
    ]
    for snippet in video.get("detailedMetadataSnippets") or []:
        parts.append(_yt_text(snippet.get("snippetText")))
    return " ".join(part for part in parts if part)


def is_relevant_youtube_hit(item: dict) -> bool:
    text = " ".join(str(item.get(k) or "") for k in ("title", "channel", "snippet")).lower()
    text = re.sub(r"https?://\S+", " ", text)
    text = re.sub(r"\s+", " ", text)
    if re.search(r"\bpre(?:-|\s*)save\b|presave", text):
        return False
    has_product = bool(re.search(r"\bsave(?:-|\s+)to(?:-|\s+)spotify\b|\bsave-to-spotify\b", text))
    context_terms = ("ai", "agent", "podcast", "personal", "claude", "openclaw", "codex", "github", "cli", "command line", "command-line", "automation", "automate")
    has_context = any(term in text for term in context_terms)
    has_save_spotify_context = "save" in text and "spotify" in text and has_context
    has_personal_podcast = "spotify" in text and bool(re.search(r"\bpersonal podcasts?\b", text))
    return (has_product and has_context) or has_save_spotify_context or has_personal_podcast


def youtube_hits(limit: int = 100):
    """Fetch recently uploaded, product-relevant YouTube search results (no API key)."""
    out = []
    seen_video_ids = set()
    errors = []
    headers = {
        "User-Agent": "Mozilla/5.0 (compatible; nyx-save-to-spotify-tracker/1.0)",
        "Accept-Language": "en-US,en;q=0.9",
    }

    for query in YOUTUBE_QUERIES:
        q = urllib.parse.quote_plus(query)
        search_urls = [
            # sp=CAI%253D is YouTube's "Recently uploaded" search filter.
            f"https://www.youtube.com/results?search_query={q}&sp=CAI%253D",
        ]
        for url in search_urls:
            try:
                req = urllib.request.Request(url, headers=headers)
                with urllib.request.urlopen(req, timeout=20) as r:
                    doc = r.read().decode("utf-8", errors="replace")
                data = _extract_yt_initial_data(doc)
                if not data:
                    errors.append(f"{query}: markup did not include ytInitialData for {url}")
                    continue
                for node in _walk_dicts(data):
                    video = node.get("videoRenderer") if isinstance(node, dict) else None
                    if not video:
                        continue
                    video_id = video.get("videoId")
                    title = _yt_text(video.get("title")) or "Untitled video"
                    if not video_id or video_id in seen_video_ids:
                        continue
                    item = {
                        "title": title,
                        "url": f"https://www.youtube.com/watch?v={video_id}",
                        "channel": _yt_text(video.get("ownerText")) or _yt_text(video.get("longBylineText")) or "YouTube",
                        "published": _yt_text(video.get("publishedTimeText")),
                        "views": _yt_text(video.get("viewCountText")),
                        "duration": _yt_text(video.get("lengthText")),
                        "snippet": _yt_snippet(video),
                        "query": query,
                    }
                    if not is_relevant_youtube_hit(item):
                        continue
                    seen_video_ids.add(video_id)
                    out.append(item)
                    if len(out) >= limit:
                        return out, ("; ".join(errors) if errors else None)
            except Exception as e:
                errors.append(f"{query} via {url}: {e!r}")

    return out, ("; ".join(errors) if errors else None)


def _extract_youtube_like_count(doc: str) -> str:
    # Watch pages usually expose the public like button label in ytInitialData.
    # The default button title is the current count; the toggled title is count+1.
    patterns = [
        r'"defaultButtonViewModel"\s*:\s*\{\s*"buttonViewModel"\s*:\s*\{[^{}]*"iconName"\s*:\s*"LIKE"[^{}]*"title"\s*:\s*"([^"]+)"',
        r'"accessibilityText"\s*:\s*"like this video along with ([^"]+?) other people"',
    ]
    for pattern in patterns:
        match = re.search(pattern, doc, re.I)
        if match:
            value = html.unescape(match.group(1)).strip()
            if value and value.lower() not in {"like", "likes"}:
                return value
    return ""


def enrich_youtube_metrics(videos: list[dict], limit: int = 30):
    """Fetch watch pages for best-effort like counts; search results already carry views."""
    errors = []
    headers = {
        "User-Agent": "Mozilla/5.0 (compatible; nyx-save-to-spotify-tracker/1.0)",
        "Accept-Language": "en-US,en;q=0.9",
    }
    for video in videos[:limit]:
        metrics = []
        if video.get("views"):
            metrics.append(video["views"])
        try:
            req = urllib.request.Request(video.get("url", ""), headers=headers)
            with urllib.request.urlopen(req, timeout=15) as r:
                doc = r.read().decode("utf-8", errors="replace")
            likes = _extract_youtube_like_count(doc)
            if likes:
                metrics.append(f"{likes} {metric_label(likes, 'like')}")
            time.sleep(0.1)
        except Exception as e:
            errors.append(f"{video.get('url')}: {e!r}")
        video["metrics"] = " · ".join(dict.fromkeys(metrics))
    return "; ".join(errors[:5]) + ("; …" if len(errors) > 5 else "") if errors else None


def hn_hits():
    try:
        out = []
        seen_urls = set()
        for term in SEARCH_TERMS:
            q = urllib.parse.quote(term)
            data = fetch_json(f"https://hn.algolia.com/api/v1/search?query={q}")
            for h in data.get("hits", []):
                title = h.get("title") or h.get("story_title") or "Untitled"
                url = h.get("url") or f"https://news.ycombinator.com/item?id={h.get('objectID')}"
                if url in seen_urls:
                    continue
                seen_urls.add(url)
                out.append({
                    "title": title,
                    "url": url,
                    "points": h.get("points"),
                    "comments": h.get("num_comments"),
                    "created_at": h.get("created_at"),
                    "query": term,
                })
                if len(out) >= 100:
                    return out, None
        return out, None
    except Exception as e:
        return [], f"HN API failed: {e!r}"


def esc(s) -> str:
    return html.escape(str(s or ""), quote=True)


def link(url: str, text: str) -> str:
    return f'<a href="{esc(url)}" target="_blank" rel="noopener noreferrer">{esc(text)}</a>'


def parse_datetime_value(value: str, now_utc: dt.datetime | None = None):
    if not value:
        return None
    text = str(value).strip()
    if not text:
        return None

    try:
        parsed = dt.datetime.fromisoformat(text.replace("Z", "+00:00"))
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=dt.timezone.utc)
    except Exception:
        pass

    try:
        parsed = email.utils.parsedate_to_datetime(text)
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=dt.timezone.utc)
    except Exception:
        pass

    for fmt in ("%Y-%m-%d %H:%M UTC", "%Y-%m-%d"):
        try:
            parsed = dt.datetime.strptime(text, fmt)
            return parsed.replace(tzinfo=dt.timezone.utc)
        except Exception:
            pass

    if now_utc:
        m = re.match(r"^(?:about\s+)?(\d+)\s+(second|minute|hour|day|week|month|year)s?\s+ago$", text, re.I)
        if m:
            n = int(m.group(1))
            unit = m.group(2).lower()
            days_per = {"second": 1 / 86400, "minute": 1 / 1440, "hour": 1 / 24, "day": 1, "week": 7, "month": 30, "year": 365}[unit]
            return now_utc - dt.timedelta(days=n * days_per)
        m = re.match(r"^(\d+)\s*(s|m|h|d|w|mo|y)\s+ago$", text, re.I)
        if m:
            n = int(m.group(1))
            unit = m.group(2).lower()
            days_per = {"s": 1 / 86400, "m": 1 / 1440, "h": 1 / 24, "d": 1, "w": 7, "mo": 30, "y": 365}[unit]
            return now_utc - dt.timedelta(days=n * days_per)
    return None


def datetime_iso(value: str, now_utc: dt.datetime | None = None) -> str:
    parsed = parse_datetime_value(value, now_utc)
    return parsed.astimezone(dt.timezone.utc).isoformat() if parsed else ""


def relative_time_text(value: str, now_utc: dt.datetime) -> str:
    parsed = parse_datetime_value(value, now_utc)
    if not parsed:
        return str(value or "")
    parsed = parsed.astimezone(dt.timezone.utc)
    delta = now_utc - parsed
    seconds = int(delta.total_seconds())
    if seconds < 0:
        seconds = abs(seconds)
        suffix = "from now"
    else:
        suffix = "ago"
    units = [
        (365 * 24 * 3600, "year"),
        (30 * 24 * 3600, "month"),
        (7 * 24 * 3600, "week"),
        (24 * 3600, "day"),
        (3600, "hour"),
        (60, "minute"),
    ]
    for unit_seconds, label in units:
        if seconds >= unit_seconds:
            count = max(1, seconds // unit_seconds)
            return f"{count} {label}{'' if count == 1 else 's'} {suffix}"
    return "just now" if suffix == "ago" else "in less than a minute"


def exact_time_title(value: str, now_utc: dt.datetime) -> str:
    parsed = parse_datetime_value(value, now_utc)
    if not parsed:
        return str(value or "")
    return parsed.astimezone(dt.timezone.utc).strftime("%Y-%m-%d %H:%M UTC")


def time_html(value: str, now_utc: dt.datetime) -> str:
    parsed = parse_datetime_value(value, now_utc)
    if not parsed:
        return esc(value)
    exact = exact_time_title(value, now_utc)
    return f'<time datetime="{esc(parsed.astimezone(dt.timezone.utc).isoformat())}" title="{esc(exact)}">{esc(relative_time_text(value, now_utc))}</time>'


def meta_html(parts, now_utc: dt.datetime, date_indexes: set[int] | None = None) -> str:
    date_indexes = date_indexes or set()
    rendered = []
    for idx, part in enumerate(parts):
        if part is None or part == "":
            continue
        rendered.append(time_html(part, now_utc) if idx in date_indexes else esc(part))
    return " · ".join(rendered)


def item_date_value(item: dict, now_utc: dt.datetime) -> str:
    for field in ("published_at", "created_at", "created", "published"):
        value = item.get(field)
        if parse_datetime_value(value, now_utc):
            return str(value)
    parsed = x_status_datetime(item.get("url", ""))
    if parsed:
        return parsed.isoformat()
    meta = item.get("meta")
    if parse_datetime_value(meta, now_utc):
        return str(meta)
    return ""


def post_meta_html(item: dict, now_utc: dt.datetime, *extra_parts: str) -> str:
    parts = [item_date_value(item, now_utc), item.get("metrics"), *extra_parts]
    return meta_html(parts, now_utc, {0})


def x_status_datetime(url: str):
    match = re.search(r"(?:twitter|x)\.com/[^/]+/status/(\d+)", str(url or ""))
    if not match:
        return None
    try:
        # Twitter/X snowflake timestamp: milliseconds since 2010-11-04.
        millis = (int(match.group(1)) >> 22) + 1288834974657
        return dt.datetime.fromtimestamp(millis / 1000, dt.timezone.utc)
    except Exception:
        return None


def recency_datetime(item: dict, now_utc: dt.datetime, *fields: str):
    for field in fields:
        parsed = parse_datetime_value(item.get(field), now_utc)
        if parsed:
            return parsed.astimezone(dt.timezone.utc)
    parsed = x_status_datetime(item.get("url", ""))
    if parsed:
        return parsed
    return dt.datetime.min.replace(tzinfo=dt.timezone.utc)


def sort_by_recency(items, now_utc: dt.datetime, *fields: str):
    return sorted(items, key=lambda item: recency_datetime(item, now_utc, *fields), reverse=True)


def dedupe_items_by_url(items):
    out = []
    seen = set()
    for item in items:
        key = normalize_url(item.get("url", "")) or item.get("title")
        if key in seen:
            continue
        seen.add(key)
        out.append(item)
    return out


def is_before_min_media_date(item: dict, now_utc: dt.datetime, *fields: str) -> bool:
    parsed = recency_datetime(item, now_utc, *fields)
    return parsed != dt.datetime.min.replace(tzinfo=dt.timezone.utc) and parsed < MIN_MEDIA_DATE


def filter_min_media_date(items, now_utc: dt.datetime, *fields: str):
    return [i for i in items if not is_before_min_media_date(i, now_utc, *fields)]


def has_presave_title(item: dict) -> bool:
    return bool(re.search(r"\bpre(?:-|\s+)save\b", str(item.get("title") or ""), re.I))


def filter_presave_titles(items):
    return [i for i in items if not has_presave_title(i)]


def render_stat_grid(stats: list[tuple[str, object]]) -> str:
    items = [
        f'<div class="stat-box"><span>{esc(label)}</span><strong>{value if isinstance(value, str) and value.startswith("<time ") else esc(value)}</strong></div>'
        for label, value in stats
        if value is not None
    ]
    return '<div class="stat-grid">' + "\n".join(items) + '</div>' if items else '<p class="empty">Stats unavailable.</p>'


def normalize_url(url: str) -> str:
    if not url:
        return ""
    try:
        parsed = urllib.parse.urlparse(url.strip())
        scheme = parsed.scheme.lower() or "https"
        netloc = parsed.netloc.lower().removeprefix("www.")
        path = parsed.path.rstrip("/") or "/"
        query = urllib.parse.parse_qsl(parsed.query, keep_blank_values=True)
        query = [(k, v) for k, v in query if not k.lower().startswith("utm_")]
        query_s = urllib.parse.urlencode(sorted(query))
        return urllib.parse.urlunparse((scheme, netloc, path, "", query_s, ""))
    except Exception:
        return url.strip().rstrip("/")


def load_remove_list() -> set[str]:
    try:
        lines = REMOVE_LIST_PATH.read_text(encoding="utf-8").splitlines()
    except FileNotFoundError:
        return set()
    blocked = set()
    for line in lines:
        line = line.split("#", 1)[0].strip()
        if line:
            blocked.add(normalize_url(line))
    return blocked


def is_removed_url(url: str, remove_urls: set[str]) -> bool:
    return bool(url) and normalize_url(url) in remove_urls


def item_key(source: str, title: str, url: str) -> str:
    raw = f"{source}\0{url or title}"
    return hashlib.sha1(raw.encode("utf-8", errors="replace")).hexdigest()


def load_seen_state():
    try:
        return json.loads(SEEN_STATE_PATH.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return {"initialized": False, "seen": {}}
    except Exception:
        return {"initialized": False, "seen": {}}


def save_seen_state(state):
    SEEN_STATE_PATH.write_text(json.dumps(state, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def run_x_logged_in_sweep() -> str | None:
    if not X_LOGGED_IN_SWEEP_SCRIPT.exists():
        return None
    try:
        import os
        if os.environ.get("STS_SKIP_X_BROWSER_SWEEP"):
            return None
        result = subprocess.run(
            ["node", str(X_LOGGED_IN_SWEEP_SCRIPT)],
            text=True,
            capture_output=True,
            timeout=120,
            check=False,
        )
        output = " ".join(part.strip() for part in [result.stdout, result.stderr] if part.strip())
        if result.returncode != 0:
            return f"Logged-in X sweep exited {result.returncode}: {output[:500]}"
        return output[:500] if output else None
    except Exception as e:
        return f"Logged-in X sweep skipped: {e!r}"


def load_x_logged_in_posts(now_utc: dt.datetime):
    try:
        data = json.loads(X_LOGGED_IN_POSTS_PATH.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return [], None
    except Exception as e:
        return [], f"Logged-in X cache read failed: {e!r}"
    out = []
    for post in data.get("posts") or []:
        if not post.get("url"):
            continue
        item = dict(post)
        item["source"] = item.get("source") or "X"
        item["title"] = item.get("title") or item.get("url")
        item["note"] = item.get("note") or "Found via logged-in X live search for save-to-spotify."
        if item.get("published_at"):
            item["published_at"] = datetime_iso(item.get("published_at"), now_utc) or item.get("published_at")
        out.append(item)
    return out, None


def run_youtube_recent_sweep() -> str | None:
    if not YOUTUBE_RECENT_SWEEP_SCRIPT.exists():
        return None
    try:
        import os
        if os.environ.get("STS_SKIP_YOUTUBE_BROWSER_SWEEP"):
            return None
        result = subprocess.run(
            ["node", str(YOUTUBE_RECENT_SWEEP_SCRIPT)],
            text=True,
            capture_output=True,
            timeout=90,
            check=False,
        )
        output = " ".join(part.strip() for part in [result.stdout, result.stderr] if part.strip())
        if result.returncode != 0:
            return f"YouTube recent sweep exited {result.returncode}: {output[:500]}"
        return output[:500] if output else None
    except Exception as e:
        return f"YouTube recent sweep skipped: {e!r}"


def load_youtube_recent_posts():
    try:
        data = json.loads(YOUTUBE_RECENT_POSTS_PATH.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return [], None
    except Exception as e:
        return [], f"YouTube recent cache read failed: {e!r}"
    out = []
    for post in data.get("posts") or []:
        item = dict(post)
        if not item.get("url"):
            continue
        item["channel"] = item.get("channel") or "YouTube"
        item["query"] = item.get("query") or 'browser: "save to spotify" recently uploaded'
        if is_relevant_youtube_hit(item):
            out.append(item)
    return out, None


def collect_seen_items(news, gh, hn, reddit, youtube, x_search, x_browser, now_utc: dt.datetime, remove_urls: set[str]):
    items = []
    for i in news:
        items.append({"source": i.get("source") or "News", "title": i.get("title"), "url": i.get("url"), "meta": i.get("published"), "published_at": i.get("published")})
    if gh and gh.get("latest_open"):
        for i in gh["latest_open"]:
            items.append({"source": f"GitHub {i.get('kind')}", "title": i.get("title"), "url": i.get("url"), "meta": i.get("created_at")})
    for i in x_search:
        items.append({"source": i.get("source") or "X", "title": i.get("title"), "url": i.get("url"), "meta": i.get("note"), "metrics": i.get("metrics"), "published_at": i.get("published_at")})
    for i in CURATED_SOCIAL:
        published_at = x_status_datetime(i.get("url", ""))
        items.append({"source": i.get("source") or "Social", "title": i.get("title"), "url": i.get("url"), "meta": i.get("note"), "metrics": i.get("metrics"), "published_at": published_at.isoformat() if published_at else None, "suppress_new": True})
    for i in x_browser:
        items.append({"source": i.get("source") or "X", "title": i.get("title"), "url": i.get("url"), "meta": i.get("note"), "metrics": i.get("metrics"), "published_at": i.get("published_at")})
    for i in hn:
        items.append({"source": "Hacker News", "title": i.get("title"), "url": i.get("url"), "meta": f"{i.get('points')} points · {i.get('comments')} comments", "published_at": i.get("created_at")})
    for i in reddit:
        items.append({"source": i.get("subreddit") or "Reddit", "title": i.get("title"), "url": i.get("url"), "meta": f"u/{i.get('author')} · {i.get('score')} pts · {i.get('comments')} comments", "published_at": i.get("created_at") or i.get("created")})
    for i in youtube:
        meta = " · ".join(part for part in [i.get("channel"), i.get("published"), i.get("views"), i.get("duration")] if part)
        items.append({"source": "YouTube", "title": i.get("title"), "url": i.get("url"), "meta": meta, "metrics": i.get("metrics") or i.get("views"), "snippet": i.get("snippet"), "published_at": i.get("published")})
    items = [item for item in items if not is_removed_url(item.get("url", ""), remove_urls)]
    for item in items:
        if item.get("published_at"):
            item["published_at"] = datetime_iso(item.get("published_at"), now_utc) or item.get("published_at")
        item["id"] = item_key(item.get("source", ""), item.get("title", ""), item.get("url", ""))
    return items


def prune_removed_seen(seen: dict, remove_urls: set[str]) -> int:
    removed_ids = [item_id for item_id, item in seen.items() if is_removed_url(item.get("url", ""), remove_urls)]
    for item_id in removed_ids:
        seen.pop(item_id, None)
    return len(removed_ids)


def prune_old_media_seen(seen: dict, now_utc: dt.datetime) -> int:
    removed_ids = []
    for item_id, item in seen.items():
        source = str(item.get("source") or "")
        if source.startswith("GitHub") or source.startswith("X /"):
            continue
        if is_before_min_media_date(item, now_utc, "published_at"):
            removed_ids.append(item_id)
    for item_id in removed_ids:
        seen.pop(item_id, None)
    return len(removed_ids)


def prune_presave_seen(seen: dict) -> int:
    removed_ids = [item_id for item_id, item in seen.items() if has_presave_title(item)]
    for item_id in removed_ids:
        seen.pop(item_id, None)
    return len(removed_ids)


def prune_irrelevant_youtube_seen(seen: dict) -> int:
    removed_ids = [
        item_id for item_id, item in seen.items()
        if item.get("source") == "YouTube" and not is_relevant_youtube_hit(item)
    ]
    for item_id in removed_ids:
        seen.pop(item_id, None)
    return len(removed_ids)


def normalize_seen_dates(seen: dict, now_utc: dt.datetime) -> int:
    """Migrate relative stored dates to absolute timestamps so charts don't drift."""
    changed = 0
    for item in seen.values():
        value = item.get("published_at")
        if not value:
            parsed = x_status_datetime(item.get("url", ""))
            if parsed:
                item["published_at"] = parsed.isoformat()
                changed += 1
            continue
        try:
            dt.datetime.fromisoformat(str(value).replace("Z", "+00:00"))
            continue
        except Exception:
            pass
        anchor = parse_datetime_value(item.get("last_seen_at"), now_utc) or parse_datetime_value(item.get("first_seen_at"), now_utc) or now_utc
        parsed = parse_datetime_value(value, anchor)
        if parsed:
            item["published_at"] = parsed.astimezone(dt.timezone.utc).isoformat()
            changed += 1
    return changed


def render_new_items(new_items, initialized: bool, now_utc: dt.datetime):
    if not initialized:
        return '<p class="empty">Tracking initialized. Future updates will lead with posts not seen before.</p>'
    if not new_items:
        return '<p class="empty">No new tracked posts since the previous update.</p>'
    return "<ul>" + "\n".join(
        f'<li><strong>{esc(i["source"])}</strong>: {link(i.get("url") or "#", i.get("title") or "Untitled")}<small>{post_meta_html(i, now_utc, i.get("meta") or "new")}</small></li>'
        for i in sort_by_recency(new_items, now_utc, "published_at", "meta", "first_seen_at")
    ) + "</ul>"


def is_social_source(source: str) -> bool:
    s = (source or "").lower()
    return s.startswith("x /") or s.startswith("r/") or s == "hacker news" or s == "youtube"


def is_media_source(source: str) -> bool:
    s = (source or "").lower()
    return not (is_social_source(s) or s.startswith("github "))


def is_social_or_media_source(source: str) -> bool:
    return is_social_source(source) or is_media_source(source)


def parse_iso_date(value: str):
    if not value:
        return None
    try:
        return dt.datetime.fromisoformat(value.replace("Z", "+00:00")).date()
    except Exception:
        return None


def render_line_chart(series: dict, today: dt.date, empty_text: str, aria_label: str, note: str, value_label: str) -> str:
    dated = {day: value for day, value in series.items() if day and value is not None}
    if not dated:
        return f'<p class="empty">{esc(empty_text)}</p>'

    start = min(dated)
    end = max(max(dated), today)
    days = []
    d = start
    while d <= end:
        days.append(d)
        d += dt.timedelta(days=1)
    values = [dated.get(day, 0) for day in days]

    width, height = 820, 240
    left, right, top, bottom = 46, 18, 20, 42
    plot_w = width - left - right
    plot_h = height - top - bottom
    max_y = max(values + [1])
    min_y = min(values + [0])
    if min_y > 0 and max_y - min_y <= 10:
        min_y = max(0, min_y - 1)
    span_y = max(1, max_y - min_y)
    mid_y = min_y + span_y // 2
    y_ticks = sorted(set([min_y, mid_y, max_y]))

    def x_at(i):
        return left + (plot_w * i / max(1, len(days) - 1))

    def y_at(v):
        return top + plot_h - (plot_h * (v - min_y) / span_y)

    points = " ".join(f"{x_at(i):.1f},{y_at(v):.1f}" for i, v in enumerate(values))
    circles = "".join(
        f'<circle cx="{x_at(i):.1f}" cy="{y_at(v):.1f}" r="4"><title>{esc(day.isoformat())}: {v} {esc(value_label)}</title></circle>'
        for i, (day, v) in enumerate(zip(days, values))
    )
    labels = "".join(
        f'<text x="{x_at(i):.1f}" y="{height - 16}" text-anchor="middle"><title>{esc(day.isoformat())}</title>{esc(relative_time_text(day.isoformat(), dt.datetime.combine(today, dt.time.min, tzinfo=dt.timezone.utc)))}</text>'
        for i, day in enumerate(days)
    )
    grid = "".join(
        f'<g><line x1="{left}" x2="{width - right}" y1="{y_at(t):.1f}" y2="{y_at(t):.1f}" />'
        f'<text x="{left - 10}" y="{y_at(t) + 4:.1f}" text-anchor="end">{t}</text></g>'
        for t in y_ticks
    )
    return f'''<div class="chart-wrap" role="img" aria-label="{esc(aria_label)}">
      <svg class="line-chart" viewBox="0 0 {width} {height}" preserveAspectRatio="xMidYMid meet">
        <g class="chart-grid">{grid}</g>
        <polyline points="{points}" />
        <g class="chart-points">{circles}</g>
        <g class="chart-labels">{labels}</g>
      </svg>
      <small>{note}</small>
    </div>'''


def social_or_media_item_day(item: dict, now_utc: dt.datetime):
    source = item.get("source", "")
    candidates = [item.get("published_at")]
    if is_media_source(source):
        candidates.extend([item.get("meta"), item.get("first_seen_at")])
    else:
        candidates.extend([item.get("first_seen_at")])
    for value in candidates:
        parsed = parse_datetime_value(value, now_utc)
        if parsed:
            return parsed.astimezone(dt.timezone.utc).date()
    parsed = x_status_datetime(item.get("url", ""))
    if parsed:
        return parsed.date()
    return None


def render_social_posts_chart(seen: dict, today: dt.date, now_utc: dt.datetime) -> str:
    counts = {}
    counted = set()
    for item in seen.values():
        if not is_social_or_media_source(item.get("source", "")):
            continue
        key = normalize_url(item.get("url", "")) or item.get("id") or item.get("title")
        if key in counted:
            continue
        counted.add(key)
        day = social_or_media_item_day(item, now_utc)
        if day:
            counts[day] = counts.get(day, 0) + 1

    if counts:
        note = f'{sum(counts.values())} social/media posts tracked since {time_html(min(counts).isoformat(), now_utc)}. Counts include news/media plus X, YouTube, Hacker News, and Reddit, plotted by publish/post date when available.'
    else:
        note = ""
    return render_line_chart(counts, today, "No social/media posts tracked yet.", "Line chart of social and media posts by day across the full timeline", note, "posts")


def update_github_star_history(state: dict, gh: dict | None, today: dt.date):
    history = state.setdefault("github_stars_by_day", {})
    if gh and gh.get("stars") is not None:
        history[today.isoformat()] = int(gh["stars"])
    return history


def render_github_stars_chart(history: dict, today: dt.date, now_utc: dt.datetime) -> str:
    series = {}
    for day, stars in (history or {}).items():
        try:
            series[dt.date.fromisoformat(day)] = int(stars)
        except Exception:
            continue
    if series:
        latest_day = max(series)
        note = f'GitHub stars tracked daily starting {time_html(min(series).isoformat(), now_utc)}. Latest: {series[latest_day]} stars on {time_html(latest_day.isoformat(), now_utc)}.'
    else:
        note = ""
    return render_line_chart(series, today, "No GitHub star history recorded yet.", "Line chart of GitHub stars per day", note, "stars")


def render():
    now_utc = dt.datetime.now(dt.timezone.utc)
    now_stockholm = now_utc.astimezone(dt.ZoneInfo("Europe/Stockholm")) if hasattr(dt, "ZoneInfo") else now_utc
    # Python exposes ZoneInfo from zoneinfo, not datetime, fallback below.


def main():
    from zoneinfo import ZoneInfo
    now_utc = dt.datetime.now(dt.timezone.utc)
    now_local = now_utc.astimezone(ZoneInfo("Europe/Stockholm"))

    remove_urls = load_remove_list()
    news, news_err = google_news_items()
    gh, gh_err = github_stats()
    clawhub, clawhub_err = clawhub_stats()
    hn, hn_err = hn_hits()
    reddit, reddit_err = reddit_hits()
    youtube, youtube_err = youtube_hits()
    youtube_sweep_note = run_youtube_recent_sweep()
    youtube_browser, youtube_browser_err = load_youtube_recent_posts()
    x_search, x_search_err = x_search_hits()
    x_sweep_note = run_x_logged_in_sweep()
    x_browser, x_browser_err = load_x_logged_in_posts(now_utc)
    news = sort_by_recency(filter_presave_titles(filter_min_media_date([i for i in news if not is_removed_url(i.get("url", ""), remove_urls)], now_utc, "published")), now_utc, "published")
    hn = sort_by_recency(filter_presave_titles(filter_min_media_date([i for i in hn if not is_removed_url(i.get("url", ""), remove_urls)], now_utc, "created_at")), now_utc, "created_at")
    reddit = sort_by_recency(filter_presave_titles(filter_min_media_date([i for i in reddit if not is_removed_url(i.get("url", ""), remove_urls)], now_utc, "created_at", "created")), now_utc, "created_at", "created")
    youtube = sort_by_recency(filter_presave_titles(filter_min_media_date([i for i in youtube if not is_removed_url(i.get("url", ""), remove_urls)], now_utc, "published")), now_utc, "published")
    youtube_browser = sort_by_recency(filter_presave_titles(filter_min_media_date([i for i in youtube_browser if not is_removed_url(i.get("url", ""), remove_urls)], now_utc, "published")), now_utc, "published")
    youtube = dedupe_items_by_url(sort_by_recency(youtube_browser + youtube, now_utc, "published"))
    youtube_metrics_err = enrich_youtube_metrics(youtube)
    x_search = sort_by_recency(filter_presave_titles(filter_min_media_date([i for i in x_search if not is_removed_url(i.get("url", ""), remove_urls)], now_utc, "published_at")), now_utc, "published_at")
    x_browser = sort_by_recency(filter_presave_titles(filter_min_media_date([i for i in x_browser if not is_removed_url(i.get("url", ""), remove_urls)], now_utc, "published_at")), now_utc, "published_at")
    if gh and gh.get("latest_open"):
        gh["latest_open"] = sort_by_recency(gh["latest_open"], now_utc, "created_at")
    errors = [e for e in [news_err, gh_err, clawhub_err, hn_err, reddit_err, youtube_err, youtube_browser_err, youtube_metrics_err, x_search_err, x_browser_err] if e]

    seen_state = load_seen_state()
    seen = seen_state.setdefault("seen", {})
    normalized_date_count = normalize_seen_dates(seen, now_utc)
    pruned_count = prune_removed_seen(seen, remove_urls) + prune_old_media_seen(seen, now_utc) + prune_presave_seen(seen) + prune_irrelevant_youtube_seen(seen)
    current_items = collect_seen_items(news, gh, hn, reddit, youtube, x_search, x_browser, now_utc, remove_urls)
    initialized = bool(seen_state.get("initialized"))
    new_items = [i for i in current_items if initialized and i["id"] not in seen and not i.get("suppress_new")]
    for i in current_items:
        stored = seen.setdefault(i["id"], {"first_seen_at": now_utc.isoformat()})
        stored.update({
            "source": i.get("source"),
            "title": i.get("title"),
            "url": i.get("url"),
            "meta": i.get("meta"),
            "metrics": i.get("metrics"),
            "snippet": i.get("snippet"),
            "published_at": i.get("published_at"),
            "last_seen_at": now_utc.isoformat(),
        })
    seen_state["initialized"] = True
    seen_state["last_updated_at"] = now_utc.isoformat()
    github_star_history = update_github_star_history(seen_state, gh, now_local.date())
    save_seen_state(seen_state)
    new_items_html = render_new_items(new_items, initialized, now_utc)
    social_chart_html = render_social_posts_chart(seen, now_local.date(), now_utc)
    github_stars_chart_html = render_github_stars_chart(github_star_history, now_local.date(), now_utc)

    gh_stats_html = "<p class='empty'>GitHub stats unavailable.</p>"
    if gh:
        gh_stats_html = render_stat_grid([
            ("Stars", gh.get("stars")),
            ("Forks", gh.get("forks")),
            ("Open issues/PRs", gh.get("open_issues")),
            ("Updated", time_html(gh.get("updated_at"), now_utc)),
        ])

    clawhub_stats_html = "<p class='empty'>ClawHub stats unavailable.</p>"
    if clawhub:
        clawhub_stats_html = render_stat_grid([
            ("Stars", clawhub.get("stars")),
            ("Downloads", clawhub.get("downloads")),
            ("Versions", clawhub.get("versions")),
            ("Current version", f"v{clawhub.get('version')}" if clawhub.get("version") else None),
            ("Updated", time_html(clawhub.get("updated"), now_utc) if clawhub.get("updated") else None),
            ("License", clawhub.get("license")),
        ])

    news_html = "\n".join(
        f'<li><strong>{esc(i["source"] or "News")}</strong>: {link(i["url"], i["title"])}<small>{time_html(i["published"], now_utc)}</small></li>'
        for i in news
    ) or "<li>No news items found this run.</li>"

    curated_x_items = [i for i in CURATED_SOCIAL if (i.get("source") or "").lower().startswith("x /") and not is_removed_url(i.get("url", ""), remove_urls)]
    x_items = dedupe_items_by_url(sort_by_recency(x_browser + x_search + curated_x_items, now_utc, "published_at"))
    other_social_items = sort_by_recency([i for i in CURATED_SOCIAL if i not in x_items and not (i.get("source") or "").lower().startswith("hacker news") and not is_removed_url(i.get("url", ""), remove_urls)], now_utc)

    x_html = "\n".join(
        f'<li><strong>{esc(i["source"])}</strong>: {link(i["url"], i["title"])}<small>{post_meta_html(i, now_utc, i.get("note"))}</small></li>'
        for i in x_items
    ) or "<li>No X posts tracked this run.</li>"

    reddit_html = "\n".join(
        f'<li><strong>{esc(i["subreddit"])}</strong>: {link(i["url"], i["title"])}<small>u/{esc(i["author"])} · {esc(i["score"])} pts · {esc(i["comments"])} comments · {time_html(i.get("created_at") or i.get("created"), now_utc)}{(" · external: " + link(i["external_url"], "source")) if i.get("external_url") else ""}</small></li>'
        for i in reddit
    ) or "<li>No Reddit hits found this run.</li>"

    youtube_html = "\n".join(
        f'<li><strong>{esc(i.get("channel") or "YouTube")}</strong>: {link(i["url"], i["title"])}<small>{post_meta_html(i, now_utc, i.get("duration"))}</small></li>'
        for i in youtube
    ) or "<li>No YouTube videos found this run.</li>"

    hn_html = "\n".join(
        f'<li><strong>Hacker News</strong>: {link(i["url"], i["title"])} <small>{meta_html([f"{i.get('points')} points", f"{i.get('comments')} comments", i.get("created_at")], now_utc, {2})}</small></li>'
        for i in hn
    ) or "<li>No Hacker News hits found this run.</li>"

    other_html = "\n".join(
        f'<li><strong>{esc(i["source"])}</strong>: {link(i["url"], i["title"])}<small>{post_meta_html(i, now_utc, i.get("note"))}</small></li>'
        for i in other_social_items
    )

    primary_html = "\n".join(
        f'<li><strong>{esc(src)}</strong>: {link(url, title)}</li>'
        for src, title, url in PRIMARY_LINKS
    )

    issues_html = ""
    if gh and gh.get("latest_open"):
        issues_html = "\n".join(
            f'<li><strong>{esc(i["kind"])}</strong>: {link(i["url"], i["title"])} <small>{time_html(i["created_at"], now_utc)}</small></li>'
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
    .social-sites {{ display:grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap:1rem; align-items:start; }}
    .social-site h2 {{ display:flex; align-items:baseline; justify-content:space-between; gap:1rem; }}
    .count {{ color:var(--muted); font-size:.78rem; font-weight:500; }}
    @media (max-width: 860px) {{ .social-sites {{ grid-template-columns: 1fr; }} }}
    .card {{ border:1px solid var(--line); background:var(--card); border-radius:24px; padding:1.2rem; box-shadow: 0 20px 80px #0005; backdrop-filter: blur(16px); }}
    h2 {{ margin:.1rem 0 1rem; font-size:1.1rem; letter-spacing:-.02em; }}
    ul {{ list-style:none; padding:0; margin:0; display:grid; gap:.85rem; }}
    li {{ line-height:1.35; }}
    a {{ color:#d9fbe4; text-decoration-color:#1ed76088; text-underline-offset:3px; }}
    a:hover {{ color:white; text-decoration-color:var(--accent); }}
    small {{ display:block; color:var(--muted); margin-top:.2rem; font-size:.82rem; }}
    .bigstat {{ font-size:1.25rem; color:#d9fbe4; font-weight:700; }}
    .stat-grid {{ display:grid; grid-template-columns: repeat(auto-fit, minmax(120px, 1fr)); gap:.7rem; margin-bottom:.9rem; }}
    .stat-box {{ border:1px solid var(--line); background:#ffffff08; border-radius:16px; padding:.8rem; min-width:0; }}
    .stat-box span {{ display:block; color:var(--muted); font-size:.78rem; margin-bottom:.25rem; }}
    .stat-box strong {{ display:block; color:#d9fbe4; font-size:1.1rem; line-height:1.15; overflow-wrap:anywhere; }}
    .chart-wrap {{ display:grid; gap:.5rem; overflow:hidden; }}
    .line-chart {{ width:100%; height:auto; display:block; }}
    .chart-grid line {{ stroke:var(--line); stroke-width:1; }}
    .chart-grid text, .chart-labels text {{ fill:var(--muted); font-size:12px; }}
    .line-chart polyline {{ fill:none; stroke:var(--accent); stroke-width:3; stroke-linecap:round; stroke-linejoin:round; filter: drop-shadow(0 0 10px #1ed76055); }}
    .chart-points circle {{ fill:var(--accent); stroke:#d9fbe4; stroke-width:2; }}
    .warn {{ border-color:#806b2a; }}
    .highlight {{ border-color:#1ed76088; box-shadow: 0 20px 90px #1ed76022; }}
    .empty {{ color:var(--muted); margin:0; }}
    footer {{ max-width:1120px; margin:auto; color:var(--muted); padding:0 clamp(1rem, 5vw, 4rem) 3rem; font-size:.9rem; }}
  </style>
</head>
<body>
  <header>
    <h1>Save to Spotify chatter tracker</h1>
    <p class="lede">A lightweight hourly snapshot of where people are talking about Spotify’s beta CLI for saving AI-generated personal podcasts into Spotify.</p>
    <div class="meta">
      <span class="pill">Last updated: {time_html(now_utc.isoformat(), now_utc)}</span>
      <span class="pill">Auto-refresh target: hourly</span>
    </div>
  </header>
  <main>
    <section class="card highlight">
      <h2>New since last update</h2>
      {new_items_html}
    </section>
    <section class="card">
      <h2>Current read</h2>
      <p class="bigstat">Conversation is mostly press + Spotify/dev X + GitHub, with ClawHub install/download stats and Reddit tracked directly. Seen posts are persisted so fresh items appear first.</p>
    </section>
    <div class="grid">
      <section class="card"><h2>Primary links</h2><ul>{primary_html}</ul></section>
      <section class="card"><h2>ClawHub skill stats</h2>{clawhub_stats_html}<small>{link(CLAWHUB_URL, "Source: ClawHub skill page")}</small></section>
      <section class="card"><h2>GitHub repo pulse</h2>{gh_stats_html}<ul>{issues_html}</ul></section>
    </div>
    <section class="card"><h2>GitHub stars per day</h2>{github_stars_chart_html}</section>
    <section class="card"><h2>Latest news pickup</h2><ul>{news_html}</ul></section>
    <section class="card"><h2>Social + media posts per day</h2>{social_chart_html}</section>
    <section class="social-sites">
      <section class="card social-site"><h2>X <span class="count">{len(x_items)} items</span></h2><ul>{x_html}</ul></section>
      <section class="card social-site"><h2>YouTube <span class="count">{len(youtube)} items</span></h2><ul>{youtube_html}</ul></section>
      <section class="card social-site"><h2>Reddit <span class="count">{len(reddit)} items</span></h2><ul>{reddit_html}</ul></section>
      <section class="card social-site"><h2>Hacker News <span class="count">{len(hn)} items</span></h2><ul>{hn_html}</ul></section>
      {f'<section class="card social-site"><h2>Other <span class="count">{len(other_social_items)} items</span></h2><ul>{other_html}</ul></section>' if other_html else ''}
    </section>
    <section class="card"><h2>Remove list</h2><p class="empty">{len(remove_urls)} URLs excluded from this snapshot. {pruned_count} previously tracked matches pruned this run. {normalized_date_count} stored dates normalized for chart stability.</p></section>
    {errors_html}
  </main>
  <footer>Generated by Nyx. Sources are fetched from Google News RSS, GitHub API, ClawHub public skill page, YouTube searches, Hacker News Algolia API, tools/reddit_reader.py, search-engine site:x.com sweeps, plus curated social overrides.</footer>
</body>
</html>
"""
    with open("index.html", "w", encoding="utf-8") as f:
        f.write(html_doc)

if __name__ == "__main__":
    main()
