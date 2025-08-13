from datetime import datetime
import jdatetime
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