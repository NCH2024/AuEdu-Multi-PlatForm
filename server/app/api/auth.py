# server/app/api/auth.py
import os
import httpx
from fastapi import APIRouter, Request, HTTPException

router = APIRouter()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")


@router.post("/v1/token")
async def login_proxy(request: Request):
    """
    Proxy tới Supabase để client không phải biết URL thực tế.
    """
    body = await request.json()
    grant_type = request.query_params.get("grant_type", "password")
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{SUPABASE_URL}/auth/v1/token?grant_type={grant_type}",
            json=body,
            headers={"apikey": SUPABASE_KEY, "Content-Type": "application/json"},
        )
    if resp.status_code != 200:
        raise HTTPException(status_code=resp.status_code, detail=resp.json())
    return resp.json()
