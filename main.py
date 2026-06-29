from fastapi import FastAPI,Request
from apscheduler.schedulers.background import BackgroundScheduler
from agent_workflow import agent
from gmail import authenticate,get_email_body,get_email_metadata,retrieve_latest_mail
import time


def renew_watch():
    service.users().watch(
        userId="me",
        body={
            "topicName": "projects/notification-alert-agent/topics/gmail-notifications"
        }
    ).execute()
    print("Gmail watch renewed")

scheduler = BackgroundScheduler()
scheduler.add_job(renew_watch, "interval", days=6)  # renew every 6 days, before 7 day expiry
scheduler.start()
service=authenticate()

trigger=service.users().watch(
    userId="me",
    body={
        "topicName":
        "projects/notification-alert-agent/topics/gmail-notifications"
    }
).execute()

app = FastAPI()

@app.get("/")
def home():
    return {"message":"Welcome to CortexMail!"}

@app.post("/gmail")
def gmail(request:Request):

    email_json = retrieve_latest_mail(service)
    if email_json is not None:
        result=agent.invoke({
            "email":{
                "body":email_json["body"],
                "subject":email_json["subject"],
                "sender":email_json["sender"]
            }
        })
        return {"response":"sent!"}
