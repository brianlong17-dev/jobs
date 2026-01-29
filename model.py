from pydantic import BaseModel, Field, field_validator, model_validator
from typing import List, Literal, Optional
from instructor import Maybe

class JobAnalysisSimple(BaseModel):
    title: str
    company: str
    languages: List[str]
    frameworks: List[str]
    tools: List[str] = Field(description="e.g. Docker, Kubernetes, Git, Jira")
    cloud_platforms: List[str]
    
    work_setting: Literal["Remote", "Hybrid", "On-site", "Unknown"]
    min_years_experience: Optional[int] = Field(description="Minimum years of experience required. If a range, provide the lower bound.")
    seniority_level: Literal["Junior", "Mid", "Senior", "Lead", "Unknown"]
    # Market Intelligence
    salary_range: Optional[str] = Field(description="Extract if mentioned, else None")
    
    @field_validator('languages', 'frameworks', 'tools', mode='before')
    @classmethod
    def ensure_lowercase(cls, v):
        """Ensures tags are consistent for easier filtering."""
        if isinstance(v, list):
            return [item.lower().strip() for item in v]
        return v

class Salary(BaseModel):
    min_amount: Optional[float] = None
    max_amount: Optional[float] = None
    currency: Optional[str] = "EUR"
    interval: Literal["hourly", "yearly", "monthly", "Unknown"] = "Unknown"
    @model_validator(mode='after')
    def check_if_empty(self) -> 'Salary':
        # If the LLM returned 0.0 or nothing for both, we treat the whole thing as None
        if not self.min_amount and not self.max_amount:
            return None # This will make data.salary actually None
        return self
    
class JobAnalysisComplex(JobAnalysisSimple):
    domain_knowledge: List[str] = Field(
        description="Industry specific knowledge like 'E-commerce', 'Blockchain', or 'HIPAA compliance'",
        default_factory=list
    )
    
    salary: Salary = Field(
        default=None, 
        description="Extract structured salary data if compensation is mentioned (e.g. '35k', '40k-50k'). If no salary is mentioned at all, return None."
    )
    
    
    
    
    

    