from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
import os
from dotenv import load_dotenv
load_dotenv()
import base64
import threading

PERSONAl_EMAIL = os.getenv("PERSONAL_EMAIL")
COLLEGE_EMAIL = os.getenv("COLLEGE_EMAIL")
WORK_EMAIL = os.getenv("WORK_EMAIL")

lock=threading.Lock()

processed_emails=set()

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

def retrieve_latest_mail(service, account_email):
    results = service.users().messages().list(
        userId="me",
        maxResults=5,
        labelIds=["INBOX"]
    ).execute()

    messages = results.get("messages", [])
    if not messages:
        return None

    latest_mail = messages[0]["id"]

    with lock:
        if latest_mail in processed_emails:
            return None
        processed_emails.add(latest_mail)

    email = service.users().messages().get(userId="me", id=latest_mail).execute()

    # Apply label as an audit trail / for visibility in Gmail, not for dedup logic
    service.users().messages().modify(
        userId="me",
        id=latest_mail,
        body={"addLabelIds": [LABEL_IDS[account_email]]}
    ).execute()

    data = get_email_body(email["payload"])
    info = get_email_metadata(email)

    if data is not None:
        return {"sender": info["sender"], "subject": info["subject"], "body": data,
                "receiver_name": info["receiver_name"], "receiver_email": info["receiver_email"]}