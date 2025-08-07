from database.init_db import create_connection

def create_bank(bank_name):
    conn = create_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO Banks (bank_name) VALUES (?)", (bank_name,))
    conn.commit()
    conn.close()

def get_all_banks():
    conn = create_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, bank_name FROM Banks")
    result = cursor.fetchall()
    conn.close()
    return result

def get_bank_by_name(bank_name):
    conn = create_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, bank_name FROM Banks WHERE bank_name = ?", (bank_name,))
    result = cursor.fetchone()
    conn.close()
    return result

def delete_bank(bank_id):
    conn = create_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM Banks WHERE id = ?", (bank_id,))
    conn.commit()
    conn.close()
