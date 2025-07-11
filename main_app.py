#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
مدول اصلی برنامه مغایرت‌گیری بانک، پوز و حسابداری
این ماژول نقطه ورود اصلی برنامه است و مسئول راه‌اندازی رابط کاربری و اتصال تمام ماژول‌های دیگر است.
"""

import sys
import os
import traceback
from datetime import datetime

# تنظیم کدگذاری برای پشتیبانی از زبان فارسی
import locale
import platform

# افزودن مسیر پروژه به مسیرهای پایتون
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(BASE_DIR)

# واردسازی ماژول‌های برنامه
from PySide6.QtWidgets import QApplication, QMessageBox, QSplashScreen
from PySide6.QtCore import Qt, QTranslator, QLocale, QLibraryInfo, QTimer
from PySide6.QtGui import QPixmap, QFont, QFontDatabase

from config.config import APPLICATION_NAME, APPLICATION_VERSION, APPLICATION_ORGANIZATION
from modules.logger import setup_logging, get_logger, log_exception
from modules.database_manager import DatabaseManager
from ui.main_window import MainWindow


# راه‌اندازی سیستم لاگ
setup_logging()
logger = get_logger(__name__)

def setup_persian_support():
    """
    تنظیم پشتیبانی از زبان فارسی
    """
    try:
        # تنظیم لوکال برای پشتیبانی از فارسی
        if platform.system() == 'Windows':
            locale.setlocale(locale.LC_ALL, 'Persian_Iran.1256')
        else:  # لینوکس و مک
            locale.setlocale(locale.LC_ALL, 'fa_IR.UTF-8')
        
        logger.info("پشتیبانی از زبان فارسی با موفقیت تنظیم شد.")
        return True
    except Exception as e:
        logger.warning(f"خطا در تنظیم پشتیبانی از زبان فارسی: {str(e)}")
        return False

def setup_qt_persian_support(app):
    """
    تنظیم پشتیبانی از زبان فارسی در Qt
    """
    try:
        # افزودن فونت‌های فارسی
        fonts_dir = os.path.join(BASE_DIR, 'config', 'fonts')
        if os.path.exists(fonts_dir):
            for font_file in os.listdir(fonts_dir):
                if font_file.endswith('.ttf'):
                    font_path = os.path.join(fonts_dir, font_file)
                    QFontDatabase.addApplicationFont(font_path)
        
        # تنظیم فونت پیش‌فرض برنامه
        default_font = QFont("Tahoma", 9)  # فونت تاهوما برای رابط کاربری
        app.setFont(default_font)
        
        # تنظیم جهت راست به چپ برای رابط کاربری
        app.setLayoutDirection(Qt.RightToLeft)
        
        # تنظیم مترجم Qt
        translator = QTranslator()
        translator.load("qtbase_" + QLocale.system().name(),
                       QLibraryInfo.location(QLibraryInfo.TranslationsPath))
        app.installTranslator(translator)
        
        logger.info("پشتیبانی از زبان فارسی در Qt با موفقیت تنظیم شد.")
        return True
    except Exception as e:
        logger.warning(f"خطا در تنظیم پشتیبانی از زبان فارسی در Qt: {str(e)}")
        return False

def exception_hook(exc_type, exc_value, exc_traceback):
    """
    هندلر استثناهای پیش‌بینی نشده
    """
    # ثبت استثنا در لاگ
    log_exception(exc_value, exc_traceback)
    
    # نمایش پیام خطا به کاربر
    error_msg = f"خطای پیش‌بینی نشده: {str(exc_value)}"
    QMessageBox.critical(None, "خطای سیستم", error_msg)

def main():
    """
    تابع اصلی برنامه که مسئول راه‌اندازی برنامه است
    """
    try:
        # ثبت شروع برنامه در لاگ
        logger.info(f"شروع برنامه {APPLICATION_NAME} نسخه {APPLICATION_VERSION}")
        
        # تنظیم هندلر استثناهای پیش‌بینی نشده
        sys.excepthook = exception_hook
        
        # راه‌اندازی برنامه Qt
        app = QApplication(sys.argv)
        app.setApplicationName(APPLICATION_NAME)
        app.setApplicationVersion(APPLICATION_VERSION)
        app.setOrganizationName(APPLICATION_ORGANIZATION)
        
        # تنظیم پشتیبانی از زبان فارسی
        setup_persian_support()
        setup_qt_persian_support(app)
        
        # نمایش صفحه اسپلش
        splash_pixmap = QPixmap(os.path.join(BASE_DIR, 'config', 'splash.svg'))
        if not splash_pixmap.isNull():
            splash = QSplashScreen(splash_pixmap)
            splash.show()
            app.processEvents()
        else:
            splash = None
        
        # راه‌اندازی پایگاه داده
        db_manager = DatabaseManager()
        db_manager.connect()
        db_manager.setup_database()
        
        # راه‌اندازی پنجره اصلی با تاخیر
        def show_main_window():
            main_window = MainWindow()
            main_window.show()
            if splash:
                splash.finish(main_window)
        
        # نمایش پنجره اصلی پس از 1 ثانیه
        QTimer.singleShot(1000, show_main_window)
        
        # اجرای حلقه رویداد برنامه
        return app.exec()
    
    except Exception as e:
        # ثبت خطا در لاگ
        logger.critical(f"خطای بحرانی در اجرای برنامه: {str(e)}")
        log_exception(e, traceback.extract_tb(sys.exc_info()[2]))
        
        # نمایش پیام خطا به کاربر
        error_msg = f"خطای بحرانی در اجرای برنامه: {str(e)}"
        QMessageBox.critical(None, "خطای سیستم", error_msg)
        
        return 1

if __name__ == "__main__":
    sys.exit(main())