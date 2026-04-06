import jwt
import datetime
import logging
import os
import sqlite3
from pathlib import Path
from fastapi import FastAPI, Form, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from passlib.context import CryptContext
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def load_env_file(env_path: str = ".env"):
    env_file = Path(env_path)
    if not env_file.exists():
        return

    for raw_line in env_file.read_text().splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue

        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


load_env_file()

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

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
SECRET_KEY = os.environ.get("SECRET_KEY")
DB_PATH = os.environ.get("DB_PATH", "game.db")

if not SECRET_KEY:
    raise RuntimeError("SECRET_KEY must be set in the environment or .env file")

if len(SECRET_KEY) < 32:
    raise RuntimeError("SECRET_KEY must be at least 32 characters long")

# --- Database Setup ---
def init_db():
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            "CREATE TABLE IF NOT EXISTS users "
            "(username TEXT PRIMARY KEY, password TEXT, gold INTEGER)"
        )


init_db()


def _validate_credentials(username: str, password: str) -> None:
    if not username or not username.strip():
        raise HTTPException(status_code=422, detail="Invalid input")
    if len(username) < 3 or len(username) > 32:
        raise HTTPException(status_code=422, detail="Invalid input")
    if not username.replace("_", "").isalnum():
        raise HTTPException(status_code=422, detail="Invalid input")
    if len(password) < 8 or len(password) > 128:
        raise HTTPException(status_code=422, detail="Invalid input")


# --- Auth Routes ---
@app.post("/register")
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


@app.post("/login")
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
