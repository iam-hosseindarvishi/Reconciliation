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
    
    def __init__(self, data: List[Dict[str, Any]], headers: List[str], parent=None):
        """
        مقداردهی اولیه کلاس DataTableModel
        
        پارامترها:
            data: لیست دیکشنری‌های داده
            headers: لیست عناوین ستون‌ها
            parent: ویجت والد
        """
        super().__init__(parent)
        self._data = data
        self._headers = headers
        self._keys = []
        
        # استخراج کلیدهای دیکشنری برای دسترسی به داده‌ها
        if data and len(data) > 0:
            self._keys = list(data[0].keys())
    
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
            if col < len(self._keys):
                key = self._keys[col]
                value = self._data[row].get(key, "")
                
                # فرمت‌بندی مقادیر خاص
                if key in ["Deposit_Amount", "Withdrawal_Amount", "Debit", "Credit", "Transaction_Amount"]:
                    if value and value != 0:
                        return format_currency(value)
                
                return str(value)
        
        elif role == Qt.TextAlignmentRole:
            # تراز متن
            if col < len(self._keys):
                key = self._keys[col]
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
    
    def update_data(self, data: List[Dict[str, Any]]):
        """
        به‌روزرسانی داده‌های جدول
        
        پارامترها:
            data: لیست دیکشنری‌های داده جدید
        """
        self.beginResetModel()
        self._data = data
        if data and len(data) > 0:
            self._keys = list(data[0].keys())
        else:
            self._keys = []
        self.endResetModel()