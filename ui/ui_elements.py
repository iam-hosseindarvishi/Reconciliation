#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
ماژول المان‌های رابط کاربری
این ماژول شامل کلاس‌ها و توابع مربوط به رابط کاربری برنامه است.
"""

import os
import sys
import time
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple, Callable

from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QTabWidget,
    QPushButton, QLabel, QLineEdit, QFileDialog, QTextEdit,
    QTableView, QHeaderView, QMessageBox, QProgressBar, QComboBox,
    QGroupBox, QFormLayout, QSplitter, QCheckBox, QDialog, QDialogButtonBox
)
from PySide6.QtCore import Qt, QAbstractTableModel, QModelIndex, Signal, Slot, QThread, QTimer
from PySide6.QtGui import QColor, QFont, QIcon, QTextCursor

from modules.data_loader import DataLoader
from modules.database_manager import DatabaseManager
from modules.reconciliation_logic import ReconciliationEngine
from modules.report_generator import ReportGenerator
from modules.logger import get_logger
from modules.utils import convert_gregorian_to_jalali_str, format_currency

# ایجاد شیء لاگر
logger = get_logger(__name__)

# تنظیمات مسیرها
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG_DIR = os.path.join(BASE_DIR, 'config')
REPORTS_DIR = os.path.join(BASE_DIR, 'reports')


class LogTextEdit(QTextEdit):
    """
    کلاس سفارشی برای نمایش لاگ‌ها با رنگ‌های مختلف
    """
    
    def __init__(self, parent=None):
        """
        مقداردهی اولیه کلاس LogTextEdit
        
        پارامترها:
            parent: ویجت والد
        """
        super().__init__(parent)
        self.setReadOnly(True)
        self.setFont(QFont("Consolas", 10))
    
    def append_log(self, text: str, color: str = "black"):
        """
        افزودن متن لاگ با رنگ مشخص
        
        پارامترها:
            text: متن لاگ
            color: رنگ متن (نام رنگ یا کد هگزادسیمال)
        """
        self.moveCursor(QTextCursor.End)
        current_time = datetime.now().strftime("%H:%M:%S")
        formatted_text = f"[{current_time}] {text}"
        self.append(f"<span style='color: {color};'>{formatted_text}</span>")
        self.moveCursor(QTextCursor.End)
        # اسکرول به پایین
        self.verticalScrollBar().setValue(self.verticalScrollBar().maximum())


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


class ImportWorker(QThread):
    """
    کلاس کارگر برای واردسازی داده‌ها در پس‌زمینه
    """
    
    # سیگنال‌های مختلف برای اطلاع‌رسانی پیشرفت و نتیجه
    progress_updated = Signal(int, str)
    import_completed = Signal(bool, str)
    log_message = Signal(str, str)
    
    def __init__(self, data_loader: DataLoader, db_manager: DatabaseManager, 
                 bank_file: str, pos_folder: str, accounting_file: str):
        """
        مقداردهی اولیه کلاس ImportWorker
        
        پارامترها:
            data_loader: نمونه‌ای از کلاس DataLoader
            db_manager: نمونه‌ای از کلاس DatabaseManager
            bank_file: مسیر فایل بانک
            pos_folder: مسیر پوشه فایل‌های پوز
            accounting_file: مسیر فایل حسابداری
        """
        super().__init__()
        self.data_loader = data_loader
        self.db_manager = db_manager
        self.bank_file = bank_file
        self.pos_folder = pos_folder
        self.accounting_file = accounting_file
    
    def run(self):
        """
        اجرای عملیات واردسازی داده‌ها
        """
        try:
            # واردسازی داده‌های بانک
            if self.bank_file:
                self.progress_updated.emit(10, "در حال بارگذاری داده‌های بانک...")
                self.log_message.emit(f"بارگذاری داده‌های بانک از فایل {os.path.basename(self.bank_file)}", "blue")
                
                bank_data = self.data_loader.load_bank_data(self.bank_file)
                if bank_data:
                    self.progress_updated.emit(30, "در حال ذخیره داده‌های بانک در پایگاه داده...")
                    self.db_manager.insert_bank_transactions(bank_data)
                    self.log_message.emit(f"{len(bank_data)} رکورد بانکی با موفقیت بارگذاری شد.", "green")
                else:
                    self.log_message.emit("خطا در بارگذاری داده‌های بانک.", "red")
            
            # واردسازی داده‌های پوز
            if self.pos_folder:
                self.progress_updated.emit(40, "در حال بارگذاری داده‌های پوز...")
                self.log_message.emit(f"بارگذاری داده‌های پوز از پوشه {os.path.basename(self.pos_folder)}", "blue")
                
                pos_data = self.data_loader.load_pos_data(self.pos_folder)
                if pos_data:
                    self.progress_updated.emit(60, "در حال ذخیره داده‌های پوز در پایگاه داده...")
                    self.db_manager.insert_pos_transactions(pos_data)
                    self.log_message.emit(f"{len(pos_data)} رکورد پوز با موفقیت بارگذاری شد.", "green")
                else:
                    self.log_message.emit("خطا در بارگذاری داده‌های پوز.", "red")
            
            # واردسازی داده‌های حسابداری
            if self.accounting_file:
                self.progress_updated.emit(70, "در حال بارگذاری داده‌های حسابداری...")
                self.log_message.emit(f"بارگذاری داده‌های حسابداری از فایل {os.path.basename(self.accounting_file)}", "blue")
                
                accounting_data = self.data_loader.load_accounting_data(self.accounting_file)
                if accounting_data:
                    self.progress_updated.emit(90, "در حال ذخیره داده‌های حسابداری در پایگاه داده...")
                    self.db_manager.insert_accounting_entries(accounting_data)
                    self.log_message.emit(f"{len(accounting_data)} رکورد حسابداری با موفقیت بارگذاری شد.", "green")
                else:
                    self.log_message.emit("خطا در بارگذاری داده‌های حسابداری.", "red")
            
            self.progress_updated.emit(100, "واردسازی داده‌ها با موفقیت انجام شد.")
            self.import_completed.emit(True, "واردسازی داده‌ها با موفقیت انجام شد.")
            
        except Exception as e:
            logger.error(f"خطا در واردسازی داده‌ها: {str(e)}")
            self.log_message.emit(f"خطا در واردسازی داده‌ها: {str(e)}", "red")
            self.import_completed.emit(False, f"خطا در واردسازی داده‌ها: {str(e)}")


class ReconciliationWorker(QThread):
    """
    کلاس کارگر برای انجام مغایرت‌گیری در پس‌زمینه
    """
    
    # سیگنال‌های مختلف برای اطلاع‌رسانی پیشرفت و نتیجه
    progress_updated = Signal(int, str)
    reconciliation_completed = Signal(bool, str)
    log_message = Signal(str, str)
    
    def __init__(self, reconciliation_engine: ReconciliationEngine):
        """
        مقداردهی اولیه کلاس ReconciliationWorker
        
        پارامترها:
            reconciliation_engine: نمونه‌ای از کلاس ReconciliationEngine
        """
        super().__init__()
        self.reconciliation_engine = reconciliation_engine
    
    def run(self):
        """
        اجرای عملیات مغایرت‌گیری
        """
        try:
            # مغایرت‌گیری شاپرک (پوز)
            self.progress_updated.emit(10, "در حال مغایرت‌گیری تراکنش‌های شاپرک (پوز)...")
            self.log_message.emit("شروع مغایرت‌گیری تراکنش‌های شاپرک (پوز)...", "blue")
            
            shaparak_results = self.reconciliation_engine.reconcile_shaparak_pos()
            self.log_message.emit(
                f"مغایرت‌گیری شاپرک (پوز): {shaparak_results['matched']} مورد تطبیق، "
                f"{shaparak_results['unmatched']} مورد عدم تطبیق.",
                "green" if shaparak_results['matched'] > 0 else "orange"
            )
            
            # مغایرت‌گیری چک‌ها
            self.progress_updated.emit(30, "در حال مغایرت‌گیری چک‌ها...")
            self.log_message.emit("شروع مغایرت‌گیری چک‌ها...", "blue")
            
            checks_results = self.reconciliation_engine.reconcile_checks()
            self.log_message.emit(
                f"مغایرت‌گیری چک‌ها: {checks_results['matched']} مورد تطبیق، "
                f"{checks_results['unmatched']} مورد عدم تطبیق.",
                "green" if checks_results['matched'] > 0 else "orange"
            )
            
            # مغایرت‌گیری انتقال‌ها
            self.progress_updated.emit(50, "در حال مغایرت‌گیری انتقال‌ها...")
            self.log_message.emit("شروع مغایرت‌گیری انتقال‌ها...", "blue")
            
            transfers_results = self.reconciliation_engine.reconcile_transfers()
            self.log_message.emit(
                f"مغایرت‌گیری انتقال‌ها: {transfers_results['matched']} مورد تطبیق، "
                f"{transfers_results['unmatched']} مورد عدم تطبیق.",
                "green" if transfers_results['matched'] > 0 else "orange"
            )
            
            # مغایرت‌گیری پوز با حسابداری
            self.progress_updated.emit(70, "در حال مغایرت‌گیری پوز با حسابداری...")
            self.log_message.emit("شروع مغایرت‌گیری پوز با حسابداری...", "blue")
            
            pos_acc_results = self.reconciliation_engine.reconcile_pos_accounting()
            self.log_message.emit(
                f"مغایرت‌گیری پوز با حسابداری: {pos_acc_results['matched']} مورد تطبیق، "
                f"{pos_acc_results['unmatched']} مورد عدم تطبیق.",
                "green" if pos_acc_results['matched'] > 0 else "orange"
            )
            
            # پیشنهاد بر اساس پسوند کارت
            self.progress_updated.emit(90, "در حال یافتن پیشنهادات بر اساس پسوند کارت...")
            self.log_message.emit("شروع یافتن پیشنهادات بر اساس پسوند کارت...", "blue")
            
            card_suffix_hints = self.reconciliation_engine.find_card_suffix_hints()
            self.log_message.emit(
                f"{len(card_suffix_hints['results'])} پیشنهاد بر اساس پسوند کارت یافت شد.",
                "green" if len(card_suffix_hints['results']) > 0 else "orange"
            )
            
            # نمایش نتایج کلی
            total_matched = (
                shaparak_results['matched'] + 
                checks_results['matched'] + 
                transfers_results['matched'] + 
                pos_acc_results['matched']
            )
            
            self.progress_updated.emit(100, "مغایرت‌گیری با موفقیت انجام شد.")
            self.log_message.emit(f"مغایرت‌گیری با موفقیت انجام شد. مجموعاً {total_matched} مورد تطبیق یافت شد.", "green")
            self.reconciliation_completed.emit(True, "مغایرت‌گیری با موفقیت انجام شد.")
            
        except Exception as e:
            logger.error(f"خطا در مغایرت‌گیری: {str(e)}")
            self.log_message.emit(f"خطا در مغایرت‌گیری: {str(e)}", "red")
            self.reconciliation_completed.emit(False, f"خطا در مغایرت‌گیری: {str(e)}")


class ManualReconciliationDialog(QDialog):
    """
    دیالوگ مغایرت‌گیری دستی
    """
    
    def __init__(self, reconciliation_engine: ReconciliationEngine, record_type: str, record_id: int, parent=None):
        """
        مقداردهی اولیه کلاس ManualReconciliationDialog
        
        پارامترها:
            reconciliation_engine: نمونه‌ای از کلاس ReconciliationEngine
            record_type: نوع رکورد (bank, pos, accounting)
            record_id: شناسه رکورد
            parent: ویجت والد
        """
        super().__init__(parent)
        self.reconciliation_engine = reconciliation_engine
        self.record_type = record_type
        self.record_id = record_id
        
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
            if self.record_type == "bank":
                record = self.reconciliation_engine.db_manager.get_bank_transaction_by_id(self.record_id)
                if record:
                    amount = record.get("Deposit_Amount") or record.get("Withdrawal_Amount") or 0
                    amount_str = format_currency(amount)
                    self.record_info_label.setText(
                        f"تاریخ: {record.get('Date', '')}, مبلغ: {amount_str}, "
                        f"نوع: {record.get('Transaction_Type_Bank', '')}, "
                        f"توضیحات: {record.get('Description_Bank', '')[:50]}"
                    )
            
            elif self.record_type == "pos":
                record = self.reconciliation_engine.db_manager.get_pos_transaction_by_id(self.record_id)
                if record:
                    amount_str = format_currency(record.get("Transaction_Amount", 0))
                    self.record_info_label.setText(
                        f"تاریخ: {record.get('Transaction_Date', '')}, مبلغ: {amount_str}, "
                        f"ترمینال: {record.get('Terminal_ID', '')}, "
                        f"کارت: {record.get('Card_Number', '')[-4:] if record.get('Card_Number') else ''}"
                    )
            
            elif self.record_type == "accounting":
                record = self.reconciliation_engine.db_manager.get_accounting_entry_by_id(self.record_id)
                if record:
                    amount = record.get("Debit") or record.get("Credit") or 0
                    amount_str = format_currency(amount)
                    self.record_info_label.setText(
                        f"نوع: {record.get('Entry_Type_Acc', '')}, مبلغ: {amount_str}, "
                        f"شماره: {record.get('Account_Reference_Suffix', '')}, "
                        f"تاریخ: {record.get('Due_Date', '')}"
                    )
            
            # بارگذاری رکوردهای قابل مغایرت‌گیری
            self.on_record_type_changed()
            
        except Exception as e:
            logger.error(f"خطا در بارگذاری داده‌های دیالوگ مغایرت‌گیری دستی: {str(e)}")
            QMessageBox.critical(self, "خطا", f"خطا در بارگذاری داده‌ها: {str(e)}")
    
    def on_record_type_changed(self):
        """
        تغییر نوع رکورد برای مغایرت‌گیری
        """
        try:
            selected_type = self.record_type_combo.currentText()
            
            if selected_type == "بانک":
                # بارگذاری رکوردهای بانکی
                records = self.reconciliation_engine.db_manager.get_unreconciled_bank_transactions()
                headers = ["تاریخ", "مبلغ واریز", "مبلغ برداشت", "توضیحات", "نوع تراکنش", "شناسه پیگیری"]
                
                # تنظیم مدل داده
                model = DataTableModel(records, headers)
                self.records_table.setModel(model)
            
            elif selected_type == "پوز":
                # بارگذاری رکوردهای پوز
                records = self.reconciliation_engine.db_manager.get_unreconciled_pos_transactions()
                headers = ["تاریخ", "ساعت", "مبلغ", "شماره کارت", "شناسه ترمینال", "شماره پیگیری"]
                
                # تنظیم مدل داده
                model = DataTableModel(records, headers)
                self.records_table.setModel(model)
            
            elif selected_type == "حسابداری":
                # بارگذاری رکوردهای حسابداری
                records = self.reconciliation_engine.db_manager.get_unreconciled_accounting_entries()
                headers = ["نوع", "شماره", "بدهکار", "بستانکار", "تاریخ سررسید", "توضیحات"]
                
                # تنظیم مدل داده
                model = DataTableModel(records, headers)
                self.records_table.setModel(model)
            
        except Exception as e:
            logger.error(f"خطا در تغییر نوع رکورد برای مغایرت‌گیری: {str(e)}")
            QMessageBox.critical(self, "خطا", f"خطا در بارگذاری داده‌ها: {str(e)}")
    
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
            result = self.reconciliation_engine.manual_reconcile(
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


class DataImportTab(QWidget):
    """
    تب واردسازی داده‌ها
    """
    
    # سیگنال‌های مختلف برای اطلاع‌رسانی
    import_completed = Signal(bool)
    
    def __init__(self, data_loader: DataLoader, db_manager: DatabaseManager):
        """
        مقداردهی اولیه کلاس DataImportTab
        
        پارامترها:
            data_loader: نمونه‌ای از کلاس DataLoader
            db_manager: نمونه‌ای از کلاس DatabaseManager
        """
        super().__init__()
        self.data_loader = data_loader
        self.db_manager = db_manager
        
        self.bank_file = ""
        self.pos_folder = ""
        self.accounting_file = ""
        
        self.init_ui()
    
    def init_ui(self):
        """
        راه‌اندازی رابط کاربری
        """
        layout = QVBoxLayout()
        
        # گروه انتخاب فایل‌ها
        file_group = QGroupBox("انتخاب فایل‌ها")
        file_layout = QFormLayout()
        
        # انتخاب فایل بانک
        self.bank_file_edit = QLineEdit()
        self.bank_file_edit.setReadOnly(True)
        self.bank_file_btn = QPushButton("انتخاب فایل بانک")
        self.bank_file_btn.clicked.connect(self.select_bank_file)
        
        bank_layout = QHBoxLayout()
        bank_layout.addWidget(self.bank_file_edit)
        bank_layout.addWidget(self.bank_file_btn)
        file_layout.addRow("فایل بانک (.xls):", bank_layout)
        
        # انتخاب پوشه پوز
        self.pos_folder_edit = QLineEdit()
        self.pos_folder_edit.setReadOnly(True)
        self.pos_folder_btn = QPushButton("انتخاب پوشه پوز")
        self.pos_folder_btn.clicked.connect(self.select_pos_folder)
        
        pos_layout = QHBoxLayout()
        pos_layout.addWidget(self.pos_folder_edit)
        pos_layout.addWidget(self.pos_folder_btn)
        file_layout.addRow("پوشه پوز (.xlsx):", pos_layout)
        
        # انتخاب فایل حسابداری
        self.accounting_file_edit = QLineEdit()
        self.accounting_file_edit.setReadOnly(True)
        self.accounting_file_btn = QPushButton("انتخاب فایل حسابداری")
        self.accounting_file_btn.clicked.connect(self.select_accounting_file)
        
        accounting_layout = QHBoxLayout()
        accounting_layout.addWidget(self.accounting_file_edit)
        accounting_layout.addWidget(self.accounting_file_btn)
        file_layout.addRow("فایل حسابداری (.xls):", accounting_layout)
        
        file_group.setLayout(file_layout)
        layout.addWidget(file_group)
        
        # دکمه واردسازی داده‌ها
        self.import_btn = QPushButton("واردسازی داده‌ها")
        self.import_btn.clicked.connect(self.import_data)
        self.import_btn.setMinimumHeight(40)
        layout.addWidget(self.import_btn)
        
        # نوار پیشرفت
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        layout.addWidget(self.progress_bar)
        
        # برچسب وضعیت
        self.status_label = QLabel("آماده برای واردسازی داده‌ها...")
        layout.addWidget(self.status_label)
        
        # ناحیه لاگ
        log_group = QGroupBox("گزارش فعالیت‌ها")
        log_layout = QVBoxLayout()
        
        self.log_text = LogTextEdit()
        log_layout.addWidget(self.log_text)
        
        log_group.setLayout(log_layout)
        layout.addWidget(log_group)
        
        self.setLayout(layout)
    
    def select_bank_file(self):
        """
        انتخاب فایل بانک
        """
        file_path, _ = QFileDialog.getOpenFileName(
            self, "انتخاب فایل بانک", "", "Excel Files (*.xls)"
        )
        
        if file_path:
            self.bank_file = file_path
            self.bank_file_edit.setText(file_path)
            self.log_text.append_log(f"فایل بانک انتخاب شد: {os.path.basename(file_path)}", "blue")
    
    def select_pos_folder(self):
        """
        انتخاب پوشه پوز
        """
        folder_path = QFileDialog.getExistingDirectory(
            self, "انتخاب پوشه پوز", ""
        )
        
        if folder_path:
            self.pos_folder = folder_path
            self.pos_folder_edit.setText(folder_path)
            self.log_text.append_log(f"پوشه پوز انتخاب شد: {os.path.basename(folder_path)}", "blue")
    
    def select_accounting_file(self):
        """
        انتخاب فایل حسابداری
        """
        file_path, _ = QFileDialog.getOpenFileName(
            self, "انتخاب فایل حسابداری", "", "Excel Files (*.xls)"
        )
        
        if file_path:
            self.accounting_file = file_path
            self.accounting_file_edit.setText(file_path)
            self.log_text.append_log(f"فایل حسابداری انتخاب شد: {os.path.basename(file_path)}", "blue")
    
    def import_data(self):
        """
        واردسازی داده‌ها
        """
        # بررسی انتخاب حداقل یک فایل
        if not self.bank_file and not self.pos_folder and not self.accounting_file:
            QMessageBox.warning(self, "هشدار", "لطفاً حداقل یک فایل را انتخاب کنید.")
            return
        
        # غیرفعال کردن دکمه‌ها
        self.import_btn.setEnabled(False)
        self.bank_file_btn.setEnabled(False)
        self.pos_folder_btn.setEnabled(False)
        self.accounting_file_btn.setEnabled(False)
        
        # تنظیم نوار پیشرفت
        self.progress_bar.setValue(0)
        self.status_label.setText("در حال واردسازی داده‌ها...")
        
        # ایجاد و شروع کارگر واردسازی
        self.import_worker = ImportWorker(
            self.data_loader, self.db_manager,
            self.bank_file, self.pos_folder, self.accounting_file
        )
        
        # اتصال سیگنال‌ها
        self.import_worker.progress_updated.connect(self.update_progress)
        self.import_worker.import_completed.connect(self.on_import_completed)
        self.import_worker.log_message.connect(self.log_text.append_log)
        
        # شروع کارگر
        self.import_worker.start()
    
    def update_progress(self, value: int, message: str):
        """
        به‌روزرسانی نوار پیشرفت
        
        پارامترها:
            value: مقدار پیشرفت (0-100)
            message: پیام وضعیت
        """
        self.progress_bar.setValue(value)
        self.status_label.setText(message)
    
    def on_import_completed(self, success: bool, message: str):
        """
        تکمیل واردسازی داده‌ها
        
        پارامترها:
            success: آیا واردسازی موفقیت‌آمیز بوده است
            message: پیام نتیجه
        """
        # فعال کردن دکمه‌ها
        self.import_btn.setEnabled(True)
        self.bank_file_btn.setEnabled(True)
        self.pos_folder_btn.setEnabled(True)
        self.accounting_file_btn.setEnabled(True)
        
        # نمایش پیام نتیجه
        self.status_label.setText(message)
        
        if success:
            QMessageBox.information(self, "موفقیت", "واردسازی داده‌ها با موفقیت انجام شد.")
            # ارسال سیگنال تکمیل واردسازی
            self.import_completed.emit(True)
        else:
            QMessageBox.critical(self, "خطا", f"خطا در واردسازی داده‌ها: {message}")


class ReconciliationTab(QWidget):
    """
    تب مغایرت‌گیری
    """
    
    def __init__(self, db_manager: DatabaseManager, reconciliation_engine: ReconciliationEngine):
        """
        مقداردهی اولیه کلاس ReconciliationTab
        
        پارامترها:
            db_manager: نمونه‌ای از کلاس DatabaseManager
            reconciliation_engine: نمونه‌ای از کلاس ReconciliationEngine
        """
        super().__init__()
        self.db_manager = db_manager
        self.reconciliation_engine = reconciliation_engine
        
        self.init_ui()
    
    def init_ui(self):
        """
        راه‌اندازی رابط کاربری
        """
        layout = QVBoxLayout()
        
        # دکمه شروع مغایرت‌گیری
        self.reconcile_btn = QPushButton("شروع مغایرت‌گیری")
        self.reconcile_btn.clicked.connect(self.start_reconciliation)
        self.reconcile_btn.setMinimumHeight(40)
        layout.addWidget(self.reconcile_btn)
        
        # نوار پیشرفت
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        layout.addWidget(self.progress_bar)
        
        # برچسب وضعیت
        self.status_label = QLabel("آماده برای مغایرت‌گیری...")
        layout.addWidget(self.status_label)
        
        # اسپلیتر برای تقسیم فضا بین لاگ و جدول
        splitter = QSplitter(Qt.Vertical)
        
        # ناحیه لاگ
        log_group = QGroupBox("گزارش فعالیت‌ها")
        log_layout = QVBoxLayout()
        
        self.log_text = LogTextEdit()
        log_layout.addWidget(self.log_text)
        
        log_group.setLayout(log_layout)
        splitter.addWidget(log_group)
        
        # ناحیه رکوردهای مغایرت‌گیری نشده
        unreconciled_group = QGroupBox("رکوردهای مغایرت‌گیری نشده")
        unreconciled_layout = QVBoxLayout()
        
        # کومبوباکس نوع رکورد
        self.record_type_combo = QComboBox()
        self.record_type_combo.addItems(["بانک", "پوز", "حسابداری"])
        self.record_type_combo.currentIndexChanged.connect(self.load_unreconciled_records)
        unreconciled_layout.addWidget(QLabel("نوع رکورد:"))
        unreconciled_layout.addWidget(self.record_type_combo)
        
        # جدول رکوردها
        self.records_table = QTableView()
        self.records_table.setSelectionBehavior(QTableView.SelectRows)
        self.records_table.setSelectionMode(QTableView.SingleSelection)
        self.records_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        unreconciled_layout.addWidget(self.records_table)
        
        # دکمه‌های عملیات
        buttons_layout = QHBoxLayout()
        
        self.manual_reconcile_btn = QPushButton("مغایرت‌گیری دستی")
        self.manual_reconcile_btn.clicked.connect(self.manual_reconcile)
        buttons_layout.addWidget(self.manual_reconcile_btn)
        
        self.refresh_btn = QPushButton("بازخوانی")
        self.refresh_btn.clicked.connect(self.load_unreconciled_records)
        buttons_layout.addWidget(self.refresh_btn)
        
        unreconciled_layout.addLayout(buttons_layout)
        
        unreconciled_group.setLayout(unreconciled_layout)
        splitter.addWidget(unreconciled_group)
        
        # تنظیم اندازه اولیه اسپلیتر
        splitter.setSizes([200, 400])
        
        layout.addWidget(splitter)
        
        self.setLayout(layout)
        
        # بارگذاری اولیه رکوردها
        QTimer.singleShot(100, self.load_unreconciled_records)
    
    def start_reconciliation(self):
        """
        شروع مغایرت‌گیری
        """
        # غیرفعال کردن دکمه‌ها
        self.reconcile_btn.setEnabled(False)
        self.manual_reconcile_btn.setEnabled(False)
        self.refresh_btn.setEnabled(False)
        
        # تنظیم نوار پیشرفت
        self.progress_bar.setValue(0)
        self.status_label.setText("در حال انجام مغایرت‌گیری...")
        
        # ایجاد و شروع کارگر مغایرت‌گیری
        self.reconciliation_worker = ReconciliationWorker(self.reconciliation_engine)
        
        # اتصال سیگنال‌ها
        self.reconciliation_worker.progress_updated.connect(self.update_progress)
        self.reconciliation_worker.reconciliation_completed.connect(self.reconciliation_completed)
        self.reconciliation_worker.log_message.connect(self.log_text.append_log)
        
        # شروع کارگر
        self.reconciliation_worker.start()
    
    def update_progress(self, value: int, message: str):
        """
        به‌روزرسانی نوار پیشرفت
        
        پارامترها:
            value: مقدار پیشرفت (0-100)
            message: پیام وضعیت
        """
        self.progress_bar.setValue(value)
        self.status_label.setText(message)
    
    def reconciliation_completed(self, success: bool, message: str):
        """
        تکمیل مغایرت‌گیری
        
        پارامترها:
            success: آیا مغایرت‌گیری موفقیت‌آمیز بوده است
            message: پیام نتیجه
        """
        # فعال کردن دکمه‌ها
        self.reconcile_btn.setEnabled(True)
        self.manual_reconcile_btn.setEnabled(True)
        self.refresh_btn.setEnabled(True)
        
        # نمایش پیام نتیجه
        self.status_label.setText(message)
        
        # بازخوانی رکوردهای مغایرت‌گیری نشده
        self.load_unreconciled_records()
        
        if success:
            QMessageBox.information(self, "موفقیت", "مغایرت‌گیری با موفقیت انجام شد.")
        else:
            QMessageBox.critical(self, "خطا", f"خطا در مغایرت‌گیری: {message}")
    
    def load_unreconciled_records(self):
        """
        بارگذاری رکوردهای مغایرت‌گیری نشده
        """
        try:
            record_type = self.record_type_combo.currentText()
            
            if record_type == "بانک":
                # بارگذاری رکوردهای بانکی مغایرت‌گیری نشده
                records = self.db_manager.get_unreconciled_bank_transactions()
                headers = ["تاریخ", "مبلغ واریز", "مبلغ برداشت", "توضیحات", "نوع تراکنش", "شناسه پیگیری"]
                
                # تنظیم مدل داده
                model = DataTableModel(records, headers)
                self.records_table.setModel(model)
                
                # به‌روزرسانی وضعیت
                self.status_label.setText(f"{len(records)} رکورد بانکی مغایرت‌گیری نشده یافت شد.")
            
            elif record_type == "پوز":
                # بارگذاری رکوردهای پوز مغایرت‌گیری نشده
                records = self.db_manager.get_unreconciled_pos_transactions()
                headers = ["تاریخ", "ساعت", "مبلغ", "شماره کارت", "شناسه ترمینال", "شماره پیگیری"]
                
                # تنظیم مدل داده
                model = DataTableModel(records, headers)
                self.records_table.setModel(model)
                
                # به‌روزرسانی وضعیت
                self.status_label.setText(f"{len(records)} رکورد پوز مغایرت‌گیری نشده یافت شد.")
            
            elif record_type == "حسابداری":
                # بارگذاری رکوردهای حسابداری مغایرت‌گیری نشده
                records = self.db_manager.get_unreconciled_accounting_entries()
                headers = ["نوع", "شماره", "بدهکار", "بستانکار", "تاریخ سررسید", "توضیحات"]
                
                # تنظیم مدل داده
                model = DataTableModel(records, headers)
                self.records_table.setModel(model)
                
                # به‌روزرسانی وضعیت
                self.status_label.setText(f"{len(records)} رکورد حسابداری مغایرت‌گیری نشده یافت شد.")
            
        except Exception as e:
            logger.error(f"خطا در بارگذاری رکوردهای مغایرت‌گیری نشده: {str(e)}")
            QMessageBox.critical(self, "خطا", f"خطا در بارگذاری رکوردها: {str(e)}")
    
    def refresh_data(self):
        """
        بازخوانی داده‌ها
        """
        self.load_unreconciled_records()
    
    def manual_reconcile(self):
        """
        مغایرت‌گیری دستی
        """
        try:
            # بررسی انتخاب رکورد
            selected_indexes = self.records_table.selectionModel().selectedRows()
            if not selected_indexes:
                QMessageBox.warning(self, "هشدار", "لطفاً یک رکورد را انتخاب کنید.")
                return
            
            selected_row = selected_indexes[0].row()
            record_type = self.record_type_combo.currentText()
            
            # تعیین نوع و شناسه رکورد
            if record_type == "بانک":
                record_type_en = "bank"
                record_id = self.records_table.model()._data[selected_row].get("id")
            elif record_type == "پوز":
                record_type_en = "pos"
                record_id = self.records_table.model()._data[selected_row].get("id")
            elif record_type == "حسابداری":
                record_type_en = "accounting"
                record_id = self.records_table.model()._data[selected_row].get("id")
            
            # نمایش دیالوگ مغایرت‌گیری دستی
            dialog = ManualReconciliationDialog(
                self.reconciliation_engine, record_type_en, record_id, self
            )
            
            if dialog.exec_() == QDialog.Accepted:
                # بازخوانی رکوردهای مغایرت‌گیری نشده
                self.load_unreconciled_records()
                self.log_text.append_log("مغایرت‌گیری دستی با موفقیت انجام شد.", "green")
            
        except Exception as e:
            logger.error(f"خطا در مغایرت‌گیری دستی: {str(e)}")
            QMessageBox.critical(self, "خطا", f"خطا در مغایرت‌گیری دستی: {str(e)}")


class ReportsTab(QWidget):
    """
    تب گزارش‌ها
    """
    
    def __init__(self, db_manager: DatabaseManager, report_generator: ReportGenerator):
        """
        مقداردهی اولیه کلاس ReportsTab
        
        پارامترها:
            db_manager: نمونه‌ای از کلاس DatabaseManager
            report_generator: نمونه‌ای از کلاس ReportGenerator
        """
        super().__init__()
        self.db_manager = db_manager
        self.report_generator = report_generator
        
        self.init_ui()
    
    def init_ui(self):
        """
        راه‌اندازی رابط کاربری
        """
        layout = QVBoxLayout()
        
        # گروه گزارش‌ها
        reports_group = QGroupBox("گزارش‌ها")
        reports_layout = QVBoxLayout()
        
        # دکمه‌های گزارش‌ها
        self.unmatched_bank_btn = QPushButton("گزارش تراکنش‌های بانکی مغایرت‌گیری نشده")
        self.unmatched_bank_btn.clicked.connect(self.generate_unmatched_bank_report)
        reports_layout.addWidget(self.unmatched_bank_btn)
        
        self.unmatched_accounting_btn = QPushButton("گزارش ورودی‌های حسابداری مغایرت‌گیری نشده")
        self.unmatched_accounting_btn.clicked.connect(self.generate_unmatched_accounting_report)
        reports_layout.addWidget(self.unmatched_accounting_btn)
        
        self.pos_not_in_accounting_btn = QPushButton("گزارش تراکنش‌های پوز که در حسابداری نیستند")
        self.pos_not_in_accounting_btn.clicked.connect(self.generate_pos_not_in_accounting_report)
        reports_layout.addWidget(self.pos_not_in_accounting_btn)
        
        self.accounting_pos_not_in_pos_btn = QPushButton("گزارش ورودی‌های حسابداری پوز که در تراکنش‌های پوز نیستند")
        self.accounting_pos_not_in_pos_btn.clicked.connect(self.generate_accounting_pos_not_in_pos_report)
        reports_layout.addWidget(self.accounting_pos_not_in_pos_btn)
        
        self.duplicate_accounting_btn = QPushButton("گزارش ورودی‌های حسابداری تکراری")
        self.duplicate_accounting_btn.clicked.connect(self.generate_duplicate_accounting_entries_report)
        reports_layout.addWidget(self.duplicate_accounting_btn)
        
        self.summary_report_btn = QPushButton("گزارش خلاصه مغایرت‌گیری")
        self.summary_report_btn.clicked.connect(self.generate_reconciliation_summary_report)
        reports_layout.addWidget(self.summary_report_btn)
        
        reports_group.setLayout(reports_layout)
        layout.addWidget(reports_group)
        
        # ناحیه وضعیت
        status_group = QGroupBox("وضعیت")
        status_layout = QVBoxLayout()
        
        self.status_label = QLabel("آماده برای تولید گزارش...")
        status_layout.addWidget(self.status_label)
        
        status_group.setLayout(status_layout)
        layout.addWidget(status_group)
        
        # ناحیه گزارش‌های اخیر
        recent_reports_group = QGroupBox("گزارش‌های اخیر")
        recent_reports_layout = QVBoxLayout()
        
        self.recent_reports_text = QTextEdit()
        self.recent_reports_text.setReadOnly(True)
        recent_reports_layout.addWidget(self.recent_reports_text)
        
        recent_reports_group.setLayout(recent_reports_layout)
        layout.addWidget(recent_reports_group)
        
        self.setLayout(layout)
        
        # بارگذاری اولیه گزارش‌های اخیر
        QTimer.singleShot(100, self.load_recent_reports)
    
    def load_recent_reports(self):
        """
        بارگذاری گزارش‌های اخیر
        """
        try:
            # بررسی وجود دایرکتوری گزارش‌ها
            if not os.path.exists(REPORTS_DIR):
                self.recent_reports_text.setText("هیچ گزارشی یافت نشد.")
                return
            
            # دریافت لیست فایل‌های گزارش
            report_files = [f for f in os.listdir(REPORTS_DIR) if f.endswith('.pdf')]
            report_files.sort(key=lambda x: os.path.getmtime(os.path.join(REPORTS_DIR, x)), reverse=True)
            
            if not report_files:
                self.recent_reports_text.setText("هیچ گزارشی یافت نشد.")
                return
            
            # نمایش گزارش‌های اخیر
            report_text = ""
            for i, file in enumerate(report_files[:10], 1):  # نمایش 10 گزارش اخیر
                file_path = os.path.join(REPORTS_DIR, file)
                file_time = os.path.getmtime(file_path)
                file_date = datetime.fromtimestamp(file_time).strftime('%Y-%m-%d %H:%M:%S')
                jalali_date = convert_gregorian_to_jalali_str(file_date, '%Y-%m-%d %H:%M:%S', '%Y/%m/%d %H:%M:%S')
                
                report_text += f"{i}. {file} - {jalali_date}\n"
            
            self.recent_reports_text.setText(report_text)
            
        except Exception as e:
            logger.error(f"خطا در بارگذاری گزارش‌های اخیر: {str(e)}")
            self.recent_reports_text.setText(f"خطا در بارگذاری گزارش‌های اخیر: {str(e)}")
    
    def generate_unmatched_bank_report(self):
        """
        تولید گزارش تراکنش‌های بانکی مغایرت‌گیری نشده
        """
        try:
            self.status_label.setText("در حال تولید گزارش تراکنش‌های بانکی مغایرت‌گیری نشده...")
            
            # تولید گزارش
            report_path = self.report_generator.generate_unmatched_bank_report()
            
            if report_path:
                self.status_label.setText(f"گزارش با موفقیت در {report_path} ذخیره شد.")
                QMessageBox.information(self, "موفقیت", f"گزارش با موفقیت در {report_path} ذخیره شد.")
                
                # بازخوانی گزارش‌های اخیر
                self.load_recent_reports()
            else:
                self.status_label.setText("خطا در تولید گزارش.")
                QMessageBox.critical(self, "خطا", "خطا در تولید گزارش.")
            
        except Exception as e:
            logger.error(f"خطا در تولید گزارش تراکنش‌های بانکی مغایرت‌گیری نشده: {str(e)}")
            self.status_label.setText(f"خطا در تولید گزارش: {str(e)}")
            QMessageBox.critical(self, "خطا", f"خطا در تولید گزارش: {str(e)}")
    
    def generate_unmatched_accounting_report(self):
        """
        تولید گزارش ورودی‌های حسابداری مغایرت‌گیری نشده
        """
        try:
            self.status_label.setText("در حال تولید گزارش ورودی‌های حسابداری مغایرت‌گیری نشده...")
            
            # تولید گزارش
            report_path = self.report_generator.generate_unmatched_accounting_report()
            
            if report_path:
                self.status_label.setText(f"گزارش با موفقیت در {report_path} ذخیره شد.")
                QMessageBox.information(self, "موفقیت", f"گزارش با موفقیت در {report_path} ذخیره شد.")
                
                # بازخوانی گزارش‌های اخیر
                self.load_recent_reports()
            else:
                self.status_label.setText("خطا در تولید گزارش.")
                QMessageBox.critical(self, "خطا", "خطا در تولید گزارش.")
            
        except Exception as e:
            logger.error(f"خطا در تولید گزارش ورودی‌های حسابداری مغایرت‌گیری نشده: {str(e)}")
            self.status_label.setText(f"خطا در تولید گزارش: {str(e)}")
            QMessageBox.critical(self, "خطا", f"خطا در تولید گزارش: {str(e)}")
    
    def generate_pos_not_in_accounting_report(self):
        """
        تولید گزارش تراکنش‌های پوز که در حسابداری نیستند
        """
        try:
            self.status_label.setText("در حال تولید گزارش تراکنش‌های پوز که در حسابداری نیستند...")
            
            # تولید گزارش
            report_path = self.report_generator.generate_pos_not_in_accounting_report()
            
            if report_path:
                self.status_label.setText(f"گزارش با موفقیت در {report_path} ذخیره شد.")
                QMessageBox.information(self, "موفقیت", f"گزارش با موفقیت در {report_path} ذخیره شد.")
                
                # بازخوانی گزارش‌های اخیر
                self.load_recent_reports()
            else:
                self.status_label.setText("خطا در تولید گزارش.")
                QMessageBox.critical(self, "خطا", "خطا در تولید گزارش.")
            
        except Exception as e:
            logger.error(f"خطا در تولید گزارش تراکنش‌های پوز که در حسابداری نیستند: {str(e)}")
            self.status_label.setText(f"خطا در تولید گزارش: {str(e)}")
            QMessageBox.critical(self, "خطا", f"خطا در تولید گزارش: {str(e)}")
    
    def generate_accounting_pos_not_in_pos_report(self):
        """
        تولید گزارش ورودی‌های پوز حسابداری که در پوز نیستند
        """
        try:
            self.status_label.setText("در حال تولید گزارش ورودی‌های پوز حسابداری که در پوز نیستند...")
            
            # تولید گزارش
            report_path = self.report_generator.generate_accounting_pos_not_in_pos_report()
            
            if report_path:
                self.status_label.setText(f"گزارش با موفقیت در {report_path} ذخیره شد.")
                QMessageBox.information(self, "موفقیت", f"گزارش با موفقیت در {report_path} ذخیره شد.")
                
                # بازخوانی گزارش‌های اخیر
                self.load_recent_reports()
            else:
                self.status_label.setText("خطا در تولید گزارش.")
                QMessageBox.critical(self, "خطا", "خطا در تولید گزارش.")
            
        except Exception as e:
            logger.error(f"خطا در تولید گزارش ورودی‌های پوز حسابداری که در پوز نیستند: {str(e)}")
            self.status_label.setText(f"خطا در تولید گزارش: {str(e)}")
            QMessageBox.critical(self, "خطا", f"خطا در تولید گزارش: {str(e)}")
    
    def generate_duplicate_accounting_entries_report(self):
        """
        تولید گزارش ورودی‌های تکراری حسابداری
        """
        try:
            self.status_label.setText("در حال تولید گزارش ورودی‌های تکراری حسابداری...")
            
            # تولید گزارش
            report_path = self.report_generator.generate_duplicate_accounting_entries_report()
            
            if report_path:
                self.status_label.setText(f"گزارش با موفقیت در {report_path} ذخیره شد.")
                QMessageBox.information(self, "موفقیت", f"گزارش با موفقیت در {report_path} ذخیره شد.")
                
                # بازخوانی گزارش‌های اخیر
                self.load_recent_reports()
            else:
                self.status_label.setText("خطا در تولید گزارش.")
                QMessageBox.critical(self, "خطا", "خطا در تولید گزارش.")
            
        except Exception as e:
            logger.error(f"خطا در تولید گزارش ورودی‌های تکراری حسابداری: {str(e)}")
            self.status_label.setText(f"خطا در تولید گزارش: {str(e)}")
            QMessageBox.critical(self, "خطا", f"خطا در تولید گزارش: {str(e)}")
    
    def generate_reconciliation_summary_report(self):
        """
        تولید گزارش خلاصه مغایرت‌گیری
        """
        try:
            self.status_label.setText("در حال تولید گزارش خلاصه مغایرت‌گیری...")
            
            # تولید گزارش
            report_path = self.report_generator.generate_reconciliation_summary_report()
            
            if report_path:
                self.status_label.setText(f"گزارش با موفقیت در {report_path} ذخیره شد.")
                QMessageBox.information(self, "موفقیت", f"گزارش با موفقیت در {report_path} ذخیره شد.")
                
                # بازخوانی گزارش‌های اخیر
                self.load_recent_reports()
            else:
                self.status_label.setText("خطا در تولید گزارش.")
                QMessageBox.critical(self, "خطا", "خطا در تولید گزارش.")
            
        except Exception as e:
            logger.error(f"خطا در تولید گزارش خلاصه مغایرت‌گیری: {str(e)}")
            self.status_label.setText(f"خطا در تولید گزارش: {str(e)}")
            QMessageBox.critical(self, "خطا", f"خطا در تولید گزارش: {str(e)}")