from pydantic import BaseModel, Field, EmailStr
from datetime import datetime

class TicketCreate(BaseModel):
    customer_email: EmailStr
    subject: str = Field(min_length=10, max_length=255)
    message: str = Field(min_length=10)

class TicketResponse(BaseModel):
    id: int
    customer_email: EmailStr
    subject: str
    message: str
    priority: str
    category: str
    status: str
    created_at: datetime
    updated_at: datetime

    model_config = {
        "from_attributes": True 
        }
    
class TicketListItem(BaseModel):
    id: int
    customer_email: EmailStr
    subject: str
    priority: str | None
    category: str | None
    status: str
    created_at: datetime
    needs_human: bool
    model_config = {
        "from_attributes": True 
        }