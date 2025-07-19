#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sqlite3

def check_invalid_dates():
    conn = sqlite3.connect('e:/Work Space/Reconciliation/data/reconciliation_db.sqlite')
    cursor = conn.cursor()
    
    # بررسی تعداد رکوردهای نامعتبر
    cursor.execute("SELECT COUNT(*) FROM BankTransactions WHERE Date IN ('1404/02/30', '1404/02/31')")
    count = cursor.fetchone()[0]
    print(f'تعداد رکوردهای نامعتبر: {count}')
    
    # نمایش نمونه رکوردهای نامعتبر
    cursor.execute("SELECT id, Date, Description_Bank FROM BankTransactions WHERE Date IN ('1404/02/30', '1404/02/31') LIMIT 10")
    results = cursor.fetchall()
    
    print('\nنمونه رکوردهای نامعتبر:')
    for row in results:
        desc = row[2][:50] + '...' if row[2] and len(row[2]) > 50 else row[2]
        print(f'ID: {row[0]}, تاریخ: {row[1]}, توضیحات: {desc}')
    
    conn.close()

if __name__ == '__main__':
    check_invalid_dates()