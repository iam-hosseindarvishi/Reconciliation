import os
import logging
import threading
import sqlite3
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import ttkbootstrap as ttk
from ttkbootstrap.constants import *
from tkinter import StringVar, BooleanVar, messagebox
from ttkbootstrap.scrolled import ScrolledText
import arabic_reshaper
from bidi.algorithm import get_display
from config.settings import (
    DB_PATH, DATA_DIR, DEFAULT_FONT, DEFAULT_FONT_SIZE,
    HEADER_FONT_SIZE, BUTTON_FONT_SIZE
)
from database.banks_repository import get_all_banks

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
            command=self.delete_all_records
        )
        delete_all_button.pack(side="right", padx=PADX)
        
        delete_reconciled_button = ttk.Button(
            buttons_frame, text="حذف رکوردهای مغایرت گیری شده", style='Danger.TButton',
            command=self.delete_reconciled_records
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
            bank_stats = self.get_bank_statistics()
            # استفاده از after برای اجرای به‌روزرسانی UI در حلقه اصلی
            self.after(100, lambda: self._update_bank_statistics_ui(bank_stats))
            
            # دریافت آمار حسابداری
            accounting_stats = self.get_accounting_statistics()
            self.after(200, lambda: self._update_accounting_statistics_ui(accounting_stats))
            
            # دریافت آمار پوز
            pos_stats = self.get_pos_statistics()
            self.after(300, lambda: self._update_pos_statistics_ui(pos_stats))
            
            self.after(400, lambda: self.status_var.set("آمار با موفقیت بارگذاری شد"))
            self.logger.info("آمار با موفقیت بارگذاری شد")
        except Exception as e:
            self.logger.error(f"خطا در بارگذاری آمار: {str(e)}")
            self.after(0, lambda e=e: self.status_var.set(f"خطا در بارگذاری آمار: {str(e)}"))
    
    def get_bank_statistics(self):
        """دریافت آمار بانک‌ها"""
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            
            # دریافت لیست بانک‌ها
            banks = get_all_banks()
            
            stats = []
            for bank_id, bank_name in banks:
                # تعداد کل رکوردها
                cursor.execute("SELECT COUNT(*) FROM BankTransactions WHERE bank_id = ?", (bank_id,))
                total_records = cursor.fetchone()[0]
                
                # تعداد رکوردهای مغایرت‌گیری شده
                cursor.execute("SELECT COUNT(*) FROM BankTransactions WHERE bank_id = ? AND is_reconciled = 1", (bank_id,))
                reconciled_records = cursor.fetchone()[0]
                
                # تعداد رکوردهای مغایرت‌گیری نشده
                unreconciled_records = total_records - reconciled_records
                
                # درصد مغایرت‌گیری شده
                reconciled_percentage = 0
                if total_records > 0:
                    reconciled_percentage = (reconciled_records / total_records) * 100
                
                stats.append({
                    "bank_id": bank_id,
                    "bank_name": bank_name,
                    "total_records": total_records,
                    "reconciled_records": reconciled_records,
                    "unreconciled_records": unreconciled_records,
                    "reconciled_percentage": reconciled_percentage
                })
            
            conn.close()
            return stats
        except Exception as e:
            self.logger.error(f"خطا در دریافت آمار بانک‌ها: {str(e)}")
            raise
    
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
                # تمام عملیات matplotlib در حلقه اصلی tkinter
                self._create_bank_chart(bank_stats)
        except Exception as e:
            self.logger.error(f"خطا در به‌روزرسانی UI آمار بانک‌ها: {str(e)}")
            
    def _create_bank_chart(self, bank_stats):
        """ایجاد نمودار بانک‌ها"""
        try:
            fig, ax = plt.subplots(figsize=(6, 4))
            
            # تبدیل نام‌های بانک به فرمت صحیح فارسی با استفاده از arabic-reshaper و bidi
            bank_names_original = [stat['bank_name'] for stat in bank_stats]
            bank_names = [get_display(arabic_reshaper.reshape(name)) for name in bank_names_original]
            reconciled = [stat['reconciled_records'] for stat in bank_stats]
            unreconciled = [stat['unreconciled_records'] for stat in bank_stats]
            
            # تنظیم فونت فارسی برای matplotlib
            import matplotlib.font_manager as fm
            font_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'assets', 'fonts', 'Vazir.ttf')
            if os.path.exists(font_path):
                fm.fontManager.addfont(font_path)
                plt.rcParams['font.family'] = 'Vazir, Tahoma'
            else:
                plt.rcParams['font.family'] = 'Tahoma'
            plt.rcParams['axes.unicode_minus'] = False
            # تنظیم راست به چپ بودن متن
            plt.rcParams['axes.formatter.use_locale'] = True
            plt.rcParams['text.color'] = 'black'
            
            # ایجاد نمودار میله‌ای
            x = range(len(bank_names))
            width = 0.35
            
            # تبدیل برچسب‌ها به فرمت صحیح فارسی
            reshaped_label1 = get_display(arabic_reshaper.reshape('مغایرت‌گیری شده'))
            reshaped_label2 = get_display(arabic_reshaper.reshape('مغایرت‌گیری نشده'))
            
            ax.bar([i - width/2 for i in x], reconciled, width, label=reshaped_label1)
            ax.bar([i + width/2 for i in x], unreconciled, width, label=reshaped_label2)
            
            # تبدیل عنوان‌ها به فرمت صحیح فارسی
            reshaped_ylabel = get_display(arabic_reshaper.reshape('تعداد رکوردها'))
            reshaped_title = get_display(arabic_reshaper.reshape('وضعیت مغایرت‌گیری بانک‌ها'))
            
            ax.set_ylabel(reshaped_ylabel)
            ax.set_title(reshaped_title)
            ax.set_xticks(x)
            ax.set_xticklabels(bank_names)
            ax.legend()
            
            # اضافه کردن نمودار به UI
            canvas = FigureCanvasTkAgg(fig, master=self.bank_chart_frame)
            canvas.draw()
            canvas.get_tk_widget().pack(fill="both", expand=True)
        except Exception as e:
            self.logger.error(f"خطا در ایجاد نمودار بانک‌ها: {str(e)}")
    
    def get_accounting_statistics(self):
        """دریافت آمار حسابداری"""
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            
            # دریافت لیست بانک‌ها
            banks = get_all_banks()
            
            stats = []
            for bank_id, bank_name in banks:
                # تعداد کل رکوردها
                cursor.execute("SELECT COUNT(*) FROM AccountingTransactions WHERE bank_id = ?", (bank_id,))
                total_records = cursor.fetchone()[0]
                
                # تعداد رکوردهای مغایرت‌گیری شده
                cursor.execute("SELECT COUNT(*) FROM AccountingTransactions WHERE bank_id = ? AND is_reconciled = 1", (bank_id,))
                reconciled_records = cursor.fetchone()[0]
                
                # تعداد رکوردهای مغایرت‌گیری نشده
                unreconciled_records = total_records - reconciled_records
                
                # درصد مغایرت‌گیری شده
                reconciled_percentage = 0
                if total_records > 0:
                    reconciled_percentage = (reconciled_records / total_records) * 100
                
                stats.append({
                    "bank_id": bank_id,
                    "bank_name": bank_name,
                    "total_records": total_records,
                    "reconciled_records": reconciled_records,
                    "unreconciled_records": unreconciled_records,
                    "reconciled_percentage": reconciled_percentage
                })
            
            conn.close()
            return stats
        except Exception as e:
            self.logger.error(f"خطا در دریافت آمار حسابداری: {str(e)}")
            raise
    
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
                # تمام عملیات matplotlib در حلقه اصلی tkinter
                self._create_accounting_chart(accounting_stats)
        except Exception as e:
            self.logger.error(f"خطا در به‌روزرسانی UI آمار حسابداری: {str(e)}")
            
    def _create_accounting_chart(self, accounting_stats):
        """ایجاد نمودار حسابداری"""
        try:
            fig, ax = plt.subplots(figsize=(6, 4))
            
            # تبدیل نام‌های بانک به فرمت صحیح فارسی با استفاده از arabic-reshaper و bidi
            bank_names_original = [stat['bank_name'] for stat in accounting_stats]
            bank_names = [get_display(arabic_reshaper.reshape(name)) for name in bank_names_original]
            reconciled = [stat['reconciled_records'] for stat in accounting_stats]
            unreconciled = [stat['unreconciled_records'] for stat in accounting_stats]
            
            # تنظیم فونت فارسی برای matplotlib
            import matplotlib.font_manager as fm
            font_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'assets', 'fonts', 'Vazir.ttf')
            if os.path.exists(font_path):
                fm.fontManager.addfont(font_path)
                plt.rcParams['font.family'] = 'Vazir, Tahoma'
            else:
                plt.rcParams['font.family'] = 'Tahoma'
            plt.rcParams['axes.unicode_minus'] = False
            # تنظیم راست به چپ بودن متن
            plt.rcParams['axes.formatter.use_locale'] = True
            plt.rcParams['text.color'] = 'black'
            
            # ایجاد نمودار میله‌ای
            x = range(len(bank_names))
            width = 0.35
            
            # تبدیل برچسب‌ها به فرمت صحیح فارسی
            reshaped_label1 = get_display(arabic_reshaper.reshape('مغایرت‌گیری شده'))
            reshaped_label2 = get_display(arabic_reshaper.reshape('مغایرت‌گیری نشده'))
            
            ax.bar([i - width/2 for i in x], reconciled, width, label=reshaped_label1)
            ax.bar([i + width/2 for i in x], unreconciled, width, label=reshaped_label2)
            
            # تبدیل عنوان‌ها به فرمت صحیح فارسی
            reshaped_ylabel = get_display(arabic_reshaper.reshape('تعداد رکوردها'))
            reshaped_title = get_display(arabic_reshaper.reshape('وضعیت مغایرت‌گیری حسابداری'))
            
            ax.set_ylabel(reshaped_ylabel)
            ax.set_title(reshaped_title)
            ax.set_xticks(x)
            ax.set_xticklabels(bank_names)
            ax.legend()
            
            # اضافه کردن نمودار به UI
            canvas = FigureCanvasTkAgg(fig, master=self.accounting_chart_frame)
            canvas.draw()
            canvas.get_tk_widget().pack(fill="both", expand=True)
        except Exception as e:
            self.logger.error(f"خطا در ایجاد نمودار حسابداری: {str(e)}")
    
    def get_pos_statistics(self):
        """دریافت آمار پوز"""
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            
            # دریافت لیست بانک‌ها
            banks = get_all_banks()
            
            stats = []
            for bank_id, bank_name in banks:
                # تعداد کل رکوردها
                cursor.execute("SELECT COUNT(*) FROM PosTransactions WHERE bank_id = ?", (bank_id,))
                total_records = cursor.fetchone()[0]
                
                # تعداد رکوردهای مغایرت‌گیری شده
                cursor.execute("SELECT COUNT(*) FROM PosTransactions WHERE bank_id = ? AND is_reconciled = 1", (bank_id,))
                reconciled_records = cursor.fetchone()[0]
                
                # تعداد رکوردهای مغایرت‌گیری نشده
                unreconciled_records = total_records - reconciled_records
                
                # درصد مغایرت‌گیری شده
                reconciled_percentage = 0
                if total_records > 0:
                    reconciled_percentage = (reconciled_records / total_records) * 100
                
                stats.append({
                    "bank_id": bank_id,
                    "bank_name": bank_name,
                    "total_records": total_records,
                    "reconciled_records": reconciled_records,
                    "unreconciled_records": unreconciled_records,
                    "reconciled_percentage": reconciled_percentage
                })
            
            conn.close()
            return stats
        except Exception as e:
            self.logger.error(f"خطا در دریافت آمار پوز: {str(e)}")
            raise
    
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
                fig, ax = plt.subplots(figsize=(6, 4))
                
                # تبدیل نام‌های بانک به فرمت صحیح فارسی با استفاده از arabic-reshaper و bidi
                bank_names_original = [stat['bank_name'] for stat in pos_stats]
                bank_names = [get_display(arabic_reshaper.reshape(name)) for name in bank_names_original]
                reconciled = [stat['reconciled_records'] for stat in pos_stats]
                unreconciled = [stat['unreconciled_records'] for stat in pos_stats]
                
                # تنظیم فونت فارسی برای matplotlib
                import matplotlib.font_manager as fm
                font_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'assets', 'fonts', 'Vazir.ttf')
                if os.path.exists(font_path):
                    fm.fontManager.addfont(font_path)
                    plt.rcParams['font.family'] = 'Vazir, Tahoma'
                else:
                    plt.rcParams['font.family'] = 'Tahoma'
                plt.rcParams['axes.unicode_minus'] = False
                # تنظیم راست به چپ بودن متن
                plt.rcParams['axes.formatter.use_locale'] = True
                plt.rcParams['text.color'] = 'black'
                
                # ایجاد نمودار میله‌ای
                x = range(len(bank_names))
                width = 0.35
                
                # تبدیل برچسب‌ها به فرمت صحیح فارسی
                reshaped_label1 = get_display(arabic_reshaper.reshape('مغایرت‌گیری شده'))
                reshaped_label2 = get_display(arabic_reshaper.reshape('مغایرت‌گیری نشده'))
                
                ax.bar([i - width/2 for i in x], reconciled, width, label=reshaped_label1)
                ax.bar([i + width/2 for i in x], unreconciled, width, label=reshaped_label2)
                
                # تبدیل عنوان‌ها به فرمت صحیح فارسی
                reshaped_ylabel = get_display(arabic_reshaper.reshape('تعداد رکوردها'))
                reshaped_title = get_display(arabic_reshaper.reshape('وضعیت مغایرت‌گیری پوز'))
                
                ax.set_ylabel(reshaped_ylabel)
                ax.set_title(reshaped_title)
                ax.set_xticks(x)
                ax.set_xticklabels(bank_names)
                ax.legend()
                
                # اضافه کردن نمودار به UI
                canvas = FigureCanvasTkAgg(fig, master=self.pos_chart_frame)
                canvas.draw()
                canvas.get_tk_widget().pack(fill="both", expand=True)
        except Exception as e:
            self.logger.error(f"خطا در به‌روزرسانی UI آمار پوز: {str(e)}")
    
    def delete_all_records(self):
        """حذف کل رکوردها از تمامی جداول"""
        try:
            # نمایش پیام تأیید
            confirm = messagebox.askyesno(
                "تأیید حذف", 
                "آیا از حذف کل رکوردها از تمامی جداول اطمینان دارید؟ این عمل غیرقابل بازگشت است!",
                icon='warning'
            )
            
            if not confirm:
                return
            
            # اجرای در یک ترد جداگانه برای جلوگیری از انسداد UI
            threading.Thread(target=self._delete_all_records_thread, daemon=True).start()
        except Exception as e:
            self.logger.error(f"خطا در حذف کل رکوردها: {str(e)}")
            self.status_var.set(f"خطا در حذف کل رکوردها: {str(e)}")
            messagebox.showerror("خطا", f"خطا در حذف کل رکوردها: {str(e)}")
    
    def _delete_all_records_thread(self):
        """حذف کل رکوردها در یک ترد جداگانه"""
        try:
            self.logger.info("در حال حذف کل رکوردها...")
            self.status_var.set("در حال حذف کل رکوردها...")
            
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            
            # حذف رکوردها از جداول
            cursor.execute("DELETE FROM ReconciliationResults")
            cursor.execute("DELETE FROM BankTransactions")
            cursor.execute("DELETE FROM AccountingTransactions")
            cursor.execute("DELETE FROM PosTransactions")
            
            # ریست کردن شمارنده‌های خودکار
            cursor.execute("DELETE FROM sqlite_sequence WHERE name IN ('ReconciliationResults', 'BankTransactions', 'AccountingTransactions', 'PosTransactions')")
            
            conn.commit()
            conn.close()
            
            self.logger.info("کل رکوردها با موفقیت حذف شدند")
            self.status_var.set("کل رکوردها با موفقیت حذف شدند")
            
            # به‌روزرسانی آمار
            self.load_statistics()
            
            # نمایش پیام موفقیت
            messagebox.showinfo("موفقیت", "کل رکوردها با موفقیت حذف شدند")
        except Exception as e:
            self.logger.error(f"خطا در حذف کل رکوردها: {str(e)}")
            self.status_var.set(f"خطا در حذف کل رکوردها: {str(e)}")
            messagebox.showerror("خطا", f"خطا در حذف کل رکوردها: {str(e)}")
    
    def delete_reconciled_records(self):
        """حذف رکوردهای مغایرت‌گیری شده از تمامی جداول"""
        try:
            # نمایش پیام تأیید
            confirm = messagebox.askyesno(
                "تأیید حذف", 
                "آیا از حذف رکوردهای مغایرت‌گیری شده از تمامی جداول اطمینان دارید؟ این عمل غیرقابل بازگشت است!",
                icon='warning'
            )
            
            if not confirm:
                return
            
            # اجرای در یک ترد جداگانه برای جلوگیری از انسداد UI
            threading.Thread(target=self._delete_reconciled_records_thread, daemon=True).start()
        except Exception as e:
            self.logger.error(f"خطا در حذف رکوردهای مغایرت‌گیری شده: {str(e)}")
            self.status_var.set(f"خطا در حذف رکوردهای مغایرت‌گیری شده: {str(e)}")
            messagebox.showerror("خطا", f"خطا در حذف رکوردهای مغایرت‌گیری شده: {str(e)}")
    
    def _delete_reconciled_records_thread(self):
        """حذف رکوردهای مغایرت‌گیری شده در یک ترد جداگانه"""
        try:
            self.logger.info("در حال حذف رکوردهای مغایرت‌گیری شده...")
            self.status_var.set("در حال حذف رکوردهای مغایرت‌گیری شده...")
            
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            
            # دریافت شناسه‌های رکوردهای مغایرت‌گیری شده
            cursor.execute("SELECT id FROM BankTransactions WHERE is_reconciled = 1")
            bank_ids = [row[0] for row in cursor.fetchall()]
            
            cursor.execute("SELECT id FROM AccountingTransactions WHERE is_reconciled = 1")
            accounting_ids = [row[0] for row in cursor.fetchall()]
            
            cursor.execute("SELECT id FROM PosTransactions WHERE is_reconciled = 1")
            pos_ids = [row[0] for row in cursor.fetchall()]
            
            # حذف رکوردهای مرتبط از جدول نتایج مغایرت‌گیری
            if bank_ids:
                placeholders = ", ".join(["?" for _ in bank_ids])
                cursor.execute(f"DELETE FROM ReconciliationResults WHERE bank_record_id IN ({placeholders})", bank_ids)
            
            if accounting_ids:
                placeholders = ", ".join(["?" for _ in accounting_ids])
                cursor.execute(f"DELETE FROM ReconciliationResults WHERE acc_id IN ({placeholders})", accounting_ids)
            
            if pos_ids:
                placeholders = ", ".join(["?" for _ in pos_ids])
                cursor.execute(f"DELETE FROM ReconciliationResults WHERE pos_id IN ({placeholders})", pos_ids)
            
            # حذف رکوردهای مغایرت‌گیری شده از جداول اصلی
            cursor.execute("DELETE FROM BankTransactions WHERE is_reconciled = 1")
            cursor.execute("DELETE FROM AccountingTransactions WHERE is_reconciled = 1")
            cursor.execute("DELETE FROM PosTransactions WHERE is_reconciled = 1")
            
            conn.commit()
            conn.close()
            
            self.logger.info("رکوردهای مغایرت‌گیری شده با موفقیت حذف شدند")
            self.status_var.set("رکوردهای مغایرت‌گیری شده با موفقیت حذف شدند")
            
            # به‌روزرسانی آمار
            self.load_statistics()
            
            # نمایش پیام موفقیت
            messagebox.showinfo("موفقیت", "رکوردهای مغایرت‌گیری شده با موفقیت حذف شدند")
        except Exception as e:
            self.logger.error(f"خطا در حذف رکوردهای مغایرت‌گیری شده: {str(e)}")
            self.status_var.set(f"خطا در حذف رکوردهای مغایرت‌گیری شده: {str(e)}")
            messagebox.showerror("خطا", f"خطا در حذف رکوردهای مغایرت‌گیری شده: {str(e)}")
    
    def print_report(self):
        """چاپ گزارش آماری"""
        try:
            # ایجاد یک فایل HTML موقت برای چاپ
            import tempfile
            import webbrowser
            import os
            from datetime import datetime
            
            # دریافت آمار
            bank_stats = self.get_bank_statistics()
            accounting_stats = self.get_accounting_statistics()
            pos_stats = self.get_pos_statistics()
            
            # ایجاد محتوای HTML
            html_content = """<!DOCTYPE html>
            <html dir="rtl">
            <head>
                <meta charset="UTF-8">
                <title>گزارش آماری سیستم مغایرت‌گیری</title>
                <style>
                    body { font-family: 'Tahoma', 'Arial', sans-serif; direction: rtl; }
                    table { width: 100%; border-collapse: collapse; margin-top: 20px; }
                    th, td { border: 1px solid #ddd; padding: 8px; text-align: right; }
                    th { background-color: #f2f2f2; }
                    h1, h2, h3 { text-align: center; }
                    .report-header { margin-bottom: 20px; }
                    .report-footer { margin-top: 20px; text-align: center; }
                    .section { margin-bottom: 30px; }
                    @media print {
                        body { width: 21cm; height: 29.7cm; margin: 0; }
                        .no-print { display: none; }
                        button { display: none; }
                    }
                </style>
            </head>
            <body>
                <div class="report-header">
                    <h1>گزارش آماری سیستم مغایرت‌گیری</h1>
                    <p>تاریخ گزارش: %s</p>
                </div>
                
                <div class="section">
                    <h2>آمار بانک‌ها</h2>
                    <table>
                        <thead>
                            <tr>
                                <th>نام بانک</th>
                                <th>تعداد کل رکوردها</th>
                                <th>تعداد مغایرت‌گیری شده</th>
                                <th>تعداد مغایرت‌گیری نشده</th>
                                <th>درصد مغایرت‌گیری شده</th>
                            </tr>
                        </thead>
                        <tbody>
                            %s
                        </tbody>
                    </table>
                </div>
                
                <div class="section">
                    <h2>آمار حسابداری</h2>
                    <table>
                        <thead>
                            <tr>
                                <th>نام بانک</th>
                                <th>تعداد کل رکوردها</th>
                                <th>تعداد مغایرت‌گیری شده</th>
                                <th>تعداد مغایرت‌گیری نشده</th>
                                <th>درصد مغایرت‌گیری شده</th>
                            </tr>
                        </thead>
                        <tbody>
                            %s
                        </tbody>
                    </table>
                </div>
                
                <div class="section">
                    <h2>آمار پوز</h2>
                    <table>
                        <thead>
                            <tr>
                                <th>نام بانک</th>
                                <th>تعداد کل رکوردها</th>
                                <th>تعداد مغایرت‌گیری شده</th>
                                <th>تعداد مغایرت‌گیری نشده</th>
                                <th>درصد مغایرت‌گیری شده</th>
                            </tr>
                        </thead>
                        <tbody>
                            %s
                        </tbody>
                    </table>
                </div>
                
                <div class="report-footer">
                    <p>گزارش سیستم مغایرت‌گیری</p>
                </div>
                
                <div class="no-print" style="text-align: center; margin-top: 20px;">
                    <button onclick="window.print()">چاپ</button>
                </div>
            </body>
            </html>
            """
            
            # ایجاد تاریخ گزارش
            report_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            # ایجاد ردیف‌های جدول بانک
            bank_rows = ""
            for stat in bank_stats:
                bank_rows += f"""<tr>
                    <td>{stat['bank_name']}</td>
                    <td>{stat['total_records']}</td>
                    <td>{stat['reconciled_records']}</td>
                    <td>{stat['unreconciled_records']}</td>
                    <td>{stat['reconciled_percentage']:.2f}%</td>
                </tr>
                """
            
            # ایجاد ردیف‌های جدول حسابداری
            accounting_rows = ""
            for stat in accounting_stats:
                accounting_rows += f"""<tr>
                    <td>{stat['bank_name']}</td>
                    <td>{stat['total_records']}</td>
                    <td>{stat['reconciled_records']}</td>
                    <td>{stat['unreconciled_records']}</td>
                    <td>{stat['reconciled_percentage']:.2f}%</td>
                </tr>
                """
            
            # ایجاد ردیف‌های جدول پوز
            pos_rows = ""
            for stat in pos_stats:
                pos_rows += f"""<tr>
                    <td>{stat['bank_name']}</td>
                    <td>{stat['total_records']}</td>
                    <td>{stat['reconciled_records']}</td>
                    <td>{stat['unreconciled_records']}</td>
                    <td>{stat['reconciled_percentage']:.2f}%</td>
                </tr>
                """
            
            # تکمیل محتوای HTML
            html_content = html_content % (report_date, bank_rows, accounting_rows, pos_rows)
            
            # ایجاد فایل موقت
            with tempfile.NamedTemporaryFile(delete=False, suffix='.html', mode='w', encoding='utf-8') as f:
                f.write(html_content)
                temp_file_path = f.name
            
            # باز کردن فایل در مرورگر برای چاپ
            webbrowser.open('file://' + os.path.realpath(temp_file_path))
            
            self.logger.info("فایل چاپ با موفقیت ایجاد شد")
            self.status_var.set("فایل چاپ با موفقیت ایجاد شد")
        except Exception as e:
            self.logger.error(f"خطا در چاپ گزارش: {str(e)}")
            self.status_var.set(f"خطا در چاپ گزارش: {str(e)}")
            messagebox.showerror("خطا", f"خطا در چاپ گزارش: {str(e)}")