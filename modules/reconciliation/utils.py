#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
توابع کمکی برای مغایرت‌گیری
این ماژول شامل توابع کمکی مورد استفاده در فرآیند مغایرت‌گیری است.
"""

import re
from datetime import datetime
from typing import Optional
from modules.logger import get_logger

# ایجاد شیء لاگر
logger = get_logger(__name__)

def validate_persian_date(date_str: str) -> bool:
    """
    اعتبارسنجی تاریخ شمسی
    
    پارامترها:
        date_str: رشته تاریخ به فرمت YYYY/MM/DD
        
    خروجی:
        True اگر تاریخ معتبر باشد، در غیر این صورت False
    """
    try:
        if not date_str or not isinstance(date_str, str):
            return False
            
        # بررسی فرمت کلی
        if not re.match(r'^\d{4}/\d{2}/\d{2}$', date_str):
            return False
            
        parts = date_str.split('/')
        year = int(parts[0])
        month = int(parts[1])
        day = int(parts[2])
        
        # بررسی محدوده سال (1300-1500)
        if year < 1300 or year > 1500:
            return False
            
        # بررسی محدوده ماه (1-12)
        if month < 1 or month > 12:
            return False
            
        # تعداد روزهای هر ماه در تقویم شمسی
        days_in_month = {
            1: 31, 2: 31, 3: 31, 4: 31, 5: 31, 6: 31,  # بهار و تابستان
            7: 30, 8: 30, 9: 30, 10: 30, 11: 30,        # پاییز
            12: 29  # زمستان (اسفند)
        }
        
        # بررسی سال کبیسه برای ماه اسفند
        if month == 12:
            # در تقویم شمسی، سال کبیسه هر 4 سال یکبار است
            # اما قانون دقیق‌تر: سال % 33 در چرخه 128 ساله
            # برای سادگی از قانون ساده استفاده می‌کنیم
            if is_persian_leap_year(year):
                days_in_month[12] = 30
                
        # بررسی محدوده روز
        max_days = days_in_month.get(month, 31)
        if day < 1 or day > max_days:
            return False
            
        return True
        
    except (ValueError, IndexError):
        return False

def is_persian_leap_year(year: int) -> bool:
    """
    تشخیص سال کبیسه در تقویم شمسی
    
    پارامترها:
        year: سال شمسی
        
    خروجی:
        True اگر سال کبیسه باشد
    """
    # الگوریتم ساده برای تشخیص سال کبیسه شمسی
    # هر 4 سال یکبار کبیسه است، اما با استثناهایی
    cycle_year = year % 128
    leap_years_in_cycle = [1, 5, 9, 13, 17, 22, 26, 30, 34, 38, 42, 46, 50, 55, 59, 63, 67, 71, 75, 79, 83, 88, 92, 96, 100, 104, 108, 112, 116, 121, 125]
    return cycle_year in leap_years_in_cycle

def safe_parse_persian_date(date_str: str) -> Optional[datetime]:
    """
    پارس امن تاریخ شمسی با اعتبارسنجی
    
    پارامترها:
        date_str: رشته تاریخ
        
    خروجی:
        شیء datetime یا None در صورت خطا
    """
    if not validate_persian_date(date_str):
        logger.error(f"تاریخ شمسی نامعتبر: {date_str}")
        return None
        
    # تلاش برای پارس کردن تاریخ با فرمت‌های مختلف
    for date_format in ['%Y/%m/%d', '%Y-%m-%d', '%d/%m/%Y']:
        try:
            return datetime.strptime(str(date_str), date_format)
        except ValueError:
            continue
            
    logger.error(f"فرمت تاریخ نامعتبر: {date_str}")
    return None

def extract_switch_tracking_number(description: str) -> Optional[str]:
    """
    استخراج شماره پیگیری سوئیچ از توضیحات
    
    پارامترها:
        description: متن توضیحات
        
    خروجی:
        شماره پیگیری یا None
    """
    # جستجو برای عدد بعد از عبارت "شماره پیگیری سوئیچ"
    pattern = r'شماره پیگیری سوئیچ[:\s]*(\d+)'
    match = re.search(pattern, description)
    return match.group(1) if match else None