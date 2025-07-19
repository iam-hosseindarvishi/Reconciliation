#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
بررسی رکوردهای باقی‌مانده با تاریخ‌های نامعتبر
"""

import sqlite3
import os

def check_remaining_invalid_dates():
    """
    بررسی رکوردهای باقی‌مانده با تاریخ‌های نامعتبر در پایگاه داده
    """
    db_path = os.path.join('data', 'reconciliation_db.sqlite')
    
    if not os.path.exists(db_path):
        print(f"فایل پایگاه داده یافت نشد: {db_path}")
        return
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # بررسی تعداد کل رکوردها
        cursor.execute("SELECT COUNT(*) FROM BankTransactions")
        total_count = cursor.fetchone()[0]
        print(f"تعداد کل رکوردها در BankTransactions: {total_count}")
        
        # بررسی رکوردهای با تاریخ‌های نامعتبر
        invalid_dates = ['1404/02/30', '1404/02/31']
        
        for invalid_date in invalid_dates:
            cursor.execute("""
                SELECT COUNT(*) FROM BankTransactions 
                WHERE transaction_date = ?
            """, (invalid_date,))
            count = cursor.fetchone()[0]
            print(f"تعداد رکوردهای با تاریخ {invalid_date}: {count}")
            
            if count > 0:
                # نمایش نمونه‌ای از رکوردهای نامعتبر
                cursor.execute("""
                    SELECT id, transaction_date, amount, description 
                    FROM BankTransactions 
                    WHERE transaction_date = ?
                    LIMIT 5
                """, (invalid_date,))
                
                records = cursor.fetchall()
                print(f"نمونه رکوردهای با تاریخ {invalid_date}:")
                for record in records:
                    print(f"  ID: {record[0]}, تاریخ: {record[1]}, مبلغ: {record[2]}, شرح: {record[3]}")
                print()
        
        # بررسی سایر تاریخ‌های مشکوک
        cursor.execute("""
            SELECT DISTINCT transaction_date, COUNT(*) as count
            FROM BankTransactions 
            WHERE transaction_date LIKE '%/02/30' OR transaction_date LIKE '%/02/31'
               OR transaction_date LIKE '%/02/32' OR transaction_date LIKE '%/02/33'
            GROUP BY transaction_date
            ORDER BY transaction_date
        """)
        
        suspicious_dates = cursor.fetchall()
        if suspicious_dates:
            print("تاریخ‌های مشکوک دیگر:")
            for date, count in suspicious_dates:
                print(f"  {date}: {count} رکورد")
        else:
            print("تاریخ‌های مشکوک دیگری یافت نشد.")
        
        conn.close()
        
    except Exception as e:
        print(f"خطا در بررسی پایگاه داده: {e}")

if __name__ == '__main__':
    check_remaining_invalid_dates()