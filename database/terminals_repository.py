from database.init_db import create_connection

def create_terminal(terminal_number, terminal_name):
    conn = create_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO Terminals (terminal_number, terminal_name) VALUES (?, ?)", (terminal_number, terminal_name))
    conn.commit()
    conn.close()

def get_all_terminals():
    conn = create_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, terminal_number, terminal_name FROM Terminals")
    result = cursor.fetchall()
    conn.close()
    return result

def get_terminal_by_number(terminal_number):
    conn = create_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, terminal_number, terminal_name FROM Terminals WHERE terminal_number = ?", (terminal_number,))
    result = cursor.fetchone()
    conn.close()
    return result

def delete_terminal(terminal_number):
    conn = create_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM Terminals WHERE terminal_number = ?", (terminal_number,))
    conn.commit()
    conn.close()
