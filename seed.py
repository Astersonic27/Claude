"""Create demo users:  python seed.py   (password for everyone: change-me-123)"""
import sqlite3
from contextlib import closing

from werkzeug.security import generate_password_hash

from app import create_app

USERS = [("admin", "Alex Admin", 1), ("priya", "Priya Sharma", 0), ("liam", "Liam Chen", 0),
         ("sofia", "Sofia Rossi", 0), ("mohammed", "Mohammed Sifatullah", 0)]

app = create_app()
with closing(sqlite3.connect(app.config["DATABASE"])) as conn:
    for username, name, admin in USERS:
        conn.execute("INSERT OR IGNORE INTO users (username, display_name, password_hash, is_admin) VALUES (?,?,?,?)",
                     (username, name, generate_password_hash("change-me-123"), admin))
    conn.commit()
print("Seeded", len(USERS), "users into", app.config["DATABASE"])
