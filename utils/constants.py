"""ثابت‌های سیستم مغایرت‌گیری - یکپارچه‌سازی شده برای تمام ماژول‌ها"""

# =============================================================================
# ثابت‌های بانک‌ها
# =============================================================================
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

# =============================================================================
# سیستم یکپارچه انواع تراکنش - برای تمام بانک‌ها و سیستم‌ها
# =============================================================================

class TransactionTypes:
    """کلاس یکپارچه برای انواع تراکنش‌ها"""
    # انواع اصلی تراکنش‌ها
    RECEIVED_POS = 'Received_Pos'
    RECEIVED_CHECK = 'Received_Check' 
    PAID_CHECK = 'Paid_Check'
    PAID_TRANSFER = 'Paid_Transfer'
    RECEIVED_TRANSFER = 'Received_Transfer'
    BANK_FEES = 'Bank_Fees'
    POS = 'Pos'  # برای سیستم حسابداری
    SHAPARAK = 'Shaparak'  # برای تراکنش‌های شاپرک
    UNKNOWN = 'Unknown'
    
    # لیست تمام انواع تراکنش‌ها
    ALL_TYPES = [
        RECEIVED_POS,
        RECEIVED_CHECK,
        PAID_CHECK, 
        PAID_TRANSFER,
        RECEIVED_TRANSFER,
        BANK_FEES,
        POS,
        SHAPARAK,
        UNKNOWN
    ]
    
    # نقشه تبدیل نام‌های فارسی به انگلیسی
    PERSIAN_TO_ENGLISH = {
        'چک دريافتني': RECEIVED_CHECK,
        'حواله/فيش دريافتني': RECEIVED_TRANSFER,
        'پوز دريافتني': POS,
        'چک پرداختني': PAID_CHECK,
        'حواله/فيش پرداختني': PAID_TRANSFER,
        'کارمزد': BANK_FEES,
        'دریافتی': RECEIVED_TRANSFER,
        'پرداختی': PAID_TRANSFER,
        'پوز': POS,
        'چک': RECEIVED_CHECK
    }
    
    # نقشه تبدیل انگلیسی به فارسی
    ENGLISH_TO_PERSIAN = {v: k for k, v in PERSIAN_TO_ENGLISH.items()}

# انواع تراکنش‌های مجاز برای هر بانک (برای سازگاری با کد قدیمی)
MELLAT_TRANSACTION_TYPES = {
    'RECEIVED_POS': TransactionTypes.RECEIVED_POS,
    'BANK_FEES': TransactionTypes.BANK_FEES,
    'PAID_TRANSFER': TransactionTypes.PAID_TRANSFER,
    'RECEIVED_TRANSFER': TransactionTypes.RECEIVED_TRANSFER,
    'SHAPARAK': TransactionTypes.SHAPARAK,
    'UNKNOWN': TransactionTypes.UNKNOWN
}

KESHAVARZI_TRANSACTION_TYPES = {
    'RECEIVED_POS': TransactionTypes.RECEIVED_POS,
    'RECEIVED_CHECK': TransactionTypes.RECEIVED_CHECK,
    'PAID_CHECK': TransactionTypes.PAID_CHECK,
    'PAID_TRANSFER': TransactionTypes.PAID_TRANSFER,
    'RECEIVED_TRANSFER': TransactionTypes.RECEIVED_TRANSFER,
    'BANK_FEES': TransactionTypes.BANK_FEES,
    'UNKNOWN': TransactionTypes.UNKNOWN
}

# نقشه تبدیل برای سیستم حسابداری (برای سازگاری با کد قدیمی)
TRANSACTION_TYPE_MAP = TransactionTypes.PERSIAN_TO_ENGLISH

# =============================================================================
# وضعیت‌های مغایرت‌گیری
# =============================================================================
class ReconciliationStatus:
    """وضعیت‌های مغایرت‌گیری"""
    NOT_CHECKED = 0  # هنوز بررسی نشده
    MATCHED = 1      # تطبیق داده شده  
    UNMATCHED = 2    # عدم تطبیق
    
    # برای سازگاری با کد قدیمی
    STATUS_MAP = {
        'NOT_CHECKED': NOT_CHECKED,
        'MATCHED': MATCHED,
        'UNMATCHED': UNMATCHED
    }

# برای سازگاری با کد قدیمی
RECONCILIATION_STATUS = ReconciliationStatus.STATUS_MAP

# =============================================================================
# توابع کمکی برای کار با انواع تراکنش
# =============================================================================

def get_transaction_type_display_name(transaction_type):
    """دریافت نام نمایشی فارسی برای نوع تراکنش"""
    return TransactionTypes.ENGLISH_TO_PERSIAN.get(transaction_type, transaction_type)

def convert_persian_to_english_transaction_type(persian_type):
    """تبدیل نوع تراکنش فارسی به انگلیسی"""
    return TransactionTypes.PERSIAN_TO_ENGLISH.get(persian_type, TransactionTypes.UNKNOWN)

def is_valid_transaction_type(transaction_type):
    """بررسی معتبر بودن نوع تراکنش"""
    return transaction_type in TransactionTypes.ALL_TYPES

def get_bank_supported_transaction_types(bank_id):
    """دریافت انواع تراکنش‌های پشتیبانی شده توسط بانک"""
    if bank_id == MELLAT_BANK_ID:
        return list(MELLAT_TRANSACTION_TYPES.values())
    elif bank_id == KESHAVARZI_BANK_ID:
        return list(KESHAVARZI_TRANSACTION_TYPES.values())
    else:
        return TransactionTypes.ALL_TYPES
