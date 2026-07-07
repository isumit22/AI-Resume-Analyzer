from __future__ import annotations

import os
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path

from jose import JWTError, jwt
from passlib.context import CryptContext


DATABASE_PATH = Path(__file__).resolve().parent.parent / "data" / "analyses.db"
SECRET_KEY = os.getenv("JWT_SECRET_KEY", "dev-only-change-me")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "10080"))

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def _connect() -> sqlite3.Connection:
    DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(DATABASE_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def initialize_auth_store() -> None:
    with _connect() as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )
        connection.commit()


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def get_user_by_username(username: str):
    initialize_auth_store()
    with _connect() as connection:
        row = connection.execute(
            "SELECT user_id, username, password_hash, created_at FROM users WHERE username = ?",
            (username,),
        ).fetchone()
    return row


def create_user(username: str, password: str):
    initialize_auth_store()
    created_at = datetime.now(timezone.utc).isoformat()
    password_hash = hash_password(password)

    with _connect() as connection:
        connection.execute(
            "INSERT INTO users (username, password_hash, created_at) VALUES (?, ?, ?)",
            (username, password_hash, created_at),
        )
        connection.commit()

    return get_user_by_username(username)


def authenticate_user(username: str, password: str):
    user = get_user_by_username(username)
    if user is None:
        return create_user(username, password)

    if not verify_password(password, user["password_hash"]):
        return None

    return user


def create_access_token(*, subject: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {"sub": subject, "exp": expire}
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def decode_token(token: str) -> str | None:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        return None

    subject = payload.get("sub")
    return subject if isinstance(subject, str) else None
