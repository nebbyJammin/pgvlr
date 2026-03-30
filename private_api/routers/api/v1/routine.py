
from datetime import datetime, time, timedelta, timezone
from asyncpg import Pool, PostgresError
from fastapi import APIRouter, Depends, HTTPException
from typing import Any, Dict, List

from utils.utils import get_pool


router = APIRouter()

EPOCH_SINCE_DATE_START = "ABS(EXTRACT(EPOCH FROM (date_start - NOW() AT TIME ZONE 'UTC')))"
EPOCH_SINCE_LAST_SCRAPED = "EXTRACT(EPOCH FROM (NOW() AT TIME ZONE 'UTC' - last_scraped))"

@router.get("/high-priority")
async def get_high_priority_tasks(pool: Pool = Depends(get_pool)):
    try:
        async with pool.acquire() as conn:
            # -1 = unknown, 0 = upcoming, 1 = ongoing, 2 = completed
            # Get matches that are upcoming within the next week and need to be scraped (>= 10 minutes)
            rows = await conn.fetch(f"""
                SELECT id, event_id, date_start FROM matches
                WHERE 
                    (STATUS = 1) 
                        OR
                    (
                        STATUS <= 0 
                        AND ({EPOCH_SINCE_DATE_START} / 3600 <= 24*7 OR date_start IS NULL)
                        AND {EPOCH_SINCE_LAST_SCRAPED} / 60 >= 10
                    )
            """)

            match_tasks = [dict(row) for row in rows]
            for match_task in match_tasks:
            # Calculate priorities
                start_time = match_task.get("date_start")
                if start_time:
                    time_delta: timedelta = start_time - datetime.now(tz=timezone.utc)
                else:
                    time_delta: timedelta = timedelta()
                minutes_till_start = max(time_delta.total_seconds() / 60, 0)
                match_task["priority"] = round(100 + max(1000 - 5 * minutes_till_start, 0))
                del match_task["date_start"]

            # Get events that are upcoming or unknown and need to be scraped (>=120 minutes)
            # Scrape events that have started/will start within half a year
            # Note that the scraper will recursively scrape events
            rows = await conn.fetch(f"""
                SELECT id, series_id, date_start from events
                WHERE status <= 0
                AND {EPOCH_SINCE_LAST_SCRAPED} / 60 >= 120
                AND ({EPOCH_SINCE_DATE_START} / 3600 <= 24*7*26)
            """)

            event_tasks: List[Dict[str, Any]] = [dict(row) for row in rows]

            # Get events that are ongoing and need to be scraped (>=30 minutes)
            # Note that the scraper will recursively scrape events
            rows = await conn.fetch(f"""
                SELECT id, series_id, date_start from events where status = 1
                and {EPOCH_SINCE_LAST_SCRAPED} / 60 >= 30
            """)

            event_tasks.extend([dict(row) for row in rows])

            for event_task in event_tasks:
                start_time = event_task.get("date_start")
                if start_time:
                    time_delta: timedelta = datetime.combine(start_time, datetime.min.time(), tzinfo=timezone.utc) - datetime.now(tz=timezone.utc)
                else:
                    time_delta: timedelta = timedelta()
                minutes_till_start = max(time_delta.total_seconds() / 60, 0)
                event_task["priority"] = round(50 + max(60 - minutes_till_start, 0))
                del event_task["date_start"]
    
    except PostgresError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return { 
        "status":"success", 
        "data": {
            "match": match_tasks,
            "event": event_tasks,
        }
    }

@router.get("/low-priority")
async def get_low_priority_tasks(pool: Pool = Depends(get_pool)):
    try:
        async with pool.acquire() as conn:
            # Scrape all events/matches with completed status that started within the last week every 2 days
            rows = await conn.fetch(
                f"""
                SELECT id, event_id from matches
                WHERE status = 2
                AND {EPOCH_SINCE_LAST_SCRAPED} / 3600 >= 48
                AND {EPOCH_SINCE_DATE_START} / 3600 <= 24 * 7
                """
            )

            #  matches.extend([{**dict(row), "priority": 5} for row in rows])
            matches = [{**dict(row), "priority": 5} for row in rows]

            rows = await conn.fetch(
                f"""
                SELECT id, series_id from events
                WHERE status = 2
                AND {EPOCH_SINCE_LAST_SCRAPED} / 3600 >= 48
                AND {EPOCH_SINCE_DATE_START} / 3600 <= 24 * 7
                """
            )

            #  events.extend([{**dict(row), "priority": 5} for row in rows])
            events = [{**dict(row), "priority": 5} for row in rows]

            # Scrape all events/matches with completed status that started within the last 90 days every 2 weeks
            rows = await conn.fetch(
                f"""
                SELECT id, event_id from matches
                WHERE status = 2
                AND {EPOCH_SINCE_LAST_SCRAPED} / 3600 >= 24 * 14
                AND {EPOCH_SINCE_DATE_START} / 3600 <= 24 * 90
                """
            )

            matches.extend([{**dict(row), "priority": 3} for row in rows])

            rows = await conn.fetch(
                f"""
                SELECT id, series_id from events
                WHERE status = 2
                AND {EPOCH_SINCE_LAST_SCRAPED} / 3600 >= 24 * 14
                AND {EPOCH_SINCE_DATE_START} / 3600 <= 24 * 90
                """
            )

            events.extend([{**dict(row), "priority": 3}for row in rows])

            # TODO: MAKE SCRAPING VERY HISTORICAL DATA OPTIONAL
            # Scrape all matches with completed status that started within the last year every 3 months
            #  rows = await conn.fetch(
                #  f"""
                #  SELECT id, event_id from matches
                #  WHERE status = 2
                #  AND {EPOCH_SINCE_LAST_SCRAPED} / 3600 >= 24 * 30 * 3
                #  AND {EPOCH_SINCE_DATE_START} / 3600 <= 24 * 365
                #  """
            #  )
#
            #  matches.extend([{**dict(row), "priority": 2} for row in rows])
#
            #  rows = await conn.fetch(
                #  f"""
                #  SELECT id, series_id from events
                #  WHERE status = 2
                #  AND {EPOCH_SINCE_LAST_SCRAPED} / 3600 >= 24 * 30 * 3
                #  AND {EPOCH_SINCE_DATE_START} / 3600 <= 24 * 365
                #  """
            #  )
#
            #  events.extend([{**dict(row), "priority": 2} for row in rows])

            # NOTE: We are not doing this anymore:
            # Scrape all events/matches with completed status that started over a year ago every 6 months
            #  rows = await conn.fetch(
                #  f"""
                #  SELECT id, event_id from matches
                #  WHERE status = 2
                #  AND {EPOCH_SINCE_LAST_SCRAPED} / 3600 >= 24 * 30 * 6
                #  AND {EPOCH_SINCE_DATE_START} / 3600 > 24 * 365
                #  """
            #  )
#
            #  matches.extend([{**dict(row), "priority": 1} for row in rows])
#
            #  rows = await conn.fetch(
                #  f"""
                #  SELECT id, series_id from events
                #  WHERE status = 2
                #  AND {EPOCH_SINCE_LAST_SCRAPED} / 3600 >= 24 * 30 * 6
                #  AND {EPOCH_SINCE_DATE_START} / 3600 > 24 * 365
                #  """
            #  )
#
            #  events.extend([{**dict(row), "priority": 1} for row in rows])

            # Scrape all series within 20 of the max series every day
            rows = await conn.fetch(
                f"""
                SELECT id from series
                WHERE status = 2
                AND {EPOCH_SINCE_LAST_SCRAPED} / 3600 >= 24
                AND id >= (SELECT max(id)-20 FROM SERIES)
                """
            )

            series = [dict(row) for row in rows] # Priority 0 is implicit, so no need to pass it in

    except PostgresError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return {
            "status": "success",
            "data": {
                "match": matches,
                "event": events,
                "series": series,
            }
    }
