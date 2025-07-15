from flask import Flask, jsonify
import requests
from datetime import datetime, timedelta, timezone
import os
import re

app = Flask(__name__)

# === Configuration ===
SENT_LOG = "sent_bounties.txt"
SLACK_WEBHOOK_URL = os.getenv("SLACK_WEBHOOK_URL")
FIRECRAWL_API_KEY = os.getenv("FIRECRAWL_API_KEY")

# === Health check endpoint for Vercel ===
@app.route("/")
def health():
    return jsonify({"status": "ok"})

def parse_posted_time(text):
    match = re.search(r'(\d+)\s+(minute|hour|day|month)s?\s+ago', text)
    if not match:
        return None
    value = int(match.group(1))
    unit = match.group(2)
    now = datetime.now(timezone.utc)
    if unit == 'minute':
        return now - timedelta(minutes=value)
    elif unit == 'hour':
        return now - timedelta(hours=value)
    elif unit == 'day':
        return now - timedelta(days=value)
    elif unit == 'month':
        return now - timedelta(days=30 * value)
    return None

def extract_bounties_with_time(firecrawl_json):
    markdown = firecrawl_json["data"].get("markdown", "")
    lines = markdown.splitlines()
    bounties = []
    current_price = None
    current_posted_time = None
    current_title = None
    current_link = None
    description_lines = []
    user = None
    due_date = None
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        price_match = re.match(r'- \$([0-9,.]+)', line)
        if price_match:
            current_price = float(price_match.group(1).replace(',', ''))
        if 'ago' in line:
            current_posted_time = parse_posted_time(line)
        title_match = re.match(r'### \[(.*?)\]\((.*?)\)', line)
        if title_match:
            current_title = title_match.group(1)
            current_link = title_match.group(2)
            description_lines = []
            user = None
            due_date = None
            for j in range(i+1, min(i+15, len(lines))):
                lookahead = lines[j].strip()
                if lookahead.startswith("### ["):
                    break
                if 'due' in lookahead:
                    due_match = re.search(r'due\s+(.*?)(?:\n|$)', lookahead)
                    if due_match:
                        due_date = due_match.group(1).strip()
                if re.match(r'\[.*\]\(https://replit.com/@.*\)', lookahead):
                    user_match = re.match(r'\[(.*?)\]\(.*?\)', lookahead)
                    if user_match:
                        user = user_match.group(1)
                description_lines.append(lookahead)
            description = ' '.join(description_lines).strip()
            if current_posted_time and (datetime.now(timezone.utc) - current_posted_time).total_seconds() <= 86400:
                bounties.append({
                    'title': current_title,
                    'link': current_link,
                    'price': current_price,
                    'posted_time': current_posted_time,
                    'description': description
                })
            current_price = None
            current_posted_time = None
            current_title = None
            current_link = None
        i += 1
    return bounties

def get_top_bounties(bounties):
    if not bounties:
        print("⚠️ No bounties found")
        return []
    max_price = max(b['price'] for b in bounties)
    top_bounties = [b for b in bounties if b['price'] == max_price]
    print(f"🏆 Found {len(top_bounties)} top bounties at ${max_price}:")
    for b in top_bounties:
        print(b)
    return top_bounties

def get_bounties():
    print("📡 Fetching bounties via Firecrawl /scrape API...")
    url ="https://api.firecrawl.dev/v1/scrape"

    headers = {
        "Authorization": f"Bearer {FIRECRAWL_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "url": "https://replit.com/bounties",
        "formats": ["markdown"],
        "onlyMainContent": False,
        "waitFor": 2000
    }
    try:
        resp = requests.post(url, headers=headers, json=payload, timeout=60)
        data = resp.json()
        print("[DEBUG] Raw Firecrawl API response:")
        print(data)
        bounties = extract_bounties_with_time(data)
        print(f"✅ Parsed {len(bounties)} bounties")
        for b in bounties:
            print(f"[DEBUG] Parsed Bounty: {b['title']} | Price: {b['price']} | Date: {b['posted_time']} | Link: {b['link']}")
        return bounties
    except requests.exceptions.Timeout:
        print("❌ Firecrawl API request timed out after 60 seconds.")
        return []
    except Exception as e:
        print(f"❌ Firecrawl API error: {e}")
        return []

# === Utility functions ===
def filter_recent(bounties):
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(hours=24)
    print(f"[DEBUG] Now: {now.isoformat()}, Cutoff: {cutoff.isoformat()}")
    for b in bounties:
        print(f"[DEBUG] Bounty: {b['title']} | Created At: {b['created_at'].isoformat()}")
    return [b for b in bounties if b["created_at"] > cutoff]

def read_sent_links():
    return set(open(SENT_LOG).read().splitlines()) if os.path.exists(SENT_LOG) else set()

def write_sent_link(link):
    with open(SENT_LOG, "a") as f:
        f.write(link + "\n")

def send_to_slack(bounty):
    if not SLACK_WEBHOOK_URL:
        print("⚠️ Slack webhook not configured")
        return
    print(f"[DEBUG] Sending to Slack: {bounty['title']} | {bounty['link']}")
    msg = {
        "text": f"🔥 New Top Bounty!\n*{bounty['title']}*\n🔗 {bounty['link']}"
    }
    res = requests.post(SLACK_WEBHOOK_URL, json=msg)
    print("✅ Slack sent" if res.status_code == 200 else f"❌ Slack error: {res.text}")

# === Main scraping logic (can be called by endpoint or scheduler) ===
def run_scraper():
    bounties = get_bounties()
    top_bounties = get_top_bounties(bounties)
    sent = read_sent_links()
    unsent = [b for b in top_bounties if b["link"] not in sent]
    if not unsent:
        return {"message": "No new bounties found in the last 24 hours."}
    top = unsent[0]
    send_to_slack({"title": top["title"], "link": top["link"]})
    write_sent_link(top["link"])
    return {"message": "Sent top bounty to Slack.", "bounty": top}

# === Flask endpoint ===
@app.route("/scrape", methods=["GET"])
def scrape_bounties():
    result = run_scraper()
    return jsonify(result)

# === Debug endpoint to view all parsed bounties ===
@app.route("/bounties", methods=["GET"])
def view_bounties():
    bounties = get_bounties()
    return jsonify({"bounties": [
        {
            "title": b["title"],
            "price": b["price"],
            "link": b["link"],
            "posted_time": b["posted_time"].isoformat() if isinstance(b["posted_time"], datetime) else str(b["posted_time"])
        }
        for b in bounties
    ]})

# For Vercel: do not use app.run()
if __name__ == "__main__":
    app.run(debug=True)
