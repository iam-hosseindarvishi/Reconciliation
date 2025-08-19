import pandas as pd
from utils.constants import MELLAT_TRANSACTION_TYPES
from utils.pos_excel_importer import persian_to_gregorian
from database.bank_transaction_repository import create_bank_transaction
from utils.logger_config import setup_logger

# راه‌اندازی لاگر
logger = setup_logger('utils.mellat_bank_processor')

def process_mellat_bank_file(mellat_file_path, bank_id):
    """پردازش فایل اکسل بانک ملت با مدیریت خطا و لاگینگ"""
    """
    پردازش فایل اکسل بانک ملت و ذخیره تراکنش‌ها در دیتابیس
    """
    report = {
        'total_rows': 0,
        'processed': 0,
        'errors': [],
        'transaction_types': {}
    }
    
    try:
        # خواندن فایل اکسل
        df = pd.read_excel(mellat_file_path)
        report['total_rows'] = len(df)
        
        for index, row in df.iterrows():
            try:
                # تعیین نوع تراکنش بر اساس شرایط
                transaction_type = determine_transaction_type(row)
                
                # بروزرسانی آمار
                report['transaction_types'][transaction_type] = report['transaction_types'].get(transaction_type, 0) + 1
                
                # محاسبه مبلغ (بدهکار یا بستانکار)
                debit = float(row['مبلغ گردش بدهکار'] or 0)
                credit = float(row['مبلغ گردش بستانکار'] or 0)
                amount = credit if float(row['مبلغ گردش بستانکار'] or 0) != 0 else debit

                
                # تبدیل تاریخ به میلادی
                gregorian_date = persian_to_gregorian(str(row['تاریخ']))
                
                # آماده‌سازی داده‌های تراکنش
                transaction_data = {
                    'bank_id': bank_id,
                    'transaction_date': gregorian_date,
                    'transaction_time': str(row['زمان']),
                    'amount': amount,
                    'description': str(row['شرح']),
                    'reference_number': str(row['کد حسابگری']),
                    'extracted_terminal_id': '',  # خالی برای بانک ملت
                    'extracted_tracking_number': str(row['شماره سریال']),
                    'transaction_type': transaction_type,
                    'is_reconciled': 0
                }
                
                # ذخیره در دیتابیس
                create_bank_transaction(transaction_data)
                report['processed'] += 1
                
            except Exception as e:
                error_msg = f"خطا در پردازش ردیف {index + 1}: {str(e)}"
                report['errors'].append(error_msg)
                
    except Exception as e:
        error_msg = f"خطا در خواندن فایل: {str(e)}"
        report['errors'].append(error_msg)
    
    return report

def determine_transaction_type(row):
    """
    تعیین نوع تراکنش بر اساس شرایط پیچیده
    """
    beneficiary = str(row['واریز کننده/ ذیتفع'])
    branch = str(row['شعبه'])
    description = str(row['شرح'])
    has_credit = float(row['مبلغ گردش بستانکار'] or 0) != 0
    has_debit = float(row['مبلغ گردش بدهکار'] or 0) != 0
    
    # پیش شرط برای مشخص شدن پایا
    if(branch == 'خیابان شیخ آباد' and (('از اینترنت' and 'پایا' in description) and ('کارمزد' not in description or 'کارمزد پایا' not in beneficiary)) and has_debit):
        return MELLAT_TRANSACTION_TYPES['PAID_TRANSFER']
    # شرط ۱: تراکنش‌های POS از طریق شاپرک
    if ((('شاپرک-پوز' in beneficiary and 
        branch == 'شاپرک') or 'حواله شاپرک' in description ) and 
        has_credit):
        return MELLAT_TRANSACTION_TYPES['RECEIVED_POS']

    # شرط حواله ها و واریز انتقالی
    if(('حواله' in description or 'حواله همراه بانک' in description) and has_credit):
        return MELLAT_TRANSACTION_TYPES['RECEIVED_TRANSFER']
    if('واریز انتقالی' in description and has_credit):
        return MELLAT_TRANSACTION_TYPES['RECEIVED_TRANSFER']
    # شرط ۲: کارمزدهای بانکی
    if ('کارمزد' in description and 
        branch == 'اداره کل مدیریت عملیات'):
        return MELLAT_TRANSACTION_TYPES['BANK_FEES']
    if('کارمزد پایا' in beneficiary and has_debit):
        return MELLAT_TRANSACTION_TYPES['BANK_FEES']

    # شرط ۳: انتقال‌های دریافتی (پایا یا لحظه‌ای)
    if ((branch in ['اداره امور پایا', 'اداره امور پرداخت لحظه ای'] or  'پایا' in description  ) and has_credit):
        return MELLAT_TRANSACTION_TYPES['RECEIVED_TRANSFER']
    
    # شرط ۴: انتقال‌های دریافتی (حسابداری متمرکز)
    if (branch == 'اداره حسابداری متمرکز' and has_credit):
        return MELLAT_TRANSACTION_TYPES['RECEIVED_TRANSFER']
    
    # شرط ۵: انتقال‌های پرداختی
    if ((branch == 'اداره حسابداری متمرکز' or description in ['پایا','از اینترنت']) and has_debit):
        return MELLAT_TRANSACTION_TYPES['PAID_TRANSFER']
    

    # شرط ۶: تراکنش‌های POS از طریق پایا
    if (branch == 'اداره امور پایا' and 'پوز' in beneficiary):
        return MELLAT_TRANSACTION_TYPES['RECEIVED_POS']
    
    # حالت پیش‌فرض
    return MELLAT_TRANSACTION_TYPES['UNKNOWN']
