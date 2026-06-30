from fastapi import FastAPI,Request,BackgroundTasks
from apscheduler.schedulers.background import BackgroundScheduler
from agent_workflow import agent
from gmail import authenticate,get_email_body,get_email_metadata,retrieve_new_emails
import time
import json
import base64
import os
from dotenv import load_dotenv
load_dotenv()

PERSONAl_EMAIL=os.getenv("PERSONAL_EMAIL")
COLLEGE_EMAIL=os.getenv("COLLEGE_EMAIL")
WORK_EMAIL=os.getenv("WORK_EMAIL")


def renew_watch():
    for email, service in services.items():
        response = service.users().watch(
            userId="me",
            body={
                "topicName": "projects/notification-alert-agent/topics/gmail-notifications"
            }
        ).execute()
        print(f"Renewed watch for {email}")

scheduler = BackgroundScheduler()
scheduler.add_job(renew_watch, "interval", days=6)  # renew every 6 days, before 7 day expiry
scheduler.start()

services = {
    PERSONAl_EMAIL: authenticate("/etc/secrets/personal_token.json"),
    COLLEGE_EMAIL: authenticate("/etc/secrets/college_token.json"),
    WORK_EMAIL: authenticate("/etc/secrets/iitm_token.json")
}

for email, service in services.items():
    response = service.users().watch(
        userId="me",
        body={
            "topicName": "projects/notification-alert-agent/topics/gmail-notifications"
        }
    ).execute()

app = FastAPI()

@app.get("/")
def home():
    return {"message":"Welcome to CortexMail!"}

def process_email(service,account_email):
    """Runs the heavy work (Gmail fetch, LLM calls, Telegram send) after responding to Pub/Sub"""

    email_json = retrieve_new_emails(service,account_email)

    if email_json is not None:
        agent.invoke({
            "email": {
                "body": email_json["body"],
                "subject": email_json["subject"],
                "sender": email_json["sender"],
                "receiver_name": email_json["receiver_name"],
                "receiver_email": email_json["receiver_email"]
            }
        })

@app.post("/gmail")
async def gmail(request:Request,background_tasks: BackgroundTasks):

    body = await request.json()
    pubsub_data = body["message"]["data"]
    decoded = json.loads(
        base64.b64decode(pubsub_data).decode("utf-8")
    )

    email_address = decoded["emailAddress"]
    service = services[email_address]

    background_tasks.add_task(process_email, service,email_address)

    return {"response":"Message sent!"}

