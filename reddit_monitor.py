import feedparser
import requests
import os
import time

# --- 1. YOUR TARGETS ---
SUBREDDITS = "SSCCGL+SSC+IndiaCareer+ssc_cgl" 
KEYWORDS = [
    "english", "grammar", "vocab", "vocabulary", 
    "sp bakshi", "blackbook", "phrasal verbs", 
    "one-word substitutions", "idioms", "comprehension"
]

# --- 2. SECRETS FROM GITHUB ---
TG_BOT_TOKEN = os.environ.get("TG_BOT_TOKEN")
TG_CHAT_ID = os.environ.get("TG_CHAT_ID")

def send_telegram_message(text):
    url = f"https://api.telegram.org/bot{TG_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": TG_CHAT_ID, "text": text, "parse_mode": "HTML"}
    requests.post(url, json=payload)

def main():
    # Reddit RSS URL for combined subreddits sorted by new
    rss_url = f"https://www.reddit.com/r/{SUBREDDITS}/new.rss"
    
    # We must use a standard web browser header, or Reddit will block the RSS request
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
    
    print(f"Fetching RSS feed: {rss_url}")
    response = requests.get(rss_url, headers=headers)
    feed = feedparser.parse(response.content)
    
    # Calculate time 65 minutes ago
    time_limit = time.time() - (65 * 60)
    
    for entry in feed.entries:
        # Convert RSS publication time to standard timestamp
        entry_time = time.mktime(entry.published_parsed)
        
        # Check 1: Is the post from the last hour?
        if entry_time > time_limit:
            
            # Combine title and body text, convert to lowercase
            full_text = (entry.title + " " + entry.summary).lower()
            
            # Check 2: Are any of our keywords in the text?
            matched_keywords = [kw for kw in KEYWORDS if kw in full_text]
            
            if matched_keywords:
                msg = (
                    f"🔴 <b>New Post — r/{entry.tags[0].term if hasattr(entry, 'tags') else 'Reddit'}</b>\n"
                    f"📌 {entry.title}\n"
                    f"🔑 <i>Matched: {', '.join(matched_keywords)}</i>\n"
                    f"👤 {entry.author}\n"
                    f"🔗 {entry.link}"
                )
                send_telegram_message(msg)
                print(f"Alert sent for: {entry.title}")

if __name__ == "__main__":
    main()
