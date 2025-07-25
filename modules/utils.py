#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
ماژول توابع کمکی
این ماژول شامل توابع کمکی و ابزارهای مورد نیاز در سراسر برنامه است.
"""

import os
import re
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any, Union
import pandas as pd

from modules.logger import get_logger

# ایجاد شیء لاگر
logger = get_logger(__name__)


def convert_date_format(date_str: str, from_format: str, to_format: str) -> str:
    """
    تبدیل فرمت تاریخ با پشتیبانی از فرمت‌های مختلف
    
    پارامترها:
        date_str: رشته تاریخ ورودی
        from_format: فرمت ورودی ('YYYY/MM/DD' یا 'YYYYMMDD')
        to_format: فرمت خروجی ('YYYY/MM/DD' یا 'YYYYMMDD')
        
    خروجی:
        رشته تاریخ با فرمت جدید
    """
    try:
        if not date_str:
            return ""
            
        date_str = date_str.strip()
        
        # تبدیل از YYYY/MM/DD به YYYYMMDD
        if from_format == 'YYYY/MM/DD' and to_format == 'YYYYMMDD':
            if '/' in date_str:
                parts = date_str.split('/')
                if len(parts) == 3:
                    year, month, day = parts
                    # اطمینان از اینکه ماه و روز دو رقمی هستند
                    month = month.zfill(2)
                    day = day.zfill(2)
                    return f"{year}{month}{day}"
            return date_str.replace('/', '')
            
        # تبدیل از YYYYMMDD به YYYY/MM/DD
        elif from_format == 'YYYYMMDD' and to_format == 'YYYY/MM/DD':
            if len(date_str) == 8 and date_str.isdigit():
                year = date_str[:4]
                month = date_str[4:6]
                day = date_str[6:8]
                return f"{year}/{month}/{day}"
            return date_str
            
        # پشتیبانی از فرمت YY/MM/DD -> 14YYMMDD
        elif from_format == 'YY/MM/DD' and to_format == 'YYYYMMDD':
            if '/' in date_str:
                parts = date_str.split('/')
                if len(parts) == 3:
                    year, month, day = parts
                    # اضافه کردن 14 به ابتدای سال دو رقمی
                    full_year = f"14{year.zfill(2)}"
                    month = month.zfill(2)
                    day = day.zfill(2)
                    return f"{full_year}{month}{day}"
                    
        # اگر فرمت‌ها یکسان باشند
        if from_format == to_format:
            return date_str
            
        # تلاش برای تبدیل با استفاده از datetime
        date_obj = datetime.strptime(date_str, from_format)
        return date_obj.strftime(to_format)
        
    except Exception as e:
        logger.warning(f"خطا در تبدیل فرمت تاریخ: {str(e)}, تاریخ: {date_str}")
        return date_str  # بازگرداندن تاریخ اصلی در صورت خطا


def get_current_persian_date() -> str:
    """
    دریافت تاریخ فارسی فعلی در فرمت YYYY-MM-DD HH:MM:SS
    
    خروجی:
        تاریخ فارسی فعلی
    """
    return datetime.now().strftime('%Y-%m-%d %H:%M:%S')


def convert_bank_date_to_accounting_format(date_str: str) -> str:
    """
    تبدیل فرمت تاریخ بانکی به فرمت حسابداری
    
    پارامترها:
        date_str: رشته تاریخ بانکی
        
    خروجی:
        رشته تاریخ با فرمت حسابداری
    """
    try:
        if not date_str:
            return ""
            
        # تبدیل فرمت‌های مختلف تاریخ
        if '/' in date_str:
            return convert_date_format(date_str, 'YYYY/MM/DD', 'YYYYMMDD')
        else:
            return date_str
    except Exception as e:
        logger.warning(f"خطا در تبدیل فرمت تاریخ بانکی: {str(e)}, تاریخ: {date_str}")
        return date_str


def jalali_to_gregorian(jy: int, jm: int, jd: int) -> Tuple[int, int, int]:
    """
    تبدیل تاریخ جلالی به میلادی
    
    پارامترها:
        jy: سال جلالی
        jm: ماه جلالی
        jd: روز جلالی
        
    خروجی:
        تاپل (سال، ماه، روز) میلادی
    """
    jy += 1595
    days = -355668 + (365 * jy) + ((jy // 33) * 8) + (((jy % 33) + 3) // 4) + jd
    
    if jm < 7:
        days += (jm - 1) * 31
    else:
        days += ((jm - 7) * 30) + 186
    
    gy = 400 * (days // 146097)
    days %= 146097
    
    if days > 36524:
        days -= 1
        gy += 100 * (days // 36524)
        days %= 36524
        
        if days >= 365:
            days += 1
    
    gy += 4 * (days // 1461)
    days %= 1461
    
    if days > 365:
        gy += (days - 1) // 365
        days = (days - 1) % 365
    
    gd = days + 1
    
    if ((gy % 4 == 0 and gy % 100 != 0) or (gy % 400 == 0)):
        kab = 29
    else:
        kab = 28
    
    sal_a = [0, 31, kab, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    gm = 0
    
    while gm < 13 and gd > sal_a[gm]:
        gd -= sal_a[gm]
        gm += 1
    
    return gy, gm, gd


def get_previous_date(date_str: str) -> str:
    """
    دریافت تاریخ یک روز قبل با فرمت YYYYMMDD

    پارامترها:
        date_str: رشته تاریخ با فرمت YYYYMMDD

    خروجی:
        رشته تاریخ یک روز قبل با فرمت YYYYMMDD
    """
    try:
        # تبدیل رشته به شیء تاریخ
        current_date = datetime.strptime(date_str, '%Y%m%d')
        # کم کردن یک روز
        previous_date = current_date - timedelta(days=1)
        # تبدیل به رشته با فرمت مورد نظر
        return previous_date.strftime('%Y%m%d')
    except (ValueError, TypeError):
        # در صورت بروز خطا، تاریخ اصلی را باز می‌گرداند
        return date_str

def gregorian_to_jalali(gy: int, gm: int, gd: int) -> Tuple[int, int, int]:
    """
    تبدیل تاریخ میلادی به جلالی
    
    پارامترها:
        gy: سال میلادی
        gm: ماه میلادی
        gd: روز میلادی
        
    خروجی:
        تاپل (سال، ماه، روز) جلالی
    """
    g_d_m = [0, 31, 59, 90, 120, 151, 181, 212, 243, 273, 304, 334]
    
    if (gy > 1600):
        jy = 979
        gy -= 1600
    else:
        jy = 0
        gy -= 621
    
    gy2 = (gm > 2) and (gy + 1) or gy
    days = (365 * gy) + ((gy2 + 3) // 4) - ((gy2 + 99) // 100) + ((gy2 + 399) // 400) - 80 + gd + g_d_m[gm - 1]
    jy += 33 * (days // 12053)
    days %= 12053
    jy += 4 * (days // 1461)
    days %= 1461
    
    if days > 365:
        jy += (days - 1) // 365
        days = (days - 1) % 365
    
    if days < 186:
        jm = 1 + (days // 31)
        jd = 1 + (days % 31)
    else:
        jm = 7 + ((days - 186) // 30)
        jd = 1 + ((days - 186) % 30)
    
    return jy, jm, jd


def convert_jalali_to_gregorian_str(jalali_date: str, input_format: str = '%Y/%m/%d', output_format: str = '%Y-%m-%d') -> Optional[str]:
    """
    تبدیل رشته تاریخ جلالی به میلادی
    
    پارامترها:
        jalali_date: رشته تاریخ جلالی
        input_format: فرمت ورودی
        output_format: فرمت خروجی
        
    خروجی:
        رشته تاریخ میلادی یا None در صورت خطا
    """
    try:
        # استخراج اجزای تاریخ از رشته
        date_obj = datetime.strptime(jalali_date, input_format)
        jy, jm, jd = date_obj.year, date_obj.month, date_obj.day
        
        # تبدیل به میلادی
        gy, gm, gd = jalali_to_gregorian(jy, jm, jd)
        
        # ایجاد شیء تاریخ میلادی
        g_date = datetime(gy, gm, gd)
        
        # تبدیل به رشته با فرمت مورد نظر
        return g_date.strftime(output_format)
    except Exception as e:
        logger.warning(f"خطا در تبدیل تاریخ جلالی به میلادی: {str(e)}, تاریخ: {jalali_date}")
        return None


def convert_gregorian_to_jalali_str(gregorian_date: str, input_format: str = '%Y-%m-%d', output_format: str = '%Y/%m/%d') -> Optional[str]:
    """
    تبدیل رشته تاریخ میلادی به جلالی
    
    پارامترها:
        gregorian_date: رشته تاریخ میلادی
        input_format: فرمت ورودی
        output_format: فرمت خروجی
        
    خروجی:
        رشته تاریخ جلالی یا None در صورت خطا
    """
    try:
        # استخراج اجزای تاریخ از رشته
        date_obj = datetime.strptime(gregorian_date, input_format)
        gy, gm, gd = date_obj.year, date_obj.month, date_obj.day
        
        # تبدیل به جلالی
        jy, jm, jd = gregorian_to_jalali(gy, gm, gd)
        
        # تبدیل به رشته با فرمت مورد نظر
        jalali_date_str = output_format.replace('%Y', str(jy)).replace('%m', str(jm).zfill(2)).replace('%d', str(jd).zfill(2))
        return jalali_date_str
    except Exception as e:
        logger.warning(f"خطا در تبدیل تاریخ میلادی به جلالی: {str(e)}, تاریخ: {gregorian_date}")
        return None


def extract_digits(text: str) -> Optional[str]:
    """
    استخراج ارقام از یک رشته
    
    پارامترها:
        text: رشته ورودی
        
    خروجی:
        رشته حاوی فقط ارقام یا None در صورت عدم وجود رقم
    """
    if not text or not isinstance(text, str):
        return None
        
    digits = re.sub(r'\D', '', text)
    return digits if digits else None


def format_currency(amount: Union[float, int, str]) -> str:
    """
    فرمت‌بندی مبلغ به صورت پولی
    
    پارامترها:
        amount: مبلغ
        
    خروجی:
        رشته فرمت‌بندی شده
    """
    try:
        if isinstance(amount, str):
            amount = float(amount.replace(',', ''))
        
        return f"{int(amount):,}"
    except Exception as e:
        logger.warning(f"خطا در فرمت‌بندی مبلغ: {str(e)}, مبلغ: {amount}")
        return str(amount)


def normalize_persian_text(text: str) -> str:
    """
    یکسان‌سازی متن فارسی
    
    پارامترها:
        text: متن ورودی
        
    خروجی:
        متن یکسان‌سازی شده
    """
    if not text or not isinstance(text, str):
        return ""
    
    # تبدیل کاراکترهای عربی به فارسی
    replacements = {
        'ي': 'ی',
        'ك': 'ک',
        '٠': '۰',
        '١': '۱',
        '٢': '۲',
        '٣': '۳',
        '٤': '۴',
        '٥': '۵',
        '٦': '۶',
        '٧': '۷',
        '٨': '۸',
        '٩': '۹'
    }
    
    for arabic, persian in replacements.items():
        text = text.replace(arabic, persian)
    
    # حذف فاصله‌های اضافی
    text = re.sub(r'\s+', ' ', text).strip()
    
    return text


def get_file_extension(file_path: str) -> str:
    """
    دریافت پسوند فایل
    
    پارامترها:
        file_path: مسیر فایل
        
    خروجی:
        پسوند فایل
    """
    return os.path.splitext(file_path)[1].lower()


def is_excel_file(file_path: str) -> bool:
    """
    بررسی اینکه آیا فایل از نوع اکسل است
    
    پارامترها:
        file_path: مسیر فایل
        
    خروجی:
        True اگر فایل اکسل باشد، در غیر این صورت False
    """
    ext = get_file_extension(file_path)
    return ext in ['.xls', '.xlsx', '.xlsm']


def read_excel_file(file_path: str, sheet_name: Optional[str] = None) -> pd.DataFrame:
    """
    خواندن فایل اکسل
    
    پارامترها:
        file_path: مسیر فایل
        sheet_name: نام شیت (اختیاری)
        
    خروجی:
        دیتافریم پانداس
    """
    try:
        if not os.path.exists(file_path):
            logger.error(f"فایل {file_path} وجود ندارد.")
            return pd.DataFrame()
            
        if not is_excel_file(file_path):
            logger.error(f"فایل {file_path} یک فایل اکسل معتبر نیست.")
            return pd.DataFrame()
        
        # خواندن فایل اکسل
        if sheet_name:
            df = pd.read_excel(file_path, sheet_name=sheet_name)
        else:
            df = pd.read_excel(file_path)
            
        return df
    except Exception as e:
        logger.error(f"خطا در خواندن فایل اکسل {file_path}: {str(e)}")
        return pd.DataFrame()


def find_close_matches(value: float, values_list: List[float], tolerance: float = 0.01) -> List[int]:
    """
    یافتن مقادیر نزدیک در یک لیست
    
    پارامترها:
        value: مقدار مورد نظر
        values_list: لیست مقادیر
        tolerance: حد تلرانس (اختلاف مجاز)
        
    خروجی:
        لیست ایندکس‌های مقادیر نزدیک
    """
    matches = []
    for i, v in enumerate(values_list):
        if abs(v - value) <= tolerance:
            matches.append(i)
    return matches


def convert_short_jalali_to_standard(date_str: str) -> Optional[str]:
    """
    تبدیل فرمت تاریخ شمسی از YY/MM/DD به YYYY/MM/DD
    
    پارامترها:
        date_str: رشته تاریخ شمسی با فرمت YY/MM/DD
        
    خروجی:
        رشته تاریخ با فرمت YYYY/MM/DD یا None در صورت خطا
    """
    try:
        if not date_str or not isinstance(date_str, str):
            return None
            
        # حذف فاصله‌های احتمالی
        date_str = date_str.strip()
        
        # بررسی الگوی YY/MM/DD
        pattern = r'^(\d{2})/(\d{1,2})/(\d{1,2})$'
        match = re.match(pattern, date_str)
        
        if not match:
            return date_str  # اگر الگو مطابقت نداشت، همان رشته را برگردان
            
        yy, mm, dd = match.groups()
        
        # تبدیل به YYYY/MM/DD
        # برای سال‌های کمتر از 1400، قرن 14 را اضافه می‌کنیم
        # برای سال‌های بیشتر از 1400، قرن 13 را اضافه می‌کنیم
        if int(yy) < 40:  # فرض می‌کنیم سال‌های 00 تا 39 مربوط به 1400 تا 1439 هستند
            yyyy = f"14{yy}"
        else:  # فرض می‌کنیم سال‌های 40 تا 99 مربوط به 1340 تا 1399 هستند
            yyyy = f"13{yy}"
            
        # اطمینان از دو رقمی بودن ماه و روز
        mm = mm.zfill(2)
        dd = dd.zfill(2)
        
        return f"{yyyy}/{mm}/{dd}"
    except Exception as e:
        logger.warning(f"خطا در تبدیل فرمت تاریخ شمسی: {str(e)}, تاریخ: {date_str}")
        return None


def get_date_range(date_str: str, days_before: int = 0, days_after: int = 0, 
                  date_format: str = '%Y/%m/%d') -> List[str]:
    """
    دریافت محدوده تاریخ
    
    پارامترها:
        date_str: رشته تاریخ
        days_before: تعداد روزهای قبل
        days_after: تعداد روزهای بعد
        date_format: فرمت تاریخ
        
    خروجی:
        لیست رشته‌های تاریخ
    """
    try:
        date_obj = datetime.strptime(date_str, date_format)
        date_range = []
        
        for i in range(-days_before, days_after + 1):
            new_date = date_obj + timedelta(days=i)
            date_range.append(new_date.strftime(date_format))
            
        return date_range
    except Exception as e:
        logger.warning(f"خطا در محاسبه محدوده تاریخ: {str(e)}, تاریخ: {date_str}")
        return [date_str]  # در صورت خطا، فقط تاریخ اصلی را برگردان