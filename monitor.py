#!/usr/bin/env python3
"""
Reddit Keyword Monitor → Telegram Notifier
Uses RSS feeds. Substring keyword matching. RSS limit 100.
"""

import os
import json
import time
import re
import datetime
import collections
import xml.etree.ElementTree as ET
import requests

CONFIG_FILE   = "config.json"
SEEN_FILE     = "seen_ids.json"
STATE_FILE    = "state.json"
HEARTBEAT_N   = 6   # send "no match" ping every N quiet runs (~6h if cron=hourly)
HEADERS       = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

NS = {
    "atom": "http://www.w3.org/2005/Atom",
    "media": "http://search.yahoo.com/mrss/"
}

# ── startup checks ────────────────────────────────────────────────────────────

def get_env(key):
    val = os.environ.get(key, "").strip()
    if not val:
        raise SystemExit(f"[FATAL] Environment variable '{key}' is missing or empty.")
    return val

# ── config / state ────────────────────────────────────────────────────────────

def load_config():
    try:
        with open(CONFIG_FILE) as f:
            return json.load(f)
    except FileNotFoundError:
        raise SystemExit(f"[FATAL] {CONFIG_FILE} not found.")
    except json.JSONDecodeError as e:
        raise SystemExit(f"[FATAL] {CONFIG_FILE} is invalid JSON: {e}")

def load_seen():
    """Returns an OrderedDict used as an ordered set for stable trimming."""
    if os.path.exists(SEEN_FILE):
        try:
            with open(SEEN_FILE) as f:
                items = json.load(f)
            return collections.OrderedDict.fromkeys(items)
        except Exception:
            pass
    return collections.OrderedDict()

def save_seen(od):
    items = list(od.keys())[-5000:]   # oldest keys dropped first — stable order
    with open(SEEN_FILE, "w") as f:
        json.dump(items, f)

def load_state():
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE) as f:
                return json.load(f)
        except Exception:
            pass
    return {"quiet_runs": 0}

def save_state(state):
    with open(STATE_FILE, "w") as f:
        json.dump(state, f)

# ── telegram ──────────────────────────────────────────────────────────────────

def send_telegram(bot_token, chat_id, message, retries=1):
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": message,
        "parse_mode": "HTML",
        "disable_web_page_preview": True,
    }
    payload["text"] = payload["text"][:4090]   # Telegram hard limit is 4096
    for attempt in range(retries + 1):
        try:
            r = requests.post(url, json=payload, timeout=10)
            if r.ok:
                return True
            print(f"  [TELEGRAM ERROR] {r.status_code}: {r.text}")
            if attempt < retries:
                time.sleep(3)
        except requests.RequestException as e:
            print(f"  [TELEGRAM EXCEPTION] {e}")
            if attempt < retries:
                time.sleep(3)
    return False
    # Note: callers only add to `seen` on True — failed alerts are retried next run.

# ── rss ───────────────────────────────────────────────────────────────────────

def fetch_rss(subreddit, feed_type="new"):
    if feed_type == "comments":
        url = f"https://www.reddit.com/r/{subreddit}/comments/.rss?limit=100"
    else:
        url = f"https://www.reddit.com/r/{subreddit}/new/.rss?limit=100"
    try:
        r = requests.get(url, headers=HEADERS, timeout=20)
        r.raise_for_status()
        root = ET.fromstring(r.content)
        return root.findall("atom:entry", NS)
    except Exception as e:
        print(f"  [ERROR] r/{subreddit} {feed_type}: {e}")
        return None   # None = fetch failed; [] = fetched but empty

def get_entry_data(entry):
    eid     = entry.findtext("atom:id", default="", namespaces=NS).strip()
    title   = entry.findtext("atom:title", default="", namespaces=NS).strip()
    content = entry.findtext("atom:content", default="", namespaces=NS).strip()
    link_el = entry.find("atom:link", NS)
    link    = link_el.get("href", "") if link_el is not None else ""
    author  = entry.findtext("atom:author/atom:name", default="", namespaces=NS).strip()
    # `updated` omitted — not used downstream
    return eid, title, content, link, author

# ── text helpers ──────────────────────────────────────────────────────────────

def strip_html(text):
    return re.sub(r"<[^>]+>", " ", text).strip()

def matches_keyword(text, keyword):
    """Plain substring match (case-insensitive). Catches CGL2024, #CGLprep, r/SSCCGL etc."""
    if not text:
        return False
    return keyword.lower() in text.lower()

def find_matches(text, keywords):
    return [kw for kw in keywords if matches_keyword(text, kw)]

# ── formatters ────────────────────────────────────────────────────────────────

def format_post_alert(subreddit, title, content, link, author, matched_in_title, matched_in_body):
    lines = [
        f"🔴 <b>New Post</b> — r/{subreddit}",
        f"📌 <b>{title}</b>\n"
    ]
    if content:
        preview = content[:800] + ("..." if len(content) > 800 else "")
        lines.append(f"📝 <i>{preview}</i>\n")
    if matched_in_title:
        lines.append(f"🎯 <b>Title:</b> <code>{', '.join(matched_in_title)}</code>")
    if matched_in_body:
        lines.append(f"📄 <b>Body:</b> <code>{', '.join(matched_in_body)}</code>")
    lines.append(f"👤 {author}")
    lines.append(f"🔗 {link}")
    return "\n".join(lines)

def format_comment_alert(subreddit, content, link, author, matched_kws):
    plain   = strip_html(content)
    preview = plain[:800] + ("..." if len(plain) > 800 else "")
    return (
        f"💬 <b>New Comment</b> — r/{subreddit}\n\n"
        f"📝 <i>{preview}</i>\n\n"
        f"🎯 <b>Comment Match:</b> <code>{', '.join(matched_kws)}</code>\n"
        f"👤 {author}\n"
        f"🔗 {link}"
    )

# ── main ──────────────────────────────────────────────────────────────────────

def main():
    bot_token = get_env("TELEGRAM_BOT_TOKEN")
    chat_id   = get_env("TELEGRAM_CHAT_ID")
    config    = load_config()
    seen      = load_seen()
    state     = load_state()

    watches = config.get("watches", [])

    # Global defaults; can be overridden per-watch in future
    default_check_posts    = config.get("check_posts", True)
    default_check_body     = config.get("check_body", True)
    default_check_comments = config.get("check_comments", True)

    alerts_sent = 0

    for watch in watches:
        subreddit = watch["subreddit"].strip()
        keywords  = [kw.strip() for kw in watch.get("keywords", []) if kw.strip()]
        if not keywords:
            continue

        # Per-watch overrides with global fallback
        check_posts    = watch.get("check_posts",    default_check_posts)
        check_body     = watch.get("check_body",     default_check_body)
        check_comments = watch.get("check_comments", default_check_comments)

        print(f"\n▶ r/{subreddit}  |  {len(keywords)} keywords")

        if check_posts or check_body:
            entries = fetch_rss(subreddit, "new")
            time.sleep(2)

            if entries is not None:
                for entry in entries:
                    eid, title, content, link, author = get_entry_data(entry)
                    if not eid or eid in seen:
                        continue

                    matched_in_title = find_matches(title, keywords) if check_posts else []
                    matched_in_body  = find_matches(strip_html(content), keywords) if check_body else []
                    matched_in_body  = [k for k in matched_in_body if k not in matched_in_title]

                    if matched_in_title or matched_in_body:
                        all_kws = matched_in_title + matched_in_body
                        print(f"  ✅ Post: {all_kws} → {title[:60]}")
                        msg = format_post_alert(subreddit, title, strip_html(content), link, author, matched_in_title, matched_in_body)
                        ok  = send_telegram(bot_token, chat_id, msg, retries=1)
                        if ok:
                            alerts_sent += 1
                            seen[eid] = None   # only mark seen after successful delivery
                        time.sleep(0.5)
                    else:
                        seen[eid] = None

        if check_comments:
            entries = fetch_rss(subreddit, "comments")
            time.sleep(2)

            if entries is not None:
                for entry in entries:
                    eid, title, content, link, author = get_entry_data(entry)
                    cid = "c_" + eid
                    if not eid or cid in seen:
                        continue

                    plain = strip_html(content)
                    matched_kws = find_matches(plain, keywords)
                    if matched_kws:
                        print(f"  ✅ Comment: {matched_kws} → {plain[:60]}")
                        msg = format_comment_alert(subreddit, content, link, author, matched_kws)
                        ok  = send_telegram(bot_token, chat_id, msg, retries=1)
                        if ok:
                            alerts_sent += 1
                            seen[cid] = None   # only mark seen after successful delivery
                        time.sleep(0.5)
                    else:
                        seen[cid] = None

    save_seen(seen)

    print(f"\n✔ Done. Alerts sent: {alerts_sent}")

    # Heartbeat: fires every HEARTBEAT_N consecutive quiet runs.
    # Resets on any successful alert — intentional, a match means pipeline is live.
    if alerts_sent == 0:
        state["quiet_runs"] = state.get("quiet_runs", 0) + 1
        if state["quiet_runs"] >= HEARTBEAT_N:
            now = (
                datetime.datetime.now(datetime.timezone.utc)
                + datetime.timedelta(hours=5, minutes=30)
            ).strftime("%d %b %Y %H:%M IST")
            msg = (
                f"🔍 <b>Reddit Monitor</b>\n"
                f"━━━━━━━━━━━━━━━━━━━━\n"
                f"No keyword matches in last {HEARTBEAT_N} runs.\n"
                f"🕐 {now}\n"
                f"📡 {len(watches)} subreddits checked"
            )
            send_telegram(bot_token, chat_id, msg, retries=1)
            state["quiet_runs"] = 0
    else:
        state["quiet_runs"] = 0

    save_state(state)

if __name__ == "__main__":
    main()
