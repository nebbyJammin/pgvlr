from fastapi import Request, Depends
from asyncpg.pool import Pool

def get_pool(request: Request) -> Pool:
    return request.app.state.pool
