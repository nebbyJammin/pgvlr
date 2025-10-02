from fastapi import APIRouter, Depends, HTTPException
from models.match import VLRMatchList
from utils.utils import get_pool
from models.event import VLREvent, VLREventList
from asyncpg.pool import Pool
from typing import Optional
from asyncpg import PostgresError

router = APIRouter() # Let the v1 parent handle the prefix

@router.get("/")
async def get_matches(event_id: Optional[int] = None, page: Optional[int] = None, pool: Pool = Depends(get_pool)):
    LIMIT = 25

    query = "SELECT * FROM MATCHES WHERE TRUE"
    params = []
    i = 1

    if event_id is not None:
        query += f" AND event_id = ${i}"
        params.append(event_id)
        i += 1

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
async def add_match_bulk(matches_list: VLRMatchList, pool: Pool = Depends(get_pool)):
    results = []

    async with pool.acquire() as conn:
        async with conn.transaction():
            for item in matches_list.matches:
                try:
    #  id | vlr_id | event_id | stage | tournament_round | tournament_note | status | date_start | team_1_id | team_2_id | score_1 | score_2
    #  ----+--------+----------+-------+------------------+-----------------+--------+------------+-----------+-----------+---------+---------
                    await conn.execute(
                        """
                        INSERT INTO matches (id, vlr_id, event_id, 
                        stage, tournament_round, tournament_note, status, date_start, team_1_id,
                        team_2_id, score_1, score_2, last_scraped)
                        VALUES ($1, $2, $3, $4, $5, 
                        $6, $7, $8, $9, $10, $11, $12, $13)
                        ON CONFLICT(id) DO UPDATE
                        SET vlr_id = EXCLUDED.vlr_id,
                            event_id = EXCLUDED.event_id,
                            stage = EXCLUDED.stage,
                            tournament_round = EXCLUDED.tournament_round,
                            tournament_note = EXCLUDED.tournament_note,
                            status = EXCLUDED.status,
                            date_start = EXCLUDED.date_start,
                            team_1_id = EXCLUDED.team_1_id,
                            team_2_id = EXCLUDED.team_2_id,
                            score_1 = EXCLUDED.score_1,
                            score_2 = EXCLUDED.score_2,
                            last_scraped = EXCLUDED.last_scraped
                        """,
                        item.vlr_id,
                        item.vlr_id,
                        item.event_id,
                        item.stage,
                        item.tournament_round,
                        item.tournament_note,
                        item.status,
                        item.date_start,
                        item.team_1_id,
                        item.team_2_id,
                        item.score_1,
                        item.score_2,
                        item.date_scraped
                    )

                except Exception as e:
                    raise HTTPException(status_code=400, detail=f"Insertion failed: {e} for {item}")

    return {"message": "ok"}
