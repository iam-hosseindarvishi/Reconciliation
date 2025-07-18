#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
تب واردسازی داده‌ها
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFormLayout, QLabel, QPushButton,
    QFileDialog, QProgressBar, QMessageBox, QGroupBox, QComboBox
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
        
        # شناسه بانک انتخاب شده (واحد برای همه فایل‌ها)
        self.selected_bank_id = None
        # راه‌اندازی رابط کاربری
        self.init_ui()
    
    def init_ui(self):
        """
        راه‌اندازی رابط کاربری
        """
        layout = QVBoxLayout()
        
        # بخش اطلاعات تکمیلی
        self.create_additional_info_section(layout)
        
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
        
        # انتخاب بانک (واحد برای همه فایل‌ها)
        self.bank_combo = QComboBox()
        self.bank_combo.currentIndexChanged.connect(self.on_bank_selection_changed)
        file_layout.addRow("انتخاب بانک:", self.bank_combo)
        
        file_group.setLayout(file_layout)
        layout.addWidget(file_group)
        
        # دکمه‌های واردسازی و پاک کردن ورودی‌ها
        buttons_layout = QHBoxLayout()
        self.import_button = QPushButton("شروع واردسازی داده‌ها")
        self.import_button.clicked.connect(self.import_data)
        self.clear_inputs_button = QPushButton("پاک کردن ورودی‌ها")
        self.clear_inputs_button.clicked.connect(self.clear_file_inputs)
        buttons_layout.addWidget(self.import_button)
        buttons_layout.addWidget(self.clear_inputs_button)
        layout.addLayout(buttons_layout)
        
        # بخش پاکسازی داده‌ها
        self.create_data_cleanup_section(layout)
        
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
        
        # بارگذاری لیست بانک‌ها
        self.load_banks()
    
    def load_banks(self):
        """
        بارگذاری لیست بانک‌ها در کمبوباکس
        """
        try:
            banks = self.db_manager.get_all_banks()
            
            # پاک کردن کمبوباکس
            self.bank_combo.clear()
            
            # افزودن گزینه پیش‌فرض
            self.bank_combo.addItem("انتخاب بانک", None)
            
            # افزودن بانک‌ها
            for bank in banks:
                bank_name = bank['BankName']
                bank_id = bank['id']
                self.bank_combo.addItem(bank_name, bank_id)
                
        except Exception as e:
            logger.error(f"خطا در بارگذاری لیست بانک‌ها: {str(e)}")
    
    def on_bank_selection_changed(self, index):
        """
        رویداد تغییر انتخاب بانک
        """
        self.selected_bank_id = self.bank_combo.currentData()
    
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
        
        # بررسی انتخاب بانک
        if not self.selected_bank_id:
            QMessageBox.warning(self, "هشدار", "لطفاً بانک را انتخاب کنید.")
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
            self.bank_file_path,
            self.pos_file_path,
            self.accounting_file_path,
            self.selected_bank_id,
            self.selected_bank_id,
            self.selected_bank_id
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
    
    def create_additional_info_section(self, layout):
        """
        ایجاد بخش اطلاعات تکمیلی
        """
        info_group = QGroupBox("اطلاعات تکمیلی")
        info_layout = QFormLayout()
        
        # تاریخ آخرین رکورد حسابداری
        self.latest_accounting_date_label = QLabel("در حال بارگذاری...")
        info_layout.addRow("تاریخ آخرین رکورد حسابداری:", self.latest_accounting_date_label)
        
        # تاریخ آخرین رکورد بانک
        self.latest_bank_date_label = QLabel("در حال بارگذاری...")
        info_layout.addRow("تاریخ آخرین رکورد بانک:", self.latest_bank_date_label)
        
        # تاریخ آخرین تراکنش پوز
        self.latest_pos_date_label = QLabel("در حال بارگذاری...")
        info_layout.addRow("تاریخ آخرین تراکنش پوز:", self.latest_pos_date_label)
        
        info_group.setLayout(info_layout)
        layout.addWidget(info_group)
        
        # بارگذاری اطلاعات
        self.load_additional_info()
    
    def create_data_cleanup_section(self, layout):
        """
        ایجاد بخش پاکسازی داده‌ها
        """
        cleanup_group = QGroupBox("پاکسازی داده‌ها")
        cleanup_layout = QHBoxLayout()
        
        # دکمه پاک کردن کلیه داده‌ها
        self.clear_all_data_button = QPushButton("پاک کردن کلیه داده‌ها")
        self.clear_all_data_button.clicked.connect(self.clear_all_data)
        cleanup_layout.addWidget(self.clear_all_data_button)
        
        # دکمه حذف اطلاعات مغایرت‌گیری شده
        self.clear_reconciled_data_button = QPushButton("حذف اطلاعات مغایرت‌گیری شده")
        self.clear_reconciled_data_button.clicked.connect(self.clear_reconciled_data)
        cleanup_layout.addWidget(self.clear_reconciled_data_button)
        
        cleanup_group.setLayout(cleanup_layout)
        layout.addWidget(cleanup_group)
    
    def load_additional_info(self):
        """
        بارگذاری اطلاعات تکمیلی
        """
        try:
            # دریافت تاریخ آخرین رکورد حسابداری
            latest_accounting_date = self.db_manager.get_latest_accounting_entry_date()
            if latest_accounting_date:
                self.latest_accounting_date_label.setText(latest_accounting_date)
            else:
                self.latest_accounting_date_label.setText("هیچ رکوردی موجود نیست")
            
            # دریافت تاریخ آخرین رکورد بانک
            latest_bank_date = self.db_manager.get_latest_bank_transaction_date()
            if latest_bank_date:
                self.latest_bank_date_label.setText(latest_bank_date)
            else:
                self.latest_bank_date_label.setText("هیچ رکوردی موجود نیست")
            
            # دریافت تاریخ آخرین تراکنش پوز
            latest_pos_date = self.db_manager.get_latest_pos_transaction_date()
            if latest_pos_date:
                self.latest_pos_date_label.setText(latest_pos_date)
            else:
                self.latest_pos_date_label.setText("هیچ رکوردی موجود نیست")
                
        except Exception as e:
            logger.error(f"خطا در بارگذاری اطلاعات تکمیلی: {str(e)}")
            self.latest_accounting_date_label.setText("خطا در بارگذاری")
            self.latest_bank_date_label.setText("خطا در بارگذاری")
            self.latest_pos_date_label.setText("خطا در بارگذاری")
    
    def clear_file_inputs(self):
        """
        پاک کردن ورودی‌های انتخاب فایل
        """
        # پاک کردن مسیرهای فایل
        self.bank_file_path = ""
        self.pos_file_path = ""
        self.accounting_file_path = ""
        
        # پاک کردن متن لیبل‌ها
        self.bank_file_label.setText("فایل انتخاب نشده")
        self.pos_file_label.setText("فایل انتخاب نشده")
        self.accounting_file_label.setText("فایل انتخاب نشده")
        
        # بازنشانی انتخاب بانک
        self.bank_combo.setCurrentIndex(0)
        
        self.log_text.append_log("ورودی‌های انتخاب فایل پاک شدند.", "blue")
    
    def clear_all_data(self):
        """
        پاک کردن کلیه داده‌ها به استثنای بانک‌ها
        """
        reply = QMessageBox.question(
            self, 
            "تایید پاکسازی", 
            "آیا مطمئن هستید که می‌خواهید کلیه داده‌ها (به استثنای بانک‌ها) را حذف کنید؟\n\nاین عملیات غیرقابل بازگشت است.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            try:
                success = self.db_manager.clear_all_data_except_banks()
                if success:
                    QMessageBox.information(self, "موفقیت", "کلیه داده‌ها با موفقیت حذف شدند.")
                    self.log_text.append_log("کلیه داده‌ها به استثنای بانک‌ها حذف شدند.", "green")
                    # به‌روزرسانی اطلاعات تکمیلی
                    self.load_additional_info()
                else:
                    QMessageBox.critical(self, "خطا", "خطا در حذف داده‌ها.")
                    self.log_text.append_log("خطا در حذف کلیه داده‌ها.", "red")
            except Exception as e:
                logger.error(f"خطا در پاک کردن کلیه داده‌ها: {str(e)}")
                QMessageBox.critical(self, "خطا", f"خطا در حذف داده‌ها: {str(e)}")
    
    def clear_reconciled_data(self):
        """
        حذف اطلاعات مغایرت‌گیری شده
        """
        reply = QMessageBox.question(
            self, 
            "تایید حذف", 
            "آیا مطمئن هستید که می‌خواهید اطلاعات مغایرت‌گیری شده را حذف کنید؟\n\nاین عملیات غیرقابل بازگشت است.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            try:
                success = self.db_manager.clear_reconciled_data()
                if success:
                    QMessageBox.information(self, "موفقیت", "اطلاعات مغایرت‌گیری شده با موفقیت حذف شدند.")
                    self.log_text.append_log("اطلاعات مغایرت‌گیری شده حذف شدند.", "green")
                    # به‌روزرسانی اطلاعات تکمیلی
                    self.load_additional_info()
                else:
                    QMessageBox.critical(self, "خطا", "خطا در حذف اطلاعات مغایرت‌گیری شده.")
                    self.log_text.append_log("خطا در حذف اطلاعات مغایرت‌گیری شده.", "red")
            except Exception as e:
                logger.error(f"خطا در حذف اطلاعات مغایرت‌گیری شده: {str(e)}")
                QMessageBox.critical(self, "خطا", f"خطا در حذف اطلاعات مغایرت‌گیری شده: {str(e)}")