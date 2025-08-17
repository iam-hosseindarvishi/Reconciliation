import os
import pandas as pd
from database.terminals_repository import create_terminal, get_terminal_by_number
from database.pos_transactions_repository import create_pos_transaction
from datetime import datetime
from utils.logger_config import setup_logger
from utils.helpers import persian_to_gregorian
# راه‌اندازی لاگر
logger = setup_logger('utils.pos_excel_importer')



def process_pos_files(pos_folder_path, bank_id):
    """پردازش فایل‌های پوز با مدیریت خطا و لاگینگ"""
    # اضافه کردن لاگ برای دیباگ
    logger.info(f"شروع پردازش پوز با مسیر: {pos_folder_path} و شناسه بانک: {bank_id}")
    logger.info(f"نوع مسیر: {type(pos_folder_path)}, مقدار: {pos_folder_path}")
    
    report = {
        'files_processed': 0,
        'transactions_saved': 0,
        'terminals_created': 0,
        'errors': []
    }

    # بررسی وجود پوشه
    logger.info(f"بررسی وجود پوشه: {pos_folder_path}")
    if not os.path.isdir(pos_folder_path):
        error_msg = f"پوشه یافت نشد: {pos_folder_path}"
        logger.error(error_msg)
        report['errors'].append(error_msg)
        return report
    logger.info(f"پوشه یافت شد: {pos_folder_path}")

    # یافتن فایل‌های اکسل
    try:
        # لیست تمام فایل‌های موجود در پوشه
        all_files = os.listdir(pos_folder_path)
        logger.info(f"تعداد کل فایل‌ها در پوشه: {len(all_files)}")
        logger.info(f"لیست فایل‌ها: {all_files}")
        
        # فیلتر کردن فقط فایل‌های اکسل
        files = [f for f in all_files if f.lower().endswith(('.xlsx', '.xls'))]
        logger.info(f"تعداد {len(files)} فایل اکسل در پوشه {pos_folder_path} یافت شد")
        logger.info(f"لیست فایل‌های اکسل: {files}")
    except Exception as e:
        error_msg = f"خطا در خواندن محتوای پوشه {pos_folder_path}: {str(e)}"
        logger.error(error_msg)
        report['errors'].append(error_msg)
        return report

    # پردازش هر فایل
    for file in files:
        file_path = os.path.join(pos_folder_path, file)
        logger.info(f"شروع پردازش فایل: {file} با مسیر کامل: {file_path}")
        
        try:
            # خواندن فایل اکسل
            logger.info(f"در حال خواندن فایل اکسل: {file_path}")
            df = pd.read_excel(file_path)
            logger.info(f"فایل اکسل با موفقیت خوانده شد. تعداد سطرها: {len(df)}")
            
            # نمایش ستون‌های فایل برای دیباگ
            logger.info(f"ستون‌های فایل: {list(df.columns)}")
            
            report['files_processed'] += 1
            
            # فیلتر تراکنش‌های خرید
            if 'نوع تراکنش' not in df.columns:
                logger.error(f"ستون 'نوع تراکنش' در فایل {file} یافت نشد")
                continue
                
            df = df[df['نوع تراکنش'] == 'خريد']
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
                        amount = float(row['مبلغ تراکنش'])
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
                    logger.info(f"در حال ثبت تراکنش با داده‌های: {transaction_data}")
                    try:
                        transaction_id = create_pos_transaction(transaction_data)
                        report['transactions_saved'] += 1
                        logger.info(f"تراکنش جدید با شناسه {transaction_id} ثبت شد: ترمینال {terminal_number}, مبلغ {amount}")
                    except Exception as e:
                        logger.error(f"خطا در ثبت تراکنش: {str(e)}")
                        report['errors'].append(f"خطا در ثبت تراکنش: {str(e)}")
                        continue

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
