#banks
MELLAT_BANK_ID = 1
KESHAVARZI_BANK_ID = 2

MELLAT_BANK_NAME = 'بانک ملت'
KESHAVARZI_BANK_NAME = 'بانک کشاورزی'

MELLAT_BANK = {
    'id': MELLAT_BANK_ID,
    'name': MELLAT_BANK_NAME
}

KESHAVARZI_BANK = {
    'id': KESHAVARZI_BANK_ID,
    'name': KESHAVARZI_BANK_NAME
}

BANKS = {
    MELLAT_BANK_ID: MELLAT_BANK_NAME,
    KESHAVARZI_BANK_ID: KESHAVARZI_BANK_NAME
}

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
    'RECEIVED_POS': 'Received_Pos',
    'BANK_FEES': 'Bank_Fees',
    'PAID_TRANSFER': 'Paid_Transfer',
    'RECEIVED_TRANSFER': 'Received_Transfer',
    'UNKNOWN': 'Unknown'
}

# ثابت‌های نوع تراکنش برای بانک کشاورزی
KESHAVARZI_TRANSACTION_TYPES = {
    'RECEIVED_POS': 'Received_Pos',
    'RECEIVED_CHECK': 'Received_Check',
    'PAID_CHECK': 'Paid_Check',
    'PAID_TRANSFER': 'Paid_Transfer',
    'RECEIVED_TRANSFER': 'Received_Transfer',
    'BANK_FEES': 'Bank_Fees',
    'UNKNOWN': 'Unknown'
}

# وضعیت‌های مغایرت‌گیری
RECONCILIATION_STATUS = {
    'NOT_CHECKED': 0,  # هنوز بررسی نشده
    'MATCHED': 1,      # تطبیق داده شده
    'UNMATCHED': 2    # عدم تطبیق
}
