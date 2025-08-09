import sys
import os
import traceback
import locale
import ttkbootstrap as ttk
from tkinter import messagebox
from config.settings import (
    WINDOW_WIDTH, WINDOW_HEIGHT, WINDOW_RESIZABLE,
    DEFAULT_FONT, DEFAULT_FONT_SIZE, HEADER_FONT_SIZE,
    BUTTON_FONT_SIZE, RTL, ENCODING
)
from database.init_db import init_db
from ui.bank_tab import BankTab
from ui.data_entry_tab import DataEntryTab
from utils.logger_config import setup_logger

# تنظیم کدگذاری کنسول برای نمایش درست متون فارسی
if sys.platform.startswith('win'):
    # تنظیم کدگذاری کنسول ویندوز
    os.system('chcp 65001')
    # تنظیم محیط برای پشتیبانی از فارسی
    if os.environ.get('PYTHONIOENCODING') != 'utf-8':
        os.environ['PYTHONIOENCODING'] = 'utf-8'

# تنظیم locale برای پشتیبانی از زبان فارسی
try:
    locale.setlocale(locale.LC_ALL, 'fa_IR.UTF-8')
except locale.Error:
    try:
        locale.setlocale(locale.LC_ALL, 'Persian_Iran.1256')
    except locale.Error:
        pass

# راه‌اندازی لاگر
logger = setup_logger('main')

def main():
    """
    تابع اصلی برنامه با مدیریت خطا و لاگینگ
    """
    try:
        # راه‌اندازی پایگاه داده
        logger.info("در حال راه‌اندازی پایگاه داده...")
        init_db()
        logger.info("پایگاه داده با موفقیت راه‌اندازی شد")

        # ایجاد پنجره اصلی
        logger.info("در حال ایجاد رابط کاربری...")
        app = ttk.Window(themename="cosmo")
        app.title("مدیریت مغایرت‌گیری")
        app.geometry(f"{WINDOW_WIDTH}x{WINDOW_HEIGHT}")
        app.resizable(WINDOW_RESIZABLE, WINDOW_RESIZABLE)

        # تنظیم فونت‌ها برای پشتیبانی از فارسی
        default_font = (DEFAULT_FONT, DEFAULT_FONT_SIZE, 'bold')
        header_font = (DEFAULT_FONT, HEADER_FONT_SIZE, 'bold')
        button_font = (DEFAULT_FONT, BUTTON_FONT_SIZE, 'bold')
        
        style = ttk.Style()
        # تنظیم فونت و وزن برای تمام عناصر رابط کاربری
        style.configure('.', font=default_font)  # تنظیم پیش‌فرض برای همه
        style.configure('TLabel', font=default_font)
        style.configure('TButton', font=button_font)
        style.configure('Treeview', font=default_font)
        style.configure('TEntry', font=default_font)
        style.configure('Header.TLabel', font=header_font)
        style.configure('Treeview.Heading', font=header_font)  # هدر جداول
        
        # تنظیم فونت برای منوها و کامبوباکس‌ها
        app.option_add('*TCombobox*Listbox.font', default_font)
        app.option_add('*Menu.font', default_font)
        
        # تنظیم جهت نوشتار از راست به چپ
        if RTL:
            app.tk.call('tk', 'scaling', 1.0)
            app.tk.call('encoding', 'system', ENCODING)

        # تنظیم مدیریت خطای سراسری
        app.report_callback_exception = handle_exception

        # ایجاد نوت‌بوک
        notebook = ttk.Notebook(app)
        notebook.pack(fill="both", expand=True)

        try:
            # افزودن تب ورود اطلاعات
            logger.info("در حال بارگذاری تب ورود اطلاعات...")
            data_entry_tab = DataEntryTab(notebook)
            notebook.add(data_entry_tab, text="ورود اطلاعات")
            logger.info("تب ورود اطلاعات با موفقیت بارگذاری شد")
        except Exception as e:
            logger.error(f"خطا در بارگذاری تب ورود اطلاعات: {str(e)}")
            raise

        try:
            # افزودن تب مدیریت بانک‌ها
            logger.info("در حال بارگذاری تب مدیریت بانک‌ها...")
            bank_tab = BankTab(notebook)
            notebook.add(bank_tab, text="مدیریت بانک‌ها")
            logger.info("تب مدیریت بانک‌ها با موفقیت بارگذاری شد")
        except Exception as e:
            logger.error(f"خطا در بارگذاری تب مدیریت بانک‌ها: {str(e)}")
            raise

        logger.info("رابط کاربری با موفقیت راه‌اندازی شد")
        
        # شروع حلقه اصلی برنامه
        app.mainloop()

    except Exception as e:
        logger.critical(f"خطای بحرانی در اجرای برنامه: {str(e)}")
        logger.critical(f"جزئیات خطا:\n{traceback.format_exc()}")
        messagebox.showerror(
            "خطای بحرانی",
            "متأسفانه خطای غیرمنتظره‌ای رخ داده است. لطفاً با پشتیبانی تماس بگیرید.\n\n"
            f"جزئیات خطا: {str(e)}"
        )
        sys.exit(1)

def handle_exception(exc_type, exc_value, exc_traceback):
    """
    مدیریت خطاهای مربوط به رابط کاربری
    """
    # لاگ کردن خطا
    logger.error("خطای رابط کاربری:")
    logger.error("".join(traceback.format_exception(exc_type, exc_value, exc_traceback)))
    
    # نمایش پیام خطا به کاربر
    error_message = str(exc_value)
    if not error_message:
        error_message = str(exc_type.__name__)
    
    messagebox.showerror(
        "خطا",
        f"خطایی رخ داده است:\n\n{error_message}\n\n"
        "جزئیات خطا در فایل لاگ ثبت شده است."
    )

if __name__ == "__main__":
    main()
