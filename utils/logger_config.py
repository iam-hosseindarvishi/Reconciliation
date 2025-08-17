import os
import logging
import locale
import codecs
from config.settings import DATA_DIR

def setup_logger(name):
    """تنظیمات مرکزی لاگر با پشتیبانی از زبان فارسی"""
    # تنظیم locale برای پشتیبانی از زبان فارسی
    try:
        locale.setlocale(locale.LC_ALL, 'fa_IR.UTF-8')
    except locale.Error:
        try:
            locale.setlocale(locale.LC_ALL, 'Persian_Iran.1256')
        except locale.Error:
            pass

    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    
    # اطمینان از وجود دایرکتوری
    os.makedirs(DATA_DIR, exist_ok=True)
    
    # فرمتر برای لاگ‌ها
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s', 
                                datefmt='%Y-%m-%d %H:%M:%S')
    
    # هندلر برای فایل خطا با پشتیبانی از UTF-8
    error_path = os.path.join(DATA_DIR, 'error.txt')
    error_handler = logging.FileHandler(error_path, 'a', 'utf-8')
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(formatter)
    logger.addHandler(error_handler)
    
    # هندلر برای لاگ عمومی با پشتیبانی از UTF-8
    log_path = os.path.join(DATA_DIR, 'Log.txt')
    file_handler = logging.FileHandler(log_path, 'a', 'utf-8')
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    
    # اضافه کردن BOM به فایل‌های لاگ در صورت نیاز
    for path in [error_path, log_path]:
        if not os.path.exists(path) or os.path.getsize(path) == 0:
            with open(path, 'wb') as f:
                f.write(codecs.BOM_UTF8)
    
    return logger
