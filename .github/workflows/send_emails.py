import os
import json
import requests
import csv
from datetime import datetime

COMPOSIO_API_KEY = os.environ["COMPOSIO_API_KEY"]
SHEET_ID = os.environ["SHEET_ID"]
DAILY_LIMIT = 45
PER_ACCOUNT_LIMIT = 15
PROGRESS_FILE = "progress.json"

# Your 3 Gmail accounts - we'll fill these after connecting them
GMAIL_ACCOUNTS = [
    "account1@gmail.com",
    "account2@gmail.com", 
    "account3@gmail.com",
]

EMAIL_SUBJECT = "Quick note for {first_name}"

EMAIL_BODY = """Hi {first_name},

I came across {company} and wanted to reach out personally.

{custom_line}

Would love to connect and see if there's a fit.

Best,
Stanley"""


def load_progress():
    if os.path.exists(PROGRESS_FILE):
        with open(PROGRESS_FILE, "r") as f:
            return json.load(f)
    return {"last_row": 1}  # 1 means header row already skipped


def save_progress(data):
    with open(PROGRESS_FILE, "w") as f:
        json.dump(data, f)


def fetch_leads():
    # Fetch sheet as CSV using the public sheet ID
    url = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv"
    response = requests.get(url)
    response.raise_for_status()
    lines = response.text.splitlines()
    reader = csv.DictReader(lines)
    return list(reader)


def send_email(to_email, subject, body, gmail_account):
    url = "https://backend.composio.dev/api/v1/actions/GMAIL_SEND_EMAIL/execute"
    headers = {
        "x-api-key": COMPOSIO_API_KEY,
        "Content-Type": "application/json"
    }
    payload = {
        "connectedAccountId": gmail_account,  # will update this after connecting
        "input": {
            "recipient_email": to_email,
            "subject": subject,
            "body": body,
            "is_html": False
        }
    }
    response = requests.post(url, json=payload, headers=headers)
    return response.status_code == 200


def main():
    progress = load_progress()
    leads = fetch_leads()
    
    start = progress["last_row"]
    batch = leads[start:start + DAILY_LIMIT]

    if not batch:
        print("No more leads to send. All done!")
        return

    sent_count = 0
    for i, lead in enumerate(batch):
        # Rotate across 3 accounts, 15 each
        account = GMAIL_ACCOUNTS[i // PER_ACCOUNT_LIMIT]
        
        subject = EMAIL_SUBJECT.format(first_name=lead["first_name"])
        body = EMAIL_BODY.format(
            first_name=lead["first_name"],
            company=lead.get("company", "your company"),
            custom_line=lead.get("custom_line", "")
        )

        success = send_email(lead["email"], subject, body, account)
        
        if success:
            sent_count += 1
            print(f"Sent to {lead['email']}")
        else:
            print(f"Failed: {lead['email']}")

    progress["last_row"] = start + len(batch)
    progress["last_run"] = datetime.utcnow().isoformat()
    progress["total_sent"] = progress.get("total_sent", 0) + sent_count
    save_progress(progress)
    print(f"Done. Sent {sent_count} emails today. Total so far: {progress['total_sent']}")


if __name__ == "__main__":
    main()
