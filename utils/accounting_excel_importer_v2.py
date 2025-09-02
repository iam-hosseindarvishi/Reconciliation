import pandas as pd
from database.accounting_repository import create_accounting_transaction
from utils.helpers import persian_to_gregorian, normalize_shamsi_date
from utils.logger_config import setup_logger
import re

# راه‌اندازی لاگر


logger = setup_logger('utils.accounting_excel_importer_v2')

def import_accounting_excel_v2(accounting_file_path, bank_id):
    """
    پردازش فایل اکسل حسابداری با ساختار جدید
    """
    report = {
        'transactions_saved': 0,
        'errors': []
    }
    try:
        # خواندن فایل اکسل
        df = pd.read_excel(accounting_file_path)
        logger.info(f"فایل اکسل با {len(df)} سطر خوانده شد")
    except Exception as e:
        report['errors'].append(f"خطا در خواندن فایل: {e}")
        logger.error(f"خطا در خواندن فایل: {e}")
        return report
    
    # پردازش هر سطر از فایل اکسل
    for idx, row in df.iterrows():
        try:
            # تعیین نوع تراکنش بر اساس ستون "نوع"
            type_name=str(row.get('نوع', '')).strip()
            transaction_type = determine_transaction_type(type_name)
            if not transaction_type:
                logger.warning(f"نوع تراکنش نامعتبر در سطر {idx+1}: {row.get('نوع', '')}")
                continue  # نوع تراکنش نامعتبر، رد شود
            
            # استخراج مبلغ از ستون بدهکار یا بستانکار
            amount = 0
            if pd.notna(row.get('بدهکار')) and float(row.get('بدهکار', 0)) > 0:
                amount = float(row.get('بدهکار', 0))
            elif pd.notna(row.get('بستانکار')) and float(row.get('بستانکار', 0)) > 0:
                amount = float(row.get('بستانکار', 0))
            
            # استخراج شماره کارت از ستون شرح
            # card_number = extract_card_number(str(row.get('شرح', '')))
            
            # تبدیل تاریخ شمسی به میلادی
            date_str = str(row.get('تاریخ', ''))
            gregorian_date = persian_to_gregorian(date_str)
            
            # ایجاد دیکشنری داده‌های تراکنش
            transaction_data = {
                'bank_id': bank_id,
                'transaction_number': str(row.get('شماره', '')),
                'transaction_amount': amount,
                'due_date': gregorian_date,  # استفاده از تاریخ به عنوان due_date
                'collection_date': gregorian_date,  # استفاده از همان تاریخ برای collection_date
                'transaction_type': transaction_type,
                'customer_name': str(row.get('کد/نام طرف حساب', '')),
                'is_new_system':1,
                'description': str(row.get('شرح', '')),
                'is_reconciled': 0
            }
            
            # ذخیره تراکنش در پایگاه داده
            create_accounting_transaction(transaction_data)
            report['transactions_saved'] += 1
            
        except Exception as e:
            error_msg = f"خطا در پردازش سطر {idx+1}: {e}"
            report['errors'].append(error_msg)
            logger.error(error_msg)
    
    return report

def determine_transaction_type(type_str):
    """
    تعیین نوع تراکنش بر اساس ستون "نوع"
    """
    # type_str = type_str
    
    # نگاشت انواع تراکنش‌ها
    transaction_type_map = {
        'پوز /حواله/فيش و دريافتني تجاري': 'Pos / Received Transfer',
        # 'حواله دريافتني تجاري': 'Received Transfer',
        # 'فيش دريافتني تجاري': 'Received Transfer',
        # 'دريافتني تجاري': 'Received Transfer',
        'پوز /حواله/فيش و پرداختني تجاري': 'Pos / Paid Transfer',
        # 'حواله پرداختني تجاري': 'Paid Transfer',
        # 'فيش پرداختني تجاري': 'Paid Transfer',
        # 'پرداختني تجاري': 'Paid Transfer',
        'اسناد دریافتنی/تجاری': 'Received Check',
        'اسناد پرداختی تجاری': 'Paid Check'
    }
    
    # بررسی نوع تراکنش
    for key, value in transaction_type_map.items():
        if key in type_str:
            return value
    
    logger.warning(f"نوع تراکنش ناشناخته: {type_str}")
    return None

def extract_card_number(description):
    """
    استخراج شماره کارت از ستون شرح
    مثال: دفتر مرکزی - ک 6040
    در اینجا 6040 باید به عنوان شماره کارت استخراج شود
    """
    if not description:
        return ''
    
    # الگوی جستجو برای یافتن شماره کارت (حرف ک و سپس یک عدد)
    pattern = r'ک\s*(\d+)'
    match = re.search(pattern, description)
    
    if match:
        return match.group(1).strip()
    
    return ''