import pandas as pd
from database.repositories.accounting import create_accounting_transaction
from utils.helpers import persian_to_gregorian,normalize_shamsi_date
from utils.constants import TRANSACTION_TYPE_MAP

def import_accounting_excel(accounting_file_path, bank_id):
    report = {
        'transactions_saved': 0,
        'errors': []
    }
    try:
        df = pd.read_excel(accounting_file_path)
    except Exception as e:
        report['errors'].append(f"Error reading file: {e}")
        return report
    for idx, row in df.iterrows():
        try:
            transaction_type = TRANSACTION_TYPE_MAP.get(str(row.get('نوع')).strip(), None)
            if not transaction_type:
                continue  # نوع تراکنش نامعتبر، رد شود
            # استفاده از نام ستون‌های صحیح (ی عربی)
            collection_date_raw = str(row.get('تاريخ وصول', '')).strip()  # حذف فاصله‌های اضافی
            due_date_raw = row.get('تاريخ سررسيد', '')  # ي عربی
            
            # تبدیل collection_date از فرمت "04/02/10" به "1404/02/10"
            if collection_date_raw and len(collection_date_raw.split('/')) == 3:
                parts = collection_date_raw.split('/')
                if len(parts[0]) == 2:  # اگر سال دو رقمی باشد
                    collection_date_raw = f"14{parts[0]}/{parts[1]}/{parts[2]}"
            
            transaction_data = {
                'bank_id': bank_id,
                'transaction_number': str(row.get('شماره', '')),
                'transaction_amount': float(row.get('مبلغ', 0)),
                'due_date': persian_to_gregorian(normalize_shamsi_date(str(due_date_raw))),
                'collection_date': persian_to_gregorian(collection_date_raw),
                'transaction_type': transaction_type,
                'customer_name': str(row.get('نام مشتري', '')),
                "description": str(row.get('توضیحات', '')),
                'is_reconciled': 0
            }
            create_accounting_transaction(transaction_data)
            report['transactions_saved'] += 1
        except Exception as e:
            report['errors'].append(f"Row {idx+1}: {e}")
    return report
