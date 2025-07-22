# Utils module
import re
from typing import Optional, Union, Tuple
from datetime import datetime

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
        # logger.warning(f"خطا در تبدیل تاریخ میلادی به جلالی: {str(e)}, تاریخ: {gregorian_date}")
        return None

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
        # logger.warning(f"خطا در فرمت‌بندی مبلغ: {str(e)}, مبلغ: {amount}")
        return str(amount)

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
        # logger.warning(f"خطا در تبدیل فرمت تاریخ شمسی: {str(e)}, تاریخ: {date_str}")
        return None

__all__ = ['convert_short_jalali_to_standard', 'format_currency', 'convert_gregorian_to_jalali_str', 'gregorian_to_jalali']