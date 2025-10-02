from fastapi import APIRouter, Depends, HTTPException
from utils.utils import get_pool
from models.series import VLRSeries, VLRSeriesList
from asyncpg.pool import Pool
from typing import Optional
from asyncpg import PostgresError

router = APIRouter() # Let api_v1 handle prefix

@router.get("/")
async def get_series(pool: Pool = Depends(get_pool)):
    try:
        async with pool.acquire() as conn:
            rows = await conn.fetch("SELECT * FROM SERIES")
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
