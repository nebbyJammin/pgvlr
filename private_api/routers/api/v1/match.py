from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query
from models.match import VLRMatchList
from utils.utils import get_pool
from models.event import VLREvent, VLREventList
from asyncpg.pool import Pool
from typing import List, Optional
from asyncpg import PostgresError

router = APIRouter() # Let the v1 parent handle the prefix

@router.get("/")
async def get_matches(event_id: Optional[int] =
                            Query(None, ge=0), 
                        match_id: Optional[int] =
                            Query(None, ge=0),
                        stage: Optional[str] =
                            Query(None, description="Queries matches that contains the tournament stage as a substring (case insensitive). An example of a tournament stage could be 'Group Stage' or 'Playoffs'"),
                        tournament_round: Optional[str] =
                            Query(None, description="Queries matches that contains the tournmaent round as a substring (case insensitive). An example of a tournament round could be 'Round 1', 'Round 2', 'Finals' or 'Lower Round 1'"),
                        tournament_note: Optional[str] =
                            Query(None, description="Queries matches with similar tournament notes. Most of the time, this will contain information about the match like 'Bo1', 'Bo3', '2 maps', but sometimes it may include information if the a map/entire match was forfeited."), \
                        status: Optional[List[int]] =
                            Query(None, description="Search by status. -1 = Unknown, 0 = Upcoming, 1 = Ongoing, 2 = Completed"), \
                        date_start: Optional[datetime] =
                            Query(None, description="Specify an earliest datetime (inclusive) in ISO 8601 format (without timezone data -> Implicitly using UTC time)."), \
                        date_end: Optional[datetime] =
                            Query(None, description="Specify a latest date (inclusive) in ISO 8601 format (without timezone data -> Implicitly using UTC time)."), \
                        team_id: Optional[List[int]] =
                            Query(None, description="Specify a list of team IDs to query matches that have those teams participate in the matches."), \
                        page: Optional[int] = None, pool: Pool = Depends(get_pool)):
    LIMIT = 100

    query = "SELECT * FROM MATCHES WHERE TRUE"
    params = []
    i = 1

    if event_id:
        query += f" AND event_id = ${i}"
        params.append(f"%{event_id}%")
        i += 1

    if match_id:
        query += f" AND id = ${i}"
        params.append(f"%{match_id}%")
        i += 1

    if stage:
        query += f" AND stage ILIKE ${i}"
        params.append(f"%{stage}%")
        i += 1

    if tournament_round:
        query += f" AND tournament_round ILIKE ${i}"
        params.append(f"%{tournament_round}%")
        i += 1

    if tournament_note:
        query += f" AND tournament_note ILIKE ${i}"
        params.append(f"%{tournament_note}%")
        i += 1

    if status:
        for s in status:
            if s < -1 or s > 2:
                raise HTTPException(status_code=400, detail="Status must be between -1 and 2 inclusive.")

        placeholders = ", ".join(f"${i+j}" for j in range(len(status)))
        query += f" AND status in ({placeholders})"
        params.extend(status)
        i += len(status)

    if date_start:
        query += f" AND date_start >= ${i}"
        params.append(date_start)
        i += 1

    if date_end:
        query += f" AND date_start <= ${i}"
        params.append(date_end)
        i += 1

    if team_id:
        placeholders = ", ".join(f"${i+j}" for j in range(len(team_id)))
        query += f" AND ( team_1_id in ({placeholders}) or team_2_id in ({placeholders}) )"
        params.extend(team_id)
        i += len(team_id)

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
    
    match_list = [dict(row) for row in rows]

    return {"status": "success", "data": match_list}

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
                        team_2_id, score_1, score_2, vods, streams, last_scraped)
                        VALUES ($1, $2, $3, $4, $5, 
                        $6, $7, $8, $9, $10, $11, $12, $13, $14, $15)
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
                            vods = EXCLUDED.vods,
                            streams = EXCLUDED.streams,
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
                        item.vods,
                        item.streams,
                        item.date_scraped
                    )

                except Exception as e:
                    raise HTTPException(status_code=400, detail=f"Insertion failed: {e} for {item}")

    return {"message": "ok"}
