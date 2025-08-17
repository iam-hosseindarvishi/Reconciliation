import pandas as pd
import os

# ایجاد مسیر فایل
file_path = os.path.join(os.path.dirname(__file__), 'sample_keshavarzi_data.xlsx')

# ایجاد داده‌های نمونه
data = [
    # نمونه تراکنش POS (مرکز شاپرک)
    {
        'date': '1402/01/15',
        'time': '10:30:45',
        'trantitle': 'تراکنش POS',
        'bed': 0,
        'bes': 1500000,
        'fulldesc': '040210031100000000388202617740ACH1مرکزشاپرک',
        'depositorname': 'مرکزشاپرک',
        'branchname': 'شعبه مرکزی'
    },
    # نمونه وصول چک
    {
        'date': '1402/01/16',
        'time': '11:20:30',
        'trantitle': 'وصول چكاوك',
        'bed': 0,
        'bes': 2500000,
        'fulldesc': 'وصول چك شماره 123456 - شماره پيگيري سوئيچ: 711697',
        'depositorname': 'علی محمدی',
        'branchname': 'شعبه ونک'
    },
    # نمونه چک انتقالی
    {
        'date': '1402/01/17',
        'time': '09:15:20',
        'trantitle': 'چك انتقالي',
        'bed': 1800000,
        'bes': 0,
        'fulldesc': 'چك انتقالي شماره 654321 - سريال 954992',
        'depositorname': 'حسین رضایی',
        'branchname': 'شعبه صادقیه'
    },
    # نمونه انتقال دریافتی
    {
        'date': '1402/01/18',
        'time': '14:45:10',
        'trantitle': 'انتقالPAYMENT',
        'bed': 0,
        'bes': 3000000,
        'fulldesc': 'انتقال وجه از کارت بانک ملی 6037991234567890',
        'depositorname': 'زهرا کریمی',
        'branchname': 'شعبه تجریش'
    },
    # نمونه انتقال پرداختی
    {
        'date': '1402/01/19',
        'time': '16:30:25',
        'trantitle': 'انتقالATM',
        'bed': 2000000,
        'bes': 0,
        'fulldesc': 'انتقال وجه به کارت بانک صادرات 6037691234567890',
        'depositorname': 'مهدی احمدی',
        'branchname': 'شعبه پاسداران'
    },
    # نمونه واریز تجمعی
    {
        'date': '1402/01/20',
        'time': '08:50:15',
        'trantitle': 'واريزتجمعي',
        'bed': 0,
        'bes': 5000000,
        'fulldesc': 'واریز تجمعی از حساب 0102030405 - کارت 6037761234567890',
        'depositorname': 'شرکت الف',
        'branchname': 'شعبه فرشته'
    },
    # نمونه انتقال از کیوسک
    {
        'date': '1402/01/21',
        'time': '12:10:35',
        'trantitle': 'انتقالKYOS',
        'bed': 0,
        'bes': 1200000,
        'fulldesc': 'انتقال از کیوسک - کارت 6037661234567890 - شماره پیگیری 123456',
        'depositorname': 'فاطمه نوری',
        'branchname': 'شعبه نیاوران'
    }
]

# ایجاد DataFrame
df = pd.DataFrame(data)

# ذخیره به فایل اکسل
df.to_excel(file_path, index=False)

print(f"فایل نمونه در مسیر {file_path} ایجاد شد.")