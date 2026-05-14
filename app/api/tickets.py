from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.dependencies import get_db
from app.schemas.ticket import TicketResponse, TicketListItem, TicketCreate
from app.services.ticket_service import create_ticket, get_ticket, list_tickets
from app.tasks.ticket_tasks import analyze_ticket

router = APIRouter(prefix="/tickets", tags=["tickets"])

@router.post(
    "",
    response_model=TicketResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_ticket_endpoint(data: TicketCreate, db: Session = Depends(get_db)):
    ticket = create_ticket(db, data)
    analyze_ticket.delay(ticket.id)
    return ticket   

@router.get(
    "",
    response_model=list[TicketListItem])
def list_tickets_endpoint(db: Session = Depends(get_db)):
    return list_tickets(db)

@router.get("/{ticket_id}",
            response_model=TicketResponse)
def get_ticket_endpoint(ticket_id: int, db: Session = Depends(get_db)):
    ticket = get_ticket(db, ticket_id)

    if not ticket:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ticket not found")
    
    return ticket