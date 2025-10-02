from typing import Optional
from fastapi import FastAPI, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response
from asyncpg.pool import Pool
from asyncpg.exceptions import PostgresError
from routers.api import api_v1
import asyncpg
import os

from models.series import VLRSeries, VLRSeriesList
from models.event import VLREvent, VLREventList

app = FastAPI(title="VLR GG PRIVATE API")

def get_pool() -> Pool:
    return app.state.pool

app.include_router(api_v1.api_v1_router) # Register routes for v1 api

@app.on_event("startup")
async def startup():
    app.state.pool = await asyncpg.create_pool(
        user=os.getenv("POSTGRES_USER", "postgres"),
        password=os.getenv("POSTGRES_PASSWORD", "password"),
        database=os.getenv("POSTGRES_DB", "mydb"),
        host=os.getenv("PRIVATE_API_DB_HOST", "localhost"),
        port=int(os.getenv("PRIVATE_API_DB_PORT", 5432))
    )

@app.on_event("shutdown")
async def shutdown():
    await get_pool().close()

@app.middleware("http")
async def no_cache_middleware(request, call_next):
    response: Response = await call_next(request)
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    response.headers["Pragma"] = "no-cache"

    return response

@app.get("/")
async def root():
    return {"message": "Hello from the PRIVATE VLR SCRAPER API!"}

@app.delete("/dev/reset_schema")
async def reset_schema():
    try:
        async with get_pool().acquire() as conn:
            async with conn.transaction():
                # DROP TABLES
                await conn.execute(
                    """
                    DO $$
                    DECLARE
                        r RECORD;
                    BEGIN
                        FOR r IN (SELECT tablename FROM pg_tables WHERE schemaname
                        = 'public') LOOP
                            EXECUTE 'DROP TABLE IF EXISTS ' || quote_ident(r.tablename) || ' CASCADE';
                        END LOOP;
                    END
                    $$;
                    """
                )

                # CREATE SERIES TABLE
                await conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS series(
                        id SERIAL,
                        vlr_id INT NOT NULL,
                        name VARCHAR(500) NOT NULL,
                        description TEXT,
                        status SMALLINT NOT NULL,
                        last_scraped TIMESTAMP NOT NULL,

                        CONSTRAINT series_pk_id PRIMARY KEY (id),
                        CONSTRAINT series_unique_vlr_id UNIQUE (vlr_id)
                    )
                    """
                )

                # CREATE EVENTS
                await conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS events (
                        id SERIAL,
                        vlr_id INT NOT NULL,
                        name VARCHAR(300) NOT NULL,
                        status SMALLINT NOT NULL,
                        series_id INT NOT NULL,
                        region VARCHAR(10),
                        location_long VARCHAR(200),
                        tags TEXT[] NOT NULL,
                        prize TEXT NOT NULL,
                        date_str TEXT,
                        date_start DATE,
                        date_end DATE,
                        thumbnail TEXT,
                        last_scraped TIMESTAMP NOT NULL,

                        CONSTRAINT events_pk_id PRIMARY KEY (id),
                        CONSTRAINT events_unique_vlr_id UNIQUE (vlr_id),
                        CONSTRAINT events_fk_series_id FOREIGN KEY (series_id) REFERENCES series(id)
                    )
                    """
                )

                # TEAMS
                await conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS teams (
                        id SERIAL,
                        vlr_id INT NOT NULL,
                        name VARCHAR(200) NOT NULL,
                        tricode VARCHAR(20),
                        country_short VARCHAR(10),
                        country_long VARCHAR(100),
                        status INT NOT NULL,
                        logo TEXT NOT NULL,
                        socials TEXT[] NOT NULL,
                        last_scraped TIMESTAMP NOT NULL,

                        CONSTRAINT teams_pk_id PRIMARY KEY (id),
                        CONSTRAINT teams_unique_vlr_id UNIQUE (vlr_id)
                    )
                    """
                )

                # MATCHES
                await conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS matches (
                        id SERIAL,
                        vlr_id INT NOT NULL,
                        event_id INT NOT NULL,
                        stage VARCHAR(200) NOT NULL,
                        tournament_round VARCHAR(200) NOT NULL,
                        tournament_note TEXT,
                        status INT NOT NULL,
                        date_start TIMESTAMP,
                        team_1_id INT,
                        team_2_id INT,
                        score_1 INT,
                        score_2 INT,
                        last_scraped TIMESTAMP NOT NULL,
                        
                        CONSTRAINT matches_pk_id PRIMARY KEY (id),
                        CONSTRAINT matches_unique_vlr_id UNIQUE (vlr_id),
                        CONSTRAINT matches_fk_team_1_id FOREIGN KEY (team_1_id) references teams(id),
                        CONSTRAINT matches_fk_team_2_id FOREIGN KEY (team_2_id) references teams(id)
                    )
                    """         
                )

                #  series_to_insert = [
                    #  (74, 74, 'Valorant Champions Tour 2025', 'Riot''s official 2025 tournament circuit.', 1),
                    #  (73, 73, 'RIOT Games ONE', 'Riot Games ONE is the off-season programme for all things Riot-related organised by Riot Games Japan', 2),
                #  ]
#
                #  # CREATE SAMPLE SERIES
                #  await conn.executemany(
                    #  """
                    #  INSERT INTO SERIES (id, vlr_id, name, description, status)
                    #  VALUES ($1, $2, $3, $4, $5)
                    #  ON CONFLICT (id) DO NOTHING
                    #  """,
                    #  series_to_insert
                #  )

    except PostgresError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return {"message": "success"}
