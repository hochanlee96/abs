from fastapi import FastAPI, Depends, Header, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session
from .db import get_db
from .auth_google import verify_google_id_token_from_header
from .crud_accounts import upsert_account_from_google
from .models import Base
from .db import engine

app = FastAPI(title="Baseball Sim API")

@app.get("/health")
def health():
    return {"ok": True}

@app.get("/me")
def me(db: Session = Depends(get_db), authorization: str | None = Header(default=None)):
    payload = verify_google_id_token_from_header(authorization)
    acc = upsert_account_from_google(db, payload)
    return {
        "account_id": acc.account_id,
        "google_sub": acc.google_sub,
        "email": acc.email,
        "display_name": acc.display_name,
        "avatar_url": acc.avatar_url,
    }

@app.websocket("/ws/match/{match_id}")
async def ws_match(websocket: WebSocket, match_id: int):
    # MVP: ws auth는 token query param이 제일 단순
    token = websocket.query_params.get("token")
    try:
        verify_google_id_token_from_header(f"Bearer {token}")
    except Exception:
        await websocket.close(code=1008)
        return

    await websocket.accept()
    try:
        await websocket.send_json({"type": "CONNECTED", "match_id": match_id})

        # 데모: 클라이언트에서 보내는 메시지 echo
        while True:
            msg = await websocket.receive_text()
            await websocket.send_json({"type": "ECHO", "message": msg})
    except WebSocketDisconnect:
        pass