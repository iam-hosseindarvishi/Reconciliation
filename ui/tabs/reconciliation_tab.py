#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
تب مغایرت‌گیری
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QProgressBar,
    QTableView, QHeaderView, QMessageBox, QGroupBox, QTabWidget, QMenu
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QAction

from modules.database_manager import DatabaseManager
from modules.reconciliation_logic import ReconciliationEngine
from modules.logger import get_logger
from ui.widgets import LogTextEdit, DataTableModel
from ui.workers import ReconciliationWorker
from ui.dialogs import ManualReconciliationDialog

# ایجاد شیء لاگر
logger = get_logger(__name__)


class ReconciliationTab(QWidget):
    """
    تب مغایرت‌گیری
    """
    
    # سیگنال‌ها
    reconciliation_completed = Signal(bool, str)
    
    def __init__(self, parent=None):
        """
        مقداردهی اولیه کلاس ReconciliationTab
        
        پارامترها:
            db_manager: نمونه‌ای از کلاس DatabaseManager
            parent: ویجت والد
        """
        super().__init__(parent)
        self.db_manager = DatabaseManager()
        self.reconciliation_engine = ReconciliationEngine()
        
        # راه‌اندازی رابط کاربری
        self.init_ui()
    
    def init_ui(self):
        """
        راه‌اندازی رابط کاربری
        """
        layout = QVBoxLayout()
        
        # دکمه شروع مغایرت‌گیری
        self.start_button = QPushButton("شروع مغایرت‌گیری")
        self.start_button.clicked.connect(self.start_reconciliation)
        layout.addWidget(self.start_button)
        
        # نوار پیشرفت
        progress_layout = QHBoxLayout()
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.status_label = QLabel("آماده برای مغایرت‌گیری")
        progress_layout.addWidget(self.progress_bar)
        progress_layout.addWidget(self.status_label)
        layout.addLayout(progress_layout)
        
        # تب‌های نمایش نتایج
        self.results_tabs = QTabWidget()
        
        # تب مغایرت‌های بانک
        self.bank_tab = QWidget()
        bank_layout = QVBoxLayout()
        self.bank_table = QTableView()
        self.bank_table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.bank_table.customContextMenuRequested.connect(lambda pos: self.show_context_menu(pos, "bank"))
        self.bank_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        bank_layout.addWidget(self.bank_table)
        self.bank_tab.setLayout(bank_layout)
        self.results_tabs.addTab(self.bank_tab, "مغایرت‌های بانک")
        
        # تب مغایرت‌های پوز
        self.pos_tab = QWidget()
        pos_layout = QVBoxLayout()
        self.pos_table = QTableView()
        self.pos_table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.pos_table.customContextMenuRequested.connect(lambda pos: self.show_context_menu(pos, "pos"))
        self.pos_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        pos_layout.addWidget(self.pos_table)
        self.pos_tab.setLayout(pos_layout)
        self.results_tabs.addTab(self.pos_tab, "مغایرت‌های پوز")
        
        # تب مغایرت‌های حسابداری
        self.accounting_tab = QWidget()
        accounting_layout = QVBoxLayout()
        self.accounting_table = QTableView()
        self.accounting_table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.accounting_table.customContextMenuRequested.connect(lambda pos: self.show_context_menu(pos, "accounting"))
        self.accounting_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        accounting_layout.addWidget(self.accounting_table)
        self.accounting_tab.setLayout(accounting_layout)
        self.results_tabs.addTab(self.accounting_tab, "مغایرت‌های حسابداری")
        
        layout.addWidget(self.results_tabs)
        
        # ویجت لاگ
        self.log_text = LogTextEdit()
        layout.addWidget(self.log_text)
        
        self.setLayout(layout)
        
        # بارگذاری داده‌های موجود
        self.load_existing_data()
    
    def load_existing_data(self):
        """
        بارگذاری داده‌های موجود
        """
        try:
            # بارگذاری مغایرت‌های بانک
            bank_unreconciled = self.db_manager.get_unreconciled_bank_transactions()
            if bank_unreconciled:
                headers = ["تاریخ", "مبلغ واریز", "مبلغ برداشت", "توضیحات", "نوع تراکنش", "شناسه پیگیری"]
                self.bank_table.setModel(DataTableModel(bank_unreconciled, headers))
            
            # بارگذاری مغایرت‌های پوز
            pos_unreconciled = self.db_manager.get_unreconciled_pos_transactions()
            if pos_unreconciled:
                headers = ["تاریخ", "ساعت", "مبلغ", "شماره کارت", "شناسه ترمینال", "شماره پیگیری"]
                self.pos_table.setModel(DataTableModel(pos_unreconciled, headers))
            
            # بارگذاری مغایرت‌های حسابداری
            accounting_unreconciled = self.db_manager.get_unreconciled_accounting_entries()
            if accounting_unreconciled:
                headers = ["نوع", "شماره", "بدهکار", "بستانکار", "تاریخ سررسید", "توضیحات"]
                self.accounting_table.setModel(DataTableModel(accounting_unreconciled, headers))
            
        except Exception as e:
            logger.error(f"خطا در بارگذاری داده‌های موجود: {str(e)}")
            self.log_text.append_log(f"خطا در بارگذاری داده‌های موجود: {str(e)}", "red")
    
    def start_reconciliation(self):
        """
        شروع مغایرت‌گیری
        """
        # غیرفعال کردن دکمه شروع
        self.start_button.setEnabled(False)
        
        # تنظیم نوار پیشرفت
        self.progress_bar.setValue(0)
        self.status_label.setText("در حال انجام مغایرت‌گیری...")
        
        # ایجاد و راه‌اندازی ReconciliationWorker
        self.reconciliation_worker = ReconciliationWorker(self.reconciliation_engine)
        
        # اتصال سیگنال‌ها
        self.reconciliation_worker.progress_updated.connect(self.update_progress)
        self.reconciliation_worker.reconciliation_completed.connect(self.on_reconciliation_completed)
        self.reconciliation_worker.log_message.connect(self.log_text.append_log)
        
        # شروع ReconciliationWorker
        self.reconciliation_worker.start()
    
    def update_progress(self, progress, status_text):
        """
        به‌روزرسانی نوار پیشرفت
        
        پارامترها:
            progress: درصد پیشرفت
            status_text: متن وضعیت
        """
        self.progress_bar.setValue(progress)
        self.status_label.setText(status_text)
    
    def on_reconciliation_completed(self, success, message):
        """
        تکمیل مغایرت‌گیری
        
        پارامترها:
            success: وضعیت موفقیت
            message: پیام نتیجه
        """
        # فعال کردن دکمه شروع
        self.start_button.setEnabled(True)
        
        # نمایش پیام نتیجه
        self.status_label.setText(message)
        
        # به‌روزرسانی جداول
        self.load_existing_data()
        
        # نمایش پیام اطلاعاتی در صورت موفقیت
        if success:
            QMessageBox.information(self, "موفقیت", message)
        else:
            QMessageBox.critical(self, "خطا", message)
        
        # ارسال سیگنال تکمیل مغایرت‌گیری
        self.reconciliation_completed.emit(success, message)
    
    def show_context_menu(self, position, table_type):
        """
        نمایش منوی راست‌کلیک
        
        پارامترها:
            position: موقعیت کلیک
            table_type: نوع جدول (bank, pos, accounting)
        """
        # تعیین جدول مورد نظر
        if table_type == "bank":
            table = self.bank_table
        elif table_type == "pos":
            table = self.pos_table
        elif table_type == "accounting":
            table = self.accounting_table
        else:
            return
        
        # بررسی انتخاب ردیف
        index = table.indexAt(position)
        if not index.isValid():
            return
        
        # ایجاد منو
        menu = QMenu()
        manual_reconcile_action = QAction("مغایرت‌گیری دستی", self)
        menu.addAction(manual_reconcile_action)
        
        # اجرای منو
        action = menu.exec_(table.viewport().mapToGlobal(position))
        
        # پردازش اکشن انتخاب شده
        if action == manual_reconcile_action:
            self.open_manual_reconciliation_dialog(table_type, index.row())
    
    def open_manual_reconciliation_dialog(self, record_type, row_index):
        """
        باز کردن دیالوگ مغایرت‌گیری دستی
        
        پارامترها:
            record_type: نوع رکورد (bank, pos, accounting)
            row_index: شاخص ردیف
        """
        try:
            # دریافت شناسه رکورد
            if record_type == "bank":
                record_id = self.bank_table.model()._data[row_index].get("id")
            elif record_type == "pos":
                record_id = self.pos_table.model()._data[row_index].get("id")
            elif record_type == "accounting":
                record_id = self.accounting_table.model()._data[row_index].get("id")
            else:
                return
            
            # ایجاد و نمایش دیالوگ
            dialog = ManualReconciliationDialog(self.reconciliation_engine, record_type, record_id, self)
            result = dialog.exec_()
            
            # به‌روزرسانی جداول در صورت موفقیت
            if result == dialog.Accepted:
                self.load_existing_data()
                self.log_text.append_log("مغایرت‌گیری دستی با موفقیت انجام شد.", "green")
            
        except Exception as e:
            logger.error(f"خطا در باز کردن دیالوگ مغایرت‌گیری دستی: {str(e)}")
            self.log_text.append_log(f"خطا در باز کردن دیالوگ مغایرت‌گیری دستی: {str(e)}", "red")
            QMessageBox.critical(self, "خطا", f"خطا در باز کردن دیالوگ مغایرت‌گیری دستی: {str(e)}")