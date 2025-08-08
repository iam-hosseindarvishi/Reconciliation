import os
import pandas as pd
from database.terminals_repository import create_terminal, get_terminal_by_number
from database.pos_transactions_repository import create_pos_transaction
from datetime import datetime

# تابع تبدیل تاریخ شمسی به میلادی با استفاده از jdatetime
import jdatetime
def persian_to_gregorian(jalali_date_str):
    """
    Converts a Jalali (Persian) date string to Gregorian date string in format YYYY-MM-DD.
    Supports input formats: yyyy/mm/dd, yyyy-mm-dd, or yyyy.mm.dd
    Returns empty string if conversion fails.
    """
    if not jalali_date_str:
        return ''
    for sep in ['/', '-', '.']:
        if sep in jalali_date_str:
            parts = jalali_date_str.split(sep)
            if len(parts) == 3:
                try:
                    y, m, d = map(int, parts)
                    gdate = jdatetime.date(y, m, d).togregorian()
                    return gdate.strftime('%Y-%m-%d')
                except Exception:
                    return ''
    return ''

def import_pos_folder(pos_folder_path, bank_id):
    report = {
        'files_processed': 0,
        'transactions_saved': 0,
        'errors': []
    }
    if not os.path.isdir(pos_folder_path):
        report['errors'].append(f"Folder not found: {pos_folder_path}")
        return report
    files = [f for f in os.listdir(pos_folder_path) if f.lower().endswith(('.xlsx', '.xls'))]
    for file in files:
        file_path = os.path.join(pos_folder_path, file)
        try:
            df = pd.read_excel(file_path)
            report['files_processed'] += 1
            # فقط تراکنش‌های نوع خرید
            df = df[df['نوع تراکنش'] == 'خرید']
            for _, row in df.iterrows():
                terminal_number = str(row['شناسه شعبه مشتری']).strip()
                terminal_name = str(row['نام شعبه مشتری']).strip()
                # ثبت ترمینال در صورت جدید بودن
                if not get_terminal_by_number(terminal_number):
                    create_terminal(terminal_number, terminal_name)
                # تبدیل تاریخ
                transaction_date = persian_to_gregorian(str(row['تاریخ تراکنش']))
                transaction_data = {
                    'terminal_number': terminal_number,
                    'bank_id': bank_id,
                    'card_number': str(row.get('شماره کارت', '')),
                    'transaction_date': transaction_date,
                    'transaction_amount': float(row['مبلغ']),
                    'tracking_number': str(row.get('شماره پیگیری', '')),
                    'is_reconciled': 0
                }
                create_pos_transaction(transaction_data)
                report['transactions_saved'] += 1
        except Exception as e:
            report['errors'].append(f"Error in {file}: {e}")
    return report
