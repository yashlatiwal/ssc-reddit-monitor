import feedparser
import requests
import os
import time

# --- 1. YOUR TARGETS ---
# Combined subreddits (Duplicates removed)
SUBREDDITS = "ssc+SSCCGL+SSC_CGL_Beginners+SSCexamsIndia+SSCEnglish" 

# Comprehensive keyword list for SSC English With Yash
KEYWORDS = [
    # Books, Educators & Resources
    "blackbook english", "pinnacle english", "neetu singh vol 1", "neetu singh vol 2", 
    "plinth to paramount", "kiran english pyq", "mb publication english", "ajay k singh english", 
    "mirror of common errors", "sp bakshi", "word power made easy", "norman lewis", 
    "wren and martin", "objective general english", "english for general competitions", 
    "pinnacle vs kiran", "blackbook vs word power", "neetu singh vs rani ma'am", "ssc english notes", 
    "english pdf for ssc", "vocab pdf", "best book for ssc english", "gagan pratap english", 
    "abhinay maths english", "rbe english", "testbook mocks", "oliveboard english mocks", 
    "practicemock", "ssc english previous year", "tcs pattern english", "latest tcs vocab", 
    "tcs english questions", "cgl 2025 solved", "english sectional mock", "english quiz", 
    "ssc english telegram", "english daily plan", "vocab daily target", "grammar notes", 
    "english practice set", "volume 1", "mb publication", "pinnacle",

    # Grammar & Core Topics
    "common errors", "sentence improvement", "fill in the blanks", "active passive voice", 
    "direct indirect speech", "narration", "spotting errors", "subject verb agreement", "tense rules", 
    "conditional sentences", "noun errors", "pronoun rules", "adjective degrees", "adverb position", 
    "preposition chart", "fixed prepositions", "phrasal verbs list", "conjunctions", "question tag", 
    "articles rules", "gerund vs infinitive", "participles", "modal auxiliaries", "inversion grammar", 
    "causative verbs", "parallelism in english", "clause analysis", "synthesis of sentences", 
    "transformation of sentences", "subjunctive mood", "articles a an the", "prepositional phrases", 
    "sentence rearrangement", "pqrs tricks", "jumbled sentences", "cloze test tips", "reading comprehension", 
    "passage solving", "sentence completion", "error detection", "spelling correction", "homonyms", 
    "confusing words", "grammar logic", "etymology", "root word method", "grammar concepts", 
    "functional grammar", "english rules pdf", "grammar for ssc", "active passive", "jumbled", 
    "cloze test", "comprehension", "error spotting", "grammar rules",

    # Vocabulary & Word Power
    "one word substitution", "idioms and phrases", "synonyms antonyms", "tcs vocab", "repeated ssc vocab", 
    "hindu vocabulary", "daily vocab", "vocab for cgl", "vocab tricks", "how to remember vocab", 
    "mnemonics for english", "vocabulary for stenographer", "hardest ssc vocab", "exam oriented vocab", 
    "vocab strategy", "vocab made easy", "root words a-z", "prefix suffix", "greek roots", "latin roots", 
    "commonly misspelled words", "foreign words in english", "phrasals for ssc", "idioms for cgl", 
    "a-z synonyms", "vocabulary booster", "word of the day ssc", "english word power", "vocab quiz", 
    "vocabulary schedule", "how to finish blackbook", "blackbook review", "vocab short notes", 
    "vocabulary mapping", "contextual vocabulary", "sentence based vocab", "vocab flashcards", 
    "ssc english words", "vocabulary revision", "vocab audio", "english root words list", "vocab help", 
    "vocabulary group", "vocab challenges", "improve english vocab", "phrasal verbs", "ows", "idioms", 
    "root words", "vocab", "vocabulary",

    # Strategy & Pain Points
    "english score not increasing", "how to improve english", "english for beginners", "ssc english weak", 
    "zero level english", "english strategy for 2026", "cgl english 45/45", "mains english 135/135", 
    "negative marking in english", "time management english", "how to read newspaper", "editorial analysis", 
    "english mock analysis", "sectional score low", "english comprehension help", "cloze test accuracy", 
    "pqrs time taking", "grammar vs vocab", "reading habit for ssc", "how to start english prep", 
    "english preparation tips", "english fear", "ssc english medium vs hindi", "english grammar logic", 
    "why i fail in english", "english scoring topics", "most important english topics", "ssc english daily routine", 
    "6 month english plan", "ssc english crash course", "english youtube channel", "ssc english teacher", 
    "yash english", "ssc english with yash", "lecture studio app", "english notes free", "best way to learn grammar", 
    "english doubt solving", "ssc english forum", "english community", "english weak", "improve english", 
    "english strategy", "english score"
]

# --- 2. SECRETS FROM GITHUB ---
TG_BOT_TOKEN = os.environ.get("TG_BOT_TOKEN")
TG_CHAT_ID = os.environ.get("TG_CHAT_ID")

def send_telegram_message(text):
    url = f"https://api.telegram.org/bot{TG_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": TG_CHAT_ID, "text": text, "parse_mode": "HTML", "disable_web_page_preview": True}
    try:
        response = requests.post(url, json=payload)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"Error sending Telegram message: {e}")

def main():
    # Reddit RSS URL for combined subreddits sorted by new
    rss_url = f"https://www.reddit.com/r/{SUBREDDITS}/new.rss"
    
    # We must use a standard web browser header, or Reddit will block the RSS request
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
    
    print(f"Fetching RSS feed: {rss_url}")
    try:
        response = requests.get(rss_url, headers=headers)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"Error fetching RSS feed: {e}")
        return

    feed = feedparser.parse(response.content)
    
    # Calculate time 65 minutes ago
    time_limit = time.time() - (65 * 60)
    
    for entry in feed.entries:
        # Convert RSS publication time to standard timestamp
        try:
            entry_time = time.mktime(entry.published_parsed)
        except AttributeError:
            continue # Skip if date cannot be parsed
        
        # Check 1: Is the post from the last hour?
        if entry_time > time_limit:
            
            # Combine title and body text, convert to lowercase for matching
            title = entry.title if hasattr(entry, 'title') else ""
            summary = entry.summary if hasattr(entry, 'summary') else ""
            full_text = (title + " " + summary).lower()
            
            # Check 2: Are any of our keywords in the text?
            matched_keywords = [kw for kw in KEYWORDS if kw in full_text]
            
            if matched_keywords:
                # Get the specific subreddit name
                sub_name = entry.tags[0].term if hasattr(entry, 'tags') and len(entry.tags) > 0 else 'Reddit'
                author_name = entry.author if hasattr(entry, 'author') else 'Unknown'
                post_link = entry.link if hasattr(entry, 'link') else ''

                msg = (
                    f"🔴 <b>New Post — r/{sub_name}</b>\n"
                    f"📌 {title}\n"
                    f"🔑 <i>Matched: {', '.join(matched_keywords)}</i>\n"
                    f"👤 {author_name}\n"
                    f"🔗 {post_link}"
                )
                send_telegram_message(msg)
                print(f"Alert sent for: {title}")

if __name__ == "__main__":
    main()
