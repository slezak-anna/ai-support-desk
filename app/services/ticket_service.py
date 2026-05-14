from app.models.ticket import Ticket
from sqlalchemy.orm import Session
from app.schemas.ticket import TicketCreate

def create_ticket(db_session: Session, data: TicketCreate):
    ticket = Ticket(
        customer_email=data.customer_email,
        subject=data.subject,
        message=data.message,
    )
    db_session.add(ticket)
    db_session.commit()
    db_session.refresh(ticket)

    return ticket

def get_ticket(db_session: Session, ticket_id: int):
    return db_session.query(Ticket).filter(Ticket.id == ticket_id).first()

def list_tickets(db_session: Session):
    return db_session.query(Ticket).order_by(Ticket.id.desc()).all()

def update_ticket_analysis(db_session: Session, ticket_id: int, *, status:str, priority: str, category: str, draft_reply: str | None, needs_human: bool) -> Ticket | None:
    ticket = get_ticket(db_session, ticket_id)

    if not ticket:
        return None
    
    ticket.status = status
    ticket.priority = priority     
    ticket.category = category
    ticket.draft_reply = draft_reply
    ticket.needs_human = needs_human

    db_session.commit()
    db_session.refresh(ticket)
    return ticket