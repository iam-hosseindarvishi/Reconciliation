import sqlite3

conn = sqlite3.connect('data/reconciliation_db.sqlite')
cursor = conn.cursor()

cursor.execute("SELECT DISTINCT Transaction_Type_Bank FROM BankTransactions")

for row in cursor.fetchall():
    print(row[0])

conn.close()