#!/usr/bin/env python3
"""
Reddit Keyword Monitor → Telegram Notifier
Uses RSS feeds. Shows match location (title/body/comment). Word boundary matching.
"""

import os
import json
import time
import re
import xml.etree.ElementTree as ET
import requests

CONFIG_FILE = "config.json"
SEEN_FILE   = "seen_ids.json"
HEADERS     = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

NS = {
    "atom": "http://www.w3.org/2005/Atom",
    "media": "http://search.yahoo.com/mrss/"
}

def load_config():
    with open(CONFIG_FILE) as f:
        return json.load(f)

def load_seen():
    if os.path.exists(SEEN_FILE):
        with open(SEEN_FILE) as f:
            return set(json.load(f))
    return set()

def save_seen(seen):
    trimmed = list(seen)[-5000:]
    with open(SEEN_FILE, "w") as f:
        json.dump(trimmed, f)

def send_telegram(bot_token, chat_id, message):
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": message,
        "parse_mode": "HTML",
        "disable_web_page_preview": True,
    }
    r = requests.post(url, json=payload, timeout=10)
    if not r.ok:
        print(f"  [TELEGRAM ERROR] {r.status_code}: {r.text}")
    return r.ok

def fetch_rss(subreddit, feed_type="new"):
    if feed_type == "comments":
        url = f"https://www.reddit.com/r/{subreddit}/comments/.rss?limit=25"
    else:
        url = f"https://www.reddit.com/r/{subreddit}/new/.rss?limit=25"
    try:
        r = requests.get(url, headers=HEADERS, timeout=20)
        r.raise_for_status()
        root = ET.fromstring(r.content)
        return root.findall("atom:entry", NS)
    except Exception as e:
        print(f"  [ERROR] r/{subreddit} {feed_type}: {e}")
        return []

def get_entry_data(entry):
    eid     = entry.findtext("atom:id", default="", namespaces=NS).strip()
    title   = entry.findtext("atom:title", default="", namespaces=NS).strip()
    content = entry.findtext("atom:content", default="", namespaces=NS).strip()
    link_el = entry.find("atom:link", NS)
    link    = link_el.get("href", "") if link_el is not None else ""
    author  = entry.findtext("atom:author/atom:name", default="", namespaces=NS).strip()
    updated = entry.findtext("atom:updated", default="", namespaces=NS).strip()
    return eid, title, content, link, author, updated

def strip_html(text):
    return re.sub(r"<[^>]+>", " ", text).strip()

def matches_keyword(text, keyword):
    """
    Word-boundary aware matching.
    Short keywords (1 word, <=4 chars) require word boundaries.
    Multi-word or longer keywords use simple substring match.
    """
    if not text:
        return False
    text_lower = text.lower()
    kw_lower   = keyword.lower()

    words = kw_lower.split()
    if len(words) == 1 and len(kw_lower) <= 4:
        # strict word boundary for short single words like "ows", "vocab"
        pattern = r'\b' + re.escape(kw_lower) + r'\b'
        return bool(re.search(pattern, text_lower))
    else:
        return kw_lower in text_lower

def find_matches(text, keywords):
    """Return list of all matched keywords."""
    found = []
    for kw in keywords:
        if matches_keyword(text, kw):
            found.append(kw)
    return found

def format_post_alert(subreddit, title, link, author, matched_in_title, matched_in_body):
    lines = [
        f"🔴 <b>New Post</b> — r/{subreddit}",
        f"📌 {title}",
    ]
    if matched_in_title:
        lines.append(f"🎯 <b>Title match:</b> <code>{', '.join(matched_in_title)}</code>")
    if matched_in_body:
        lines.append(f"📄 <b>Body match:</b> <code>{', '.join(matched_in_body)}</code>")
    lines.append(f"👤 {author}")
    lines.append(f"🔗 {link}")
    return "\n".join(lines)

def format_comment_alert(subreddit, content, link, author, matched_kws):
    preview = strip_html(content)[:200]
    return (
        f"💬 <b>New Comment</b> — r/{subreddit}\n"
        f"💬 <i>{preview}...</i>\n"
        f"🎯 <b>Comment match:</b> <code>{', '.join(matched_kws)}</code>\n"
        f"👤 {author}\n"
        f"🔗 {link}"
    )

def main():
    config    = load_config()
    seen      = load_seen()
    bot_token = os.environ["TELEGRAM_BOT_TOKEN"].strip()
    chat_id   = os.environ["TELEGRAM_CHAT_ID"].strip()

    watches        = config.get("watches", [])
    check_posts    = config.get("check_posts", True)
    check_body     = config.get("check_body", True)
    check_comments = config.get("check_comments", True)

    alerts_sent = 0

    for watch in watches:
        subreddit = watch["subreddit"].strip()
        keywords  = [kw.strip() for kw in watch.get("keywords", []) if kw.strip()]
        if not keywords:
            continue

        print(f"\n▶ r/{subreddit}  |  {len(keywords)} keywords")

        # ── Posts ──────────────────────────────────────────────────────────
        if check_posts or check_body:
            entries = fetch_rss(subreddit, "new")
            time.sleep(2)

            for entry in entries:
                eid, title, content, link, author, updated = get_entry_data(entry)
                if not eid or eid in seen:
                    continue

                matched_in_title = find_matches(title, keywords) if check_posts else []
                matched_in_body  = find_matches(strip_html(content), keywords) if check_body else []

                # Remove body matches that are already in title matches
                matched_in_body = [k for k in matched_in_body if k not in matched_in_title]

                if matched_in_title or matched_in_body:
                    all_kws = matched_in_title + matched_in_body
                    print(f"  ✅ Post: {all_kws} → {title[:60]}")
                    msg = format_post_alert(subreddit, title, link, author, matched_in_title, matched_in_body)
                    send_telegram(bot_token, chat_id, msg)
                    alerts_sent += 1
                    time.sleep(0.5)

                seen.add(eid)

        # ── Comments ───────────────────────────────────────────────────────
        if check_comments:
            entries = fetch_rss(subreddit, "comments")
            time.sleep(2)

            for entry in entries:
                eid, title, content, link, author, updated = get_entry_data(entry)
                cid = "c_" + eid
                if not eid or cid in seen:
                    continue

                matched_kws = find_matches(strip_html(content), keywords)
                if matched_kws:
                    print(f"  ✅ Comment: {matched_kws} → {strip_html(content)[:60]}")
                    msg = format_comment_alert(subreddit, content, link, author, matched_kws)
                    send_telegram(bot_token, chat_id, msg)
                    alerts_sent += 1
                    time.sleep(0.5)

                seen.add(cid)

    save_seen(seen)
    print(f"\n✔ Done. Alerts sent: {alerts_sent}")

if __name__ == "__main__":
    main()
