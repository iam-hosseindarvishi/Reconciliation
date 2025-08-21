from database.bank_transaction_repository import get_unreconciled_transactions_by_bank as get_unreconciled_bank_records

# آزمایش برای بانک با شناسه 1
bank_id = 1
records = get_unreconciled_bank_records(bank_id)

print(f"تعداد رکوردهای مغایرت‌گیری نشده برای بانک {bank_id}: {len(records)}")

# نمایش چند رکورد اول
for i, record in enumerate(records[:5]):
    print(f"رکورد {i+1}:")
    print(f"  شناسه: {record['id']}")
    print(f"  تاریخ: {record['transaction_date']}")
    print(f"  مبلغ: {record['amount']}")
    print(f"  توضیحات: {record.get('description', '')}")
    print()

# آزمایش برای بانک با شناسه 2
bank_id = 2
records = get_unreconciled_bank_records(bank_id)

print(f"تعداد رکوردهای مغایرت‌گیری نشده برای بانک {bank_id}: {len(records)}")

# نمایش چند رکورد اول
for i, record in enumerate(records[:5]):
    print(f"رکورد {i+1}:")
    print(f"  شناسه: {record['id']}")
    print(f"  تاریخ: {record['transaction_date']}")
    print(f"  مبلغ: {record['amount']}")
    print(f"  توضیحات: {record.get('description', '')}")
    print()