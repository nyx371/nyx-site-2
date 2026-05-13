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

NEWS_QUERY = '"Save to Spotify" Spotify AI podcasts'
YOUTUBE_QUERIES = [
    '"save to spotify" CLI',
    'Spotify "Personal Podcasts" "AI agents"',
    '"Spotify Personal Podcasts"',
    '"personal-podcasts-launch"',
]
CLAWHUB_URL = "https://clawhub.ai/spotify/save-to-spotify"

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
        params = {
            "q": '\"Save to Spotify\"',
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
        out = []
        for child in reddit_reader.listing_children(result.data):
            post = child.get("data", {})
            title = reddit_reader.clean(post.get("title"))
            if not title:
                continue
            created_dt = dt.datetime.fromtimestamp(
                post.get("created_utc", 0), dt.timezone.utc
            )
            created = created_dt.strftime("%Y-%m-%d %H:%M UTC")
            out.append({
                "title": title,
                "url": reddit_reader.post_url(post.get("permalink", "")),
                "subreddit": post.get("subreddit_name_prefixed") or f"r/{post.get('subreddit', '?')}",
                "author": post.get("author") or "?",
                "score": post.get("score", 0),
                "comments": post.get("num_comments", 0),
                "created": created,
                "created_at": created_dt.isoformat(),
                "external_url": post.get("url") if post.get("url") and not str(post.get("url")).startswith("https://www.reddit.com") else "",
            })
        return out, None
    except BaseException as e:
        return [], f"Reddit reader failed: {e!r}"


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


def youtube_hits(limit: int = 12):
    """Fetch YouTube search results from public search pages (no API key)."""
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
            f"https://www.youtube.com/results?search_query={q}",
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
                    seen_video_ids.add(video_id)
                    out.append({
                        "title": title,
                        "url": f"https://www.youtube.com/watch?v={video_id}",
                        "channel": _yt_text(video.get("ownerText")) or _yt_text(video.get("longBylineText")) or "YouTube",
                        "published": _yt_text(video.get("publishedTimeText")),
                        "views": _yt_text(video.get("viewCountText")),
                        "duration": _yt_text(video.get("lengthText")),
                        "query": query,
                    })
                    if len(out) >= limit:
                        return out, ("; ".join(errors) if errors else None)
            except Exception as e:
                errors.append(f"{query} via {url}: {e!r}")

    return out, ("; ".join(errors) if errors else None)

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


def collect_seen_items(news, gh, hn, reddit, youtube, remove_urls: set[str]):
    items = []
    for i in news:
        items.append({"source": i.get("source") or "News", "title": i.get("title"), "url": i.get("url"), "meta": i.get("published"), "published_at": i.get("published")})
    if gh and gh.get("latest_open"):
        for i in gh["latest_open"]:
            items.append({"source": f"GitHub {i.get('kind')}", "title": i.get("title"), "url": i.get("url"), "meta": i.get("created_at")})
    for i in CURATED_SOCIAL:
        published_at = x_status_datetime(i.get("url", ""))
        items.append({"source": i.get("source") or "Social", "title": i.get("title"), "url": i.get("url"), "meta": i.get("note"), "published_at": published_at.isoformat() if published_at else None, "suppress_new": True})
    for i in hn:
        items.append({"source": "Hacker News", "title": i.get("title"), "url": i.get("url"), "meta": f"{i.get('points')} points · {i.get('comments')} comments", "published_at": i.get("created_at")})
    for i in reddit:
        items.append({"source": i.get("subreddit") or "Reddit", "title": i.get("title"), "url": i.get("url"), "meta": f"u/{i.get('author')} · {i.get('score')} pts · {i.get('comments')} comments", "published_at": i.get("created_at") or i.get("created")})
    for i in youtube:
        meta = " · ".join(part for part in [i.get("channel"), i.get("published"), i.get("views"), i.get("duration")] if part)
        items.append({"source": "YouTube", "title": i.get("title"), "url": i.get("url"), "meta": meta, "published_at": i.get("published")})
    items = [item for item in items if not is_removed_url(item.get("url", ""), remove_urls)]
    for item in items:
        item["id"] = item_key(item.get("source", ""), item.get("title", ""), item.get("url", ""))
    return items


def prune_removed_seen(seen: dict, remove_urls: set[str]) -> int:
    removed_ids = [item_id for item_id, item in seen.items() if is_removed_url(item.get("url", ""), remove_urls)]
    for item_id in removed_ids:
        seen.pop(item_id, None)
    return len(removed_ids)


def render_new_items(new_items, initialized: bool, now_utc: dt.datetime):
    if not initialized:
        return '<p class="empty">Tracking initialized. Future updates will lead with posts not seen before.</p>'
    if not new_items:
        return '<p class="empty">No new tracked posts since the previous update.</p>'
    return "<ul>" + "\n".join(
        f'<li><strong>{esc(i["source"])}</strong>: {link(i.get("url") or "#", i.get("title") or "Untitled")}<small>{time_html(i.get("meta") or "new", now_utc)}</small></li>'
        for i in sort_by_recency(new_items, now_utc, "meta", "first_seen_at")
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
    for item in seen.values():
        if not is_social_or_media_source(item.get("source", "")):
            continue
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
    news = sort_by_recency([i for i in news if not is_removed_url(i.get("url", ""), remove_urls)], now_utc, "published")
    hn = sort_by_recency([i for i in hn if not is_removed_url(i.get("url", ""), remove_urls)], now_utc, "created_at")
    reddit = sort_by_recency([i for i in reddit if not is_removed_url(i.get("url", ""), remove_urls)], now_utc, "created_at", "created")
    youtube = sort_by_recency([i for i in youtube if not is_removed_url(i.get("url", ""), remove_urls)], now_utc, "published")
    if gh and gh.get("latest_open"):
        gh["latest_open"] = sort_by_recency(gh["latest_open"], now_utc, "created_at")
    errors = [e for e in [news_err, gh_err, clawhub_err, hn_err, reddit_err, youtube_err] if e]

    seen_state = load_seen_state()
    seen = seen_state.setdefault("seen", {})
    pruned_count = prune_removed_seen(seen, remove_urls)
    current_items = collect_seen_items(news, gh, hn, reddit, youtube, remove_urls)
    initialized = bool(seen_state.get("initialized"))
    new_items = [i for i in current_items if initialized and i["id"] not in seen and not i.get("suppress_new")]
    for i in current_items:
        stored = seen.setdefault(i["id"], {"first_seen_at": now_utc.isoformat()})
        stored.update({
            "source": i.get("source"),
            "title": i.get("title"),
            "url": i.get("url"),
            "meta": i.get("meta"),
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

    x_items = sort_by_recency([i for i in CURATED_SOCIAL if (i.get("source") or "").lower().startswith("x /") and not is_removed_url(i.get("url", ""), remove_urls)], now_utc)
    other_social_items = sort_by_recency([i for i in CURATED_SOCIAL if i not in x_items and not is_removed_url(i.get("url", ""), remove_urls)], now_utc)

    x_html = "\n".join(
        f'<li><strong>{esc(i["source"])}</strong>: {link(i["url"], i["title"])}<small>{esc(i["note"])}</small></li>'
        for i in x_items
    ) or "<li>No X posts tracked this run.</li>"

    reddit_html = "\n".join(
        f'<li><strong>{esc(i["subreddit"])}</strong>: {link(i["url"], i["title"])}<small>u/{esc(i["author"])} · {esc(i["score"])} pts · {esc(i["comments"])} comments · {time_html(i.get("created_at") or i.get("created"), now_utc)}{(" · external: " + link(i["external_url"], "source")) if i.get("external_url") else ""}</small></li>'
        for i in reddit
    ) or "<li>No Reddit hits found this run.</li>"

    youtube_html = "\n".join(
        f'<li><strong>{esc(i.get("channel") or "YouTube")}</strong>: {link(i["url"], i["title"])}<small>{meta_html([i.get("published"), i.get("views"), i.get("duration")], now_utc, {0})}</small></li>'
        for i in youtube
    ) or "<li>No YouTube videos found this run.</li>"

    other_items = []
    for i in other_social_items:
        other_items.append({"item": i, "date": recency_datetime(i, now_utc), "kind": "curated"})
    for i in hn:
        other_items.append({"item": i, "date": recency_datetime(i, now_utc, "created_at"), "kind": "hn"})
    other_items.sort(key=lambda row: row["date"], reverse=True)
    other_html_parts = []
    for row in other_items:
        i = row["item"]
        if row["kind"] == "hn":
            other_html_parts.append(f'<li><strong>Hacker News</strong>: {link(i["url"], i["title"])} <small>{meta_html([f"{i.get('points')} points", f"{i.get('comments')} comments", i.get("created_at")], now_utc, {2})}</small></li>')
        else:
            other_html_parts.append(f'<li><strong>{esc(i["source"])}</strong>: {link(i["url"], i["title"])}<small>{esc(i["note"])}</small></li>')
    other_html = "\n".join(other_html_parts) or "<li>No other community hits found this run.</li>"

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
    .social-columns {{ display:grid; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); gap:1rem; align-items:start; }}
    .social-column {{ border:1px solid var(--line); background:#ffffff08; border-radius:18px; padding:1rem; min-width:0; }}
    .social-column h3 {{ margin:0 0 .85rem; font-size:1rem; color:#d9fbe4; }}
    @media (max-width: 860px) {{ .social-columns {{ grid-template-columns: 1fr; }} }}
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
    <section class="card">
      <h2>Social / community places to watch</h2>
      <div class="social-columns">
        <section class="social-column"><h3>X</h3><ul>{x_html}</ul></section>
        <section class="social-column"><h3>YouTube</h3><ul>{youtube_html}</ul></section>
        <section class="social-column"><h3>Reddit</h3><ul>{reddit_html}</ul></section>
        <section class="social-column"><h3>Other</h3><ul>{other_html}</ul></section>
      </div>
    </section>
    <section class="card"><h2>Remove list</h2><p class="empty">{len(remove_urls)} URLs excluded from this snapshot. {pruned_count} previously tracked matches pruned this run.</p></section>
    {errors_html}
  </main>
  <footer>Generated by Nyx. Sources are fetched from Google News RSS, GitHub API, ClawHub public skill page, YouTube searches, Hacker News Algolia API, tools/reddit_reader.py, plus curated social links found during the first sweep.</footer>
</body>
</html>
"""
    with open("index.html", "w", encoding="utf-8") as f:
        f.write(html_doc)

if __name__ == "__main__":
    main()
