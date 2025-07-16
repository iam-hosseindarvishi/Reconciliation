#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
تب مدیریت بانک‌ها
"""

import os
import sys
from typing import List, Dict, Any

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFormLayout,
    QLineEdit, QPushButton, QTableWidget, QTableWidgetItem,
    QHeaderView, QMessageBox, QGroupBox, QLabel
)
from PySide6.QtCore import Qt, Signal

# افزودن مسیر پروژه به مسیرهای پایتون
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from modules.database_manager import DatabaseManager
from modules.logger import get_logger

# تنظیم لاگر
logger = get_logger(__name__)

class BankManagementTab(QWidget):
    """
    تب مدیریت بانک‌ها
    """
    
    # سیگنال‌ها
    bank_added = Signal(bool, str)  # موفقیت، پیام
    bank_updated = Signal(bool, str)  # موفقیت، پیام
    bank_deleted = Signal(bool, str)  # موفقیت، پیام
    
    def __init__(self):
        super().__init__()
        
        # مدیر پایگاه داده
        self.db_manager = DatabaseManager()
        
        # متغیرهای داخلی
        self.selected_bank_id = None
        
        # راه‌اندازی رابط کاربری
        self.setup_ui()
        
        # بارگذاری داده‌های اولیه
        self.load_banks()
        
        logger.info("تب مدیریت بانک‌ها راه‌اندازی شد.")
    
    def setup_ui(self):
        """
        راه‌اندازی رابط کاربری
        """
        # چیدمان اصلی
        main_layout = QVBoxLayout(self)
        
        # گروه افزودن/ویرایش بانک
        bank_form_group = QGroupBox("افزودن/ویرایش بانک")
        form_layout = QFormLayout(bank_form_group)
        
        # فیلدهای ورودی
        self.bank_name_edit = QLineEdit()
        self.bank_name_edit.setPlaceholderText("نام بانک (مثال: بانک ملی)")
        form_layout.addRow("نام بانک:", self.bank_name_edit)
        
        self.bank_code_edit = QLineEdit()
        self.bank_code_edit.setPlaceholderText("کد بانک (اختیاری)")
        form_layout.addRow("کد بانک:", self.bank_code_edit)
        
        # دکمه‌های عملیات
        buttons_layout = QHBoxLayout()
        
        self.add_button = QPushButton("افزودن بانک")
        self.add_button.clicked.connect(self.add_bank)
        buttons_layout.addWidget(self.add_button)
        
        self.update_button = QPushButton("به‌روزرسانی بانک")
        self.update_button.clicked.connect(self.update_bank)
        self.update_button.setEnabled(False)
        buttons_layout.addWidget(self.update_button)
        
        self.clear_button = QPushButton("پاک کردن فرم")
        self.clear_button.clicked.connect(self.clear_form)
        buttons_layout.addWidget(self.clear_button)
        
        buttons_layout.addStretch()
        form_layout.addRow(buttons_layout)
        
        main_layout.addWidget(bank_form_group)
        
        # گروه لیست بانک‌ها
        banks_list_group = QGroupBox("لیست بانک‌ها")
        list_layout = QVBoxLayout(banks_list_group)
        
        # جدول بانک‌ها
        self.banks_table = QTableWidget()
        self.banks_table.setColumnCount(3)
        self.banks_table.setHorizontalHeaderLabels(["شناسه", "نام بانک", "کد بانک"])
        
        # تنظیم عرض ستون‌ها
        header = self.banks_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        
        # تنظیم انتخاب سطر
        self.banks_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.banks_table.setSelectionMode(QTableWidget.SingleSelection)
        self.banks_table.itemSelectionChanged.connect(self.on_bank_selected)
        
        list_layout.addWidget(self.banks_table)
        
        # دکمه‌های عملیات جدول
        table_buttons_layout = QHBoxLayout()
        
        self.refresh_button = QPushButton("بروزرسانی لیست")
        self.refresh_button.clicked.connect(self.load_banks)
        table_buttons_layout.addWidget(self.refresh_button)
        
        self.delete_button = QPushButton("حذف بانک انتخابی")
        self.delete_button.clicked.connect(self.delete_bank)
        self.delete_button.setEnabled(False)
        table_buttons_layout.addWidget(self.delete_button)
        
        table_buttons_layout.addStretch()
        list_layout.addLayout(table_buttons_layout)
        
        main_layout.addWidget(banks_list_group)
        
        # اطلاعات کمکی
        info_label = QLabel(
            "نکته: برای ویرایش بانک، آن را از جدول انتخاب کنید، سپس اطلاعات را تغییر دهید و دکمه 'به‌روزرسانی بانک' را فشار دهید."
        )
        info_label.setWordWrap(True)
        info_label.setStyleSheet("color: #666; font-style: italic; padding: 10px;")
        main_layout.addWidget(info_label)
    
    def load_banks(self):
        """
        بارگذاری لیست بانک‌ها از پایگاه داده
        """
        try:
            banks = self.db_manager.get_all_banks()
            
            # پاک کردن جدول
            self.banks_table.setRowCount(0)
            
            # افزودن بانک‌ها به جدول
            for bank in banks:
                row = self.banks_table.rowCount()
                self.banks_table.insertRow(row)
                
                self.banks_table.setItem(row, 0, QTableWidgetItem(str(bank['id'])))
                self.banks_table.setItem(row, 1, QTableWidgetItem(bank['BankName'] or ''))
                self.banks_table.setItem(row, 2, QTableWidgetItem(bank['BankCode'] or ''))
            
            logger.info(f"{len(banks)} بانک بارگذاری شد.")
            
        except Exception as e:
            logger.error(f"خطا در بارگذاری لیست بانک‌ها: {str(e)}")
            QMessageBox.critical(self, "خطا", f"خطا در بارگذاری لیست بانک‌ها:\n{str(e)}")
    
    def add_bank(self):
        """
        افزودن بانک جدید
        """
        bank_name = self.bank_name_edit.text().strip()
        bank_code = self.bank_code_edit.text().strip() or None
        
        if not bank_name:
            QMessageBox.warning(self, "هشدار", "نام بانک الزامی است.")
            return
        
        try:
            success = self.db_manager.add_bank(bank_name, bank_code)
            
            if success:
                message = f"بانک '{bank_name}' با موفقیت اضافه شد."
                QMessageBox.information(self, "موفقیت", message)
                self.clear_form()
                self.load_banks()
                self.bank_added.emit(True, message)
                logger.info(message)
            else:
                message = "خطا در افزودن بانک."
                QMessageBox.critical(self, "خطا", message)
                self.bank_added.emit(False, message)
                
        except Exception as e:
            message = f"خطا در افزودن بانک: {str(e)}"
            logger.error(message)
            QMessageBox.critical(self, "خطا", message)
            self.bank_added.emit(False, message)
    
    def update_bank(self):
        """
        به‌روزرسانی بانک انتخابی
        """
        if not self.selected_bank_id:
            QMessageBox.warning(self, "هشدار", "لطفاً ابتدا بانکی را انتخاب کنید.")
            return
        
        bank_name = self.bank_name_edit.text().strip()
        bank_code = self.bank_code_edit.text().strip() or None
        
        if not bank_name:
            QMessageBox.warning(self, "هشدار", "نام بانک الزامی است.")
            return
        
        try:
            success = self.db_manager.update_bank(self.selected_bank_id, bank_name, bank_code)
            
            if success:
                message = f"بانک '{bank_name}' با موفقیت به‌روزرسانی شد."
                QMessageBox.information(self, "موفقیت", message)
                self.clear_form()
                self.load_banks()
                self.bank_updated.emit(True, message)
                logger.info(message)
            else:
                message = "خطا در به‌روزرسانی بانک."
                QMessageBox.critical(self, "خطا", message)
                self.bank_updated.emit(False, message)
                
        except Exception as e:
            message = f"خطا در به‌روزرسانی بانک: {str(e)}"
            logger.error(message)
            QMessageBox.critical(self, "خطا", message)
            self.bank_updated.emit(False, message)
    
    def delete_bank(self):
        """
        حذف بانک انتخابی
        """
        if not self.selected_bank_id:
            QMessageBox.warning(self, "هشدار", "لطفاً ابتدا بانکی را انتخاب کنید.")
            return
        
        # تأیید حذف
        current_row = self.banks_table.currentRow()
        bank_name = self.banks_table.item(current_row, 1).text()
        
        reply = QMessageBox.question(
            self, "تأیید حذف", 
            f"آیا مطمئن هستید که می‌خواهید بانک '{bank_name}' را حذف کنید؟\n\n"
            "توجه: اگر تراکنش‌هایی مرتبط با این بانک وجود داشته باشد، حذف امکان‌پذیر نخواهد بود.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply != QMessageBox.Yes:
            return
        
        try:
            success = self.db_manager.delete_bank(self.selected_bank_id)
            
            if success:
                message = f"بانک '{bank_name}' با موفقیت حذف شد."
                QMessageBox.information(self, "موفقیت", message)
                self.clear_form()
                self.load_banks()
                self.bank_deleted.emit(True, message)
                logger.info(message)
            else:
                message = "نمی‌توان بانک را حذف کرد. احتمالاً تراکنش‌هایی مرتبط با این بانک وجود دارد."
                QMessageBox.warning(self, "هشدار", message)
                self.bank_deleted.emit(False, message)
                
        except Exception as e:
            message = f"خطا در حذف بانک: {str(e)}"
            logger.error(message)
            QMessageBox.critical(self, "خطا", message)
            self.bank_deleted.emit(False, message)
    
    def on_bank_selected(self):
        """
        رویداد انتخاب بانک از جدول
        """
        current_row = self.banks_table.currentRow()
        
        if current_row >= 0:
            # دریافت اطلاعات بانک انتخابی
            self.selected_bank_id = int(self.banks_table.item(current_row, 0).text())
            bank_name = self.banks_table.item(current_row, 1).text()
            bank_code = self.banks_table.item(current_row, 2).text()
            
            # پر کردن فرم
            self.bank_name_edit.setText(bank_name)
            self.bank_code_edit.setText(bank_code)
            
            # فعال کردن دکمه‌های ویرایش و حذف
            self.update_button.setEnabled(True)
            self.delete_button.setEnabled(True)
        else:
            self.clear_form()
    
    def clear_form(self):
        """
        پاک کردن فرم
        """
        self.bank_name_edit.clear()
        self.bank_code_edit.clear()
        self.selected_bank_id = None
        
        # غیرفعال کردن دکمه‌های ویرایش و حذف
        self.update_button.setEnabled(False)
        self.delete_button.setEnabled(False)
        
        # پاک کردن انتخاب جدول
        self.banks_table.clearSelection()
    
    def get_all_banks(self) -> List[Dict[str, Any]]:
        """
        دریافت لیست تمام بانک‌ها
        
        خروجی:
            لیست بانک‌ها
        """
        try:
            return self.db_manager.get_all_banks()
        except Exception as e:
            logger.error(f"خطا در دریافت لیست بانک‌ها: {str(e)}")
            return []