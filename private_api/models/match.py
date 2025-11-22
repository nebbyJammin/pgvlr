from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import date, datetime

class VLRMapPlayerSidedOverview(BaseModel):
    map_player_overviews_id: int
    acs: int
    kills: int
    deaths: int
    assists: int
    kast: int
    adr: int
    hs: int
    fk: int
    fd: int

class VLRMapPlayerOverview(BaseModel):
    summary: Optional[VLRMapPlayerSidedOverview]
    attack: Optional[VLRMapPlayerSidedOverview]
    defence: Optional[VLRMapPlayerSidedOverview]

    map_id: int
    player_id: int
    team_id: int

    # These fields are normally in the "performance tab" but to reduce the amount of joining, we just put them as a player stat
    two_ks: Optional[int]
    three_ks: Optional[int]
    four_ks: Optional[int]
    five_ks: Optional[int]
    one_vs_one: Optional[int]
    one_vs_two: Optional[int]
    one_vs_three: Optional[int]
    one_vs_four: Optional[int]
    one_vs_five: Optional[int]
    econ: Optional[int]
    plants: Optional[int]
    defuses: Optional[int]

class VLRMapRoundData(BaseModel):
    t_side_won: bool
    round_outcome: int

class VLRMap(BaseModel):
    vlr_id: int
    map_num: int
    map_name: str
    map_picked_by_team_id: Optional[int]
    t_side_starting_team_id: Optional[int]

    round_data: List[VLRMapRoundData]

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
    
    maps: Optional[VLRMap]

    date_scraped: datetime

class VLRMatchList(BaseModel):
    matches: List[VLRMatch]
