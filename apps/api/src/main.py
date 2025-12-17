from fastapi import FastAPI, Depends, Header, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from .db import get_db
from .auth_google import verify_google_id_token_from_header
from .crud_accounts import upsert_account_from_google
from .models import Base
from .db import engine

from .routers import game, simulation_stream, stats

app = FastAPI(title="Baseball Sim API")

@app.on_event("startup")
def startup_event():
    from .db import SessionLocal
    from . import crud_game
    db = SessionLocal()
    try:
        trainings = crud_game.get_trainings(db)
        if not trainings:
            crud_game.create_training(db, "Weightlifting", power_delta=1)
            crud_game.create_training(db, "Running", speed_delta=1)
            crud_game.create_training(db, "Batting Practice", contact_delta=1)
            print("Seeded initial trainings")
    finally:
        db.close()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(game.router, prefix="/api/v1", tags=["game"])
app.include_router(stats.router, prefix="/api/v1", tags=["stats"])
app.include_router(simulation_stream.router, tags=["simulation"])

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