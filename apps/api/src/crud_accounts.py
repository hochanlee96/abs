from sqlalchemy.orm import Session
from sqlalchemy import select
from .models import Account

def upsert_account_from_google(db: Session, payload: dict) -> Account:
    google_sub = payload.get("sub")
    if not google_sub:
        raise ValueError("Google payload missing sub")

    email = payload.get("email")
    name = payload.get("name")
    picture = payload.get("picture")

    existing = db.execute(select(Account).where(Account.google_sub == google_sub)).scalar_one_or_none()
    if existing:
        existing.email = email
        existing.display_name = name
        existing.avatar_url = picture
        db.commit()
        db.refresh(existing)
        return existing

    acc = Account(
        google_sub=google_sub,
        email=email,
        display_name=name,
        avatar_url=picture,
    )
    db.add(acc)
    db.commit()
    db.refresh(acc)
    return acc