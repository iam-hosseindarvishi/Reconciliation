#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
پکیج ماژول‌های مغایرت‌گیری
این پکیج شامل تمام ماژول‌های مورد نیاز برای سیستم مغایرت‌گیری است.
"""

# وارد کردن کلاس‌های اصلی
from .reconciliation import ReconciliationEngine
from .pos_deposit_reconciliation import PosDepositReconciliation
from .received_transfer_reconciliation import ReceivedTransferReconciliation
from .paid_transfer_reconciliation import PaidTransferReconciliation
from .received_check_reconciliation import ReceivedCheckReconciliation
from .paid_check_reconciliation import PaidCheckReconciliation
from .database_manager import DatabaseManager
from .logger import get_logger

__all__ = [
    'ReconciliationEngine',
    'PosDepositReconciliation',
    'ReceivedTransferReconciliation',
    'PaidTransferReconciliation',
    'ReceivedCheckReconciliation',
    'PaidCheckReconciliation',
    'DatabaseManager',
    'get_logger'
]

__version__ = '1.0.0'
__author__ = 'Reconciliation System'
__description__ = 'سیستم مغایرت‌گیری مدولار'