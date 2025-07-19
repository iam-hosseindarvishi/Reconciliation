#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
تب گزارش‌گیری
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QComboBox,
    QTableView, QHeaderView, QMessageBox, QGroupBox, QFileDialog, QFormLayout
)
from PySide6.QtCore import Qt

from modules.database_manager import DatabaseManager
from modules.report_generator import ReportGenerator
from modules.logger import get_logger
from ui.widgets import LogTextEdit, DataTableModel

# ایجاد شیء لاگر
logger = get_logger(__name__)


class ReportTab(QWidget):
    """
    تب گزارش‌گیری
    """
    
    def __init__(self, parent=None):
        """
        مقداردهی اولیه کلاس ReportTab
        
        پارامترها:
            db_manager: نمونه‌ای از کلاس DatabaseManager
            parent: ویجت والد
        """
        super().__init__(parent)
        self.db_manager = DatabaseManager()
        self.report_generator = ReportGenerator()
        
        # راه‌اندازی رابط کاربری
        self.init_ui()
    
    def init_ui(self):
        """
        راه‌اندازی رابط کاربری
        """
        layout = QVBoxLayout()
        
        # گروه انتخاب نوع گزارش
        report_group = QGroupBox("انتخاب نوع گزارش")
        report_layout = QFormLayout()
        
        # کومبوباکس نوع گزارش
        self.report_type_combo = QComboBox()
        self.report_type_combo.addItems([
            "مغایرت‌های بانک",
            "مغایرت‌های پوز",
            "مغایرت‌های حسابداری",
            "تراکنش‌های تطبیق داده شده",
            "خلاصه وضعیت مغایرت‌گیری"
        ])
        self.report_type_combo.currentIndexChanged.connect(self.on_report_type_changed)
        report_layout.addRow("نوع گزارش:", self.report_type_combo)
        
        report_group.setLayout(report_layout)
        layout.addWidget(report_group)
        
        # دکمه‌های نمایش و خروجی
        buttons_layout = QHBoxLayout()
        
        self.show_report_button = QPushButton("نمایش گزارش")
        self.show_report_button.clicked.connect(self.show_report)
        buttons_layout.addWidget(self.show_report_button)
        
        self.export_excel_button = QPushButton("خروجی اکسل")
        self.export_excel_button.clicked.connect(self.export_to_excel)
        buttons_layout.addWidget(self.export_excel_button)
        
        self.export_pdf_button = QPushButton("خروجی PDF")
        self.export_pdf_button.clicked.connect(self.export_to_pdf)
        buttons_layout.addWidget(self.export_pdf_button)
        
        layout.addLayout(buttons_layout)
        
        # جدول نمایش گزارش
        self.report_table = QTableView()
        self.report_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        layout.addWidget(self.report_table)
        
        # ویجت لاگ
        self.log_text = LogTextEdit()
        layout.addWidget(self.log_text)
        
        self.setLayout(layout)
    
    def on_report_type_changed(self, index=None):
        """
        تغییر نوع گزارش
        
        پارامترها:
            index: شاخص انتخاب شده (استفاده نمی‌شود)
        """
        # پاک کردن جدول گزارش
        self.report_table.setModel(None)
    
    def show_report(self):
        """
        نمایش گزارش
        """
        try:
            report_type = self.report_type_combo.currentText()
            self.log_text.append_log(f"در حال بارگذاری گزارش: {report_type}", "blue")
            
            if report_type == "مغایرت‌های بانک":
                data = self.db_manager.get_unreconciled_bank_transactions()
                headers = ["تاریخ", "مبلغ واریز", "مبلغ برداشت", "توضیحات", "نوع تراکنش", "شناسه پیگیری"]
            
            elif report_type == "مغایرت‌های پوز":
                data = self.db_manager.get_unreconciled_pos_transactions()
                headers = ["تاریخ", "ساعت", "مبلغ", "شماره کارت", "شناسه ترمینال", "شماره پیگیری"]
            
            elif report_type == "مغایرت‌های حسابداری":
                data = self.db_manager.get_unreconciled_accounting_entries()
                headers = ["نوع", "شماره", "بدهکار", "بستانکار", "تاریخ سررسید", "توضیحات"]
            
            elif report_type == "تراکنش‌های تطبیق داده شده":
                data = self.db_manager.get_reconciled_transactions()
                headers = ["نوع رکورد 1", "شناسه رکورد 1", "نوع رکورد 2", "شناسه رکورد 2", "تاریخ تطبیق", "روش تطبیق"]
            
            elif report_type == "خلاصه وضعیت مغایرت‌گیری":
                data = self.db_manager.get_reconciliation_summary_data()
                headers = ["نوع رکورد", "تعداد کل", "تطبیق داده شده", "مغایرت‌ها", "درصد تطبیق"]
            
            else:
                self.log_text.append_log("نوع گزارش نامعتبر است.", "red")
                return
            
            if data:
                # تعیین ترتیب کلیدهای دیتابیس بر اساس نوع گزارش
                if report_type == "مغایرت‌های بانک":
                    db_keys = ['Date', 'Deposit_Amount', 'Withdrawal_Amount', 'Description_Bank', 'Transaction_Type', 'Shaparak_Deposit_Tracking_ID']
                elif report_type == "مغایرت‌های پوز":
                    db_keys = ['Transaction_Date', 'Transaction_Time', 'Transaction_Amount', 'Card_Number', 'Terminal_ID', 'POS_Tracking_Number']
                elif report_type == "مغایرت‌های حسابداری":
                    db_keys = ['Entry_Type_Acc', 'Account_Reference_Suffix', 'Debit', 'Credit', 'Due_Date', 'Description_Notes_Acc']
                elif report_type == "تراکنش‌های تطبیق داده شده":
                    db_keys = ['record_type_1', 'record_id_1', 'record_type_2', 'record_id_2', 'reconciliation_date', 'reconciliation_method']
                elif report_type == "خلاصه وضعیت مغایرت‌گیری":
                    db_keys = ['record_type', 'total_count', 'reconciled_count', 'unreconciled_count', 'reconciliation_percentage']
                else:
                    db_keys = list(data[0].keys()) if data else []
                
                self.report_table.setModel(DataTableModel(data, headers, db_keys))
                self.log_text.append_log(f"گزارش با موفقیت بارگذاری شد. تعداد رکوردها: {len(data)}", "green")
            else:
                self.log_text.append_log("داده‌ای برای نمایش وجود ندارد.", "yellow")
                self.report_table.setModel(DataTableModel([], headers, []))
            
        except Exception as e:
            logger.error(f"خطا در نمایش گزارش: {str(e)}")
            self.log_text.append_log(f"خطا در نمایش گزارش: {str(e)}", "red")
            QMessageBox.critical(self, "خطا", f"خطا در نمایش گزارش: {str(e)}")
    
    def export_to_excel(self):
        """
        خروجی گزارش به فرمت اکسل
        """
        try:
            # بررسی وجود داده در جدول
            if not self.report_table.model() or self.report_table.model().rowCount() == 0:
                QMessageBox.warning(self, "هشدار", "داده‌ای برای خروجی وجود ندارد. ابتدا گزارش را نمایش دهید.")
                return
            
            # دریافت مسیر فایل خروجی
            file_path, _ = QFileDialog.getSaveFileName(
                self, "ذخیره فایل اکسل", "", "Excel Files (*.xlsx)"
            )
            
            if not file_path:
                return
            
            # اضافه کردن پسوند .xlsx در صورت نیاز
            if not file_path.endswith(".xlsx"):
                file_path += ".xlsx"
            
            # دریافت نوع گزارش
            report_type = self.report_type_combo.currentText()
            
            # استخراج داده‌ها و هدرها از مدل جدول
            model = self.report_table.model()
            data = model._data
            headers = model._headers
            
            # ایجاد خروجی اکسل
            self.report_generator.export_to_excel(data, headers, file_path, report_type)
            
            self.log_text.append_log(f"گزارش با موفقیت در فایل {file_path} ذخیره شد.", "green")
            QMessageBox.information(self, "موفقیت", f"گزارش با موفقیت در فایل {file_path} ذخیره شد.")
            
        except Exception as e:
            logger.error(f"خطا در خروجی اکسل: {str(e)}")
            self.log_text.append_log(f"خطا در خروجی اکسل: {str(e)}", "red")
            QMessageBox.critical(self, "خطا", f"خطا در خروجی اکسل: {str(e)}")
    
    def export_to_pdf(self):
        """
        خروجی گزارش به فرمت PDF
        """
        try:
            # بررسی وجود داده در جدول
            if not self.report_table.model() or self.report_table.model().rowCount() == 0:
                QMessageBox.warning(self, "هشدار", "داده‌ای برای خروجی وجود ندارد. ابتدا گزارش را نمایش دهید.")
                return
            
            # دریافت مسیر فایل خروجی
            file_path, _ = QFileDialog.getSaveFileName(
                self, "ذخیره فایل PDF", "", "PDF Files (*.pdf)"
            )
            
            if not file_path:
                return
            
            # اضافه کردن پسوند .pdf در صورت نیاز
            if not file_path.endswith(".pdf"):
                file_path += ".pdf"
            
            # دریافت نوع گزارش
            report_type = self.report_type_combo.currentText()
            
            # استخراج داده‌ها و هدرها از مدل جدول
            model = self.report_table.model()
            data = model._data
            headers = model._headers
            
            # ایجاد خروجی PDF
            self.report_generator.export_to_pdf(data, headers, file_path, report_type)
            
            self.log_text.append_log(f"گزارش با موفقیت در فایل {file_path} ذخیره شد.", "green")
            QMessageBox.information(self, "موفقیت", f"گزارش با موفقیت در فایل {file_path} ذخیره شد.")
            
        except Exception as e:
            logger.error(f"خطا در خروجی PDF: {str(e)}")
            self.log_text.append_log(f"خطا در خروجی PDF: {str(e)}", "red")
            QMessageBox.critical(self, "خطا", f"خطا در خروجی PDF: {str(e)}")
    
    def show_summary_report(self):
        """
        نمایش گزارش خلاصه وضعیت مغایرت‌گیری
        این متد برای نمایش خودکار گزارش خلاصه پس از اتمام مغایرت‌گیری استفاده می‌شود
        """
        try:
            # انتخاب گزارش خلاصه در کومبوباکس
            summary_index = self.report_type_combo.findText("خلاصه وضعیت مغایرت‌گیری")
            if summary_index >= 0:
                self.report_type_combo.setCurrentIndex(summary_index)
            
            # نمایش گزارش
            self.show_report()
            
            # ثبت لاگ
            self.log_text.append_log("گزارش خلاصه وضعیت مغایرت‌گیری نمایش داده شد.", "blue")
            
        except Exception as e:
            logger.error(f"خطا در نمایش گزارش خلاصه: {str(e)}")
            self.log_text.append_log(f"خطا در نمایش گزارش خلاصه: {str(e)}", "red")