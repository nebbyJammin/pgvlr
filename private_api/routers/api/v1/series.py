from fastapi import APIRouter, Depends, HTTPException, Query
from utils.utils import get_pool
from models.series import VLRSeries, VLRSeriesList
from asyncpg.pool import Pool
from typing import Optional, List
from asyncpg import PostgresError

router = APIRouter() # Let api_v1 handle prefix

@router.get("/")
async def get_series(series_id: Optional[int] = \
                            Query(None, description="Search specific series id.", ge=0), \
                        name: Optional[str] = \
                            Query(None, description="Search by name (case insensitive)."), \
                        status: Optional[List[int]] = \
                            Query(None, description="Search by status. -1 = Unknown, 0 = Upcoming, 1 = Ongoing, 2 = Completed."), \
                        pool: Pool = Depends(get_pool)):
    query = "SELECT * FROM SERIES WHERE TRUE "
    params = []
    i = 1

    if series_id:
        query += f" AND id = ${i}"
        params.append(series_id)
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

    try:
        async with pool.acquire() as conn:
            rows = await conn.fetch(query, *params)
    except PostgresError as e:
        raise HTTPException(status_code=400, detail=str(e))

    series_list = [dict(row) for row in rows]

    return {"status": "success", "data": series_list}

@router.post("/bulk")
async def add_series_bulk(series_list: VLRSeriesList, pool: Pool = Depends(get_pool)):
    results = []

    async with pool.acquire() as conn:
        async with conn.transaction():
            for item in series_list.series:
                try:
                    await conn.execute(
                        """
                        INSERT INTO series (id, vlr_id, name, description, status, last_scraped)
                        VALUES ($1, $2, $3, $4, $5, $6)
                        ON CONFLICT (id) DO UPDATE
                        SET vlr_id = EXCLUDED.vlr_id,
                            name = EXCLUDED.name,
                            description = EXCLUDED.description,
                            status = EXCLUDED.status,
                            last_scraped = EXCLUDED.last_scraped
                        """,
                        item.vlr_id,
                        item.vlr_id,
                        item.name,
                        item.description,
                        item.status,
                        item.date_scraped
                    )

                except Exception as e:
                    raise HTTPException(status_code=400, detail=f"Insertion failed: {e} for {item}")

    return {"message": "ok"}

@router.get("/get-known")
async def get_known_series(pool: Pool = Depends(get_pool)):
    results = []

    async with pool.acquire() as conn:
        try:
            results = await conn.fetch(
                """
                SELECT id from series ORDER BY id;
                """
            )
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Failed to get known series ids: {e}")

    return {
            "message": "ok",
            "id": [series["id"] for series in results]
    }

@router.get("/get-known/{series_id}")
async def seen_series_id_before(series_id: int, pool: Pool = Depends(get_pool)):
    results = []
    
    async with pool.acquire() as conn:
        try:
            results = await conn.fetch(
                """
                SELECT id from series where id = $1
                """,
                series_id
            )
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Failed to check if series has been seen before: {e}")
    
    return { "message": "ok", "seen_before": len(results) > 0 }

@router.get("/get-unknown")
async def get_unknown_series(pool: Pool = Depends(get_pool)):
    results = []

    async with pool.acquire() as conn:
        try:
            results = await conn.fetch(
                """
                    SELECT i from generate_series(1, (SELECT MAX(id) FROM series)) as gs(i) 
                        WHERE NOT EXISTS ( 
                            SELECT 1 FROM series e WHERE e.id = gs.i 
                        ) 
                    ORDER BY i;
                """
            )
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Failed to return unknown series ids: {e}")

    return { "message": "ok", "id": [series["i"] for series in results]}
