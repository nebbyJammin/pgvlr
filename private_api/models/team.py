from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import date, datetime

                        #  id SERIAL,
                        #  vlr_id INT NOT NULL,
                        #  name VARCHAR(100) NOT NULL,
                        #  tricode VARCHAR(20),
                        #  country_short VARCHAR(10),
                        #  country_long VARCHAR(100),
                        #  status INT NOT NULL,
                        #  logo TEXT NOT NULL,
                        #  socials TEXT[] NOT NULL,
                        #  last_scraped TIMESTAMP NOT NULL,

class VLRTeam(BaseModel):
    vlr_id: int
    name: str
    tricode: Optional[str] = None
    country_short: Optional[str] = None
    country_long: Optional[str] = None
    status: int = Field(..., ge=-1, le=2)
    logo: str
    socials: List[str]
    date_scraped: datetime

class VLRTeamList(BaseModel):
    teams: List[VLRTeam]
