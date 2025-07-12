#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
کلاس کارگر برای واردسازی داده‌ها در پس‌زمینه
"""

import os
from PySide6.QtCore import QThread, Signal

from modules.data_loader import DataLoader
from modules.database_manager import DatabaseManager
from modules.logger import get_logger

# ایجاد شیء لاگر
logger = get_logger(__name__)


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
                
                bank_data = self.data_loader.load_bank_file(self.bank_file)
                if self.bank_file and not bank_data.empty:
                    self.progress_updated.emit(30, "در حال ذخیره داده‌های بانک در پایگاه داده...")
                    self.db_manager.insert_bank_transactions(bank_data)
                    self.log_message.emit(f"{len(bank_data)} رکورد بانکی با موفقیت بارگذاری شد.", "green")
                else:
                    self.log_message.emit("خطا در بارگذاری داده‌های بانک.", "red")
            
            # واردسازی داده‌های پوز
            if self.pos_folder:
                self.progress_updated.emit(40, "در حال بارگذاری داده‌های پوز...")
                self.log_message.emit(f"بارگذاری داده‌های پوز از پوشه {os.path.basename(self.pos_folder)}", "blue")
                
                pos_data = self.data_loader.load_pos_files(self.pos_folder)
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
                
                accounting_data = self.data_loader.load_accounting_file(self.accounting_file)
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