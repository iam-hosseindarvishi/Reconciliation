#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
دیالوگ مغایرت‌گیری دستی
"""

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, QLabel, QComboBox,
    QTableView, QHeaderView, QGroupBox, QDialogButtonBox, QMessageBox
)

from modules import reconciliation_logic
from modules.database_manager import DatabaseManager
from modules.logger import get_logger
from modules.utils import format_currency
from ui.widgets import DataTableModel

# ایجاد شیء لاگر
logger = get_logger(__name__)


class ManualReconciliationDialog(QDialog):
    """
    دیالوگ مغایرت‌گیری دستی
    """

    def __init__(self, bank_record, acc_records, pos_records, reconciliation_type, parent=None):
        """
        مقداردهی اولیه کلاس ManualReconciliationDialog
        """
        super().__init__(parent)
        self.bank_record = bank_record
        self.acc_records = acc_records
        self.pos_records = pos_records
        self.reconciliation_type = reconciliation_type
        self.selected_ids = {}
        
        self.setWindowTitle("مغایرت‌گیری دستی")
        self.setMinimumWidth(600)
        self.setMinimumHeight(400)
        
        self.init_ui()
        self.load_data()
    
    def init_ui(self):
        """
        راه‌اندازی رابط کاربری
        """
        layout = QVBoxLayout()
        
        # گروه اطلاعات رکورد انتخاب شده
        selected_group = QGroupBox("رکورد انتخاب شده")
        selected_layout = QFormLayout()
        
        self.record_info_label = QLabel()
        selected_layout.addRow("اطلاعات:", self.record_info_label)
        
        selected_group.setLayout(selected_layout)
        layout.addWidget(selected_group)
        
        # گروه انتخاب رکورد برای مغایرت‌گیری
        match_group = QGroupBox("انتخاب رکورد برای مغایرت‌گیری")
        match_layout = QVBoxLayout()
        
        # کومبوباکس نوع رکورد
        self.record_type_combo = QComboBox()
        if self.record_type == "bank":
            self.record_type_combo.addItems(["پوز", "حسابداری"])
        elif self.record_type == "pos":
            self.record_type_combo.addItems(["بانک", "حسابداری"])
        elif self.record_type == "accounting":
            self.record_type_combo.addItems(["بانک", "پوز"])
        
        self.record_type_combo.currentIndexChanged.connect(self.on_record_type_changed)
        match_layout.addWidget(QLabel("نوع رکورد:"))
        match_layout.addWidget(self.record_type_combo)
        
        # جدول رکوردها
        self.records_table = QTableView()
        self.records_table.setSelectionBehavior(QTableView.SelectRows)
        self.records_table.setSelectionMode(QTableView.SingleSelection)
        self.records_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        match_layout.addWidget(self.records_table)
        
        match_group.setLayout(match_layout)
        layout.addWidget(match_group)
        
        # دکمه‌ها
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)
        
        self.setLayout(layout)
    
    def load_data(self):
        """
        بارگذاری داده‌ها
        """
        try:
            # بارگذاری اطلاعات رکورد انتخاب شده
            amount = self.bank_record.get("Deposit_Amount") or self.bank_record.get("Withdrawal_Amount") or 0
            amount_str = format_currency(amount)
            self.record_info_label.setText(
                f"تاریخ: {self.bank_record.get('Date', '')}, مبلغ: {amount_str}, "
                f"نوع: {self.bank_record.get('Transaction_Type_Bank', '')}, "
                f"توضیحات: {self.bank_record.get('Description_Bank', '')[:50]}"
            )

            # بارگذاری رکوردهای قابل مغایرت‌گیری
            self.on_record_type_changed()
            
        except Exception as e:
            logger.error(f"خطا در بارگذاری داده‌های دیالوگ مغایرت‌گیری دستی: {str(e)}")
            QMessageBox.critical(self, "خطا", f"خطا در بارگذاری داده‌ها: {str(e)}")
    
    def on_record_type_changed(self, index=None):
        """
        تغییر نوع رکورد برای مغایرت‌گیری
        
        پارامترها:
            index: شاخص انتخاب شده (استفاده نمی‌شود)
        """
        try:
            selected_type = self.record_type_combo.currentText()
            
            if selected_type == "پوز":
                headers = ["تاریخ", "ساعت", "مبلغ", "شماره کارت", "شناسه ترمینال", "شماره پیگیری"]
                model = DataTableModel(self.pos_records, headers)
                self.records_table.setModel(model)
            
            elif selected_type == "حسابداری":
                headers = ["نوع", "شماره", "بدهکار", "بستانکار", "تاریخ سررسید", "توضیحات"]
                model = DataTableModel(self.acc_records, headers)
                self.records_table.setModel(model)
            
        except Exception as e:
            logger.error(f"خطا در تغییر نوع رکورد برای مغایرت‌گیری: {str(e)}")
            QMessageBox.critical(self, "خطا", f"خطا در بارگذاری داده‌ها: {str(e)}")
    
    def get_selected_ids(self):
        """
        شناسه‌های انتخاب شده را برمی‌گرداند.
        """
        return self.selected_ids

    def accept(self):
        """
        تایید مغایرت‌گیری دستی
        """
        try:
            # بررسی انتخاب رکورد
            selected_indexes = self.records_table.selectionModel().selectedRows()
            if not selected_indexes:
                QMessageBox.warning(self, "هشدار", "لطفاً یک رکورد را انتخاب کنید.")
                return

            selected_row = selected_indexes[0].row()
            selected_type = self.record_type_combo.currentText()

            if selected_type == "پوز":
                record_id = self.pos_records[selected_row]['id']
                self.selected_ids = {'pos_id': record_id}
            elif selected_type == "حسابداری":
                record_id = self.acc_records[selected_row]['id']
                self.selected_ids = {'acc_id': record_id}

            super().accept()
            
            # دریافت شناسه رکورد انتخاب شده
            if selected_type == "بانک":
                match_type = "bank"
                match_id = self.records_table.model()._data[selected_row].get("id")
            elif selected_type == "پوز":
                match_type = "pos"
                match_id = self.records_table.model()._data[selected_row].get("id")
            elif selected_type == "حسابداری":
                match_type = "accounting"
                match_id = self.records_table.model()._data[selected_row].get("id")
            
            # انجام مغایرت‌گیری دستی
            result = self.reconciliation_logic.manual_reconcile(
                self.record_type, self.record_id, match_type, match_id
            )
            
            if result:
                QMessageBox.information(self, "موفقیت", "مغایرت‌گیری دستی با موفقیت انجام شد.")
                super().accept()
            else:
                QMessageBox.critical(self, "خطا", "خطا در انجام مغایرت‌گیری دستی.")
            
        except Exception as e:
            logger.error(f"خطا در تایید مغایرت‌گیری دستی: {str(e)}")
            QMessageBox.critical(self, "خطا", f"خطا در انجام مغایرت‌گیری دستی: {str(e)}")