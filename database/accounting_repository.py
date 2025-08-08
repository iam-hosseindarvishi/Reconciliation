from database.init_db import create_connection

def create_accounting_transaction(data):
    conn = create_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO AccountingTransactions (
            bank_id, transaction_number, transaction_amount, due_date, collection_date, transaction_type, customer_name, description, is_reconciled
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        data.get('bank_id'),
        data.get('transaction_number'),
        data.get('transaction_amount'),
        data.get('due_date'),
        data.get('collection_date'),
        data.get('transaction_type'),
        data.get('customer_name'),
        data.get('description', ''),
        data.get('is_reconciled', 0)
    ))
    conn.commit()
    conn.close()
def get_transactions_by_type(bank_id, transaction_type):
    conn = create_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM AccountingTransactions WHERE bank_id = ? AND transaction_type = ?", (bank_id, transaction_type))
    result = cursor.fetchall()
    conn.close()
    return result

def get_transactions_by_date_and_type(bank_id, start_date, end_date, transaction_type):
    conn = create_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT * FROM AccountingTransactions
        WHERE bank_id = ? AND due_date BETWEEN ? AND ? AND transaction_type = ?
    """, (bank_id, start_date, end_date, transaction_type))
    result = cursor.fetchall()
    conn.close()
    return result


def get_transactions_by_bank(bank_id):
    conn = create_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM AccountingTransactions WHERE bank_id = ?", (bank_id,))
    result = cursor.fetchall()
    conn.close()
    return result

def get_transactions_by_due_date_and_bank(bank_id, start_date, end_date):
    conn = create_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT * FROM AccountingTransactions
        WHERE bank_id = ? AND due_date BETWEEN ? AND ?
    """, (bank_id, start_date, end_date))
    result = cursor.fetchall()
    conn.close()
    return result

def get_transactions_by_collection_date_and_bank(bank_id, start_date, end_date):
    conn = create_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT * FROM AccountingTransactions
        WHERE bank_id = ? AND collection_date BETWEEN ? AND ?
    """, (bank_id, start_date, end_date))
    result = cursor.fetchall()
    conn.close()
    return result

def update_reconciliation_status(transaction_id, status):
    conn = create_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE AccountingTransactions SET is_reconciled = ? WHERE id = ?", (int(bool(status)), transaction_id))
    conn.commit()
    conn.close()

def delete_transaction(transaction_id):
    conn = create_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM AccountingTransactions WHERE id = ?", (transaction_id,))
    conn.commit()
    conn.close()
