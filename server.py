import jwt
import datetime
import os
import sqlite3
from pathlib import Path
from fastapi import FastAPI, Form, HTTPException
from passlib.context import CryptContext


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
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
SECRET_KEY = os.environ.get("SECRET_KEY")

if not SECRET_KEY:
    raise RuntimeError("SECRET_KEY must be set in the environment or .env file")

# --- Database Setup ---
def init_db():
    conn = sqlite3.connect("game.db")
    conn.execute("CREATE TABLE IF NOT EXISTS users (username TEXT PRIMARY KEY, password TEXT, gold INTEGER)")
    conn.close()

init_db()

# --- Auth Routes ---
@app.post("/register")
async def register(username: str = Form(...), password: str = Form(...)):
    hashed = pwd_context.hash(password)
    try:
        conn = sqlite3.connect("game.db")
        conn.execute("INSERT INTO users VALUES (?, ?, ?)", (username, hashed, 100))
        conn.commit()
        return {"status": "success"}
    except:
        raise HTTPException(status_code=400, detail="User already exists")

@app.post("/login")
async def login(username: str = Form(...), password: str = Form(...)):
    conn = sqlite3.connect("game.db")
    user = conn.execute("SELECT password FROM users WHERE username = ?", (username,)).fetchone()
    
    if user and pwd_context.verify(password, user[0]):
        token = jwt.encode({
            "sub": username,
            "exp": datetime.datetime.utcnow() + datetime.timedelta(hours=24)
        }, SECRET_KEY, algorithm="HS256")
        return {"token": token}
    raise HTTPException(status_code=401, detail="Invalid credentials")