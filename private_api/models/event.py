from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import date, datetime

class VLREvent(BaseModel):
    vlr_id: int
    name: str
    status: int = Field(..., ge=-1, le=2)
    series_id: Optional[int]
    region: Optional[str]
    location_long: Optional[str]
    tags: List[str]
    prize: str
    date_str: Optional[str]
    date_start: Optional[date]
    date_end: Optional[date]
    thumbnail: Optional[str]
    date_scraped: datetime

class VLREventList(BaseModel):
    events: List[VLREvent]
