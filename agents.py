from langchain_openai import ChatOpenAI
from dotenv import load_dotenv
import os
import json

load_dotenv()
key=os.getenv("OPENAI_API_KEY")

llm=ChatOpenAI(model="gpt-4.1-mini",api_key=key)

def decision_agent(body,sender,subject,receiver_name,receiver_email):
    """Decides whether email is worth notifying to user"""

    prompt = f"""You are an email priority classifier for Viswaa, a CS student at SSN College of Engineering (Sri Sivasubramaniya Nadar College of Engineering), Chennai, who is also pursuing the IIT Madras BS degree program.

        Analyze this email and decide if it requires immediate attention.

        Email Details:
        Sender: {sender}
        Subject: {subject}
        Body: {body}
        Receiver Name: {receiver_name}
        Receiver Email: {receiver_email}

        IMPORTANT CONTEXT: If the receiver email is Viswaa's SSN college email (contains "ssn" or matches college domain), treat anything from faculty, departments, admin, or placement cell as HIGH PRIORITY regardless of other rules below, since these directly affect academics.

        Classify as HIGH PRIORITY if the email is about:
        - Internship opportunities, job openings, or recruitment calls
        - Hackathons, coding competitions, or tech fests
        - AI/ML news, research breakthroughs, LLMs, or agentic AI
        - Any event registration with a deadline
        - Scholarship or fellowship opportunities
        - Anything sent to Viswaa's college email from faculty, departments, admin, or placement cell
        - Anything related to the IIT Madras BS degree program (IITM BS), including but not limited to: course updates, new coursework or content uploaded, assignment/quiz/exam deadlines, grading or evaluation notices, term registration, fee payment deadlines, exam hall tickets, proctoring/OPPE details, discussion forum announcements, or any official communication from IIT Madras, IITM BS portal, or instructors of that program

        Classify as IMPORTANT if the email is about:
        - Anything from SSN College of Engineering (clubs, general announcements) not covered above
        - Academic matters: assignments, exams, timetables, results, attendance, lab records
        - Library notices: due dates, book availability, fines
        - College events, fests, club activities, or workshops
        - Emails from real people (professors, classmates, seniors, recruiters) requiring a response
        - Deadlines, meetings, or time-sensitive information

        Classify as NOT IMPORTANT if the email is:
        - Generic promotions or marketing unrelated to tech or college
        - Automated notifications requiring no action (OTPs, payment receipts, delivery updates)
        - Spam or bulk mail

        Respond in this exact JSON format:
        {{
            "classification": "HIGH PRIORITY" or "IMPORTANT" or "NOT IMPORTANT",
            "reason": "one line explanation"
        }}

        Return only the JSON, no other text."""

    response=llm.invoke(prompt).content
    response = response.replace("```json", "").replace("```", "").strip()
    return json.loads(response)

    return json.loads(response)

def summariser_agent(body,sender,subject,receiver_name,receiver_email):
    """Summarises the content of an email to extract key points"""

    prompt = f"""You are an intelligent email summarizer for a busy CS student.

        Email Details:
        Sender: {sender}
        Subject: {subject}
        Body: {body}
        Receiver name: {receiver_name}
        Receiver email: {receiver_email}

        Your job is to extract what actually matters from this email and present it clearly.

        Respond in this exact JSON format:
        {{
            "headline": "one punchy line describing what this email is about",
            "key_points": ["point 1", "point 2", "point 3"],
            "action_required": "what the user needs to do, or null if nothing",
            "deadline": "any deadline or time-sensitive detail mentioned, or null if none",
            "links": ["any important URLs mentioned, or empty list if none"],
            "receiver": "{receiver_name}"
        }}

        Rules:
        - headline must be under 10 words
        - key_points maximum 3, only what actually matters
        - be brutally concise, no filler
        - if its a hackathon or internship, always extract deadline and links
        - Return only the JSON, no other text."""

    response=llm.invoke(prompt).content
    response = response.replace("```json", "").replace("```", "").strip()
    return json.loads(response)


def generator_agent(classification, reason, summary_json):
    """Formatting summarised response"""

    priority_emoji = "🔴" if classification == "HIGH PRIORITY" else "🟡"

    key_points = "\n".join(f"• {point}" for point in summary_json["key_points"])
    links = "\n".join(summary_json["links"]) if summary_json["links"] else "None"

    message = f"""{priority_emoji} *{classification}*
    👤 *To:* {summary_json.get("receiver", "Unknown")}
    _{reason}_

    *{summary_json["headline"]}*

    *Key Points:*
    {key_points}

    *Action Required:* {summary_json["action_required"] or "None"}
    *Deadline:* {summary_json["deadline"] or "None"}
    *Links:* {links}

    ⏰ _Sent by CortexMail_"""

    return message







