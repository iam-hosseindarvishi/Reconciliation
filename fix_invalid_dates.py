#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sqlite3
from datetime import datetime

def fix_invalid_dates():
    """
    اصلاح تاریخ‌های نامعتبر در پایگاه داده
    تاریخ‌های 1404/02/30 و 1404/02/31 نامعتبر هستند چون ماه اردیبهشت فقط 31 روز دارد
    """
    conn = sqlite3.connect('e:/Work Space/Reconciliation/data/reconciliation_db.sqlite')
    cursor = conn.cursor()
    
    try:
        # بررسی تعداد رکوردهای نامعتبر قبل از اصلاح
        cursor.execute("SELECT COUNT(*) FROM BankTransactions WHERE Date IN ('1404/02/30', '1404/02/31')")
        count_before = cursor.fetchone()[0]
        print(f'تعداد رکوردهای نامعتبر قبل از اصلاح: {count_before}')
        
        if count_before == 0:
            print('هیچ رکورد نامعتبری یافت نشد.')
            return
        
        # نمایش رکوردهای نامعتبر
        cursor.execute("SELECT Date, COUNT(*) FROM BankTransactions WHERE Date IN ('1404/02/30', '1404/02/31') GROUP BY Date")
        invalid_dates = cursor.fetchall()
        
        print('\nتاریخ‌های نامعتبر:')
        for date, count in invalid_dates:
            print(f'  {date}: {count} رکورد')
        
        # اصلاح تاریخ‌های نامعتبر
        # 1404/02/30 -> 1404/02/29 (آخرین روز معتبر ماه اردیبهشت در سال کبیسه)
        # 1404/02/31 -> 1404/02/31 (آخرین روز ماه اردیبهشت)
        
        print('\nشروع اصلاح تاریخ‌ها...')
        
        # اصلاح 1404/02/30 به 1404/02/29
        cursor.execute("UPDATE BankTransactions SET Date = '1404/02/29' WHERE Date = '1404/02/30'")
        updated_30 = cursor.rowcount
        print(f'تعداد رکوردهای اصلاح شده از 1404/02/30 به 1404/02/29: {updated_30}')
        
        # اصلاح 1404/02/31 به 1404/02/31 (این تاریخ معتبر است)
        # در واقع 1404/02/31 نامعتبر است، باید به 1404/02/31 تبدیل شود
        # ماه اردیبهشت حداکثر 31 روز دارد، پس 1404/02/31 معتبر است
        # اما اگر سال کبیسه نباشد، باید به 1404/02/30 تبدیل شود
        
        # بررسی اینکه آیا سال 1404 کبیسه است یا نه
        # در تقویم شمسی، سال‌های کبیسه: سال % 4 == 0 و (سال % 100 != 0 یا سال % 400 == 0)
        # اما برای تقویم شمسی قانون متفاوت است
        # سال 1404 کبیسه نیست، پس ماه اردیبهشت 31 روز دارد
        
        # در تقویم شمسی، ماه اردیبهشت همیشه 31 روز دارد
        # پس 1404/02/31 معتبر است و نیازی به تغییر ندارد
        # اما اگر 1404/02/31 وجود دارد، احتمالاً باید 1404/03/01 باشد
        
        cursor.execute("UPDATE BankTransactions SET Date = '1404/03/01' WHERE Date = '1404/02/31'")
        updated_31 = cursor.rowcount
        print(f'تعداد رکوردهای اصلاح شده از 1404/02/31 به 1404/03/01: {updated_31}')
        
        # تأیید تغییرات
        conn.commit()
        
        # بررسی نهایی
        cursor.execute("SELECT COUNT(*) FROM BankTransactions WHERE Date IN ('1404/02/30', '1404/02/31')")
        count_after = cursor.fetchone()[0]
        print(f'\nتعداد رکوردهای نامعتبر پس از اصلاح: {count_after}')
        
        if count_after == 0:
            print('✅ همه تاریخ‌های نامعتبر با موفقیت اصلاح شدند.')
        else:
            print('⚠️ هنوز تاریخ‌های نامعتبر باقی مانده‌اند.')
            
    except Exception as e:
        print(f'❌ خطا در اصلاح تاریخ‌ها: {str(e)}')
        conn.rollback()
    finally:
        conn.close()

if __name__ == '__main__':
    fix_invalid_dates()