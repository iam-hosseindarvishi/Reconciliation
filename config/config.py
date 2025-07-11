#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
تنظیمات برنامه
"""

import os
import sys

# مسیر اصلی پروژه
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# مسیر پایگاه داده
DATABASE_PATH = os.path.join(BASE_DIR, 'data', 'reconciliation_db.sqlite')

# مسیر فایل‌های لاگ
LOG_DIR = os.path.join(BASE_DIR, 'data')
ACTIVITY_LOG_PATH = os.path.join(LOG_DIR, 'activity.log')
ERROR_LOG_PATH = os.path.join(LOG_DIR, 'errors.txt')

# مسیر فایل‌های گزارش
REPORTS_DIR = os.path.join(BASE_DIR, 'reports')

# تنظیمات لاگ
LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
ACTIVITY_LOG_MAX_SIZE = 10 * 1024 * 1024  # 10 مگابایت
ACTIVITY_LOG_BACKUP_COUNT = 5
ERROR_LOG_MAX_SIZE = 5 * 1024 * 1024  # 5 مگابایت
ERROR_LOG_BACKUP_COUNT = 3

# تنظیمات پایگاه داده
DB_TIMEOUT = 30  # زمان انتظار برای قفل پایگاه داده (ثانیه)

# تنظیمات بارگذاری داده
BANK_FILE_EXTENSIONS = ['.xls']
POS_FILE_EXTENSIONS = ['.xlsx']
ACCOUNTING_FILE_EXTENSIONS = ['.xls']

# نگاشت ستون‌های فایل بانک
BANK_COLUMN_MAPPING = {
    'توضیحات': 'Description_Bank',
    'واریز کننده/دریافت کننده': 'Payer_Receiver',
    'پیگیری': 'Bank_Tracking_ID',
    'پیگیری واریز': 'Shaparak_Deposit_Tracking_ID_Raw',
    'مانده': 'Balance',
    'واریز': 'Deposit_Amount',
    'برداشت': 'Withdrawal_Amount',
    'شعبه': 'Branch_Code',
    'زمان': 'Time',
    'تاریخ': 'Date'
}

# نگاشت ستون‌های فایل پوز
POS_COLUMN_MAPPING = {
    'شماره پیگیری': 'POS_Tracking_Number',
    'شماره کارت': 'Card_Number',
    'شناسه شعبه مشتری': 'Terminal_ID',
    'نام شعبه مشتری': 'Terminal_Name',
    'شناسه پایانه': 'Terminal_ID_Secondary',
    'نوع تراکنش': 'Transaction_Type_POS',
    'مبلغ تراکنش': 'Transaction_Amount',
    'تاریخ تراکنش': 'Transaction_Date',
    'ساعت تراکنش': 'Transaction_Time',
    'وضعیت تراکنش': 'Transaction_Status'
}

# نگاشت ستون‌های فایل حسابداری
ACCOUNTING_COLUMN_MAPPING = {
    'نوع': 'Entry_Type_Acc',
    'شماره': 'Account_Reference_Suffix',
    'بدهکار': 'Debit',
    'بستانکار': 'Credit',
    'تاریخ سررسید': 'Due_Date',
    'totmergedpersonsName': 'Person_Name',
    'ChqStDate': 'Check_Date',
    'توضیحات': 'Description_Notes_Acc'
}

# تنظیمات مغایرت‌گیری
DATE_TOLERANCE = 1  # تلرانس روز برای مغایرت‌گیری تاریخ
AMOUNT_TOLERANCE = 0  # تلرانس مبلغ برای مغایرت‌گیری (ریال)

# تنظیمات گزارش‌گیری
REPORT_FONT_NAME = 'Nazanin'  # نام فونت فارسی برای گزارش‌ها
REPORT_FONT_PATH = os.path.join(BASE_DIR, 'config', 'fonts', 'BNazanin.ttf')  # مسیر فونت فارسی
REPORT_TITLE_FONT_SIZE = 16
REPORT_HEADER_FONT_SIZE = 12
REPORT_BODY_FONT_SIZE = 10

# تنظیمات رابط کاربری
APPLICATION_NAME = "سیستم مغایرت‌گیری بانک، پوز و حسابداری"
APPLICATION_VERSION = "1.0.0"
APPLICATION_ORGANIZATION = "شرکت نمونه"

# ایجاد دایرکتوری‌های مورد نیاز
os.makedirs(LOG_DIR, exist_ok=True)
os.makedirs(REPORTS_DIR, exist_ok=True)
os.makedirs(os.path.dirname(DATABASE_PATH), exist_ok=True)
os.makedirs(os.path.join(BASE_DIR, 'config', 'fonts'), exist_ok=True)