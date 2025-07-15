#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
مدل داده برای نمایش در جدول
"""

from typing import Dict, List, Any
from PySide6.QtCore import Qt, QAbstractTableModel, QModelIndex
from modules.utils import format_currency


class DataTableModel(QAbstractTableModel):
    """
    مدل داده برای نمایش در جدول
    """
    
    def __init__(self, data: List[Dict[str, Any]], headers: List[str], db_keys_order: List[str], parent=None):
        """
        مقداردهی اولیه کلاس DataTableModel
        
        پارامترها:
            data: لیست دیکشنری‌های داده
            headers: لیست عناوین ستون‌ها
            db_keys_order: ترتیب کلیدهای دیتابیس
            parent: ویجت والد
        """
        super().__init__(parent)
        self._data = data
        self._headers = headers
        self._db_keys = db_keys_order
    
    def rowCount(self, parent=QModelIndex()):
        """
        تعداد سطرهای جدول
        """
        return len(self._data)
    
    def columnCount(self, parent=QModelIndex()):
        """
        تعداد ستون‌های جدول
        """
        return len(self._headers)
    
    def data(self, index, role=Qt.DisplayRole):
        """
        داده‌های جدول
        """
        if not index.isValid() or not (0 <= index.row() < len(self._data)):
            return None
        
        row = index.row()
        col = index.column()
        
        if role == Qt.DisplayRole:
            # نمایش داده
            if col < len(self._db_keys):
                key = self._db_keys[col]
                value = self._data[row].get(key, "")
                
                # فرمت‌بندی مقادیر خاص (مالی)
                if key in ["Deposit_Amount", "Withdrawal_Amount", "Debit", "Credit", "Transaction_Amount"]:
                    if value is not None and value != 0:
                        return format_currency(value)
                
                # تبدیل مقادیر بولی
                if isinstance(value, bool):
                    return "بله" if value else "خیر"
                
                return str(value)
        
        elif role == Qt.TextAlignmentRole:
            # تراز متن
            if col < len(self._db_keys):
                key = self._db_keys[col]
                if key in ["Deposit_Amount", "Withdrawal_Amount", "Debit", "Credit", "Transaction_Amount"]:
                    return Qt.AlignLeft | Qt.AlignVCenter
            
            return Qt.AlignCenter
        
        return None
    
    def headerData(self, section, orientation, role=Qt.DisplayRole):
        """
        داده‌های سرستون
        """
        if role == Qt.DisplayRole and orientation == Qt.Horizontal and section < len(self._headers):
            return self._headers[section]
        
        return None
    
    def update_data(self, data: List[Dict[str, Any]], db_keys_order: List[str]):
        """
        به‌روزرسانی داده‌های جدول
        
        پارامترها:
            data: لیست دیکشنری‌های داده جدید
            db_keys_order: ترتیب کلیدهای دیتابیس
        """
        self.beginResetModel()
        self._data = data
        self._db_keys = db_keys_order
        self.endResetModel()