#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
تب واردسازی داده‌ها
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFormLayout, QLabel, QPushButton,
    QFileDialog, QProgressBar, QMessageBox, QGroupBox
)
from PySide6.QtCore import Qt, Signal

from modules.data_loader import DataLoader
from modules.database_manager import DatabaseManager
from modules.logger import get_logger
from ui.widgets import LogTextEdit
from ui.workers import ImportWorker

import os
# ایجاد شیء لاگر
logger = get_logger(__name__)


class DataImportTab(QWidget):
    """
    تب واردسازی داده‌ها
    """
    
    # تعریف سیگنال‌ها
    import_completed = Signal(bool, str)
    
    def __init__(self, parent=None):
        """
        مقداردهی اولیه کلاس DataImportTab
        
        پارامترها:
            db_manager: نمونه‌ای از کلاس DatabaseManager
            parent: ویجت والد
        """
        super().__init__(parent)
        self.db_manager = DatabaseManager()
        self.data_loader = DataLoader()
        
        # مسیرهای فایل‌ها
        self.bank_file_path = ""
        self.pos_file_path = ""
        self.accounting_file_path = ""
         # **اضافه کردن ویژگی‌های مسیرهای پیش‌فرض برای استفاده در load_settings/save_settings**
        self.default_bank_path = ""
        self.default_pos_path = ""
        self.default_accounting_path = ""
        # راه‌اندازی رابط کاربری
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
        bank_layout = QHBoxLayout()
        self.bank_file_label = QLabel("فایل انتخاب نشده")
        self.bank_file_button = QPushButton("انتخاب فایل بانک")
        self.bank_file_button.clicked.connect(self.select_bank_file)
        bank_layout.addWidget(self.bank_file_label)
        bank_layout.addWidget(self.bank_file_button)
        file_layout.addRow("فایل بانک:", bank_layout)
        
        # انتخاب فایل پوز
        pos_layout = QHBoxLayout()
        self.pos_file_label = QLabel("فایل انتخاب نشده")
        self.pos_file_button = QPushButton("انتخاب فایل پوز")
        self.pos_file_button.clicked.connect(self.select_pos_file)
        pos_layout.addWidget(self.pos_file_label)
        pos_layout.addWidget(self.pos_file_button)
        file_layout.addRow("فایل پوز:", pos_layout)
        
        # انتخاب فایل حسابداری
        accounting_layout = QHBoxLayout()
        self.accounting_file_label = QLabel("فایل انتخاب نشده")
        self.accounting_file_button = QPushButton("انتخاب فایل حسابداری")
        self.accounting_file_button.clicked.connect(self.select_accounting_file)
        accounting_layout.addWidget(self.accounting_file_label)
        accounting_layout.addWidget(self.accounting_file_button)
        file_layout.addRow("فایل حسابداری:", accounting_layout)
        
        file_group.setLayout(file_layout)
        layout.addWidget(file_group)
        
        # دکمه واردسازی
        self.import_button = QPushButton("شروع واردسازی داده‌ها")
        self.import_button.clicked.connect(self.import_data)
        layout.addWidget(self.import_button)
        
        # نوار پیشرفت
        progress_layout = QHBoxLayout()
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.status_label = QLabel("آماده برای واردسازی داده‌ها")
        progress_layout.addWidget(self.progress_bar)
        progress_layout.addWidget(self.status_label)
        layout.addLayout(progress_layout)
        
        # ویجت لاگ
        self.log_text = LogTextEdit()
        layout.addWidget(self.log_text)
        
        self.setLayout(layout)
    
    def select_bank_file(self):
        """
        انتخاب فایل بانک
        """
        file_path, _ = QFileDialog.getOpenFileName(
            self, "انتخاب فایل بانک", "", "Excel Files (*.xlsx *.xls);;CSV Files (*.csv)"
        )
        if file_path:
            self.bank_file_path = file_path
            self.bank_file_label.setText(file_path.split("/")[-1])
            self.log_text.append_log(f"فایل بانک انتخاب شد: {file_path}", "blue")
    
    def select_pos_file(self):
        """
        انتخاب فایل پوز
        """
        folder_path = QFileDialog.getExistingDirectory(
                self, "انتخاب پوشه فایل‌های پوز", "" # عنوان پنجره و مسیر اولیه
            )
        if folder_path:
            self.pos_file_path = folder_path
            self.pos_file_label.setText(os.path.basename(folder_path)) 
            self.log_text.append_log(f"پوشه پوز انتخاب شد: {folder_path}", "blue")
    
    def select_accounting_file(self):
        """
        انتخاب فایل حسابداری
        """
        file_path, _ = QFileDialog.getOpenFileName(
            self, "انتخاب فایل حسابداری", "", "Excel Files (*.xlsx *.xls);;CSV Files (*.csv)"
        )
        if file_path:
            self.accounting_file_path = file_path
            self.accounting_file_label.setText(file_path.split("/")[-1])
            self.log_text.append_log(f"فایل حسابداری انتخاب شد: {file_path}", "blue")
    
    def import_data(self):
        """
        واردسازی داده‌ها
        """
        # بررسی انتخاب حداقل یک فایل
        if not (self.bank_file_path or self.pos_file_path or self.accounting_file_path):
            QMessageBox.warning(self, "هشدار", "لطفاً حداقل یک فایل را انتخاب کنید.")
            return
        
        # غیرفعال کردن دکمه‌ها
        self.bank_file_button.setEnabled(False)
        self.pos_file_button.setEnabled(False)
        self.accounting_file_button.setEnabled(False)
        self.import_button.setEnabled(False)
        
        # تنظیم نوار پیشرفت
        self.progress_bar.setValue(0)
        self.status_label.setText("در حال واردسازی داده‌ها...")
        
        # ایجاد و راه‌اندازی ImportWorker
        self.import_worker = ImportWorker(
            self.data_loader,
            self.db_manager,
            self.bank_file_path,
            self.pos_file_path,
            self.accounting_file_path
        )
        
        # اتصال سیگنال‌ها
        self.import_worker.progress_updated.connect(self.update_progress)
        self.import_worker.import_completed.connect(self.on_import_completed)
        self.import_worker.log_message.connect(self.log_text.append_log)
        
        # شروع ImportWorker
        self.import_worker.start()
    
    def update_progress(self, progress, status_text):
        """
        به‌روزرسانی نوار پیشرفت
        
        پارامترها:
            progress: درصد پیشرفت
            status_text: متن وضعیت
        """
        self.progress_bar.setValue(progress)
        self.status_label.setText(status_text)
    
    def on_import_completed(self, success, message):
        """
        تکمیل واردسازی داده‌ها
        
        پارامترها:
            success: وضعیت موفقیت
            message: پیام نتیجه
        """
        # فعال کردن دکمه‌ها
        self.bank_file_button.setEnabled(True)
        self.pos_file_button.setEnabled(True)
        self.accounting_file_button.setEnabled(True)
        self.import_button.setEnabled(True)
        
        # نمایش پیام نتیجه
        self.status_label.setText(message)
        
        # نمایش پیام اطلاعاتی در صورت موفقیت
        if success:
            QMessageBox.information(self, "موفقیت", message)
        else:
            QMessageBox.critical(self, "خطا", message)
        
        # ارسال سیگنال تکمیل واردسازی
        self.import_completed.emit(success, message)