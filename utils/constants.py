# ثابت‌های نوع تراکنش برای سیستم حسابداری
TRANSACTION_TYPE_MAP = {
    'چک دريافتني': 'Received Check',
    'حواله/فيش دريافتني': 'Received Transfer',
    'پوز دريافتني': 'Pos',
    'چک پرداختني': 'Paid Check',
    'حواله/فيش پرداختني': 'Paid Transfer',
}

# ثابت‌های نوع تراکنش برای بانک ملت
MELLAT_TRANSACTION_TYPES = {
    'RECEIVED_POS': 'Recived_Pos',
    'BANK_FEES': 'Bank_Fees',
    'PAID_TRANSFER': 'Paid_Transfer',
    'RECEIVED_TRANSFER': 'Received_Transfer',
    'POS': 'Pos',
    'UNKNOWN': 'Unknown'
}

# وضعیت‌های مغایرت‌گیری
RECONCILIATION_STATUS = {
    'NOT_CHECKED': 0,  # هنوز بررسی نشده
    'MATCHED': 1,      # تطبیق داده شده
    'UNMATCHED': 2    # عدم تطبیق
}

# ثابت‌های نوع تراکنش برای بانک ملت
MELLAT_TRANSACTION_TYPES = {
    'RECEIVED_POS': 'Recived_Pos',
    'BANK_FEES': 'Bank_Fees',
    'PAID_TRANSFER': 'Paid_Transfer',
    'RECEIVED_TRANSFER': 'Received_Transfer',
    'POS': 'Pos',
    'UNKNOWN': 'Unknown'
}
