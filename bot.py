import feedparser
import requests
import time
import json
import os

# config: read from env (set these as GitHub secrets)
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

RSS_FEEDS = [
    "https://openai.com/blog/rss.xml",
    "https://deepmind.com/blog/rss.xml",
    "https://huggingface.co/blog/feed.xml",
    "https://www.microsoft.com/en-us/research/feed/"
]

CHECK_INTERVAL = 300 # Check every 5 minutes (in seconds)
SENT_ITEMS_FILE = "sent_items.json" # File to keep track of sent items
# --- End of Configuration ---

def load_sent_items():
    """Loads the set of already-sent item IDs from a file."""
    try:
        with open(SENT_ITEMS_FILE, 'r') as f:
            # Load as a set for efficient lookups
            return set(json.load(f))
    except (FileNotFoundError, json.JSONDecodeError):
        return set()

def save_sent_items(sent_items):
    """Saves the set of sent item IDs to a file."""
    with open(SENT_ITEMS_FILE, 'w') as f:
        json.dump(list(sent_items), f)

def send_telegram_message(chat_id, text):
    """Sends a message to a Telegram chat using the Bot API."""
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        'chat_id': chat_id,
        'text': text,
        'parse_mode': 'HTML',
        'disable_web_page_preview': False  # We want link previews!
    }
    try:
        response = requests.post(url, data=payload)
        response.raise_for_status() # Raise an exception for bad status codes
        print(f"Message sent successfully: {text[:50]}...")
    except requests.exceptions.RequestException as e:
        print(f"Error sending message: {e}")

def check_feeds():
    """Checks all configured RSS feeds for new posts."""
    sent_items = load_sent_items()
    print(f"Checking {len(RSS_FEEDS)} feeds...")

    for feed_url in RSS_FEEDS:
        print(f"Parsing: {feed_url}")
        try:
            feed = feedparser.parse(feed_url)
            
            # Handle feed parsing errors
            if feed.bozo:
                print(f"Warning: Feed might be malformed ({feed_url}). Error: {feed.bozo_exception}")
                # Continue processing entries anyway, as some may still be valid

            for entry in feed.entries:
                item_id = entry.get('id') or entry.get('link') # Use ID or link as a unique key
                if not item_id:
                    continue
                
                if item_id not in sent_items:
                    title = entry.get('title', 'No Title')
                    link = entry.get('link')
                    print(f"New post found: {title}")
                    
                    if link:
                        message = f"<b>{title}</b>\n<a href='{link}'>Read more</a>"
                    else:
                        message = f"<b>{title}</b>"

                    send_telegram_message(TELEGRAM_CHAT_ID, message)
                    sent_items.add(item_id)
                    # Be gentle with servers, avoid rapid-fire requests
                    time.sleep(1) 
                    
        except Exception as e:
            print(f"An unexpected error occurred while processing {feed_url}: {e}")

    save_sent_items(sent_items)
    print(f"Check complete. Next check in {CHECK_INTERVAL} seconds.")

if __name__ == "__main__":
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("Error: TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID environment variables must be set.")
        exit(1)
    check_feeds()
