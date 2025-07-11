#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
ماژول ثبت وقایع (لاگر)
این ماژول مسئول ثبت وقایع و خطاهای برنامه است.
"""

import os
import logging
from logging.handlers import RotatingFileHandler
from datetime import datetime

# تنظیمات مسیرها
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOG_DIR = os.path.join(BASE_DIR, 'data')
ACTIVITY_LOG = os.path.join(LOG_DIR, 'activity.log')
ERROR_LOG = os.path.join(LOG_DIR, 'errors.txt')

# اطمینان از وجود دایرکتوری لاگ
os.makedirs(LOG_DIR, exist_ok=True)

# تنظیمات فرمت لاگ
LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
DATE_FORMAT = '%Y-%m-%d %H:%M:%S'

# لاگرهای مختلف
loggers = {}


def setup_logging():
    """
    راه‌اندازی سیستم ثبت وقایع
    """
    # تنظیم لاگر اصلی
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    
    # فرمت‌کننده لاگ
    formatter = logging.Formatter(LOG_FORMAT, DATE_FORMAT)
    
    # هندلر کنسول
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)
    
    # هندلر فایل فعالیت‌ها
    activity_handler = RotatingFileHandler(
        ACTIVITY_LOG, 
        maxBytes=10*1024*1024,  # 10 مگابایت
        backupCount=5,
        encoding='utf-8'
    )
    activity_handler.setLevel(logging.INFO)
    activity_handler.setFormatter(formatter)
    root_logger.addHandler(activity_handler)
    
    # هندلر فایل خطاها
    error_handler = RotatingFileHandler(
        ERROR_LOG, 
        maxBytes=5*1024*1024,  # 5 مگابایت
        backupCount=3,
        encoding='utf-8'
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(formatter)
    root_logger.addHandler(error_handler)
    
    logging.info("سیستم ثبت وقایع راه‌اندازی شد.")


def get_logger(name):
    """
    دریافت یک لاگر با نام مشخص
    
    پارامترها:
        name: نام لاگر (معمولاً نام ماژول)
        
    خروجی:
        شیء لاگر
    """
    if name in loggers:
        return loggers[name]
    
    logger = logging.getLogger(name)
    loggers[name] = logger
    return logger


def log_exception(e, context=""):
    """
    ثبت استثنا با جزئیات بیشتر
    
    پارامترها:
        e: شیء استثنا
        context: توضیحات اضافی در مورد زمینه استثنا
    """
    logger = get_logger(__name__)
    
    error_message = f"استثنا در {context if context else 'برنامه'}: {str(e)}"
    logger.error(error_message, exc_info=True)
    
    # ثبت در فایل خطاها
    with open(ERROR_LOG, 'a', encoding='utf-8') as f:
        timestamp = datetime.now().strftime(DATE_FORMAT)
        f.write(f"\n{timestamp} - {error_message}\n")
        import traceback
        f.write(traceback.format_exc())
        f.write("\n" + "-"*50 + "\n")