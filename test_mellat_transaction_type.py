import pandas as pd
from utils.mellat_bank_processor import determine_transaction_type
from utils.constants import MELLAT_TRANSACTION_TYPES

def test_determine_transaction_type():
    # تست برای حواله همراه بانک با مبلغ بستانکار
    row1 = {
        'واریز کننده/ ذیتفع': 'ابراهیم - محمودی بنذرکی',
        'شعبه': 'اداره حسابداری متمرکز',
        'شرح': 'حواله همراه بانک بابت ۴۹۱۲۳۶۴۷۱۴',
        'مبلغ گردش بستانکار': 243040000,
        'مبلغ گردش بدهکار': 0
    }
    
    # تست برای واریز انتقالی با مبلغ بستانکار
    row2 = {
        'واریز کننده/ ذیتفع': 'محمد رضایی',
        'شعبه': 'شعبه مرکزی',
        'شرح': 'واریز انتقالی بابت خرید',
        'مبلغ گردش بستانکار': 5000000,
        'مبلغ گردش بدهکار': 0
    }
    
    # تست برای انتقال پرداختی با مبلغ بدهکار
    row3 = {
        'واریز کننده/ ذیتفع': 'علی احمدی',
        'شعبه': 'اداره حسابداری متمرکز',
        'شرح': 'انتقال وجه',
        'مبلغ گردش بستانکار': 0,
        'مبلغ گردش بدهکار': 1000000
    }
    
    # تست برای تراکنش POS
    row4 = {
        'واریز کننده/ ذیتفع': 'شاپرک-پوز',
        'شعبه': 'شاپرک',
        'شرح': 'تراکنش پوز',
        'مبلغ گردش بستانکار': 2500000,
        'مبلغ گردش بدهکار': 0
    }
    
    # اجرای تست‌ها
    result1 = determine_transaction_type(row1)
    result2 = determine_transaction_type(row2)
    result3 = determine_transaction_type(row3)
    result4 = determine_transaction_type(row4)
    
    # چاپ نتایج
    print(f"تست ۱ (حواله همراه بانک): {result1}")
    print(f"تست ۲ (واریز انتقالی): {result2}")
    print(f"تست ۳ (انتقال پرداختی): {result3}")
    print(f"تست ۴ (تراکنش POS): {result4}")
    
    # بررسی نتایج
    assert result1 == MELLAT_TRANSACTION_TYPES['RECEIVED_TRANSFER'], "تست ۱ ناموفق بود"
    assert result2 == MELLAT_TRANSACTION_TYPES['RECEIVED_TRANSFER'], "تست ۲ ناموفق بود"
    assert result3 == MELLAT_TRANSACTION_TYPES['PAID_TRANSFER'], "تست ۳ ناموفق بود"
    assert result4 == MELLAT_TRANSACTION_TYPES['RECEIVED_POS'], "تست ۴ ناموفق بود"
    
    print("همه تست‌ها با موفقیت انجام شدند.")

if __name__ == "__main__":
    test_determine_transaction_type()