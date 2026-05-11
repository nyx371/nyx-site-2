#!/usr/bin/env python3
"""Generate the Save to Spotify chatter tracker index page."""
from __future__ import annotations

import datetime as dt
import hashlib
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
REPO_NAME = "sts-snapshot"
TRACKED_REPO = "spotify/save-to-spotify"
REDDIT_READER = pathlib.Path("/Users/agent/.openclaw/workspace/tools/reddit_reader.py")
SEEN_STATE_PATH = pathlib.Path("seen_save_to_spotify_posts.json")
REMOVE_LIST_PATH = pathlib.Path("remove_list.txt")

NEWS_QUERY = '"Save to Spotify" Spotify AI podcasts'
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

    ClawHub renders these server-side in the hero stats row, so parsing the
    public HTML is enough and avoids depending on private/internal APIs.
    """
    labels = {
        "lucide-star": "stars",
        "lucide-download": "downloads",
        "lucide-package": "versions",
        "lucide-calendar": "updated",
        "lucide-scale": "license",
    }
    try:
        doc = fetch_bytes(CLAWHUB_URL).decode("utf-8", errors="replace")
        title = _strip_html((re.search(r"<h1[^>]*>(.*?)</h1>", doc, re.S) or [None, "Save To Spotify"])[1])
        version_match = re.search(r'class="plugin-version-badge"[^>]*>\s*v\s*<!-- -->\s*([^<]+)', doc)
        row_match = re.search(r'<div class="skill-hero-stats-row">(.*?)</div>', doc, re.S)
        if not row_match:
            return None, "ClawHub stats row not found"
        stats = {"url": CLAWHUB_URL, "title": title, "version": version_match.group(1).strip() if version_match else None}
        history_seen = 0
        for span in re.findall(r'<span class="stat">(.*?)</span>', row_match.group(1), re.S):
            key = None
            for icon_class, label in labels.items():
                if icon_class in span:
                    key = label
                    break
            text = _strip_html(span)
            if key == "versions":
                stats[key] = text.replace(" versions", "")
            elif key == "updated":
                stats[key] = text.replace("Updated ", "")
            elif key:
                stats[key] = text
            elif "lucide-history" in span:
                history_seen += 1
                if history_seen == 1:
                    stats["installs_current"] = text.replace(" current", "")
                else:
                    stats["installs_all_time"] = text.replace(" all-time", "")
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


def collect_seen_items(news, gh, hn, reddit, remove_urls: set[str]):
    items = []
    for i in news:
        items.append({"source": i.get("source") or "News", "title": i.get("title"), "url": i.get("url"), "meta": i.get("published")})
    if gh and gh.get("latest_open"):
        for i in gh["latest_open"]:
            items.append({"source": f"GitHub {i.get('kind')}", "title": i.get("title"), "url": i.get("url"), "meta": i.get("created_at")})
    for i in CURATED_SOCIAL:
        items.append({"source": i.get("source") or "Social", "title": i.get("title"), "url": i.get("url"), "meta": i.get("note"), "suppress_new": True})
    for i in hn:
        items.append({"source": "Hacker News", "title": i.get("title"), "url": i.get("url"), "meta": f"{i.get('points')} points · {i.get('comments')} comments"})
    for i in reddit:
        items.append({"source": i.get("subreddit") or "Reddit", "title": i.get("title"), "url": i.get("url"), "meta": f"u/{i.get('author')} · {i.get('score')} pts · {i.get('comments')} comments"})
    items = [item for item in items if not is_removed_url(item.get("url", ""), remove_urls)]
    for item in items:
        item["id"] = item_key(item.get("source", ""), item.get("title", ""), item.get("url", ""))
    return items


def prune_removed_seen(seen: dict, remove_urls: set[str]) -> int:
    removed_ids = [item_id for item_id, item in seen.items() if is_removed_url(item.get("url", ""), remove_urls)]
    for item_id in removed_ids:
        seen.pop(item_id, None)
    return len(removed_ids)


def render_new_items(new_items, initialized: bool):
    if not initialized:
        return '<p class="empty">Tracking initialized. Future updates will lead with posts not seen before.</p>'
    if not new_items:
        return '<p class="empty">No new tracked posts since the previous update.</p>'
    return "<ul>" + "\n".join(
        f'<li><strong>{esc(i["source"])}</strong>: {link(i.get("url") or "#", i.get("title") or "Untitled")}<small>{esc(i.get("meta") or "new")}</small></li>'
        for i in new_items
    ) + "</ul>"


def is_social_source(source: str) -> bool:
    s = (source or "").lower()
    return s.startswith("x /") or s.startswith("r/") or s == "hacker news"


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
        f'<text x="{x_at(i):.1f}" y="{height - 16}" text-anchor="middle">{esc(day.strftime("%m-%d"))}</text>'
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


def render_social_posts_chart(seen: dict, today: dt.date) -> str:
    counts = {}
    for item in seen.values():
        if not is_social_source(item.get("source", "")):
            continue
        day = parse_iso_date(item.get("first_seen_at"))
        if day:
            counts[day] = counts.get(day, 0) + 1
    if counts:
        note = f'{sum(counts.values())} social/community posts tracked since {esc(min(counts).isoformat())}. Counts are based on first-seen day for X, Hacker News, and Reddit items.'
    else:
        note = ""
    return render_line_chart(counts, today, "No social/community posts tracked yet.", "Line chart of social and community posts first seen per day", note, "posts")


def update_github_star_history(state: dict, gh: dict | None, today: dt.date):
    history = state.setdefault("github_stars_by_day", {})
    if gh and gh.get("stars") is not None:
        history[today.isoformat()] = int(gh["stars"])
    return history


def render_github_stars_chart(history: dict, today: dt.date) -> str:
    series = {}
    for day, stars in (history or {}).items():
        try:
            series[dt.date.fromisoformat(day)] = int(stars)
        except Exception:
            continue
    if series:
        latest_day = max(series)
        note = f'GitHub stars tracked daily starting {esc(min(series).isoformat())}. Latest: {series[latest_day]} stars on {esc(latest_day.isoformat())}.'
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
    news = [i for i in news if not is_removed_url(i.get("url", ""), remove_urls)]
    hn = [i for i in hn if not is_removed_url(i.get("url", ""), remove_urls)]
    reddit = [i for i in reddit if not is_removed_url(i.get("url", ""), remove_urls)]
    errors = [e for e in [news_err, gh_err, clawhub_err, hn_err, reddit_err] if e]

    seen_state = load_seen_state()
    seen = seen_state.setdefault("seen", {})
    pruned_count = prune_removed_seen(seen, remove_urls)
    current_items = collect_seen_items(news, gh, hn, reddit, remove_urls)
    initialized = bool(seen_state.get("initialized"))
    new_items = [i for i in current_items if initialized and i["id"] not in seen and not i.get("suppress_new")]
    for i in current_items:
        seen.setdefault(i["id"], {"source": i.get("source"), "title": i.get("title"), "url": i.get("url"), "first_seen_at": now_utc.isoformat()})
    seen_state["initialized"] = True
    seen_state["last_updated_at"] = now_utc.isoformat()
    github_star_history = update_github_star_history(seen_state, gh, now_local.date())
    save_seen_state(seen_state)
    new_items_html = render_new_items(new_items, initialized)
    social_chart_html = render_social_posts_chart(seen, now_local.date())
    github_stars_chart_html = render_github_stars_chart(github_star_history, now_local.date())

    gh_summary = "GitHub stats unavailable"
    if gh:
        gh_summary = f"{gh['stars']} stars · {gh['forks']} forks · {gh['open_issues']} open issues/PRs · updated {esc(gh['updated_at'])}"

    clawhub_summary = "ClawHub stats unavailable"
    clawhub_html = "<li>No ClawHub stats found this run.</li>"
    if clawhub:
        clawhub_summary = (
            f"{clawhub.get('stars', '?')} stars · {clawhub.get('downloads', '?')} downloads · "
            f"{clawhub.get('versions', '?')} versions · v{clawhub.get('version') or '?'}"
        )
        clawhub_rows = [
            ("Current installs", clawhub.get("installs_current")),
            ("All-time installs", clawhub.get("installs_all_time")),
            ("Updated", clawhub.get("updated")),
            ("License", clawhub.get("license")),
        ]
        clawhub_html = "\n".join(
            f"<li><strong>{esc(label)}</strong><small>{esc(value)}</small></li>"
            for label, value in clawhub_rows
            if value is not None
        ) or clawhub_html

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
      <span class="pill">Last updated: {esc(now_local.strftime('%Y-%m-%d %H:%M %Z'))}</span>
      <span class="pill">UTC: {esc(now_utc.strftime('%Y-%m-%d %H:%M'))}</span>
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
      <section class="card"><h2>ClawHub skill stats</h2><p class="bigstat">{esc(clawhub_summary)}</p><ul>{clawhub_html}</ul><small>{link(CLAWHUB_URL, "Source: ClawHub skill page")}</small></section>
      <section class="card"><h2>GitHub repo pulse</h2><p class="bigstat">{esc(gh_summary)}</p><ul>{issues_html}</ul></section>
    </div>
    <section class="card"><h2>GitHub stars per day</h2>{github_stars_chart_html}</section>
    <section class="card"><h2>Latest news pickup</h2><ul>{news_html}</ul></section>
    <section class="card"><h2>Social posts per day</h2>{social_chart_html}</section>
    <div class="grid">
      <section class="card"><h2>Social / community places to watch</h2><ul>{social_html}</ul></section>
      <section class="card"><h2>Hacker News</h2><ul>{hn_html}</ul></section>
    </div>
    <section class="card"><h2>Reddit chatter</h2><ul>{reddit_html}</ul></section>
    <section class="card"><h2>Remove list</h2><p class="empty">{len(remove_urls)} URLs excluded from this snapshot. {pruned_count} previously tracked matches pruned this run.</p></section>
    {errors_html}
  </main>
  <footer>Generated by Nyx. Sources are fetched from Google News RSS, GitHub API, ClawHub public skill page, Hacker News Algolia API, tools/reddit_reader.py, plus curated social links found during the first sweep.</footer>
</body>
</html>
"""
    with open("index.html", "w", encoding="utf-8") as f:
        f.write(html_doc)

if __name__ == "__main__":
    main()
