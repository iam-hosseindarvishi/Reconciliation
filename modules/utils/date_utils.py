# -*- coding: utf-8 -*-
"""
ماژول ابزارهای تاریخ
شامل توابع کمکی برای تبدیل و مدیریت تاریخ‌ها
"""

import datetime
from typing import Optional

def convert_bank_date_to_accounting_format(bank_date: str) -> str:
    """
    تبدیل تاریخ بانک از فرمت YYYY/MM/DD به فرمت حسابداری YYYYMMDD
    
    پارامترها:
        bank_date: تاریخ بانک در فرمت YYYY/MM/DD
        
    خروجی:
        تاریخ در فرمت YYYYMMDD
    """
    try:
        if not bank_date:
            return ""
            
        # حذف فاصله‌های اضافی
        bank_date = bank_date.strip()
        
        # تبدیل از YYYY/MM/DD به YYYYMMDD
        if '/' in bank_date:
            parts = bank_date.split('/')
            if len(parts) == 3:
                year, month, day = parts
                # اطمینان از اینکه ماه و روز دو رقمی هستند
                month = month.zfill(2)
                day = day.zfill(2)
                return f"{year}{month}{day}"
                
        # اگر فرمت متفاوت بود، تلاش برای تبدیل مستقیم
        return bank_date.replace('/', '')
        
    except Exception as e:
        print(f"خطا در تبدیل تاریخ بانک {bank_date}: {str(e)}")
        return ""

def convert_accounting_date_to_bank_format(accounting_date: str) -> str:
    """
    تبدیل تاریخ حسابداری از فرمت YYYYMMDD به فرمت بانک YYYY/MM/DD
    
    پارامترها:
        accounting_date: تاریخ حسابداری در فرمت YYYYMMDD
        
    خروجی:
        تاریخ در فرمت YYYY/MM/DD
    """
    try:
        if not accounting_date or len(accounting_date) != 8:
            return ""
            
        year = accounting_date[:4]
        month = accounting_date[4:6]
        day = accounting_date[6:8]
        
        return f"{year}/{month}/{day}"
        
    except Exception as e:
        print(f"خطا در تبدیل تاریخ حسابداری {accounting_date}: {str(e)}")
        return ""

def get_current_persian_date() -> str:
    """
    دریافت تاریخ فارسی فعلی در فرمت YYYY-MM-DD HH:MM:SS
    
    خروجی:
        تاریخ فارسی فعلی
    """
    from datetime import datetime
    return datetime.now().strftime('%Y-%m-%d %H:%M:%S')

def get_current_persian_date_accounting_format() -> str:
    """
    دریافت تاریخ فارسی فعلی در فرمت حسابداری (YYYYMMDD)
    
    خروجی:
        تاریخ فارسی فعلی در فرمت YYYYMMDD
    """
    from datetime import datetime
    return datetime.now().strftime('%Y%m%d')

def validate_date_format(date_str: str, format_type: str = 'bank') -> bool:
    """
    اعتبارسنجی فرمت تاریخ
    
    پارامترها:
        date_str: رشته تاریخ
        format_type: نوع فرمت ('bank' برای YYYY/MM/DD یا 'accounting' برای YYYYMMDD)
        
    خروجی:
        True در صورت معتبر بودن فرمت
    """
    try:
        if not date_str:
            return False
            
        if format_type == 'bank':
            # بررسی فرمت YYYY/MM/DD
            if len(date_str) == 10 and date_str.count('/') == 2:
                parts = date_str.split('/')
                if len(parts) == 3:
                    year, month, day = parts
                    return (len(year) == 4 and year.isdigit() and 
                           len(month) <= 2 and month.isdigit() and 
                           len(day) <= 2 and day.isdigit())
                           
        elif format_type == 'accounting':
            # بررسی فرمت YYYYMMDD
            return len(date_str) == 8 and date_str.isdigit()
            
        return False
        
    except Exception as e:
        print(f"خطا در اعتبارسنجی تاریخ {date_str}: {str(e)}")
        return False

def parse_date_safely(date_str: str, format_type: str = 'bank') -> Optional[datetime.datetime]:
    """
    تبدیل ایمن رشته تاریخ به شیء datetime
    
    پارامترها:
        date_str: رشته تاریخ
        format_type: نوع فرمت ('bank' یا 'accounting')
        
    خروجی:
        شیء datetime یا None در صورت خطا
    """
    try:
        if not validate_date_format(date_str, format_type):
            return None
            
        if format_type == 'bank':
            # تبدیل از YYYY/MM/DD
            return datetime.datetime.strptime(date_str, '%Y/%m/%d')
        elif format_type == 'accounting':
            # تبدیل از YYYYMMDD
            return datetime.datetime.strptime(date_str, '%Y%m%d')
            
        return None
        
    except Exception as e:
        print(f"خطا در تبدیل تاریخ {date_str}: {str(e)}")
        return None