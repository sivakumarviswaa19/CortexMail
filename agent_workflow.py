from typing import TypedDict,List
from langgraph.graph import StateGraph,END,START

from agents import decision_agent,summariser_agent,generator_agent
from telegram_bot import send_message

class Email(TypedDict):
    body:str
    sender:str
    subject:str
    receiver_name:str
    receiver_email:str

class Decision(TypedDict):
    classification:str
    reason:str

class Summary(TypedDict):
    headline:str
    key_points:List[str]
    action_required:str
    deadline:str
    links:List[str]

class State(TypedDict):
    email:Email
    decision:Decision
    summary:Summary
    final:str

def decision_node(State):
    email=State['email']
    body=email['body']
    sender=email['sender']
    subject=email['subject']
    receiver_name=email['receiver_name']
    receiver_email=email['receiver_email']

    decision=decision_agent(body,sender,subject, receiver_name,receiver_email)
    decision["classification"] = (
        decision["classification"]
        .strip()
        .upper()
    )

    State["decision"] = decision

    return State

def summariser_node(State):
    email=State['email']
    body = email['body']
    sender = email['sender']
    subject = email['subject']
    receiver_name = email['receiver_name']
    receiver_email = email['receiver_email']

    State["summary"]=summariser_agent(body,sender,subject, receiver_name,receiver_email)
    return State

def formatter_node(State):

    reason=State["decision"]["reason"]
    classification=State["decision"]["classification"]

    summary_json=State["summary"]

    State["final"]=generator_agent(classification,reason,summary_json)

    return State

def telegram_node(State):

    final_message=State["final"]
    send_message(final_message)
    return State

def route_decision_node(State):

    classification=State["decision"]["classification"].strip().upper()


    if classification=="HIGH PRIORITY" or classification=="IMPORTANT":
        return "summariser"
    return END


graph=StateGraph(State)

graph.add_node("summariser",summariser_node)
graph.add_node("formatter",formatter_node)
graph.add_node("decision",decision_node)
graph.add_node("telegram",telegram_node)

graph.add_edge(START,"decision")
graph.add_conditional_edges("decision",route_decision_node)

graph.add_edge("summariser","formatter")
graph.add_edge("formatter","telegram")
graph.add_edge("telegram",END)

agent=graph.compile()



