import sqlite3
from pathlib import Path

DATA_DIR = Path(__file__).parent / "Data"
DB_PATH = DATA_DIR / "app.db"

def init_db():
    DATA_DIR.mkdir(exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS banks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE
        )
    """)
    conn.commit()
    conn.close()

def add_bank(name):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("INSERT INTO banks (name) VALUES (?)", (name,))
    conn.commit()
    conn.close()

def delete_bank(bank_id):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM banks WHERE id = ?", (bank_id,))
    conn.commit()
    conn.close()

def update_bank(bank_id, new_name):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("UPDATE banks SET name = ? WHERE id = ?", (new_name, bank_id))
    conn.commit()
    conn.close()

def get_all_banks():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT id, name FROM banks")
    banks = cursor.fetchall()
    conn.close()
    return banks
