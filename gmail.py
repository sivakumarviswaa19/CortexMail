from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
import os
import base64
import threading

lock=threading.Lock()

processed_emails=set()

def authenticate(token_path):
    """Authenticating and creating credentials for gmail"""

    SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]
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



def retrieve_latest_mail(service):
    """Retrieve and read the latest mail by decoding data"""

    results=service.users().messages().list(
        userId="me",
        maxResults=5
    ).execute()

    latest_mail=results["messages"][0]["id"]  #messages[0] denotes latest mail

    with lock:
        if latest_mail in processed_emails:
            return None
        processed_emails.add(latest_mail)


    email=service.users().messages().get(
        userId="me",
        id=latest_mail
    ).execute()



    data=get_email_body(email["payload"])
    info=get_email_metadata(email)
    subject=info["subject"]
    sender=info["sender"]

    if data is not None:
        return {"sender": sender, "subject": subject, "body": data,
                "receiver_name": info["receiver_name"], "receiver_email": info["receiver_email"]}




