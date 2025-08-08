import os
import pandas as pd
from database.terminals_repository import create_terminal, get_terminal_by_number
from database.pos_transactions_repository import create_pos_transaction
from datetime import datetime
import jdatetime
from utils.logger_config import setup_logger

# راه‌اندازی لاگر
logger = setup_logger('utils.pos_excel_importer')

def persian_to_gregorian(jalali_date_str):
    """
    تبدیل تاریخ شمسی به میلادی با فرمت YYYY-MM-DD
    پشتیبانی از فرمت‌های: yyyy/mm/dd, yyyy-mm-dd, یا yyyy.mm.dd
    در صورت خطا رشته خالی برمی‌گرداند
    """
    if not jalali_date_str:
        logger.warning("تاریخ شمسی خالی دریافت شد")
        return ''
    
    for sep in ['/', '-', '.']:
        if sep in jalali_date_str:
            parts = jalali_date_str.split(sep)
            if len(parts) == 3:
                try:
                    y, m, d = map(int, parts)
                    gdate = jdatetime.date(y, m, d).togregorian()
                    result = gdate.strftime('%Y-%m-%d')
                    logger.debug(f"تبدیل تاریخ شمسی {jalali_date_str} به میلادی {result}")
                    return result
                except ValueError as e:
                    logger.error(f"خطا در تبدیل تاریخ {jalali_date_str}: {str(e)}")
                    return ''
                except Exception as e:
                    logger.error(f"خطای غیرمنتظره در تبدیل تاریخ {jalali_date_str}: {str(e)}")
                    return ''
    
    logger.warning(f"فرمت تاریخ نامعتبر: {jalali_date_str}")
    return ''

def process_pos_files(pos_folder_path, bank_id):
    """پردازش فایل‌های پوز با مدیریت خطا و لاگینگ"""
    report = {
        'files_processed': 0,
        'transactions_saved': 0,
        'terminals_created': 0,
        'errors': []
    }

    # بررسی وجود پوشه
    if not os.path.isdir(pos_folder_path):
        error_msg = f"پوشه یافت نشد: {pos_folder_path}"
        logger.error(error_msg)
        report['errors'].append(error_msg)
        return report

    # یافتن فایل‌های اکسل
    try:
        files = [f for f in os.listdir(pos_folder_path) if f.lower().endswith(('.xlsx', '.xls'))]
        logger.info(f"تعداد {len(files)} فایل اکسل در پوشه {pos_folder_path} یافت شد")
    except Exception as e:
        error_msg = f"خطا در خواندن محتوای پوشه {pos_folder_path}: {str(e)}"
        logger.error(error_msg)
        report['errors'].append(error_msg)
        return report

    # پردازش هر فایل
    for file in files:
        file_path = os.path.join(pos_folder_path, file)
        logger.info(f"شروع پردازش فایل: {file}")
        
        try:
            # خواندن فایل اکسل
            df = pd.read_excel(file_path)
            report['files_processed'] += 1
            
            # فیلتر تراکنش‌های خرید
            df = df[df['نوع تراکنش'] == 'خرید']
            logger.info(f"تعداد {len(df)} تراکنش خرید در فایل {file} یافت شد")

            # پردازش هر ردیف
            for index, row in df.iterrows():
                try:
                    # استخراج اطلاعات ترمینال
                    terminal_number = str(row['شناسه شعبه مشتری']).strip()
                    terminal_name = str(row['نام شعبه مشتری']).strip()
                    
                    # بررسی و ثبت ترمینال جدید
                    if not get_terminal_by_number(terminal_number):
                        create_terminal(terminal_number, terminal_name)
                        report['terminals_created'] += 1
                        logger.info(f"ترمینال جدید ثبت شد: {terminal_number} - {terminal_name}")
                    
                    # تبدیل تاریخ
                    transaction_date = persian_to_gregorian(str(row['تاریخ تراکنش']))
                    if not transaction_date:
                        logger.warning(f"تاریخ نامعتبر در ردیف {index + 1} فایل {file}")
                        continue

                    # آماده‌سازی داده‌های تراکنش
                    try:
                        amount = float(row['مبلغ'])
                    except (ValueError, TypeError) as e:
                        logger.error(f"خطا در تبدیل مبلغ در ردیف {index + 1}: {str(e)}")
                        continue

                    transaction_data = {
                        'terminal_number': terminal_number,
                        'bank_id': bank_id,
                        'card_number': str(row.get('شماره کارت', '')),
                        'transaction_date': transaction_date,
                        'transaction_amount': amount,
                        'tracking_number': str(row.get('شماره پیگیری', '')),
                        'is_reconciled': 0
                    }

                    # ثبت تراکنش
                    create_pos_transaction(transaction_data)
                    report['transactions_saved'] += 1
                    logger.debug(f"تراکنش جدید ثبت شد: ترمینال {terminal_number}, مبلغ {amount}")

                except Exception as e:
                    error_msg = f"خطا در پردازش ردیف {index + 1} فایل {file}: {str(e)}"
                    logger.error(error_msg)
                    report['errors'].append(error_msg)

        except Exception as e:
            error_msg = f"خطا در پردازش فایل {file}: {str(e)}"
            logger.error(error_msg)
            report['errors'].append(error_msg)
            continue

    # گزارش نهایی
    logger.info(f"پردازش فایل‌های پوز به پایان رسید. "
                f"تعداد فایل‌های پردازش شده: {report['files_processed']}, "
                f"تعداد تراکنش‌های ذخیره شده: {report['transactions_saved']}, "
                f"تعداد ترمینال‌های جدید: {report['terminals_created']}, "
                f"تعداد خطاها: {len(report['errors'])}")

    return report
