import uuid
from sqlalchemy import Column, Text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from app.database import Base

class Question(Base):
    __tablename__ = "questions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    content = Column(Text, nullable=False)
    
    # E.g., {"ascitic_fluid_analysis": {"WBC": 550, "PMN_percent": 80}, "albumin_gradient": 1.5}
    diagnostic_parameters = Column(JSONB, nullable=True)
    
    # Specific quantitative lab results
    lab_frameworks = Column(JSONB, nullable=True)
    
    # Must only store ICD-9 codes
    classification_codes = Column(JSONB, nullable=True)
    
    # The technical data / ICD-9 code for exact match validation
    correct_answer_technical_data = Column(JSONB, nullable=False)
