from datetime import datetime
from pydantic import BaseModel, Field
from typing import Optional, List

class VLRSeries(BaseModel):
    vlr_id: int
    name: str
    description: Optional[str] = None
    status: int = Field(..., ge=-1, le=2)
    date_scraped: datetime

class VLRSeriesList(BaseModel):
    series: List[VLRSeries]
