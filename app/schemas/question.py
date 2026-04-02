from pydantic import BaseModel, Field, model_validator
from typing import Dict, Any, Optional, List
from uuid import UUID

class QuestionBase(BaseModel):
    content: str
    diagnostic_parameters: Optional[Dict[str, Any]] = Field(default_factory=dict, description="e.g., ascitic fluid analysis, albumin gradients")
    lab_frameworks: Optional[Dict[str, Any]] = Field(default_factory=dict)
    classification_codes: Optional[Dict[str, str]] = Field(default_factory=dict, description="Expected to be ICD-9 codes only. Format e.g., {'primary': '250.00'}")
    correct_answer_technical_data: Dict[str, Any]

    @model_validator(mode='after')
    def check_classification_codes(self) -> 'QuestionBase':
        codes = self.classification_codes
        if codes:
            for k, v in codes.items():
                if isinstance(v, str) and v.startswith("ICD10") or v.startswith("SNOMED"):
                    raise ValueError("classification_codes must exclusively store ICD-9 codes. ICD-10 and SNOMED CT are strictly forbidden.")
        return self

class QuestionCreate(QuestionBase):
    pass

class QuestionResponse(QuestionBase):
    id: UUID
    
    class Config:
        from_attributes = True
