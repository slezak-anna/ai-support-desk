from app.db.session import SessionLocal
from app.graphs.ticket_graph import build_ticket_graph
from app.services.ticket_service import get_ticket, update_ticket_analysis
from app.tasks.celery_app import celery_app

@celery_app.task(name="analyze_ticket")
def analyze_ticket(ticket_id: int) -> dict:
    db = SessionLocal()
    try:
        ticket = get_ticket(db, ticket_id)
        if not ticket:
            return {
                "ticket_id": ticket_id,
                "status": "not_found",
            }

        ticket.status = "processing"
        db.commit()
        
        graph = build_ticket_graph()
        result = graph.invoke(
            {"ticket_id": ticket.id, 
            "subject": ticket.subject, 
            "message": ticket.message,
            "priority": None,
            "category": None,
            "draft_reply": None,
            "needs_human": None
             }
        )

        update_ticket_analysis(db, ticket.id, status="needs_human" if result.get("needs_human") else "completed", priority=result.get("priority"), category=result.get("category"), needs_human=result.get("needs_human"), draft_replay=result.get("draft_reply"))
        return {
            "ticket_id": ticket.id,
            "status": "completed",
            "priority": result.get("priority"),
            "category": result.get("category"),
            "needs_human": result.get("needs_human")
        }
    finally:
        db.close()
        