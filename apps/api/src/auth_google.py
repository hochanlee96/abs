import os
from fastapi import Header, HTTPException
from google.oauth2 import id_token
from google.auth.transport import requests as grequests

GOOGLE_CLIENT_ID = os.environ["GOOGLE_CLIENT_ID"]

def verify_google_id_token_from_header(authorization: str | None) -> dict:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing Bearer token")

    token = authorization.split(" ", 1)[1].strip()
    try:
        payload = id_token.verify_oauth2_token(token, grequests.Request(), GOOGLE_CLIENT_ID)
        return payload
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid Google token")