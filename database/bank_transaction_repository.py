import sqlite3
from config.settings import DB_PATH

def create_bank_transaction(data):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO BankTransactions (
            bank_id, transaction_date, transaction_time, amount, description, reference_number, extracted_terminal_id, extracted_tracking_number, transaction_type, is_reconciled
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        data.get('bank_id'),
        data.get('transaction_date'),
        data.get('transaction_time'),
        data.get('amount'),
        data.get('description'),
        data.get('reference_number'),
        data.get('extracted_terminal_id'),
        data.get('extracted_tracking_number'),
        data.get('transaction_type'),
        data.get('is_reconciled', 0)
    ))
    conn.commit()
    conn.close()

def get_transactions_by_bank(bank_id):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM BankTransactions WHERE bank_id = ?", (bank_id,))
    result = cursor.fetchall()
    conn.close()
    return result

def get_transactions_by_terminal(bank_id, terminal_id):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM BankTransactions WHERE bank_id = ? AND extracted_terminal_id = ?", (bank_id, terminal_id))
    result = cursor.fetchall()
    conn.close()
    return result

def get_transactions_by_date_range(bank_id, start_date, end_date):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT * FROM BankTransactions
        WHERE bank_id = ? AND transaction_date BETWEEN ? AND ?
    """, (bank_id, start_date, end_date))
    result = cursor.fetchall()
    conn.close()
    return result

def get_transactions_by_bank_and_date_range(bank_id, start_date, end_date):
    return get_transactions_by_date_range(bank_id, start_date, end_date)

def get_unreconciled_transactions_by_bank(bank_id):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM BankTransactions WHERE bank_id = ? AND is_reconciled = 0", (bank_id,))
    result = cursor.fetchall()
    conn.close()
    return result

def update_reconciliation_status(transaction_id, status):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("UPDATE BankTransactions SET is_reconciled = ? WHERE id = ?", (int(bool(status)), transaction_id))
    conn.commit()
    conn.close()

def delete_transaction(transaction_id):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM BankTransactions WHERE id = ?", (transaction_id,))
    conn.commit()
    conn.close()
