from database.init_db import create_connection

def create_pos_transaction(transaction_data):
    conn = create_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO PosTransactions (
            terminal_number, bank_id, card_number, transaction_date, transaction_amount, tracking_number, is_reconciled
        ) VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (
        transaction_data.get('terminal_number'),
        transaction_data.get('bank_id'),
        transaction_data.get('card_number'),
        transaction_data.get('transaction_date'),
        transaction_data.get('transaction_amount'),
        transaction_data.get('tracking_number'),
        transaction_data.get('is_reconciled', 0)
    ))
    conn.commit()
    conn.close()

def get_transactions_by_terminal(terminal_number):
    conn = create_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM PosTransactions WHERE terminal_number = ?", (terminal_number,))
    result = cursor.fetchall()
    conn.close()
    return result

def get_transactions_by_date_and_terminal(terminal_number, date):
    conn = create_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT * FROM PosTransactions
        WHERE terminal_number = ? AND transaction_date =  ?
    """, (terminal_number, date))
    result = cursor.fetchall()
    conn.close()
    return result
def get_transaction_by_date(date):
        conn = create_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM PosTransactions WHERE transaction_date = ?", (date,))
        result = cursor.fetchall()
        conn.close()
        return result    
def update_reconciliation_status(transaction_id, status):
    conn = create_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE PosTransactions SET is_reconciled = ? WHERE id = ?", (int(bool(status)), transaction_id))
    conn.commit()
    conn.close()

def delete_transaction(transaction_id):
    conn = create_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM PosTransactions WHERE id = ?", (transaction_id,))
    conn.commit()
    conn.close()
