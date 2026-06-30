from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
import os
from dotenv import load_dotenv
load_dotenv()
import base64
import redis

PERSONAl_EMAIL = os.getenv("PERSONAL_EMAIL")
COLLEGE_EMAIL = os.getenv("COLLEGE_EMAIL")
WORK_EMAIL = os.getenv("WORK_EMAIL")
REDIS_URL=os.getenv("REDIS_URL")

# Shared, persistent store -> survives restarts and works across multiple workers
r = redis.Redis.from_url(os.getenv("REDIS_URL"), decode_responses=True)

PROCESSED_TTL_SECONDS = 60 * 60 * 24 * 7  # keep msg_id dedup keys for 7 days


def authenticate(token_path):
    """Authenticating and creating credentials for gmail"""

    SCOPES = ["https://www.googleapis.com/auth/gmail.modify"]
    if os.path.exists(token_path):
        creds = Credentials.from_authorized_user_file(
            token_path, scopes=SCOPES
        )
    else:
        raise Exception("token.json not found")

    service=build(serviceName="gmail", version="v1", credentials=creds)

    return service


def get_email_body(payload):
    """Recursively extract plain text body from any email structure"""

    if "parts" in payload:
        for part in payload["parts"]:
            result = get_email_body(part)
            if result:
                return result

    if payload.get("mimeType") == "text/plain":
        data = payload.get("body", {}).get("data")
        if data:
            return base64.urlsafe_b64decode(data).decode("utf-8")

    return None


def get_email_metadata(email):
    """Extract sender, subject, body, and receiver from email"""

    headers = email["payload"]["headers"]

    subject = next((h["value"] for h in headers if h["name"] == "Subject"), "No Subject")
    sender = next((h["value"] for h in headers if h["name"] == "From"), "Unknown Sender")
    receiver = next((h["value"] for h in headers if h["name"] == "To"), "Unknown Receiver")
    body = get_email_body(email["payload"])

    if not body:
        body = email.get("snippet", "Could not extract email body")

    # "To" header usually looks like: "Viswaa <viswaa@ssn.edu.in>"
    receiver_name = receiver.split("<")[0].strip() if "<" in receiver else receiver
    receiver_email = receiver.split("<")[1].replace(">", "").strip() if "<" in receiver else receiver

    return {
        "subject": subject,
        "sender": sender,
        "body": body,
        "receiver_name": receiver_name,
        "receiver_email": receiver_email
    }


LABEL_IDS={
    PERSONAl_EMAIL:"Label_2184135964621054581",
    COLLEGE_EMAIL:"Label_8336136197680826322",
    WORK_EMAIL:"Label_2072885846296407054"
}


def _history_key(account_email):
    return f"history_id:{account_email}"


def _get_last_history_id(account_email):
    return r.get(_history_key(account_email))


def _set_last_history_id(account_email, history_id):
    r.set(_history_key(account_email), history_id)


def _already_processed(msg_id):
    """Atomic check-and-set. Returns True if msg_id was already processed
    (by this or any other worker), False if this call just claimed it."""
    # SET NX -> only succeeds if key didn't already exist
    claimed = r.set(f"processed:{msg_id}", "1", nx=True, ex=PROCESSED_TTL_SECONDS)
    return not claimed


def retrieve_new_emails(service, account_email):
    start_history_id = _get_last_history_id(account_email)

    if start_history_id is None:
        profile = service.users().getProfile(userId="me").execute()
        _set_last_history_id(account_email, profile["historyId"])
        return []

    try:
        history = service.users().history().list(
            userId="me",
            startHistoryId=start_history_id,
            historyTypes=["messageAdded"]
        ).execute()
    except Exception:
        profile = service.users().getProfile(userId="me").execute()
        _set_last_history_id(account_email, profile["historyId"])
        return []

    new_message_ids = set()
    for record in history.get("history", []):
        for added in record.get("messagesAdded", []):
            msg_id = added["message"]["id"]
            new_message_ids.add(msg_id)

    _set_last_history_id(account_email, history.get("historyId", start_history_id))

    results = []
    for msg_id in new_message_ids:
        if _already_processed(msg_id):
            continue

        email = service.users().messages().get(userId="me", id=msg_id).execute()

        service.users().messages().modify(
            userId="me",
            id=msg_id,
            body={"addLabelIds": [LABEL_IDS[account_email]]}
        ).execute()

        data = get_email_body(email["payload"])
        info = get_email_metadata(email)

        if data is not None:
            results.append({
                "sender": info["sender"], "subject": info["subject"], "body": data,
                "receiver_name": info["receiver_name"], "receiver_email": info["receiver_email"]
            })

    return results