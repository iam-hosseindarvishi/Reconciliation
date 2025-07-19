#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
تست توابع اعتبارسنجی تاریخ شمسی
"""

import sys
sys.path.append('.')

from modules.reconciliation_logic import validate_persian_date, safe_parse_persian_date, is_persian_leap_year

def test_date_validation():
    """
    تست توابع اعتبارسنجی تاریخ
    """
    print("=== تست اعتبارسنجی تاریخ شمسی ===")
    
    # تست تاریخ‌های معتبر
    valid_dates = [
        "1404/02/29",  # روز معتبر در اردیبهشت
        "1404/02/31",  # آخرین روز اردیبهشت
        "1404/01/15",  # فروردین
        "1404/12/29",  # اسفند (سال عادی)
        "1403/12/30",  # اسفند سال کبیسه (اگر کبیسه باشد)
    ]
    
    print("\n--- تاریخ‌های معتبر ---")
    for date in valid_dates:
        is_valid = validate_persian_date(date)
        parsed = safe_parse_persian_date(date)
        print(f"{date}: معتبر={is_valid}, پارس شده={'✓' if parsed else '✗'}")
    
    # تست تاریخ‌های نامعتبر
    invalid_dates = [
        "1404/02/30",  # روز نامعتبر در اردیبهشت
        "1404/02/32",  # روز نامعتبر
        "1404/13/01",  # ماه نامعتبر
        "1404/00/15",  # ماه نامعتبر
        "1404/02/00",  # روز نامعتبر
        "1404/07/32",  # روز نامعتبر در مهر
        "1404/12/31",  # روز نامعتبر در اسفند (سال عادی)
        "abc/02/15",   # فرمت نامعتبر
        "1404-02-15",  # فرمت متفاوت (باید معتبر باشد)
        "",             # رشته خالی
        None,           # None
    ]
    
    print("\n--- تاریخ‌های نامعتبر ---")
    for date in invalid_dates:
        is_valid = validate_persian_date(str(date) if date else "")
        parsed = safe_parse_persian_date(str(date) if date else "")
        print(f"{date}: معتبر={is_valid}, پارس شده={'✓' if parsed else '✗'}")
    
    # تست سال‌های کبیسه
    print("\n--- تست سال‌های کبیسه ---")
    test_years = [1400, 1401, 1402, 1403, 1404, 1405, 1406, 1407, 1408]
    for year in test_years:
        is_leap = is_persian_leap_year(year)
        print(f"سال {year}: کبیسه={'✓' if is_leap else '✗'}")
    
    print("\n=== پایان تست ===")

if __name__ == '__main__':
    test_date_validation()