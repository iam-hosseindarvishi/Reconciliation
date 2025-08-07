import sqlite3
from config.settings import DB_PATH

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
