import os
from pathlib import Path


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

# Uses Environment Variables from .env
load_env_file()

SECRET_KEY = os.environ.get("SECRET_KEY")
DB_PATH = os.environ.get("DB_PATH", "game.db")

if not SECRET_KEY:
    raise RuntimeError("SECRET_KEY must be set in the environment or .env file")

if len(SECRET_KEY) < 32:
    raise RuntimeError("SECRET_KEY must be at least 32 characters long")
