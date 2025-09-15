import os
import logging
import threading
import ttkbootstrap as ttk
from ttkbootstrap.constants import *
from tkinter import StringVar, BooleanVar, messagebox
from ttkbootstrap.scrolled import ScrolledText
from config.settings import (
    DATA_DIR, DEFAULT_FONT, DEFAULT_FONT_SIZE,
    HEADER_FONT_SIZE, BUTTON_FONT_SIZE
)
from ui.components.dashboard import (
    StatisticsProvider,
    ChartManager,
    DashboardOperations
)

# کلاس برای نمایش لاگ‌ها در UI
class UIHandler(logging.Handler):
    def __init__(self, text_widget):
        super().__init__()
        self.text_widget = text_widget
        
    def emit(self, record):
        msg = self.format(record) + '\n'
        # ScrolledText در ttkbootstrap از state پشتیبانی نمی‌کند
        self.text_widget.insert('end', msg)
        self.text_widget.see('end')

class DashboardTab(ttk.Frame):
    def __init__(self, parent):
        super().__init__(parent)
        self.setup_logging()
        
        # متغیرهای مورد نیاز
        self.status_var = StringVar(value="آماده...")
        
        # ایجاد کامپوننت‌های مدولار
        self.statistics_provider = StatisticsProvider(self.logger)
        self.chart_manager = ChartManager(self.logger)
        self.dashboard_operations = DashboardOperations(
            logger=self.logger,
            status_callback=self._update_status
        )
        
        # تنظیم callback برای به‌روزرسانی آمار
        self.dashboard_operations.set_statistics_refresh_callback(self.load_statistics)
        
        # ایجاد ویجت‌ها
        self.create_widgets()
        
        # بارگذاری اطلاعات آماری
        self.load_statistics()
        
    def setup_logging(self):
        """راه‌اندازی سیستم لاگینگ"""
        os.makedirs(DATA_DIR, exist_ok=True)
        
        # تنظیمات کلی لاگر
        self.logger = logging.getLogger('dashboard.tab')
        self.logger.setLevel(logging.INFO)
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        
        # لاگر برای فایل خطاها
        error_handler = logging.FileHandler(os.path.join(DATA_DIR, 'dashboard_error.txt'), encoding='utf-8')
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(formatter)
        
        # لاگر برای فایل لاگ عمومی
        file_handler = logging.FileHandler(os.path.join(DATA_DIR, 'dashboard_log.txt'), encoding='utf-8')
        file_handler.setLevel(logging.INFO)
        file_handler.setFormatter(formatter)
        
        # لاگر برای کنسول با پشتیبانی از UTF-8
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(formatter)
        
        self.logger.addHandler(error_handler)
        self.logger.addHandler(file_handler)
        self.logger.addHandler(console_handler)
        # UI handler will be added after creating log_text widget

    def create_widgets(self):
        PADX = 8
        PADY = 8

        # تنظیم فونت‌ها
        self.default_font = (DEFAULT_FONT, DEFAULT_FONT_SIZE, 'bold')
        self.header_font = (DEFAULT_FONT, HEADER_FONT_SIZE, 'bold')
        self.button_font = (DEFAULT_FONT, BUTTON_FONT_SIZE, 'bold')
        self.log_font = (DEFAULT_FONT, DEFAULT_FONT_SIZE - 1, 'bold')  # کمی کوچکتر برای لاگ‌ها

        # تنظیم استایل‌ها
        style = ttk.Style()
        style.configure('Header.TLabelframe', font=self.header_font)
        style.configure('Header.TLabelframe.Label', font=self.header_font)
        style.configure('Default.TLabel', font=self.default_font)
        style.configure('Default.TEntry', font=self.default_font)
        style.configure('Bold.TButton', font=self.button_font)
        style.configure('Danger.TButton', font=self.button_font, foreground='red')

        main_frame = ttk.Frame(self)
        main_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        # === بخش آمار بانک‌ها ===
        bank_stats_frame = ttk.LabelFrame(main_frame, text="آمار بانک‌ها", style='Header.TLabelframe')
        bank_stats_frame.pack(fill="x", pady=5)
        
        # ایجاد فریم برای نمایش آمار و نمودار
        bank_content_frame = ttk.Frame(bank_stats_frame)
        bank_content_frame.pack(fill="both", expand=True, padx=PADX, pady=PADY)
        
        # فریم برای نمایش آمار متنی
        self.bank_text_frame = ttk.Frame(bank_content_frame)
        self.bank_text_frame.pack(side="right", fill="y", padx=PADX)
        
        # فریم برای نمایش نمودار
        self.bank_chart_frame = ttk.Frame(bank_content_frame)
        self.bank_chart_frame.pack(side="left", fill="both", expand=True, padx=PADX)
        
        # === بخش آمار حسابداری ===
        accounting_stats_frame = ttk.LabelFrame(main_frame, text="آمار حسابداری", style='Header.TLabelframe')
        accounting_stats_frame.pack(fill="x", pady=5)
        
        # ایجاد فریم برای نمایش آمار و نمودار
        accounting_content_frame = ttk.Frame(accounting_stats_frame)
        accounting_content_frame.pack(fill="both", expand=True, padx=PADX, pady=PADY)
        
        # فریم برای نمایش آمار متنی
        self.accounting_text_frame = ttk.Frame(accounting_content_frame)
        self.accounting_text_frame.pack(side="right", fill="y", padx=PADX)
        
        # فریم برای نمایش نمودار
        self.accounting_chart_frame = ttk.Frame(accounting_content_frame)
        self.accounting_chart_frame.pack(side="left", fill="both", expand=True, padx=PADX)
        
        # === بخش آمار پوز ===
        pos_stats_frame = ttk.LabelFrame(main_frame, text="آمار پوز", style='Header.TLabelframe')
        pos_stats_frame.pack(fill="x", pady=5)
        
        # ایجاد فریم برای نمایش آمار و نمودار
        pos_content_frame = ttk.Frame(pos_stats_frame)
        pos_content_frame.pack(fill="both", expand=True, padx=PADX, pady=PADY)
        
        # فریم برای نمایش آمار متنی
        self.pos_text_frame = ttk.Frame(pos_content_frame)
        self.pos_text_frame.pack(side="right", fill="y", padx=PADX)
        
        # فریم برای نمایش نمودار
        self.pos_chart_frame = ttk.Frame(pos_content_frame)
        self.pos_chart_frame.pack(side="left", fill="both", expand=True, padx=PADX)
        
        # === بخش دکمه‌های عملیاتی ===
        actions_frame = ttk.LabelFrame(main_frame, text="عملیات", style='Header.TLabelframe')
        actions_frame.pack(fill="x", pady=5)
        
        buttons_frame = ttk.Frame(actions_frame)
        buttons_frame.pack(fill="x", padx=PADX, pady=PADY)
        
        delete_all_button = ttk.Button(
            buttons_frame, text="حذف کل رکوردها", style='Danger.TButton',
            command=self.dashboard_operations.delete_all_records
        )
        delete_all_button.pack(side="right", padx=PADX)
        
        delete_reconciled_button = ttk.Button(
            buttons_frame, text="حذف رکوردهای مغایرت گیری شده", style='Danger.TButton',
            command=self.dashboard_operations.delete_reconciled_records
        )
        delete_reconciled_button.pack(side="right", padx=PADX)
        
        print_report_button = ttk.Button(
            buttons_frame, text="چاپ گزارش", style='Bold.TButton',
            command=self.print_report
        )
        print_report_button.pack(side="right", padx=PADX)
        
        # بخش لاگ‌ها
        log_frame = ttk.LabelFrame(main_frame, text="گزارش عملیات", style='Header.TLabelframe')
        log_frame.pack(fill="x", pady=5)
        
        self.log_text = ScrolledText(log_frame, height=5, font=self.log_font)
        self.log_text.pack(fill="both", expand=True, padx=PADX, pady=PADY)
        
        # اضافه کردن UI handler به لاگر
        ui_handler = UIHandler(self.log_text)
        ui_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
        ui_handler.setLevel(logging.INFO)
        self.logger.addHandler(ui_handler)
        
        # نوار وضعیت
        status_frame = ttk.Frame(main_frame)
        status_frame.pack(fill="x", pady=5)
        
        ttk.Label(status_frame, textvariable=self.status_var, style='Default.TLabel').pack(side="right")
    
    def _update_status(self, message):
        """به‌روزرسانی نوار وضعیت"""
        self.status_var.set(message)
    
    def load_statistics(self):
        """بارگذاری آمار و اطلاعات"""
        try:
            self.logger.info("در حال بارگذاری آمار...")
            self.status_var.set("در حال بارگذاری آمار...")
            
            # اجرای در یک ترد جداگانه برای جلوگیری از انسداد UI
            threading.Thread(target=self._load_statistics_thread, daemon=True).start()
        except Exception as e:
            self.logger.error(f"خطا در بارگذاری آمار: {str(e)}")
            self.status_var.set(f"خطا در بارگذاری آمار: {str(e)}")
    
    def _load_statistics_thread(self):
        """بارگذاری آمار در یک ترد جداگانه"""
        try:
            # دریافت آمار بانک‌ها
            bank_stats = self.statistics_provider.get_bank_statistics()
            # استفاده از after برای اجرای به‌روزرسانی UI در حلقه اصلی
            self.after(100, lambda: self._update_bank_statistics_ui(bank_stats))
            
            # دریافت آمار حسابداری
            accounting_stats = self.statistics_provider.get_accounting_statistics()
            self.after(200, lambda: self._update_accounting_statistics_ui(accounting_stats))
            
            # دریافت آمار پوز
            pos_stats = self.statistics_provider.get_pos_statistics()
            self.after(300, lambda: self._update_pos_statistics_ui(pos_stats))
            
            self.after(400, lambda: self.status_var.set("آمار با موفقیت بارگذاری شد"))
            self.logger.info("آمار با موفقیت بارگذاری شد")
        except Exception as e:
            self.logger.error(f"خطا در بارگذاری آمار: {str(e)}")
            self.after(0, lambda e=e: self.status_var.set(f"خطا در بارگذاری آمار: {str(e)}"))
    
    
    def _update_bank_statistics_ui(self, bank_stats):
        """به‌روزرسانی UI با آمار بانک‌ها"""
        try:
            # پاک کردن محتوای قبلی
            for widget in self.bank_text_frame.winfo_children():
                widget.destroy()
            
            for widget in self.bank_chart_frame.winfo_children():
                widget.destroy()
            
            # نمایش آمار متنی
            for i, stat in enumerate(bank_stats):
                bank_frame = ttk.Frame(self.bank_text_frame)
                bank_frame.pack(fill="x", pady=5)
                
                ttk.Label(
                    bank_frame, 
                    text=f"بانک {stat['bank_name']}:", 
                    style='Default.TLabel'
                ).pack(anchor="w")
                
                ttk.Label(
                    bank_frame, 
                    text=f"تعداد کل: {stat['total_records']} | مغایرت‌گیری شده: {stat['reconciled_records']} | مغایرت‌گیری نشده: {stat['unreconciled_records']}", 
                    style='Default.TLabel'
                ).pack(anchor="w")
            
            # ایجاد نمودار
            if bank_stats:
                # استفاده از chart manager برای ایجاد نمودار
                self.chart_manager.create_reconciliation_chart(
                    bank_stats, self.bank_chart_frame, "bank"
                )
        except Exception as e:
            self.logger.error(f"خطا در به‌روزرسانی UI آمار بانک‌ها: {str(e)}")
            
    
    
    def _update_accounting_statistics_ui(self, accounting_stats):
        """به‌روزرسانی UI با آمار حسابداری"""
        try:
            # پاک کردن محتوای قبلی
            for widget in self.accounting_text_frame.winfo_children():
                widget.destroy()
            
            for widget in self.accounting_chart_frame.winfo_children():
                widget.destroy()
            
            # نمایش آمار متنی
            for i, stat in enumerate(accounting_stats):
                accounting_frame = ttk.Frame(self.accounting_text_frame)
                accounting_frame.pack(fill="x", pady=5)
                
                ttk.Label(
                    accounting_frame, 
                    text=f"بانک {stat['bank_name']}:", 
                    style='Default.TLabel'
                ).pack(anchor="w")
                
                ttk.Label(
                    accounting_frame, 
                    text=f"تعداد کل: {stat['total_records']} | مغایرت‌گیری شده: {stat['reconciled_records']} | مغایرت‌گیری نشده: {stat['unreconciled_records']}", 
                    style='Default.TLabel'
                ).pack(anchor="w")
            
            # ایجاد نمودار
            if accounting_stats:
                # استفاده از chart manager برای ایجاد نمودار
                self.chart_manager.create_reconciliation_chart(
                    accounting_stats, self.accounting_chart_frame, "accounting"
                )
        except Exception as e:
            self.logger.error(f"خطا در به‌روزرسانی UI آمار حسابداری: {str(e)}")
            
    
    
    def _update_pos_statistics_ui(self, pos_stats):
        """به‌روزرسانی UI با آمار پوز"""
        try:
            # پاک کردن محتوای قبلی
            for widget in self.pos_text_frame.winfo_children():
                widget.destroy()
            
            for widget in self.pos_chart_frame.winfo_children():
                widget.destroy()
            
            # نمایش آمار متنی
            for i, stat in enumerate(pos_stats):
                pos_frame = ttk.Frame(self.pos_text_frame)
                pos_frame.pack(fill="x", pady=5)
                
                ttk.Label(
                    pos_frame, 
                    text=f"بانک {stat['bank_name']}:", 
                    style='Default.TLabel'
                ).pack(anchor="w")
                
                ttk.Label(
                    pos_frame, 
                    text=f"تعداد کل: {stat['total_records']} | مغایرت‌گیری شده: {stat['reconciled_records']} | مغایرت‌گیری نشده: {stat['unreconciled_records']}", 
                    style='Default.TLabel'
                ).pack(anchor="w")
            
            # ایجاد نمودار
            if pos_stats:
                # استفاده از chart manager برای ایجاد نمودار
                self.chart_manager.create_reconciliation_chart(
                    pos_stats, self.pos_chart_frame, "pos"
                )
        except Exception as e:
            self.logger.error(f"خطا در به‌روزرسانی UI آمار پوز: {str(e)}")
    
    
    
    
    
    def print_report(self):
        """چاپ گزارش آماری"""
        try:
            # دریافت آمار
            bank_stats = self.statistics_provider.get_bank_statistics()
            accounting_stats = self.statistics_provider.get_accounting_statistics()
            pos_stats = self.statistics_provider.get_pos_statistics()
            
            # استفاده از dashboard operations برای تولید گزارش
            self.dashboard_operations.generate_statistical_report(
                bank_stats, accounting_stats, pos_stats
            )
            
        except Exception as e:
            self.logger.error(f"خطا در چاپ گزارش: {str(e)}")
            self.status_var.set(f"خطا در چاپ گزارش: {str(e)}")
            messagebox.showerror("خطا", f"خطا در چاپ گزارش: {str(e)}")
