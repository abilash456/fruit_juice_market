import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{BASE_DIR / 'fruit_juice_market.db'}")
SECRET_KEY = os.getenv("SECRET_KEY", "CHANGE-ME-before-deployment-use-a-long-random-secret")
SESSION_COOKIE = "fruit_juice_session"
