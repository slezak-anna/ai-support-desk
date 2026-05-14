from mcp.server.fastmcp import FastMCP

from app.db.session import SessionLocal
from app.models.ticket import Ticket

mcp = FastMCP("AI Support Desk MCP")

@mcp.tool()
def get_ticket(ticket_id:int) -> dict:
    db = SessionLocal()

    try:
        ticket = db.query(Ticket).filter(Ticket.id == ticket_id).first()

        if not ticket:
            return {
                "found": False,
                "ticket_id": ticket_id
            }
        
        return {
                    "found": True,
                    "id": ticket.id,
                    "customer_email": ticket.customer_email,
                    "subject": ticket.subject,
                    "message": ticket.message,
                    "status": ticket.status,
                    "category": ticket.category,
                    "priority": ticket.priority,
                    "draft_reply": ticket.draft_reply,
                    "needs_human": ticket.needs_human,
                }
    finally:
        db.close()

@mcp.tool()
def search_tickets_by_status(status: str) -> list[dict]:
    db = SessionLocal()

    try: 
        tickets = db.query(Ticket).filter(Ticket.status == status).limit(20).all()

        return [
            {
                "id": ticket.id,
                "subject": ticket.subject,
                "status": ticket.status,
                "category": ticket.category,
                "priority": ticket.priority,
                "needs_human": ticket.needs_human,
            }
            for ticket in tickets
        ]
    finally:
        db.close()


@mcp.resource("support://policy/refunds")
def refund_policy() -> str:
    return (
        "Refund requests must be reviewed by a human support specialist. "
        "The AI system may draft a reply, but it must not promise a refund automatically."
    )


@mcp.prompt(title="Analyze Support Ticket")
def analyze_support_ticket(ticket_text: str) -> str:
    return f"""
        Analyze this support ticket.

        Classify:
        - category
        - priority
        - whether human review is required

        Ticket:
        {ticket_text}
        """

if __name__ == "__main__":
    mcp.run()