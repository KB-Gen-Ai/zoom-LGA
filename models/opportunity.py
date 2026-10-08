from typing import Literal, Any
from pydantic import BaseModel, Field, HttpUrl

class Opportunity(BaseModel):
    title: str
    description: str = ""
    publisher: str = "Unknown"
    main_contractor: str = ""
    location: str = "Saudi Arabia"
    opportunity_type: str = ""
    lead_type: Literal["DIRECT", "INDIRECT", "MARKET_INTELLIGENCE", "UNKNOWN"] = "UNKNOWN"
    scope: list[str] = Field(default_factory=list)
    deadline: str = ""
    dates: list[str] = Field(default_factory=list)
    value: str = ""
    value_type: Literal["OFFICIAL", "CONVERTED", "ESTIMATED", "UNKNOWN"] = "UNKNOWN"
    source_name: str
    source_url: str
    contact: str = ""
    summary: str = ""
    why_zoom: str = ""
    evidence: list[str] = Field(default_factory=list)
    confidence: str = "Unknown"
    score: float = 0
    score_breakdown: dict[str, float] = Field(default_factory=dict)
    raw_text: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)
