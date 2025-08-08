import os
import logging
from config.settings import DATA_DIR

def setup_logger(name):
    """تنظیمات مرکزی لاگر"""
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    
    # اطمینان از وجود دایرکتوری
    os.makedirs(DATA_DIR, exist_ok=True)
    
    # فرمتر برای لاگ‌ها
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    # هندلر برای فایل خطا
    error_handler = logging.FileHandler(os.path.join(DATA_DIR, 'error.txt'))
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(formatter)
    logger.addHandler(error_handler)
    
    # هندلر برای لاگ عمومی
    file_handler = logging.FileHandler(os.path.join(DATA_DIR, 'Log.txt'))
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    
    return logger
