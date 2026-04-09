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

import logging
import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from auth.server import router as auth_router, init_db
from game.server import router as game_router

logging.basicConfig(level=logging.INFO)

app = FastAPI()

# --- Rate Limiting ---
limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# --- CORS ---
ALLOWED_ORIGINS = os.environ.get("ALLOWED_ORIGINS", "").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in ALLOWED_ORIGINS if o.strip()],
    allow_credentials=True,
    allow_methods=["POST"],
    allow_headers=["Content-Type"],
)

# --- Routers ---
app.include_router(auth_router)
app.include_router(game_router)

# --- Init ---
init_db()
