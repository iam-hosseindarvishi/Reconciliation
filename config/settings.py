# تنظیمات کلی برنامه
import os
import sys

# تنظیمات پنجره
WINDOW_WIDTH = 1400
WINDOW_HEIGHT = 900
WINDOW_RESIZABLE = True

# تنظیمات مسیرها
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, 'Data')
DB_PATH = os.path.join(DATA_DIR, 'app.db')

# تنظیمات فونت
if sys.platform.startswith('win'):
    # فونت‌های پیش‌فرض برای ویندوز
    DEFAULT_FONT = 'B Nazanin'
    # DEFAULT_FONT = 'Microsoft Uighur'
    DEFAULT_FONT_SIZE = 18
    HEADER_FONT_SIZE = 20
    BUTTON_FONT_SIZE = 16
else:
    # فونت‌های پیش‌فرض برای لینوکس/مک
    DEFAULT_FONT = 'Vazir'
    DEFAULT_FONT_SIZE = 14
    HEADER_FONT_SIZE = 16
    BUTTON_FONT_SIZE = 14

# تنظیمات زبان و کدگذاری
ENCODING = 'utf-8'
RTL = True  # راست به چپ بودن متون
