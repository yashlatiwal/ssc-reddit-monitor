# Reddit Keyword Monitor → Telegram

Monitors subreddits for keywords. Sends Telegram notifications via GitHub Actions (free, hourly).

---

## Setup (one-time, ~5 mins)

### 1. Create a Telegram Bot
1. Open Telegram → message **@BotFather**
2. Send `/newbot` → follow prompts → copy the **bot token**
3. Start a chat with your new bot (send any message)
4. Get your **chat_id**:
   ```
   https://api.telegram.org/bot<YOUR_TOKEN>/getUpdates
   ```
   Look for `"chat":{"id":XXXXXXX}` in the response.

### 2. Create GitHub Repo
1. Create a **new private repo** on GitHub
2. Push all files from this folder into it:
   ```bash
   git init
   git add .
   git commit -m "init"
   git remote add origin https://github.com/YOUR_USER/YOUR_REPO.git
   git push -u origin main
   ```

### 3. Add Secrets to GitHub
Go to: **Repo → Settings → Secrets and variables → Actions → New repository secret**

| Secret Name           | Value                    |
|-----------------------|--------------------------|
| `TELEGRAM_BOT_TOKEN`  | Your bot token           |
| `TELEGRAM_CHAT_ID`    | Your chat ID (number)    |

### 4. Edit `config.json`
```json
{
  "check_posts": true,
  "check_body": true,
  "check_comments": true,
  "watches": [
    {
      "subreddit": "india",
      "keywords": ["SSC", "CGL", "CHSL"]
    },
    {
      "subreddit": "learnpython",
      "keywords": ["automation", "scraper"]
    }
  ]
}
```
Commit and push → GitHub Actions picks it up automatically.

### 5. Enable Actions
Go to **Actions tab** in your repo → Enable workflows if prompted.
You can also click **"Run workflow"** to test immediately.

---

## How it works
- Runs every hour via GitHub Actions cron
- Fetches latest posts + comments from each subreddit using Reddit's public JSON API (no API key needed)
- Checks title, body, and comments against your keywords (case-insensitive)
- Sends a formatted Telegram message for each match
- Saves seen IDs to `seen_ids.json` (committed back to repo) to avoid duplicate alerts
- Keeps last 5000 seen IDs to prevent unbounded growth

## Telegram Alert Format

**Post match:**
```
🔔 Reddit Alert | r/india
━━━━━━━━━━━━━━━━━━━━
🎯 Keyword: SSC  (in title)
📌 SSC CGL 2024 result declared
👤 u/someone  •  🕐 2025-01-15 10:30 UTC
🔗 Open Post
```

**Comment match:**
```
💬 Comment Alert | r/india
━━━━━━━━━━━━━━━━━━━━
🎯 Keyword: CGL
📝 I cleared SSC CGL this year after...
👤 u/someone  •  🕐 2025-01-15 10:30 UTC
🔗 Open Comment
```

## Notes
- Uses Reddit's public JSON API — no Reddit API credentials needed
- Rate limit: Reddit allows ~60 req/min for unauthenticated; this script stays well within that
- GitHub Actions free tier: 2000 min/month — hourly runs use ~24 min/day (well within limit)
