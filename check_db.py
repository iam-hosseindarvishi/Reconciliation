import sqlite3
import os

print('Checking database...')

db_path = 'data/app.db'
print(f'Database exists: {os.path.exists(db_path)}')

if os.path.exists(db_path):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Get all tables
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = cursor.fetchall()
    
    print('Tables found:')
    for table in tables:
        print(f'- {table[0]}')
    
    # Check BankTransactions table
    if ('BankTransactions',) in tables:
        cursor.execute("SELECT COUNT(*) FROM BankTransactions")
        total = cursor.fetchone()[0]
        print(f'Total BankTransactions: {total}')
        
        cursor.execute("SELECT COUNT(*) FROM BankTransactions WHERE transaction_type = 'BANK_FEE'")
        bank_fees = cursor.fetchone()[0]
        print(f'BankTransactions with type BANK_FEE: {bank_fees}')
        
        cursor.execute("SELECT COUNT(*) FROM BankTransactions WHERE amount < 0")
        negative_amount = cursor.fetchone()[0]
        print(f'BankTransactions with negative amount: {negative_amount}')
        
        cursor.execute("SELECT COUNT(*) FROM BankTransactions WHERE is_reconciled = 1")
        reconciled = cursor.fetchone()[0]
        print(f'Reconciled BankTransactions: {reconciled}')
    
    # Check BankFees table
    if ('BankFees',) in tables:
        cursor.execute("SELECT COUNT(*) FROM BankFees")
        total = cursor.fetchone()[0]
        print(f'Total BankFees: {total}')
    
    conn.close()