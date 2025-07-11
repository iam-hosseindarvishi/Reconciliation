#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
کلاس پنجره اصلی برنامه
"""

import os
import sys
from datetime import datetime

from PySide6.QtWidgets import QMainWindow, QTabWidget, QVBoxLayout, QWidget, QMessageBox
from PySide6.QtCore import Qt, QSettings

# افزودن مسیر پروژه به مسیرهای پایتون
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# واردسازی ماژول‌های برنامه
from modules.database_manager import DatabaseManager
from modules.data_loader import DataLoader
from modules.reconciliation_logic import ReconciliationEngine
from modules.report_generator import ReportGenerator
from modules.logger import get_logger
from ui.ui_elements import DataImportTab, ReconciliationTab, ReportsTab

# تنظیم لاگر
logger = get_logger(__name__)

class MainWindow(QMainWindow):
    """
    کلاس پنجره اصلی برنامه
    """
    def __init__(self):
        super().__init__()
        
        # تنظیم عنوان و ابعاد پنجره
        self.setWindowTitle("سیستم مغایرت‌گیری بانک، پوز و حسابداری")
        self.setMinimumSize(1000, 700)
        
        # تنظیم مدیر پایگاه داده
        self.db_manager = DatabaseManager()
        
        # تنظیم بارگذار داده
        self.data_loader = DataLoader(self.db_manager)
        
        # تنظیم موتور مغایرت‌گیری
        self.reconciliation_engine = ReconciliationEngine(self.db_manager)
        
        # تنظیم تولیدکننده گزارش
        self.report_generator = ReportGenerator(self.db_manager)
        
        # تنظیم تنظیمات برنامه
        self.settings = QSettings("ReconciliationApp", "Settings")
        
        # راه‌اندازی رابط کاربری
        self.setup_ui()
        
        # بارگذاری تنظیمات ذخیره شده
        self.load_settings()
        
        logger.info("پنجره اصلی برنامه با موفقیت راه‌اندازی شد.")
    
    def setup_ui(self):
        """
        راه‌اندازی رابط کاربری
        """
        # ویجت مرکزی
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # چیدمان اصلی
        main_layout = QVBoxLayout(central_widget)
        
        # تب‌ها
        self.tab_widget = QTabWidget()
        self.tab_widget.setTabPosition(QTabWidget.North)
        self.tab_widget.setTabShape(QTabWidget.Rounded)
        
        # تب ورود داده
        self.data_import_tab = DataImportTab(self.data_loader, self.db_manager)
        self.tab_widget.addTab(self.data_import_tab, "ورود داده")
        
        # تب مغایرت‌گیری
        self.reconciliation_tab = ReconciliationTab(self.db_manager, self.reconciliation_engine)
        self.tab_widget.addTab(self.reconciliation_tab, "مغایرت‌گیری")
        
        # تب گزارش‌ها
        self.reports_tab = ReportsTab(self.db_manager, self.report_generator)
        self.tab_widget.addTab(self.reports_tab, "گزارش‌ها")
        
        # افزودن تب‌ها به چیدمان اصلی
        main_layout.addWidget(self.tab_widget)
        
        # اتصال سیگنال‌ها
        self.connect_signals()
    
    def connect_signals(self):
        """
        اتصال سیگنال‌های برنامه
        """
        # اتصال سیگنال تغییر تب
        self.tab_widget.currentChanged.connect(self.on_tab_changed)
        
        # اتصال سیگنال‌های بین تب‌ها
        self.data_import_tab.import_completed.connect(self.on_import_completed)
        """
        اتصال سیگنال‌های برنامه
        """
        # اتصال سیگنال تغییر تب
        self.tab_widget.currentChanged.connect(self.on_tab_changed)
        
        # اتصال سیگنال‌های بین تب‌ها
        self.data_import_tab.import_completed.connect(self.on_import_completed)
    
    def on_tab_changed(self, index):
        """
        رویداد تغییر تب
        """
        # بروزرسانی داده‌ها در صورت نیاز
        if index == 1:  # تب مغایرت‌گیری
            self.reconciliation_tab.refresh_data()
        elif index == 2:  # تب گزارش‌ها
            self.reports_tab.load_recent_reports()
    
    def on_import_completed(self):
        """
        رویداد تکمیل ورود داده
        """
        # نمایش پیام موفقیت
        QMessageBox.information(self, "ورود داده", "ورود داده با موفقیت انجام شد.")
        
        # تغییر به تب مغایرت‌گیری
        self.tab_widget.setCurrentIndex(1)
    
    def load_settings(self):
        """
        بارگذاری تنظیمات ذخیره شده
        """
        # بارگذاری اندازه و موقعیت پنجره
        if self.settings.contains("window_geometry"):
            self.restoreGeometry(self.settings.value("window_geometry"))
        
        # بارگذاری حالت پنجره
        if self.settings.contains("window_state"):
            self.restoreState(self.settings.value("window_state"))
        
        # بارگذاری تب فعال
        if self.settings.contains("active_tab"):
            self.tab_widget.setCurrentIndex(int(self.settings.value("active_tab")))
        
        # بارگذاری مسیرهای پیش‌فرض
        if self.settings.contains("default_bank_path"):
            self.data_import_tab.default_bank_path = self.settings.value("default_bank_path")
        
        if self.settings.contains("default_pos_path"):
            self.data_import_tab.default_pos_path = self.settings.value("default_pos_path")
        
        if self.settings.contains("default_accounting_path"):
            self.data_import_tab.default_accounting_path = self.settings.value("default_accounting_path")
    
    def save_settings(self):
        """
        ذخیره تنظیمات برنامه
        """
        # ذخیره اندازه و موقعیت پنجره
        self.settings.setValue("window_geometry", self.saveGeometry())
        
        # ذخیره حالت پنجره
        self.settings.setValue("window_state", self.saveState())
        
        # ذخیره تب فعال
        self.settings.setValue("active_tab", self.tab_widget.currentIndex())
        
        # ذخیره مسیرهای پیش‌فرض
        self.settings.setValue("default_bank_path", self.data_import_tab.default_bank_path)
        self.settings.setValue("default_pos_path", self.data_import_tab.default_pos_path)
        self.settings.setValue("default_accounting_path", self.data_import_tab.default_accounting_path)
    
    def closeEvent(self, event):
        """
        رویداد بستن پنجره
        """
        # ذخیره تنظیمات
        self.save_settings()
        
        # بستن اتصال پایگاه داده
        self.db_manager.disconnect()
        
        # ثبت لاگ
        logger.info("برنامه بسته شد.")
        
        # پذیرش رویداد بستن
        event.accept()