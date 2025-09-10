from datetime import datetime
import jdatetime
from utils.logger_config import setup_logger
from datetime import timedelta
# راه‌اندازی لاگر
logger = setup_logger('utils.helpers')

def gregorian_to_persian(gregorian_date_str):
    """
    تبدیل تاریخ میلادی به شمسی با فرمت YYYY/MM/DD
    پشتیبانی از فرمت‌های: yyyy-mm-dd و yyyy-mm-dd HH:MM:SS
    در صورت خطا رشته خالی برمی‌گرداند
    """
    if not gregorian_date_str:
        logger.warning("تاریخ میلادی خالی دریافت شد")
        return ''
    
    try:
        # استخراج بخش تاریخ در صورتی که شامل زمان باشد
        if ' ' in gregorian_date_str:
            date_part = gregorian_date_str.split(' ')[0]
        else:
            date_part = gregorian_date_str
            
        # تبدیل رشته تاریخ میلادی به شیء تاریخ
        gdate = datetime.strptime(date_part, '%Y-%m-%d')
        # تبدیل به تاریخ شمسی
        jdate = jdatetime.date.fromgregorian(date=gdate.date())
        # فرمت‌بندی تاریخ شمسی
        result = jdate.strftime('%Y/%m/%d')
        logger.debug(f"تبدیل تاریخ میلادی {gregorian_date_str} به شمسی {result}")
        return result
    except ValueError as e:
        logger.error(f"خطا در تبدیل تاریخ {gregorian_date_str}: {str(e)}")
        return gregorian_date_str
    except Exception as e:
        logger.error(f"خطای غیرمنتظره در تبدیل تاریخ {gregorian_date_str}: {str(e)}")
        return gregorian_date_str

def persian_to_gregorian(jalali_date_str):
    """
    تبدیل تاریخ شمسی به میلادی با فرمت YYYY-MM-DD
    پشتیبانی از فرمت‌های: yyyy/mm/dd, yyyy-mm-dd, یا yyyy.mm.dd
    در صورت خطا رشته خالی برمی‌گرداند
    """
    if not jalali_date_str:
        logger.warning("تاریخ شمسی خالی دریافت شد")
        return ''
    
    for sep in ['/', '-', '.']:
        if sep in jalali_date_str:
            parts = jalali_date_str.split(sep)
            if len(parts) == 3:
                try:
                    y, m, d = map(int, parts)
                    gdate = jdatetime.date(y, m, d).togregorian()
                    result = gdate.strftime('%Y-%m-%d')
                    logger.debug(f"تبدیل تاریخ شمسی {jalali_date_str} به میلادی {result}")
                    return result
                except ValueError as e:
                    logger.error(f"خطا در تبدیل تاریخ {jalali_date_str}: {str(e)}")
                    return ''
                except Exception as e:
                    logger.error(f"خطای غیرمنتظره در تبدیل تاریخ {jalali_date_str}: {str(e)}")
                    return ''
    
    logger.warning(f"فرمت تاریخ نامعتبر: {jalali_date_str}")
    return ''
def normalize_shamsi_date(date_str):
    """
    رشته تاریخ شمسی با فرمت YYYYMMDD را به YYYY-MM-DD تبدیل می‌کند.

    Args:
        date_str (str): رشته تاریخ ورودی (مثال: '14040101').

    Returns:
        str: رشته تاریخ نرمال‌شده (مثال: '1404-01-01') یا یک رشته خالی در صورت خطا.
    """
    if not isinstance(date_str, str) or len(date_str) != 8 or not date_str.isdigit():
        return ""

    try:
        year = date_str[0:4]
        month = date_str[4:6]
        day = date_str[6:8]
        
        return f"{year}-{month}-{day}"
    except (ValueError, IndexError):
        return ""
def get_pos_date_from_bank(bank_date_str):
    """
    Creates POS date from bank date by subtracting one day
    Args:
        bank_date_str: Date string in YYYY-MM-DD format
    Returns:
        POS date string in YYYY-MM-DD format, empty string if error occurs
    """
    if not bank_date_str:
        logger.warning("Empty bank date received")
        return ''
    
    try:
        # Convert string to datetime object
        bank_date = datetime.strptime(bank_date_str, '%Y-%m-%d')
        # Subtract one day
        pos_date = bank_date.date() - timedelta(days=1)
        # Format back to string
        result = pos_date.strftime('%Y-%m-%d')
        logger.debug(f"Converted bank date {bank_date_str} to POS date {result}")
        return result
    except ValueError as e:
        logger.error(f"Error converting bank date {bank_date_str}: {str(e)}")
        return ''
    except Exception as e:
        logger.error(f"Unexpected error converting bank date {bank_date_str}: {str(e)}")
        return ''
