from contextlib import asynccontextmanager
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

@asynccontextmanager
async def lifespan(app: FastAPI):
    await startup()
    yield
    await shutdown()

async def startup():
    app.state.pool = await asyncpg.create_pool(
        user=os.getenv("POSTGRES_USER", "postgres"),
        password=os.getenv("POSTGRES_PASSWORD", "password"),
        database=os.getenv("POSTGRES_DB", "mydb"),
        host=os.getenv("POSTGRES_HOST", "localhost"),
        port=int(os.getenv("POSTGRES_PORT", 5432))
    )

def get_pool() -> Pool:
    return app.state.pool

async def shutdown():
    await get_pool().close()

app = FastAPI(title="VLR GG PRIVATE API", lifespan=lifespan)

app.include_router(api_v1.api_v1_router) # Register routes for v1 api

@app.middleware("http")
async def no_cache_middleware(request, call_next):
    response: Response = await call_next(request)
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    response.headers["Pragma"] = "no-cache"

    return response

@app.get("/")
async def root():
    return {"message": "This is the private API for the VLR-SCRAPER database"}

@app.get("/checkhealth")
async def check_health():
    return {"status": "ok", "message": "Service is healthy"}

@app.delete("/dev/reset_schema")
async def reset_schema():
    try:
        async with get_pool().acquire() as conn:
            async with conn.transaction():
                # Enable levenstein distance && trigram matching. This is not strictly necessary but nice for VCT//CALENDAR
                await conn.execute("CREATE EXTENSION IF NOT EXISTS fuzzystrmatch;")
                await conn.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm;")

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
                        last_scraped TIMESTAMPTZ NOT NULL,

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
                        series_id INT,
                        region VARCHAR(10),
                        location_long VARCHAR(200),
                        tags TEXT[] NOT NULL,
                        prize TEXT NOT NULL,
                        date_str TEXT,
                        date_start DATE,
                        date_end DATE,
                        thumbnail TEXT,
                        last_scraped TIMESTAMPTZ NOT NULL,

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
                        last_scraped TIMESTAMPTZ NOT NULL,

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
                        date_start TIMESTAMPTZ,
                        team_1_id INT,
                        team_2_id INT,
                        score_1 INT,
                        score_2 INT,
                        vods TEXT[],
                        streams TEXT[],
                        last_scraped TIMESTAMPTZ NOT NULL,
                        
                        CONSTRAINT matches_pk_id PRIMARY KEY (id),
                        CONSTRAINT matches_unique_vlr_id UNIQUE (vlr_id),
                        CONSTRAINT matches_fk_team_1_id FOREIGN KEY (team_1_id) references teams(id),
                        CONSTRAINT matches_fk_team_2_id FOREIGN KEY (team_2_id) references teams(id)
                    )
                    """         
                )

                # NOTE: The scope of the project has changed drastically, not scraping players and actual match data for the time being
                #  # PLAYERS
                #  await conn.execute(
                    #  """
                    #  CREATE TABLE IF NOT EXISTS players (
                        #  id SERIAL,
                        #  vlr_id INT NOT NULL,
                        #  ign VARCHAR(100) NOT NULL,
                        #  name VARCHAR(100),
                        #  country_short VARCHAR(10),
                        #  country_long VARCHAR(100),
                        #  socials TEXT[] NOT NULL,
                        #  last_scraped TIMESTAMPTZ NOT NULL,
#
                        #  CONSTRAINT players_pk_id PRIMARY KEY (id),
                        #  CONSTRAINT players_unique_vlr_id UNIQUE (vlr_id)
                    #  )
                    #  """
                #  )
#
                #  # MAP
                #  # NOTE: when map_num = 0, then it is the summary (all maps)
                #  # Join with mapplayeroverviews -> mapplayersidedoverviews to get the precise data per player (categorised by atk/def/both halves)
                #  # Join with mapplayerperformances to get the performances of each player
                #  await conn.execute(
                    #  """
                    #  CREATE TABLE IF NOT EXISTS maps (
                        #  id SERIAL,
                        #  vlr_id INT,
                        #  map_num INT NOT NULL,
                        #  map_name VARCHAR(20),
                        #  map_picked_by_team_id INT,
                        #  t_side_starting_team_id INT,
#
                        #  CONSTRAINT maps_pk_id PRIMARY KEY (id),
                        #  CONSTRAINT maps_pk_unique_vlr_id UNIQUE (vlr_id),
                        #  CONSTRAINT maps_fk_map_picked_by_team_id FOREIGN KEY (map_picked_by_team_id) references TEAMS(id)
                        #  CONSTRAINT maps_fk_t_side_starting_team_id FOREIGN KEY (map_picked_by_team_id) references TEAMS(id)
                    #  )
                    #  """
                #  )
#
                #  # Map Overview for a player
                #  # Join with mapplayersidedoverviews to get the summarised data categorised by attack/defence etc.
                #  await conn.execute(
                    #  """
                    #  CREATE TABLE IF NOT EXISTS mapplayeroverviews (
                        #  id SERIAL,
                        #  map_id INT NOT NULL,
                        #  player_id INT,
                        #  team_id INT NOT NULL,
#
                        #  two_ks INT,
                        #  three_ks INT,
                        #  four_ks INT,
                        #  five_ks INT,
#
                        #  one_vs_one INT,
                        #  one_vs_two INT,
                        #  one_vs_three INT,
                        #  one_vs_four INT,
                        #  one_vs_five INT,
#
                        #  econ INT,
                        #  plants INT,
                        #  defuses INT,
#
                        #  CONSTRAINT map_player_overviews_pk_id PRIMARY KEY (id),
                        #  CONSTRAINT map_player_overviews_fk_map_id FOREIGN KEY (map_id) REFERENCES MAPS(id),
                        #  CONSTRAINT map_player_overviews_fk_player_id FOREIGN KEY (player_id) REFERENCES PLAYERS(id),
                        #  CONSTRAINT map_player_overviews_fk_team_id FOREIGN KEY (team_id) REFERENCES TEAMS(id)
                    #  )
                    #  """
                #  )
#
                #  # NOTE: side=0 is both sides; side=1 is attack; side=2 is defence. Each row represents a players stat summary of for a map (or whole series), containing its summary, attack and defence sided stats.
                #  await conn.execute(
                    #  """
                    #  CREATE TABLE IF NOT EXISTS mapplayersidedoverviews (
                        #  id SERIAL,
                        #  map_player_overviews_id INT NOT NULL,
                        #  side VARCHAR(20),
                        #  acs INT,
                        #  kills INT,
                        #  deaths INT,
                        #  assists INT,
                        #  kast INT,
                        #  adr INT,
                        #  hs INT,
                        #  fk INT,
                        #  fd INT,
#
                        #  CONSTRAINT map_player_sided_overviews_pk_id PRIMARY KEY (id),
                        #  CONSTRAINT map_player_sided_overviews_fk_map_player_overviews_id FOREIGN KEY (map_player_overviews_id) references mapplayeroverviews(id)
                    #  )
                    #  """
                #  )
#
                #  # Agents<->Player (in some map). This is because the summary map table
                #  # may have a player play multiple agents across multiple maps
                #  await conn.execute(
                    #  """
                    #  CREATE TABLE IF NOT EXISTS mapplayeragents (
                        #  id SERIAL,
                        #  map_player_sided_overview_id INT NOT NULL,
                        #  agent VARCHAR(20),
#
                        #  CONSTRAINT map_player_agents_pk_id PRIMARY KEY (id),
                        #  CONSTRAINT map_player_agents_fk_map_player_sided_overview_id FOREIGN KEY (map_player_sided_overview_id) references mapplayersidedoverviews(id)
                    #  )
                    #  """
                #  )
#
                #  # Economy (extra details) for each map (per team)
                #  await conn.execute(
                    #  """
                    #  CREATE TABLE IF NOT EXISTS mapeconomies (
                        #  id SERIAL,
                        #  pistol_wins INT,
                        #  eco INT,
                        #  eco_wins INT,
                        #  semi_eco INT,
                        #  semi_eco_wins INT,
                        #  semi_buy INT,
                        #  semi_buy_wins INT,
                        #  full_buy INT,
                        #  full_buy_wins INT,
#
                        #  CONSTRAINT map_economies_pk_id PRIMARY KEY (id)
                    #  )
                    #  """
                #  )

    except PostgresError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return {"message": "success"}
