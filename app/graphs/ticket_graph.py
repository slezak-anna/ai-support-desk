from typing_extensions import TypedDict
from langgraph.graph import StateGraph, START, END
from langchain_ollama import ChatOllama
from app.core.settings import get_settings
from enum import Enum
from pydantic import BaseModel, Field

def get_llm():
    settings = get_settings()

    return ChatOllama(model=settings.ollama_model,
                      base_url=settings.ollama_base_url,
                      temperature=0.2)

class TicketCategory(str, Enum):
    general = "general"
    delivery = "delivery"
    refund = "refund"
    technical = "technical"

class TicketPriority(str, Enum):
    high = "high"
    medium = "medium"
    low = "low"
    
class TicketTriage(BaseModel):
    category: TicketCategory
    priority: TicketPriority

class TicketState(TypedDict):
    ticket_id: int
    subject: str
    message: str
    category: str | None
    priority: str | None
    draft_reply: str | None
    needs_human: bool


def classify_ticket(state: TicketState) -> dict:
    text = f"{state['subject']} {state['message']}".lower()

    if any(word in text for word in ['refund', 'return', 'money back']):
        category = 'refund'
    elif any(word in text for word in ['delivery', 'parcel', 'tracking']):
        category = 'delivery'
    elif any(word in text for word in ['logging', 'error', 'application']):
        category = 'technical'
    else:
        category = 'general'

    return {"category": category}


def assign_priority(state: TicketState) -> dict:
    text = f"{state['subject']} {state['message']}".lower()

    if state['category'] == 'refund':
        priority = 'high'
    elif any(word in text for word in ['urgent', 'asap', 'immediately']):
        priority = 'high'
    elif state['category'] in ['delivery', 'technical']:
        priority = 'medium'
    else:        
        priority = 'low'
    return {"priority": priority}


def triage_ticket(state: TicketState) -> dict:
    settings = get_settings()

    if not settings.use_llm_triage:  
        cat = classify_ticket(state)
        merged = {**state, **cat}
        priority = assign_priority(merged)
        return {"category": cat["category"], "priority": priority["priority"]}

    llm = get_llm()
    structured_llm = llm.with_structured_output(TicketTriage)

    prompt = f"""You triage customer support tickets for an online store.

Set category and priority together from the ticket below.

Categories (pick exactly one):
- general: other questions, product info, account
- delivery: shipping, tracking, late/missing package
- refund: returns, refunds, payment disputes, complaints
- technical: app/website bugs, login errors, broken features

Priority (pick exactly one):
- high: refund category, OR customer is angry/urgent (urgent, asap, immediately), OR serious business impact
- medium: delivery or technical issues without extreme urgency
- low: general questions, low urgency

Subject: {state["subject"]}
Message: {state["message"]}
"""
    try:
        result = structured_llm.invoke(prompt)
        return {
            "category": result.category.value,
            "priority": result.priority.value,
        }
    except Exception:
        return {"category": "general", "priority": "low"}
        

def draft_reply_deterministic(state: TicketState) -> dict:
    category = state["category"]

    if category == "refund":
        reply = (
        "Good morning, thank you for your message. "
        "This issue concerns a refund or complaint, so we will forward it to a consultant. "
        "Please be patient."
        )
    elif category == "delivery":
        reply = (
        "Good morning, thank you for contacting us. "
        "We will check the delivery status and get back to you as soon as possible."
        )
    elif category == "technical":
        reply = (
        "Good morning, thank you for reporting the technical issue. "
        "We are forwarding the issue to the technical team."
        )
    else:
        reply = (
        "Good morning, thank you for your message. "
        "We will check the issue and get back to you with a response."
        )

    return {"draft_reply": reply}


def draft_reply(state: TicketState) -> dict:
    settings = get_settings()

    if not settings.use_llm_draft:
        return draft_reply_deterministic(state)
    
    llm = get_llm()

    prompt = f"""
            You are a support assistant for an online store.

            Write a short, polite response to the customer in English.

            Request details:
            - Subject: {state["subject"]}
            - Customer message: {state["message"]}
            - Category: {state["category"]}
            - Priority: {state["priority"]}

            Rules:
            - Do not promise a refund.
            - If the matter concerns a return/complaint, state that the matter will be forwarded to a consultant.
            - Do not make up the order status.
            - The response should be a maximum of 5 sentences.
            """
    
    response = llm.invoke(prompt)

    return {
        "draft_reply": response.content
    }


def email_reviewer(state: TicketState) -> dict:
    settings = get_settings()
    draft = (state.get("draft_reply") or "").strip()
    if not settings.use_llm_draft or not draft:
        return {}

    llm = get_llm()
    prompt = f"""You are a senior support email editor. Review and fix the draft reply below.
Customer subject: {state["subject"]}
Customer message: {state["message"]}
Category: {state["category"]}
Priority: {state["priority"]}
Draft reply:
---
{draft}
---

Check and fix:
- Polite, professional English
- Max 5 sentences
- Do NOT promise a refund or specific outcome
- For refund/complaint: say it will be forwarded to a consultant (do not approve refund)
- Do NOT invent tracking numbers, delivery dates, or order status
- No placeholders like [NAME] or TODO
- Fix grammar, tone, and vague phrases
Return ONLY the corrected email body. No preamble, no quotes, no markdown.
"""
    try:
        revised = (llm.invoke(prompt).content or "").strip()
        if revised:
            return {"draft_reply": revised}
    except Exception:
        pass
    return {}


def decide_human_review(state: TicketState) -> dict:
    needs_human = state["category"] == "refund" or state["priority"] == "high"
    return {"needs_human": needs_human}


def build_ticket_graph():
    builder = StateGraph(TicketState)

    builder.add_node("triage_ticket", triage_ticket)
    builder.add_node("draft_reply", draft_reply)
    builder.add_node("email_reviewer", email_reviewer)
    builder.add_node("decide_human_review", decide_human_review)

    builder.add_edge(START, "triage_ticket")
    builder.add_edge("triage_ticket", "draft_reply")
    builder.add_edge("draft_reply", "email_reviewer")
    builder.add_edge("email_reviewer", "decide_human_review")
    builder.add_edge("decide_human_review", END)

    return builder.compile()