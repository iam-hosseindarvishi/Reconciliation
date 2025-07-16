#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
ماژول تب‌های رابط کاربری
این ماژول شامل کلاس‌های تب‌های مختلف برنامه است.
"""

from .data_import_tab import DataImportTab
from .reconciliation_tab import ReconciliationTab
from .report_tab import ReportTab
from .bank_management_tab import BankManagementTab

__all__ = ['DataImportTab', 'ReconciliationTab', 'ReportTab', 'BankManagementTab']