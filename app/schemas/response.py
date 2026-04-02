from pydantic import BaseModel
from typing import Dict, Any
from uuid import UUID
from datetime import datetime

class ResponseBase(BaseModel):
    session_id: UUID
    question_id: UUID
    submitted_technical_data: Dict[str, Any]

class ResponseCreate(ResponseBase):
    pass

class ResponseModel(ResponseBase):
    id: UUID
    user_id: UUID
    is_correct: bool
    created_at: datetime
    
    class Config:
        from_attributes = True
