import uuid
from datetime import datetime
from sqlalchemy import Column, Boolean, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from app.database import Base

class Response(Base):
    __tablename__ = "responses"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    session_id = Column(UUID(as_uuid=True), ForeignKey("sessions.id"), nullable=False)
    question_id = Column(UUID(as_uuid=True), ForeignKey("questions.id"), nullable=False)
    
    # Exact technical data submitted by the user
    submitted_technical_data = Column(JSONB, nullable=False)
    
    is_correct = Column(Boolean, nullable=False)
    
    # Used for enforcing daily limits
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    user = relationship("User")
    session = relationship("Session")
    question = relationship("Question")
