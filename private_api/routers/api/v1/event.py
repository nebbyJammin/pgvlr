from fastapi import APIRouter, Depends, HTTPException
from utils.utils import get_pool
from models.event import VLREvent, VLREventList
from asyncpg.pool import Pool
from typing import Optional
from asyncpg import PostgresError

router = APIRouter() # Let the v1 parent handle the prefix

@router.get("/")
async def get_events(series_id: Optional[int] = None, page: Optional[int] = None, pool: Pool = Depends(get_pool)):
    LIMIT = 500

    query = "SELECT * from EVENTS WHERE TRUE"
    params = []
    i = 1 # counter

    if series_id is not None:
        query += f" AND SERIES_ID = ${i}"
        params.append(series_id)
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
async def add_event_bulk(events_list: VLREventList, pool: Pool = Depends(get_pool)):
    results = []

    async with pool.acquire() as conn:
        async with conn.transaction():
            for item in events_list.events:
                try:
                    await conn.execute(
                        """
                        INSERT INTO events (id, vlr_id, name, 
                        status, series_id, region, location_long, tags, prize,
                        date_str, date_start, date_end, thumbnail, last_scraped)
                        VALUES ($1, $2, $3, $4, $5, 
                        $6, $7, $8, $9, $10, $11, $12, $13, $14)
                        ON CONFLICT(id) DO UPDATE
                        SET vlr_id = EXCLUDED.vlr_id,
                            name = EXCLUDED.name,
                            status = EXCLUDED.status,
                            series_id = EXCLUDED.series_id,
                            region = EXCLUDED.region,
                            location_long = EXCLUDED.location_long,
                            tags = EXCLUDED.tags,
                            prize = EXCLUDED.prize,
                            date_str = EXCLUDED.date_str,
                            date_start = EXCLUDED.date_start,
                            date_end = EXCLUDED.date_end,
                            thumbnail = EXCLUDED.thumbnail,
                            last_scraped = EXCLUDED.last_scraped
                        """,
                        item.vlr_id,
                        item.vlr_id,
                        item.name,
                        item.status,
                        item.series_id,
                        item.region,
                        item.location_long,
                        item.tags,
                        item.prize,
                        item.date_str,
                        item.date_start,
                        item.date_end,
                        item.thumbnail,
                        item.date_scraped
                    )

                except Exception as e:
                    raise HTTPException(status_code=400, detail=f"Insertion failed: {e} for {item}")

    return {"message":  "ok"}
