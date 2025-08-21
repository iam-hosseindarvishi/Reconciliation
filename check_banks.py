from database.banks_repository import get_all_banks

banks = get_all_banks()
print('تعداد بانک‌ها:', len(banks))
print('بانک‌ها:')
for bank in banks:
    print(f"ID: {bank['id']}, نام: {bank['bank_name']}")