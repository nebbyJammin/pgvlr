from fastapi import APIRouter, Depends, HTTPException, Query
from utils.utils import get_pool
from models.event import VLREvent, VLREventList
from asyncpg.pool import Pool
from typing import Optional, List
from asyncpg import PostgresError
from pydantic import Field
from datetime import date

router = APIRouter() # Let the v1 parent handle the prefix

@router.get("/")
async def get_events(series_id: Optional[int] = Query(None, ge=0), \
                        event_id: Optional[int] = \
                            Query(None, ge=0), \
                        name: Optional[str] = \
                            Query(None, description="Queries event that contains a substring (case insensitive)."), \
                        page: Optional[int] = \
                            Query(None, description="By default, limit is 100. Use to get more results."),\
                        status: Optional[List[int]] = \
                            Query(None, description="Search by status. -1 = Unknown, 0 = Upcoming, 1 = Ongoing, 2 = Completed"), \
                        region: Optional[str] = \
                            Query(None, description="Search by region (short version, e.g. sg is region for singapore). Will return any region codes that have that as a substring (case insensitive)."), \
                        location_long: Optional[str] = \
                            Query(None, description="Search by the long form of region (if short version is sg, then the long name will be singapore)."), \
                        tag: Optional[List[str]] = \
                            Query(None, description="Search by tag. An event may have zero or many tags. Will return partial matches (case insensitive)."), \
                        date_start: Optional[date] = \
                            Query(None, description="Specify an earliest date (inclusive) in ISO 8601 format (without timezone data -> Implicitly using UTC time)."), \
                        date_end: Optional[date] = \
                            Query(None, description="Specify a latest date (inclusive) in ISO 8601 format (without timezone data -> Implicitly using UTC time)."), \
                        pool: Pool = Depends(get_pool)):

    LIMIT = 100

    query = "SELECT * from EVENTS WHERE TRUE"
    params = []
    i = 1 # counter

    if series_id:
        query += f" AND SERIES_ID = ${i}"
        params.append(series_id)
        i += 1

    if event_id:
        query += f" AND id = ${i}"
        params.append(event_id)
        i += 1

    if name:
        query += f" AND name ILIKE ${i}"
        params.append(f"%{name}%")
        i += 1

    if status:
        for s in status:
            if s < -1 or s > 2:
                raise HTTPException(status_code=400, detail="Status must be between -1 and 2 inclusive.")

        placeholders = ", ".join(f"${i+j}" for j in range(len(status)))
        query += f" AND status in ({placeholders})"
        params.extend(status)
        i += len(status)

    if region:
        query += f" AND region ILIKE ${i}"
        params.append(f"%{region}%")
        i += 1

    if location_long:
        query += f" AND location_long ILIKE ${i}"
        params.append(f"%{location_long}%")
        i += 1

    if tag:
        placeholders = ', '.join(f"${i + j}" for j in range(len(tag)))
        query += f" AND tags @> ARRAY[{placeholders}]"
        params.extend(tag)
        i += len(tag)

    if date_start:
        query += f" AND date_start >= ${i}"
        params.append(date_start)
        i += 1

    if date_end:
        query += f" AND date_end <= ${i}"
        params.append(date_end)
        i += 1

    query += f" ORDER BY date_start DESC"

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

@router.get("/get-unknown")
async def get_unknown_events(pool: Pool = Depends(get_pool)):
    return await get_unknown_events_diff(id=None, pool=pool)

@router.get("/get-unknown-diff")
async def get_unknown_events_diff(id: Optional[List[int]] = Query(None), pool: Pool = Depends(get_pool)):
    results = []
    params = []

    query = f"""
        SELECT i from generate_series(1, (SELECT MAX(id) FROM events)) as gs
        (i)
            WHERE TRUE
    """

    if id:
        placeholders = ", ".join(f"${1+j}" for j in range(len(id)))
        params.extend(id)
        query += f" AND gs.i in ({placeholders})"

    query += f" AND NOT EXISTS(SELECT 1 FROM events e WHERE e.id = gs.i) ORDER by i"

    async with pool.acquire() as conn:
        try:
            results = await conn.fetch(query, *params)
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Failed to return unknown event ids: {e}")

    return { "message": "ok", "id": [event["i"] for event in results]}

