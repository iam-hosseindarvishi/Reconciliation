import pandas as pd
import re
from utils.constants import KESHAVARZI_TRANSACTION_TYPES
from utils.helpers import persian_to_gregorian
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
                trandesc = str(row.get('trandesc', ''))
                bed = float(row.get('bed', 0) or 0)
                bes = float(row.get('bes', 0) or 0)
                fulldesc = str(row.get('fulldesc', ''))
                depositorname = str(row.get('depositorname', ''))
                branchname = str(row.get('branchname', ''))
                
                # تعیین نوع تراکنش
                transaction_type = determine_transaction_type(trantitle, trandesc, depositorname, bed, bes, fulldesc,branchname)
                
                # بروزرسانی آمار
                report['transaction_types'][transaction_type] = report['transaction_types'].get(transaction_type, 0) + 1
                
                # محاسبه مبلغ (بدهکار یا بستانکار)
                amount = bes if bes != 0 else -bed  # مقادیر بستانکار مثبت و بدهکار منفی
                
                # استخراج شماره‌های مورد نیاز
                if(transaction_type==KESHAVARZI_TRANSACTION_TYPES['RECEIVED_POS']):
                    extracted_terminal_id = extract_terminal_id(fulldesc)
                else:
                    extracted_terminal_id = None
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

def determine_transaction_type(trantitle, trandesc, depositorname, bed, bes, fulldesc, branchname):
    """
    تعیین نوع تراکنش بر اساس قوانین مشخص شده برای فایل بانک کشاورزی.
    
    Args:
        trantitle (str): عنوان اصلی تراکنش.
        trandesc (str): شرح کوتاه تراکنش.
        depositorname (str): نام واریزکننده.
        bed (float): مبلغ بدهکار.
        bes (float): مبلغ بستانکار.
        fulldesc (str): توضیحات کامل تراکنش.
        branchname (str): نام شعبه.
        
    Returns:
        str: نوع تراکنش.
    """
    
    # اولویت اول: شناسایی کارمزدها (Bank_Fees)
    # این بخش باید اولین بررسی باشد تا کارمزدها به عنوان انتقال اشتباه گرفته نشوند
    if "كارمزد" in trantitle or "کارمزد" in trantitle:
        return KESHAVARZI_TRANSACTION_TYPES['BANK_FEES']
    
    if trantitle == "برداشت انتقالي" and "کارمزد ثبت چک" in trandesc:
        return KESHAVARZI_TRANSACTION_TYPES['BANK_FEES']
    
    # کارمزدهای مربوط به پایا/ساتنا با مبلغ کم
    if (trantitle == "پايا" or trantitle == "ساتنا") and branchname == "مبادلات الکترونيک-(ساتناوپايا":
        # مبلغ بدهکار کمتر از 1000000 ریال به عنوان کارمزد در نظر گرفته می‌شود
        if bed > 0 and bed < 1000000:
            return KESHAVARZI_TRANSACTION_TYPES['BANK_FEES']
    
    # اولویت دوم: تراکنش‌های POS
    if depositorname == "مرکزشاپرک":
        return KESHAVARZI_TRANSACTION_TYPES['RECEIVED_POS']
    
    # اولویت سوم: تراکنش‌های چک
    if trantitle == "وصول چكاوك":
        return KESHAVARZI_TRANSACTION_TYPES['RECEIVED_CHECK']
    
    if trantitle == "چك انتقالي":
        return KESHAVARZI_TRANSACTION_TYPES['PAID_CHECK']
    
    # اولویت چهارم: تراکنش‌های انتقال (Transfers)
    # حواله‌ها از طریق مبادلات الکترونیک (پایا/ساتنا)
    if branchname == "مبادلات الکترونيک-(ساتناوپايا" or branchname=="اينترنت بانك":
        if bes > 0:
            return KESHAVARZI_TRANSACTION_TYPES['RECEIVED_TRANSFER']
        elif bed > 0:
            return KESHAVARZI_TRANSACTION_TYPES['PAID_TRANSFER']
   
    # سایر حواله‌ها
    if "واریز" in trantitle or "انتقال" in trantitle:
        if bes > 0:
            return KESHAVARZI_TRANSACTION_TYPES['RECEIVED_TRANSFER']
        elif bed > 0:
            return KESHAVARZI_TRANSACTION_TYPES['PAID_TRANSFER']
     # واریزهای 
    if('عمليات متمركز' in branchname and 'واريزتجمعي' in trantitle):
        return KESHAVARZI_TRANSACTION_TYPES['RECEIVED_TRANSFER']
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

    match = re.search(r'0{3,}([0-9]{7})', fulldesc)
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
        match = re.search(r'شماره پیگیری سوئیچ:\s*(\d+)', fulldesc, re.IGNORECASE)
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
    # Extract card number between pipes after "کارت بانک" followed by any bank name
    pattern = r'\|کارت بانک [^:]+:\s*(\d{16})\|'
    match = re.search(pattern, fulldesc)
    if match:
        card_number = match.group(1)
        # Return last 4 digits
        return card_number[-4:]
    
    return ''