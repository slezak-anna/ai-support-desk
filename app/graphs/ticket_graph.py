from typing_extensions import TypedDict
from langgraph.graph import StateGraph, START, END
from langchain_ollama import ChatOllama
from app.core.settings import get_settings

def get_llm():
    settings = get_settings()

    return ChatOllama(model=settings.ollama_model,
                      base_url=settings.ollama_base_url,
                      temperature=0.2)

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

    prompt = """
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

def decide_human_review(state: TicketState) -> dict:
    needs_human = state["category"] == "refund" or state["priority"] == "high"
    return {"needs_human": needs_human}

def build_ticket_graph():
    builder = StateGraph(TicketState)

    builder.add_node("classify_ticket", classify_ticket)
    builder.add_node("assign_priority", assign_priority)
    builder.add_node("draft_reply", draft_reply)
    builder.add_node("decide_human_review", decide_human_review)

    builder.add_edge(START, "classify_ticket")
    builder.add_edge("classify_ticket", "assign_priority")
    builder.add_edge("assign_priority", "draft_reply")
    builder.add_edge("draft_reply", "decide_human_review")
    builder.add_edge("decide_human_review", END)

    return builder.compile()