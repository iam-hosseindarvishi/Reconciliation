"""
Accounting Repository Package
پکیج repository تراکنش‌های حسابداری - جدا شده از accounting_repository.py
"""

# Import all functions from modular components
from .transaction_crud import (
    create_accounting_transaction,
    get_transactions_by_bank,
    delete_transaction,
    update_accounting_transaction_reconciliation_status,
    get_transaction_by_id,
    get_transaction_count_by_bank
)

from .transaction_search import (
    get_transactions_by_type,
    get_transactions_by_date_and_type,
    get_transactions_advanced_search,
    get_transactions_by_date_less_than_amount_type,
    get_transactions_by_date_amount_type,
    get_transactions_by_date_type,
    get_transactions_by_amount_tracking,
    get_transactions_by_due_date_and_bank,
    get_transactions_by_collection_date_and_bank,
    get_accounting_transactions_for_pos,
    search_transactions_by_customer_name,
    search_transactions_by_description
)

from .transaction_type_mapper import TransactionTypeMapper

# برای سازگاری عقبی، تمام توابع را در سطح پکیج قابل دسترسی می‌کنیم
__all__ = [
    # Transaction CRUD
    'create_accounting_transaction',
    'get_transactions_by_bank', 
    'delete_transaction',
    'update_accounting_transaction_reconciliation_status',
    'get_transaction_by_id',
    'get_transaction_count_by_bank',
    
    # Transaction Search
    'get_transactions_by_type',
    'get_transactions_by_date_and_type',
    'get_transactions_advanced_search',
    'get_transactions_by_date_less_than_amount_type',
    'get_transactions_by_date_amount_type', 
    'get_transactions_by_date_type',
    'get_transactions_by_amount_tracking',
    'get_transactions_by_due_date_and_bank',
    'get_transactions_by_collection_date_and_bank',
    'get_accounting_transactions_for_pos',
    'search_transactions_by_customer_name',
    'search_transactions_by_description',
    
    # Transaction Type Mapper
    'TransactionTypeMapper'
]
