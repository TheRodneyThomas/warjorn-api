# Copyright (c) 2026 R7L LLC. All Rights Reserved.
#
# PROPRIETARY AND CONFIDENTIAL
#
# This software and its source code are the exclusive property of R7L LLC
# and are protected by copyright law and international treaties.
#
# Unauthorized copying, distribution, modification, public display, or
# public performance of this software, in whole or in part, is strictly
# prohibited without the prior written consent of R7L LLC.
#
# For licensing inquiries, contact: legal@r7l.us

import jwt
import datetime
import logging
import sqlite3
from fastapi import APIRouter, Form, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from passlib.context import CryptContext
from slowapi import Limiter
from slowapi.util import get_remote_address

from config import SECRET_KEY, DB_PATH

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth")

limiter = Limiter(key_func=get_remote_address)
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def init_db():
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            "CREATE TABLE IF NOT EXISTS users "
            "(username TEXT PRIMARY KEY, password TEXT, gold INTEGER)"
        )


def _validate_credentials(username: str, password: str) -> None:
    if not username or not username.strip():
        raise HTTPException(status_code=422, detail="Invalid input")
    if len(username) < 3 or len(username) > 32:
        raise HTTPException(status_code=422, detail="Invalid input")
    if not username.replace("_", "").isalnum():
        raise HTTPException(status_code=422, detail="Invalid input")
    if len(password) < 8 or len(password) > 128:
        raise HTTPException(status_code=422, detail="Invalid input")


@router.post("/register")
@limiter.limit("5/minute")
async def register(request: Request, username: str = Form(...), password: str = Form(...)):
    _validate_credentials(username, password)
    hashed = pwd_context.hash(password)
    try:
        with sqlite3.connect(DB_PATH) as conn:
            conn.execute(
                "INSERT INTO users VALUES (?, ?, ?)", (username, hashed, 100)
            )
        logger.info("New user registered: %s", username)
        return {"status": "success"}
    except sqlite3.IntegrityError:
        logger.warning("Registration failed (duplicate): %s", username)
        raise HTTPException(status_code=400, detail="Registration failed")
    except sqlite3.Error:
        logger.error("Database error during registration for user: %s", username)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/login")
@limiter.limit("10/minute")
async def login(request: Request, username: str = Form(...), password: str = Form(...)):
    _validate_credentials(username, password)
    try:
        with sqlite3.connect(DB_PATH) as conn:
            row = conn.execute(
                "SELECT password FROM users WHERE username = ?", (username,)
            ).fetchone()
    except sqlite3.Error:
        logger.error("Database error during login for user: %s", username)
        raise HTTPException(status_code=500, detail="Internal server error")

    if row and pwd_context.verify(password, row[0]):
        token = jwt.encode(
            {
                "sub": username,
                "exp": datetime.datetime.now(datetime.timezone.utc)
                + datetime.timedelta(hours=24),
            },
            SECRET_KEY,
            algorithm="HS256",
        )
        logger.info("Successful login: %s", username)
        return {"token": token}

    logger.warning("Failed login attempt for user: %s", username)
    raise HTTPException(status_code=401, detail="Invalid credentials")
