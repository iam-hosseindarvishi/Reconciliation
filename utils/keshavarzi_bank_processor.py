import pandas as pd
import re
from utils.constants import KESHAVARZI_TRANSACTION_TYPES
from utils.pos_excel_importer import persian_to_gregorian
from database.bank_transaction_repository import create_bank_transaction
from utils.logger_config import setup_logger

# راه‌اندازی لاگر
logger = setup_logger('utils.keshavarzi_bank_processor')

def process_keshavarzi_bank_file(keshavarzi_file_path, bank_id):
    """
    پردازش فایل اکسل بانک کشاورزی و ذخیره تراکنش‌ها در دیتابیس
    
    Args:
        keshavarzi_file_path: مسیر فایل اکسل بانک کشاورزی
        bank_id: شناسه بانک کشاورزی
        
    Returns:
        dict: گزارش پردازش شامل تعداد کل ردیف‌ها، تعداد پردازش‌شده، خطاها و آمار نوع تراکنش‌ها
    """
    report = {
        'total_rows': 0,
        'processed': 0,
        'errors': [],
        'transaction_types': {}
    }
    
    try:
        # خواندن فایل اکسل
        logger.info(f"شروع پردازش فایل بانک کشاورزی: {keshavarzi_file_path}")
        df = pd.read_excel(keshavarzi_file_path)
        report['total_rows'] = len(df)
        
        for index, row in df.iterrows():
            try:
                # استخراج داده‌های مورد نیاز
                date = str(row.get('date', ''))
                time = str(row.get('time', ''))
                trantitle = str(row.get('trantitle', ''))
                bed = float(row.get('bed', 0) or 0)
                bes = float(row.get('bes', 0) or 0)
                fulldesc = str(row.get('fulldesc', ''))
                depositorname = str(row.get('depositorname', ''))
                branchname = str(row.get('branchname', ''))
                
                # تعیین نوع تراکنش
                transaction_type = determine_transaction_type(trantitle, depositorname, bed, bes)
                
                # بروزرسانی آمار
                report['transaction_types'][transaction_type] = report['transaction_types'].get(transaction_type, 0) + 1
                
                # محاسبه مبلغ (بدهکار یا بستانکار)
                amount = bes if bes != 0 else -bed  # مقادیر بستانکار مثبت و بدهکار منفی
                
                # استخراج شماره‌های مورد نیاز
                extracted_terminal_id = extract_terminal_id(fulldesc)
                extracted_tracking_number = extract_tracking_number(fulldesc)
                source_card_number = extract_source_card_number(fulldesc)
                
                # تبدیل تاریخ به میلادی
                gregorian_date = persian_to_gregorian(date)
                
                # آماده‌سازی داده‌های تراکنش
                transaction_data = {
                    'bank_id': bank_id,
                    'transaction_date': gregorian_date,
                    'transaction_time': time,
                    'amount': amount,
                    'description': fulldesc,
                    'reference_number': branchname,  # استفاده از نام شعبه به عنوان شماره مرجع
                    'extracted_terminal_id': extracted_terminal_id,
                    'extracted_tracking_number': extracted_tracking_number,
                    'source_card_number': source_card_number,
                    'transaction_type': transaction_type,
                    'is_reconciled': 0
                }
                
                # ذخیره در دیتابیس
                create_bank_transaction(transaction_data)
                report['processed'] += 1
                logger.debug(f"تراکنش ردیف {index + 1} با موفقیت پردازش شد: {transaction_type}")
                
            except Exception as e:
                error_msg = f"خطا در پردازش ردیف {index + 1}: {str(e)}"
                logger.error(error_msg)
                report['errors'].append(error_msg)
                
    except Exception as e:
        error_msg = f"خطا در خواندن فایل: {str(e)}"
        logger.error(error_msg)
        report['errors'].append(error_msg)
    
    logger.info(f"پردازش فایل بانک کشاورزی به پایان رسید. {report['processed']} از {report['total_rows']} ردیف پردازش شد.")
    return report

def determine_transaction_type(trantitle, depositorname, bed, bes):
    """
    تعیین نوع تراکنش بر اساس شرایط مشخص شده
    
    Args:
        trantitle: عنوان تراکنش
        depositorname: نام واریزکننده
        bed: مبلغ بدهکار
        bes: مبلغ بستانکار
        
    Returns:
        str: نوع تراکنش
    """
    # شرط ۱: تراکنش‌های POS از طریق شاپرک
    if depositorname == "مرکزشاپرک":
        return KESHAVARZI_TRANSACTION_TYPES['RECEIVED_POS']
    
    # شرط ۲: وصول چک
    if trantitle == "وصول چكاوك":
        return KESHAVARZI_TRANSACTION_TYPES['RECEIVED_CHECK']
    
    # شرط ۳: چک انتقالی
    if trantitle == "چك انتقالي":
        return KESHAVARZI_TRANSACTION_TYPES['PAID_CHECK']
    
    # شرط ۴: انتقال‌ها
    transfer_keywords = ["انتقالPAYMENT", "انتقالATM", "انتقالKYOS", "واريزتجمعي"]
    if any(keyword in trantitle for keyword in transfer_keywords):
        if bes > 0:  # واریز (دریافت)
            return KESHAVARZI_TRANSACTION_TYPES['RECEIVED_TRANSFER']
        elif bed > 0:  # برداشت (پرداخت)
            return KESHAVARZI_TRANSACTION_TYPES['PAID_TRANSFER']
    
    # حالت پیش‌فرض
    return KESHAVARZI_TRANSACTION_TYPES['UNKNOWN']

def extract_terminal_id(fulldesc):
    """
    استخراج شماره ترمینال از توضیحات تراکنش
    
    Args:
        fulldesc: توضیحات کامل تراکنش
        
    Returns:
        str: شماره ترمینال استخراج شده یا رشته خالی
    """
    # الگوی جستجو برای یافتن یک رشته هفت رقمی بعد از توالی صفرها
    pattern = r'0+([0-9]{7})'
    match = re.search(pattern, fulldesc)
    if match:
        return match.group(1)
    return ''

def extract_tracking_number(fulldesc):
    """
    استخراج شماره پیگیری از توضیحات تراکنش
    
    Args:
        fulldesc: توضیحات کامل تراکنش
        
    Returns:
        str: شماره پیگیری استخراج شده یا رشته خالی
    """
    # الگوی جستجو برای شماره پیگیری سوئیچ
    if "شماره پيگيري سوئيچ:" in fulldesc:
        pattern = r'شماره پيگيري سوئيچ:\s*(\d+)'
        match = re.search(pattern, fulldesc)
        if match:
            return match.group(1)
    
    # الگوی جستجو برای سریال
    if "سريال" in fulldesc:
        pattern = r'سريال\s*(\d+)'
        match = re.search(pattern, fulldesc)
        if match:
            return match.group(1)
    
    return ''

def extract_source_card_number(fulldesc):
    """
    استخراج شماره کارت مبدأ از توضیحات تراکنش
    
    Args:
        fulldesc: توضیحات کامل تراکنش
        
    Returns:
        str: شماره کارت مبدأ استخراج شده یا رشته خالی
    """
    # الگوی جستجو برای کارت بانک [نام بانک]
    pattern = r'کارت بانک [^\s]+\s+(\d+)'
    match = re.search(pattern, fulldesc)
    if match:
        return match.group(1)
    
    # اگر الگوی بالا پیدا نشد، اولین شماره کارت موجود را استخراج می‌کنیم
    # الگوی جستجو برای شماره کارت (۱۶ رقمی)
    pattern = r'(\d{16})'
    match = re.search(pattern, fulldesc)
    if match:
        return match.group(1)
    
    return ''