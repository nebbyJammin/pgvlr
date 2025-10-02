from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import date, datetime

    #  id | vlr_id | event_id | stage | tournament_round | tournament_note | status | date_start | team_1_id | team_2_id | score_1 | score_2
    #  ----+--------+----------+-------+------------------+-----------------+--------+------------+-----------+-----------+---------+---------
class VLRMatch(BaseModel):
    vlr_id: int
    event_id: int
    stage: str
    tournament_round: str
    tournament_note: Optional[str] = None
    status: int = Field(..., ge=-1, le=2)
    date_start: Optional[datetime] = None
    team_1_id: Optional[int] = None
    team_2_id: Optional[int] = None
    score_1: Optional[int] = None
    score_2: Optional[int] = None
    date_scraped: datetime

class VLRMatchList(BaseModel):
    matches: List[VLRMatch]
