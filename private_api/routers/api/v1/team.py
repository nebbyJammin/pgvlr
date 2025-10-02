from fastapi import APIRouter, Depends, HTTPException
from models.match import VLRMatchList
from models.team import VLRTeamList
from utils.utils import get_pool
from models.event import VLREvent, VLREventList
from asyncpg.pool import Pool
from typing import Optional
from asyncpg import PostgresError

router = APIRouter() # Let the v1 parent handle the prefix

@router.get("/")
async def get_teams(page: Optional[int] = None, pool: Pool = Depends(get_pool)):
    LIMIT = 500

    query = "SELECT * FROM TEAMS WHERE TRUE"
    params = []
    i = 1

    # Apply a limit of 500 by default
    query += f" LIMIT ${i}"
    params.append(LIMIT)
    i += 1

    # Apply offset
    if page is not None and page > 0:
        query += f" OFFSET ${i}"
        params.append(LIMIT * (page - 1)) # 1 page is equal to 1 * LIMIT
        i += 1

    try:
        async with pool.acquire() as conn:
            rows = await conn.fetch(query, *params)
    except PostgresError as e:
        raise HTTPException(status_code=400, detail=str(e))
    
    events_list = [dict(row) for row in rows]

    return {"status": "success", "data": events_list}

@router.post("/bulk")
async def add_match_bulk(teams_list: VLRTeamList, pool: Pool = Depends(get_pool)):
    results = []

    async with pool.acquire() as conn:
        async with conn.transaction():
            for item in teams_list.teams:
                try:
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
                    await conn.execute(
                        """
                        INSERT INTO teams (id, vlr_id, name, 
                        tricode, country_short, country_long, status, logo, socials,
                        last_scraped)
                        VALUES ($1, $2, $3, $4, $5, 
                        $6, $7, $8, $9, $10)
                        ON CONFLICT(id) DO UPDATE
                        SET vlr_id = EXCLUDED.vlr_id,
                            name = EXCLUDED.name,
                            tricode = EXCLUDED.tricode,
                            country_short = EXCLUDED.country_short,
                            country_long = EXCLUDED.country_long,
                            status = EXCLUDED.status,
                            logo = EXCLUDED.logo,
                            socials = EXCLUDED.socials,
                            last_scraped = EXCLUDED.last_scraped
                        """,
                        item.vlr_id,
                        item.vlr_id,
                        item.name,
                        item.tricode,
                        item.country_short,
                        item.country_long,
                        item.status,
                        item.logo,
                        item.socials,
                        item.date_scraped
                    )

                    results.append({"id": item.vlr_id, "status": "ok"})
                except Exception as e:
                    raise HTTPException(status_code=400, detail=f"Insertion failed: {e} for {item}")

    return {"message": "ok"}
