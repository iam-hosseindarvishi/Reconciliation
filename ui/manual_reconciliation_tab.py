import tkinter as tk
import ttkbootstrap as ttk
from ttkbootstrap.constants import *
from tkinter import StringVar, messagebox
from tkinter.ttk import Combobox
from datetime import datetime, timedelta
import logging
import os
import queue
import threading
import decimal
import tempfile
import subprocess
import traceback
from utils.helpers import gregorian_to_persian, persian_to_gregorian
from utils.constants import MELLAT_TRANSACTION_TYPES, KESHAVARZI_TRANSACTION_TYPES
from database.banks_repository import get_all_banks
from database.bank_transaction_repository import get_unreconciled_transactions_by_bank as get_unreconciled_bank_records
from database.repositories.accounting import get_transactions_by_date_and_type as get_unreconciled_accounting_records_by_date
from database.reconciliation_results_repository import create_reconciliation_result as save_reconciliation_result
from ui.dialog.manual_reconciliation_dialog import ManualReconciliationDialog
from ui.dialog.edit_bank_record_dialog import EditBankRecordDialog
from ui.dialog.edit_accounting_record_dialog import EditAccountingRecordDialog
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from config.settings import (
    DEFAULT_FONT, DEFAULT_FONT_SIZE,
    HEADER_FONT_SIZE, BUTTON_FONT_SIZE
)

class ManualReconciliationTab(ttk.Frame):
    """تب مغایرت‌یابی دستی"""
    
    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent
        
        # تنظیم فونت‌ها - استفاده از تنظیمات یکپارچه بدون bold برای ظاهر لایت
        self.default_font = (DEFAULT_FONT, DEFAULT_FONT_SIZE)
        self.header_font = (DEFAULT_FONT, HEADER_FONT_SIZE)
        self.button_font = (DEFAULT_FONT, BUTTON_FONT_SIZE)
        
        # تنظیم استایل‌ها برای حل مشکل نمایش
        self.setup_styles()
        
        # ایجاد متغیرهای مورد نیاز
        self.selected_bank_var = StringVar()
        self.show_fees_var = tk.BooleanVar(value=False)
        
        # ایجاد ویجت‌ها
        self.create_widgets()
        
            # بارگذاری لیست بانک‌ها
        self.load_banks_to_combobox()
        
        # به‌روزرسانی اولیه UI برای اطمینان از نمایش صحیح
        self.after(100, self.refresh_ui)  # تأخیر کوتاه برای اطمینان از بارگذاری کامل
        
        # متغیرهای داده
        self.bank_records = []
        self.accounting_records = []
        self.selected_bank_record = None
        self.selected_accounting_record = None
        
        # ثبت لاگ
        logging.info("تب مغایرت‌یابی دستی ایجاد شد")
    
    def setup_styles(self):
        """تنظیم استایل‌های یکپارچه برای رفع مشکلات نمایش"""
        try:
            style = ttk.Style()
            
            # تنظیم استایل‌های اصلی
            style.configure('Header.TLabelframe', font=self.header_font)
            style.configure('Header.TLabelframe.Label', font=self.header_font)
            style.configure('Default.TLabel', font=self.default_font)
            style.configure('Default.TEntry', font=self.default_font)
            style.configure('Default.TButton', font=self.button_font)
            
            # استایل ویژه برای دکمه‌های عملیاتی
            style.configure('Operation.TButton', font=self.button_font, padding=(10, 5))
            
            # تنظیم استایل برای Treeview
            style.configure('Treeview', font=self.default_font, rowheight=25)
            style.configure('Treeview.Heading', font=self.header_font)
            
            # تنظیم استایل برای Combobox
            style.configure('TCombobox', font=self.default_font)
            style.configure('TCheckbutton', font=self.default_font)
            
            # اطمینان از اعمال تغییرات
            self.update_idletasks()
            
        except Exception as e:
            logging.warning(f"خطا در تنظیم استایل‌ها: {str(e)}")
    
    def refresh_ui(self):
        """به‌روزرسانی اجباری UI برای حل مشکل نمایش دکمه‌ها"""
        try:
            # اجبار به‌روزرسانی و بازنمایی تمام ویجت‌ها
            self.update_idletasks()
            self.update()
            
            # اعمال مجدد استایل‌ها
            self.setup_styles()
            
            # اطمینان از نمایش دکمه‌های عملیاتی
            for button in [self.show_data_button, self.edit_bank_button, self.search_button,
                          self.quick_reconcile_button, self.deduct_fee_button, 
                          self.print_report_button, self.edit_accounting_button]:
                if button.winfo_exists():
                    button.configure(style='Operation.TButton')
                    
        except Exception as e:
            logging.warning(f"خطا در به‌روزرسانی UI: {str(e)}")
    
    def create_widgets(self):
        """ایجاد ویجت‌های تب مغایرت‌یابی دستی"""
        # فریم اصلی
        main_frame = ttk.Frame(self)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # === بخش بالایی - انتخاب بانک و نمایش اطلاعات ===
        top_frame = ttk.Frame(main_frame)
        top_frame.pack(fill=tk.X, pady=5)
        
        # انتخاب بانک
        ttk.Label(top_frame, text="انتخاب بانک:", style='Default.TLabel').pack(side=tk.RIGHT, padx=5)
        self.bank_combobox = Combobox(top_frame, textvariable=self.selected_bank_var, state="readonly", width=30)
        self.bank_combobox.pack(side=tk.RIGHT, padx=5)
        self.bank_combobox.bind("<<ComboboxSelected>>", lambda event: self.show_bank_records())
        
        # دکمه نمایش اطلاعات
        self.show_data_button = ttk.Button(top_frame, text="نمایش اطلاعات", style='Operation.TButton', command=self.show_bank_records)
        self.show_data_button.pack(side=tk.RIGHT, padx=5)
        
        # چک باکس نمایش کارمزدها (برای حذف آنها از نمایش)
        self.show_fees_var = tk.BooleanVar(value=False)
        self.show_fees_checkbox = ttk.Checkbutton(top_frame, text="نمایش کارمزدها", variable=self.show_fees_var, 
                                                command=self.show_bank_records)
        self.show_fees_checkbox.pack(side=tk.RIGHT, padx=10)
        
        # لیبل نمایش تعداد رکوردها
        self.records_count_var = tk.StringVar()
        self.records_count_label = ttk.Label(top_frame, textvariable=self.records_count_var, style='Default.TLabel')
        self.records_count_label.pack(side=tk.LEFT, padx=5)
        
        # === بخش میانی - لیست رکوردهای بانک ===
        bank_frame = ttk.LabelFrame(main_frame, text="رکوردهای مغایرت‌گیری نشده بانک")
        bank_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        # ایجاد Treeview برای نمایش رکوردهای بانک
        bank_tree_frame = ttk.Frame(bank_frame)
        bank_tree_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # اسکرول‌بار برای Treeview بانک
        bank_scrollbar_y = ttk.Scrollbar(bank_tree_frame)
        bank_scrollbar_y.pack(side=tk.LEFT, fill=tk.Y)
        
        bank_scrollbar_x = ttk.Scrollbar(bank_tree_frame, orient=tk.HORIZONTAL)
        bank_scrollbar_x.pack(side=tk.BOTTOM, fill=tk.X)
        
        # ستون‌های Treeview بانک
        self.bank_tree = ttk.Treeview(bank_tree_frame, 
                                     columns=("id", "tracking_number", "date", "amount", "description", "type", "depositor", "status"),
                                     show="headings",
                                     yscrollcommand=bank_scrollbar_y.set,
                                     xscrollcommand=bank_scrollbar_x.set)
        
        # تنظیم اسکرول‌بارها
        bank_scrollbar_y.config(command=self.bank_tree.yview)
        bank_scrollbar_x.config(command=self.bank_tree.xview)
        
        # تنظیم عناوین ستون‌ها
        self.bank_tree.heading("id", text="شناسه")
        self.bank_tree.heading("tracking_number", text="شماره پیگیری")
        self.bank_tree.heading("date", text="تاریخ")
        self.bank_tree.heading("amount", text="مبلغ")
        self.bank_tree.heading("description", text="توضیحات")
        self.bank_tree.heading("type", text="نوع تراکنش")
        self.bank_tree.heading("depositor", text="واریز کننده")
        self.bank_tree.heading("status", text="وضعیت")
        
        # تنظیم عرض ستون‌ها
        self.bank_tree.column("id", width=50, anchor=tk.CENTER)
        self.bank_tree.column("tracking_number", width=120, anchor=tk.CENTER)
        self.bank_tree.column("date", width=100, anchor=tk.CENTER)
        self.bank_tree.column("amount", width=120, anchor=tk.CENTER)
        self.bank_tree.column("description", width=180)
        self.bank_tree.column("type", width=100, anchor=tk.CENTER)
        self.bank_tree.column("depositor", width=120, anchor=tk.CENTER)
        self.bank_tree.column("status", width=100, anchor=tk.CENTER)
        
        self.bank_tree.pack(fill=tk.BOTH, expand=True)
        
        # رویداد انتخاب آیتم در Treeview بانک
        self.bank_tree.bind("<<TreeviewSelect>>", self.on_bank_record_selected)
        
        # دکمه ویرایش رکورد بانک
        bank_buttons_frame = ttk.Frame(bank_frame)
        bank_buttons_frame.pack(fill=tk.X, pady=5)
        
        self.edit_bank_button = ttk.Button(bank_buttons_frame, text="ویرایش رکورد", style='Operation.TButton', command=self.edit_bank_record)
        self.edit_bank_button.pack(side=tk.RIGHT, padx=5)
        
        # === بخش جستجو ===
        search_frame = ttk.Frame(main_frame)
        search_frame.pack(fill=tk.X, pady=5)
        
        # دکمه جستجو
        self.search_button = ttk.Button(search_frame, text="جستجوی رکوردهای حسابداری", style='Operation.TButton', command=self.search_accounting_records)
        self.search_button.pack(side=tk.LEFT, padx=5)
        
        # === بخش پایینی - لیست رکوردهای حسابداری ===
        accounting_frame = ttk.LabelFrame(main_frame, text="رکوردهای حسابداری")
        accounting_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        # ایجاد Treeview برای نمایش رکوردهای حسابداری
        accounting_tree_frame = ttk.Frame(accounting_frame)
        accounting_tree_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # اسکرول‌بار برای Treeview حسابداری
        accounting_scrollbar_y = ttk.Scrollbar(accounting_tree_frame)
        accounting_scrollbar_y.pack(side=tk.LEFT, fill=tk.Y)
        
        accounting_scrollbar_x = ttk.Scrollbar(accounting_tree_frame, orient=tk.HORIZONTAL)
        accounting_scrollbar_x.pack(side=tk.BOTTOM, fill=tk.X)
        
        # ستون‌های Treeview حسابداری
        self.accounting_tree = ttk.Treeview(accounting_tree_frame, 
                                          columns=("id", "tracking_number", "date", "amount", "description", "type", "bank", "system"),
                                          show="headings",
                                          yscrollcommand=accounting_scrollbar_y.set,
                                          xscrollcommand=accounting_scrollbar_x.set)
        
        # تنظیم اسکرول‌بارها
        accounting_scrollbar_y.config(command=self.accounting_tree.yview)
        accounting_scrollbar_x.config(command=self.accounting_tree.xview)
        
        # تنظیم عناوین ستون‌ها
        self.accounting_tree.heading("id", text="شناسه")
        self.accounting_tree.heading("tracking_number", text="شماره پیگیری")
        self.accounting_tree.heading("date", text="تاریخ")
        self.accounting_tree.heading("amount", text="مبلغ")
        self.accounting_tree.heading("description", text="توضیحات")
        self.accounting_tree.heading("type", text="نوع تراکنش")
        self.accounting_tree.heading("bank", text="بانک")
        self.accounting_tree.heading("system", text="سیستم")
        
        # تنظیم عرض ستون‌ها
        self.accounting_tree.column("id", width=50, anchor=tk.CENTER)
        self.accounting_tree.column("tracking_number", width=120, anchor=tk.CENTER)
        self.accounting_tree.column("date", width=100, anchor=tk.CENTER)
        self.accounting_tree.column("amount", width=120, anchor=tk.CENTER)
        self.accounting_tree.column("description", width=200)
        self.accounting_tree.column("type", width=100, anchor=tk.CENTER)
        self.accounting_tree.column("bank", width=100, anchor=tk.CENTER)
        self.accounting_tree.column("system", width=100, anchor=tk.CENTER)
        
        self.accounting_tree.pack(fill=tk.BOTH, expand=True)
        
        # رویداد انتخاب آیتم در Treeview حسابداری
        self.accounting_tree.bind("<<TreeviewSelect>>", self.on_accounting_record_selected)
        
        # === بخش دکمه‌های عملیات ===
        operations_frame = ttk.Frame(main_frame)
        operations_frame.pack(fill=tk.X, pady=5)
        
        # دکمه مغایرت‌گیری سریع
        self.quick_reconcile_button = ttk.Button(operations_frame, text="مغایرت‌گیری سریع", style='Operation.TButton', command=self.quick_reconcile)
        self.quick_reconcile_button.pack(side=tk.RIGHT, padx=5)
        
        # دکمه کسر کارمزد
        self.deduct_fee_button = ttk.Button(operations_frame, text="کسر کارمزد", style='Operation.TButton', command=self.deduct_fee)
        self.deduct_fee_button.pack(side=tk.RIGHT, padx=5)
        
        # دکمه چاپ گزارش
        self.print_report_button = ttk.Button(operations_frame, text="چاپ گزارش", style='Operation.TButton', command=self.print_report)
        self.print_report_button.pack(side=tk.RIGHT, padx=5)
        
        # دکمه ویرایش رکورد حسابداری
        self.edit_accounting_button = ttk.Button(operations_frame, text="ویرایش رکورد حسابداری", style='Operation.TButton', command=self.edit_accounting_record)
        self.edit_accounting_button.pack(side=tk.RIGHT, padx=5)
        
        # غیرفعال کردن دکمه‌های عملیات در ابتدا
        self.disable_operation_buttons()
    
    def load_banks_to_combobox(self):
        """بارگذاری لیست بانک‌ها در کامبوباکس"""
        try:
            # ذخیره انتخاب فعلی
            current_selection = self.selected_bank_var.get()
            
            banks = get_all_banks()
            bank_names = []
            self.banks_dict = {}
            
            if not banks:
                logging.warning("هیچ بانکی در سیستم ثبت نشده است")
                self.records_count_var.set("هیچ بانکی در سیستم ثبت نشده است")
                self.bank_combobox['values'] = []
                return
            
            for bank in banks:
                bank_id = bank[0]  # شناسه بانک
                bank_name = bank[1]  # نام بانک
                bank_names.append(bank_name)
                self.banks_dict[bank_name] = bank_id
            
            self.bank_combobox['values'] = bank_names
            
            # اگر انتخاب قبلی وجود داشته و هنوز در لیست هست، آن را حفظ کن
            if current_selection and current_selection in self.banks_dict:
                self.selected_bank_var.set(current_selection)
            # در غیر این صورت، اولین مورد را انتخاب کن اگر لیست خالی نیست
            elif bank_names:
                self.bank_combobox.current(0)
                # تنظیم متغیر انتخاب شده با مقدار اولیه
                self.selected_bank_var.set(bank_names[0])
                
            # نمایش رکوردهای بانک انتخاب شده به صورت خودکار اگر بانکی انتخاب شده باشد
            if self.selected_bank_var.get():
                self.show_bank_records()
                
            logging.info(f"تعداد {len(banks)} بانک در کامبوباکس بارگذاری شد")
        except Exception as e:
            error_message = f"خطا در بارگذاری لیست بانک‌ها: {str(e)}"
            logging.error(f"{error_message}\n{traceback.format_exc()}")
            messagebox.showerror("خطا", error_message)
    
    def show_bank_records(self):
        """نمایش رکوردهای مغایرت‌گیری نشده بانک انتخاب شده"""
        try:
            selected_bank = self.selected_bank_var.get()
            if not selected_bank:
                messagebox.showwarning("هشدار", "لطفاً یک بانک را انتخاب کنید")
                return
            
            # پاک کردن داده‌های قبلی
            self.clear_trees()
            
            # دریافت شناسه بانک از دیکشنری بانک‌ها
            bank_id = self.banks_dict.get(selected_bank)
            
            if not bank_id:
                messagebox.showwarning("هشدار", "بانک انتخاب شده یافت نشد")
                return
            
            # دریافت رکوردهای مغایرت‌گیری نشده بانک
            self.bank_records = get_unreconciled_bank_records(bank_id)
            
            # فیلتر کردن رکوردهای کارمزد اگر چک باکس فعال نباشد
            show_fees = self.show_fees_var.get()
            filtered_records = []
            hidden_fee_count = 0
            for record in self.bank_records:
                # اگر رکورد کارمزد است و چک باکس فعال نیست، آن را نمایش نده
                if not show_fees and record.get('transaction_type') == KESHAVARZI_TRANSACTION_TYPES['BANK_FEES']:
                    hidden_fee_count += 1
                    continue
                filtered_records.append(record)
            
            # نمایش رکوردها در Treeview
            for record in filtered_records:
                # تبدیل تاریخ میلادی به شمسی
                shamsi_date = gregorian_to_persian(record['transaction_date'])
                
                # فرمت‌بندی مبلغ
                amount = f"{record['amount']:,}"
                
                # وضعیت
                status = "مغایرت‌گیری نشده"
                
                # نوع تراکنش
                transaction_type = record.get('transaction_type', '')
                
                self.bank_tree.insert("", tk.END, values=(
                    record['id'],
                    record.get('extracted_tracking_number', ''),
                    shamsi_date,
                    amount,
                    record.get('description', ''),
                    transaction_type,
                    record.get('depositor_name', ''),
                    status
                ))
            
            # نمایش تعداد رکوردها در لیبل به جای پیام پاپ‌آپ
            if not filtered_records:
                if not self.bank_records:
                    self.records_count_var.set(f"هیچ رکورد مغایرت‌گیری نشده‌ای برای بانک {selected_bank} یافت نشد")
                else:
                    self.records_count_var.set(f"هیچ رکورد مغایرت‌گیری نشده‌ای برای نمایش وجود ندارد (کارمزدها پنهان شده‌اند)")
            else:
                total_records = len(self.bank_records)
                filtered_count = len(filtered_records)
                
                if hidden_fee_count > 0:
                    self.records_count_var.set(f"تعداد {filtered_count} رکورد نمایش داده شده ({hidden_fee_count} رکورد کارمزد پنهان شده است)")
                else:
                    self.records_count_var.set(f"تعداد {filtered_count} رکورد مغایرت‌گیری نشده برای بانک {selected_bank} یافت شد")
                
            # به‌روزرسانی UI برای نمایش تغییرات و اطمینان از نمایش دکمه‌ها
            self.refresh_ui()
            
            logging.info(f"تعداد {len(filtered_records)} رکورد بانک نمایش داده شد")
        except Exception as e:
            error_message = f"خطا در نمایش رکوردهای بانک: {str(e)}"
            logging.error(f"{error_message}\n{traceback.format_exc()}")
            messagebox.showerror("خطا", error_message)
    
    def on_bank_record_selected(self, event):
        """رویداد انتخاب رکورد بانک"""
        selected_items = self.bank_tree.selection()
        if not selected_items:
            self.disable_operation_buttons()
            self.selected_bank_record = None
            return
        
        # دریافت آیتم انتخاب شده
        item = self.bank_tree.item(selected_items[0])
        record_id = item['values'][0]
        
        # یافتن رکورد بانک مربوطه
        self.selected_bank_record = next((r for r in self.bank_records if r['id'] == record_id), None)
        
        # فعال کردن دکمه‌های مربوطه
        self.edit_bank_button.config(state=tk.NORMAL)
        self.search_button.config(state=tk.NORMAL)
        
        # پاک کردن لیست رکوردهای حسابداری
        self.clear_accounting_tree()
        
        logging.info(f"رکورد بانک با شناسه {record_id} انتخاب شد")
    
    def on_accounting_record_selected(self, event):
        """رویداد انتخاب رکورد حسابداری"""
        selected_items = self.accounting_tree.selection()
        if not selected_items:
            self.selected_accounting_record = None
            return
        
        # دریافت آیتم انتخاب شده
        item = self.accounting_tree.item(selected_items[0])
        record_id = item['values'][0]
        
        # یافتن رکورد حسابداری مربوطه
        self.selected_accounting_record = next((r for r in self.accounting_records if r['id'] == record_id), None)
        
        # فعال کردن دکمه‌های مربوطه اگر هم رکورد بانک و هم رکورد حسابداری انتخاب شده باشند
        if self.selected_bank_record and self.selected_accounting_record:
            self.quick_reconcile_button.config(state=tk.NORMAL)
            self.deduct_fee_button.config(state=tk.NORMAL)
            self.print_report_button.config(state=tk.NORMAL)
        
        # فعال کردن دکمه ویرایش رکورد حسابداری
        self.edit_accounting_button.config(state=tk.NORMAL)
        
        logging.info(f"رکورد حسابداری با شناسه {record_id} انتخاب شد")
    
    
    def search_accounting_records(self):
        """جستجوی رکوردهای حسابداری مرتبط با رکورد بانک انتخاب شده"""
        try:
            if not self.selected_bank_record:
                messagebox.showwarning("هشدار", "لطفاً یک رکورد بانک را انتخاب کنید")
                return
            
            # پاک کردن لیست قبلی
            self.clear_accounting_tree()
            
            # دریافت تاریخ و مبلغ رکورد بانک
            bank_date = self.selected_bank_record['transaction_date']
            bank_amount = self.selected_bank_record['amount']
            
            # دریافت نوع تراکنش بانک بر اساس نوع تراکنش موجود در رکورد بانک
            bank_transaction_type = self.selected_bank_record.get('transaction_type', '')
            
            # تبدیل نوع تراکنش بانک به نوع تراکنش حسابداری
            if bank_transaction_type == MELLAT_TRANSACTION_TYPES['RECEIVED_POS'] or bank_transaction_type == KESHAVARZI_TRANSACTION_TYPES['RECEIVED_POS'] or bank_transaction_type == 'received_pos':
                transaction_type = 'Pos'
            elif bank_transaction_type == MELLAT_TRANSACTION_TYPES['PAID_TRANSFER'] or bank_transaction_type == KESHAVARZI_TRANSACTION_TYPES['PAID_TRANSFER'] or bank_transaction_type == 'paid_transfer':
                transaction_type = 'Paid Transfer'
            elif bank_transaction_type == MELLAT_TRANSACTION_TYPES['RECEIVED_TRANSFER'] or bank_transaction_type == KESHAVARZI_TRANSACTION_TYPES['RECEIVED_TRANSFER'] or bank_transaction_type == 'received_transfer':
                transaction_type = 'Received Transfer'
            elif bank_transaction_type == KESHAVARZI_TRANSACTION_TYPES['RECEIVED_CHECK'] or bank_transaction_type == 'received_check':
                transaction_type = 'Received Check'
            elif bank_transaction_type == KESHAVARZI_TRANSACTION_TYPES['PAID_CHECK'] or bank_transaction_type == 'paid_check':
                transaction_type = 'Paid Check'
            elif bank_transaction_type == MELLAT_TRANSACTION_TYPES['BANK_FEES'] or bank_transaction_type == KESHAVARZI_TRANSACTION_TYPES['BANK_FEES'] or bank_transaction_type == 'bank_fee':
                transaction_type = 'Bank Fees'
            else:
                # اگر نوع تراکنش مشخص نبود، از مقدار استفاده می‌کنیم
                transaction_type = 'Unknown'
            
            # اگر نوع تراکنش POS است، تاریخ را یک روز کاهش می‌دهیم
            search_date = bank_date
            if transaction_type == 'Pos':
                # تبدیل تاریخ به شیء datetime
                date_obj = datetime.strptime(bank_date, '%Y-%m-%d')
                # کاهش یک روز
                prev_date_obj = date_obj - timedelta(days=1)
                # تبدیل مجدد به رشته
                search_date = prev_date_obj.strftime('%Y-%m-%d')
                logging.info(f"تاریخ جستجو برای تراکنش POS از {bank_date} به {search_date} تغییر کرد")
            
            try:
                # جستجوی تمام رکوردهای حسابداری در تمام بانک‌ها با is_reconciled=0 و با تاریخ، مبلغ و نوع تراکنش مطابق
                from database.repositories.accounting import get_all_unreconciled_accounting_records_by_criteria
                
                # جستجو در سیستم‌های جدید و قدیم
                self.accounting_records = get_all_unreconciled_accounting_records_by_criteria(
                    date=search_date,
                    amount=bank_amount,
                    transaction_type=transaction_type
                )
                
            except ImportError:
                # اگر تابع جدید وجود نداشت، از تابع قدیمی استفاده کنیم ولی بدون فیلتر بانک
                try:
                    from database.repositories.accounting import get_unreconciled_accounting_records_by_date
                    
                    # جستجو در تمام بانک‌ها (None به‌عنوان bank_id)
                    self.accounting_records = get_unreconciled_accounting_records_by_date(
                        bank_id=None,  # جستجو در تمام بانک‌ها
                        start_date=search_date,
                        end_date=search_date,
                        transaction_type=transaction_type,
                        amount=bank_amount  # فیلتر بر اساس مبلغ
                    )
                except TypeError:
                    # اگر تابع قدیمی پارامتر amount را پشتیبانی نمی‌کند
                    try:
                        all_records = get_unreconciled_accounting_records_by_date(
                            bank_id=None,
                            start_date=search_date,
                            end_date=search_date,
                            transaction_type=transaction_type
                        )
                        # فیلتر دستی بر اساس مبلغ
                        self.accounting_records = [r for r in all_records if r.get('transaction_amount') == bank_amount]
                    except Exception as e:
                        logging.error(f"خطا در جستجوی رکوردهای حسابداری: {str(e)}")
                        self.accounting_records = []
            
            # نمایش رکوردها در Treeview (به جز رکوردهای کارمزد)
            for record in self.accounting_records:
                # فیلتر کردن رکوردهای کارمزد
                transaction_type = record.get('transaction_type', '')
                if transaction_type == 'Bank Fees' or 'کارمزد' in record.get('description', ''):
                    continue  # پرش از نمایش رکوردهای کارمزد
                
                # تبدیل تاریخ میلادی به شمسی
                shamsi_date = gregorian_to_persian(record.get('due_date', record.get('transaction_date', '')))
                
                # فرمت‌بندی مبلغ
                amount = f"{record.get('transaction_amount', 0):,}"
                
                # نوع تراکنش
                type_text = record.get('transaction_type', '')
                
                # نام بانک
                bank_id = record.get('bank_id')
                bank_name = next((name for name, bid in self.banks_dict.items() if bid == bank_id), "نامشخص")
                
                # تبدیل مقدار is_new_system به متن
                system_text = "سیستم جدید" if record.get('is_new_system', 0) == 1 else "سیستم قدیم"
                
                self.accounting_tree.insert("", tk.END, values=(
                    record['id'],
                    record.get('transaction_number', ''),
                    shamsi_date,
                    amount,
                    record.get('description', ''),
                    type_text,
                    bank_name,
                    system_text
                ))
            
            # فعال کردن دکمه‌های عملیات
            if self.accounting_records:
                self.edit_accounting_button.config(state=tk.NORMAL)
                logging.info(f"تعداد {len(self.accounting_records)} رکورد حسابداری یافت شد")
            else:
                messagebox.showinfo("اطلاعات", "هیچ رکورد حسابداری مغایرت‌گیری نشده‌ای با شرایط مورد نظر یافت نشد")
                logging.info("هیچ رکورد حسابداری یافت نشد")
        except Exception as e:
            error_message = f"خطا در جستجوی رکوردهای حسابداری: {str(e)}"
            logging.error(f"{error_message}\n{traceback.format_exc()}")
            messagebox.showerror("خطا", error_message)
    
    def quick_reconcile(self):
        # TODO: این متد باید بهبود یابد
        """مغایرت‌گیری سریع بین رکورد بانک و رکورد حسابداری انتخاب شده"""
        try:
            selected_bank_item = self.bank_tree.selection()
            selected_accounting_item = self.accounting_tree.selection()
            
            if not selected_bank_item or not selected_accounting_item:
                messagebox.showwarning("هشدار", "لطفاً یک رکورد بانک و یک رکورد حسابداری را انتخاب کنید")
                return
            
            # دریافت رکوردهای انتخاب شده
            bank_item = self.bank_tree.item(selected_bank_item[0])
            accounting_item = self.accounting_tree.item(selected_accounting_item[0])
            
            bank_id = bank_item['values'][0]
            accounting_id = accounting_item['values'][0]
            
            # تأیید از کاربر
            confirm = messagebox.askyesno(
                "تأیید مغایرت‌گیری", 
                "آیا از مغایرت‌گیری این دو رکورد اطمینان دارید؟"
            )
            
            if confirm:
                # ثبت مغایرت‌گیری
                from reconciliation.save_reconciliation_result import success_reconciliation_result
                from database.bank_transaction_repository import update_bank_transaction_reconciliation_status
                from database.repositories.accounting import update_accounting_transaction_reconciliation_status
                
                try:
                    # ابتدا وضعیت is_reconciled را به‌روزرسانی کنیم
                    update_bank_transaction_reconciliation_status(bank_id, 1)
                    update_accounting_transaction_reconciliation_status(accounting_id, 1)
                    
                    # سپس نتیجه مغایرت‌گیری را ثبت کنیم
                    success_reconciliation_result(
                        bank_id,  # bank_record_id
                        accounting_id,  # acc_record_id
                        None,  # pos_record_id
                        "مغایرت‌گیری دستی از طریق تب مغایرت‌یابی دستی",
                        'manual_match'
                    )
                except Exception as update_error:
                    logging.error(f"خطا در به‌روزرسانی وضعیت مغایرت‌یابی: {str(update_error)}")
                    messagebox.showerror("خطا", f"خطا در به‌روزرسانی وضعیت مغایرت‌یابی: {str(update_error)}")
                    return
                
                messagebox.showinfo("اطلاعات", "مغایرت‌گیری با موفقیت انجام شد")
                logging.info(f"مغایرت‌گیری بین رکورد بانک {bank_id} و رکورد حسابداری {accounting_id} انجام شد")
                
                # به‌روزرسانی لیست‌ها
                self.show_bank_records()
                self.clear_accounting_tree()
                self.disable_operation_buttons()
        except Exception as e:
            error_message = f"خطا در مغایرت‌گیری سریع: {str(e)}"
            logging.error(f"{error_message}\n{traceback.format_exc()}")
            messagebox.showerror("خطا", error_message)
    
    def deduct_fee(self):
        """کسر کارمزد از مبلغ رکورد بانک"""
        try:
            selected_bank_item = self.bank_tree.selection()
            selected_accounting_item = self.accounting_tree.selection()
            
            if not selected_bank_item or not selected_accounting_item:
                messagebox.showwarning("هشدار", "لطفاً یک رکورد بانک و یک رکورد حسابداری را انتخاب کنید")
                return
            
            # دریافت رکوردهای انتخاب شده
            bank_item = self.bank_tree.item(selected_bank_item[0])
            accounting_item = self.accounting_tree.item(selected_accounting_item[0])
            
            bank_id = bank_item['values'][0]
            accounting_id = accounting_item['values'][0]
            
            bank_record = next((r for r in self.bank_records if r['id'] == bank_id), None)
            accounting_record = next((r for r in self.accounting_records if r['id'] == accounting_id), None)
            
            if not bank_record or not accounting_record:
                messagebox.showwarning("هشدار", "رکوردهای انتخاب شده یافت نشدند")
                return
            
            # محاسبه کارمزد (تفاوت بین مبلغ بانک و مبلغ حسابداری)
            bank_amount = decimal.Decimal(str(bank_record['amount']))
            accounting_amount = decimal.Decimal(str(accounting_record['transaction_amount']))
            
            # اگر مبلغ بانک کوچکتر از مبلغ حسابداری باشد، کارمزد قابل محاسبه نیست
            if bank_amount < accounting_amount:
                messagebox.showwarning("هشدار", "مبلغ رکورد بانک باید بزرگتر یا مساوی مبلغ حسابداری باشد تا بتوان کارمزد را محاسبه کرد")
                return
            
            fee_amount = bank_amount - accounting_amount
            
            # نمایش پیغام تأیید
            confirm = messagebox.askyesno(
                "تأیید کسر کارمزد", 
                f"آیا از کسر کارمزد به مبلغ {fee_amount:,} از مبلغ اصلی اطمینان دارید؟\n" +
                f"مبلغ بانک: {bank_amount:,}\n" +
                f"مبلغ حسابداری: {accounting_amount:,}\n" +
                f"مبلغ کارمزد: {fee_amount:,}"
            )
            
            if confirm:
                # استفاده از Helper برای کسر کارمزد و ایجاد رکورد جدید
                from database.Helper.db_helpers import deduct_fee
                
                try:
                    # کسر کارمزد از مبلغ تراکنش و ایجاد رکورد جدید برای کارمزد
                    updated_bank_id, fee_record_id = deduct_fee(
                        bank_id,
                        float(bank_amount),
                        float(fee_amount),
                        f"کارمزد برای رکورد {bank_id}"
                    )
                    
                    if updated_bank_id and fee_record_id:
                        # ثبت مغایرت‌گیری با کارمزد با استفاده از success_reconciliation_result
                        from reconciliation.save_reconciliation_result import success_reconciliation_result
                        success_reconciliation_result(
                            updated_bank_id,  # bank_record_id
                            accounting_id,  # acc_record_id
                            None,  # pos_record_id
                            f"مغایرت‌گیری دستی با کسر کارمزد به مبلغ {fee_amount:,} ریال",
                            'manual_match_with_fee'
                        )
                    else:
                        messagebox.showerror("خطا", "خطا در کسر کارمزد از تراکنش بانکی")
                        return
                except Exception as e:
                    messagebox.showerror("خطا", f"خطا در کسر کارمزد: {str(e)}")
                    logging.error(f"خطا در کسر کارمزد: {str(e)}")
                    return
                
                messagebox.showinfo("اطلاعات", "مغایرت‌گیری با کسر کارمزد با موفقیت انجام شد")
                logging.info(f"مغایرت‌گیری با کسر کارمزد {fee_amount} بین رکورد بانک {bank_id} و رکورد حسابداری {accounting_id} انجام شد")
                
                # به‌روزرسانی لیست‌ها
                self.show_bank_records()
                self.clear_accounting_tree()
                self.disable_operation_buttons()
        except Exception as e:
            error_message = f"خطا در کسر کارمزد: {str(e)}"
            logging.error(f"{error_message}\n{traceback.format_exc()}")
            messagebox.showerror("خطا", error_message)
    
    def print_report(self):
        """چاپ گزارش به صورت PDF"""
        try:
            selected_bank_item = self.bank_tree.selection()
            
            if not selected_bank_item:
                messagebox.showwarning("هشدار", "لطفاً یک رکورد بانک را انتخاب کنید")
                return
            
            # دریافت رکورد بانک انتخاب شده
            bank_item = self.bank_tree.item(selected_bank_item[0])
            bank_id = bank_item['values'][0]
            bank_record = next((r for r in self.bank_records if r['id'] == bank_id), None)
            
            if not bank_record:
                messagebox.showwarning("هشدار", "رکورد بانک انتخاب شده یافت نشد")
                return
            
            # ایجاد فایل PDF موقت
            with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as temp_file:
                pdf_path = temp_file.name
            
            # ثبت فونت فارسی
            try:
                pdfmetrics.registerFont(TTFont('BNazanin', 'fonts/BNazanin.ttf'))
            except Exception as font_error:
                logging.error(f"خطا در بارگذاری فونت: {str(font_error)}")
                messagebox.showwarning("هشدار", "فونت فارسی یافت نشد. گزارش ممکن است به درستی نمایش داده نشود.")
            
            # ایجاد PDF
            c = canvas.Canvas(pdf_path, pagesize=A4)
            c.setFont('BNazanin', 12)
            
            # عنوان گزارش
            c.drawRightString(500, 800, "گزارش مغایرت‌یابی دستی")
            c.drawRightString(500, 780, f"تاریخ: {gregorian_to_persian(datetime.now().strftime('%Y-%m-%d'))}")
            
            # اطلاعات رکورد بانک
            c.drawRightString(500, 750, "اطلاعات رکورد بانک:")
            c.drawRightString(500, 730, f"شناسه: {bank_record['id']}")
            c.drawRightString(500, 710, f"شماره پیگیری: {bank_record.get('extracted_tracking_number', 'نامشخص')}")
            c.drawRightString(500, 690, f"تاریخ: {gregorian_to_persian(bank_record['transaction_date'])}")
            c.drawRightString(500, 670, f"مبلغ: {bank_record['amount']:,} ریال")
            c.drawRightString(500, 650, f"توضیحات: {bank_record.get('description', '')}")
            c.drawRightString(500, 630, f"نوع تراکنش: {bank_record.get('transaction_type', 'نامشخص')}")
            
            # اطلاعات رکوردهای حسابداری
            c.drawRightString(500, 600, "رکوردهای حسابداری مرتبط:")
            
            y_position = 580
            for i, record in enumerate(self.accounting_records, 1):
                c.drawRightString(500, y_position, f"رکورد {i}:")
                c.drawRightString(480, y_position - 20, f"شناسه: {record['id']}")
                c.drawRightString(480, y_position - 40, f"شماره پیگیری: {record.get('tracking_number', 'نامشخص')}")
                c.drawRightString(480, y_position - 60, f"تاریخ: {gregorian_to_persian(record['transaction_date'])}")
                c.drawRightString(480, y_position - 80, f"مبلغ: {record['transaction_amount']:,} ریال")
                c.drawRightString(480, y_position - 100, f"توضیحات: {record.get('description', '')}")
                c.drawRightString(480, y_position - 120, f"نوع تراکنش: {record.get('transaction_type', '')}")
                
                # نمایش نام بانک
                bank_id = record.get('bank_id')
                bank_name = next((name for name, bid in self.banks_dict.items() if bid == bank_id), "نامشخص")
                c.drawRightString(480, y_position - 140, f"بانک: {bank_name}")
                
                y_position -= 160
                
                # اگر به پایین صفحه رسیدیم، صفحه جدید ایجاد کنیم
                if y_position < 100:
                    c.showPage()
                    c.setFont('BNazanin', 12)
                    y_position = 750
            
            c.save()
            
            # باز کردن فایل PDF
            try:
                subprocess.Popen([pdf_path], shell=True)
                logging.info(f"گزارش PDF در مسیر {pdf_path} ایجاد و باز شد")
            except Exception as e:
                error_message = f"خطا در باز کردن فایل PDF: {str(e)}"
                logging.error(error_message)
                messagebox.showerror("خطا", error_message)
        except Exception as e:
            error_message = f"خطا در چاپ گزارش: {str(e)}"
            logging.error(f"{error_message}\n{traceback.format_exc()}")
            messagebox.showerror("خطا", error_message)
    
    
    
    def edit_bank_record(self):
        """ویرایش رکورد بانک انتخاب شده"""
        try:
            selected_item = self.bank_tree.selection()
            if not selected_item:
                messagebox.showwarning("هشدار", "لطفاً یک رکورد بانک را انتخاب کنید")
                return
            
            # دریافت آیتم انتخاب شده
            item = self.bank_tree.item(selected_item[0])
            record_id = item['values'][0]
            
            # یافتن رکورد بانک مربوطه
            bank_record = next((r for r in self.bank_records if r['id'] == record_id), None)
            
            if bank_record:
                # نمایش دیالوگ ویرایش
                dialog = EditBankRecordDialog(self, bank_record)
                
                # اگر رکورد ویرایش شد، به‌روزرسانی لیست
                if dialog.result:
                    logging.info(f"رکورد بانک با شناسه {record_id} ویرایش شد")
                    self.show_bank_records()
        except Exception as e:
            error_message = f"خطا در ویرایش رکورد بانک: {str(e)}"
            logging.error(f"{error_message}\n{traceback.format_exc()}")
            messagebox.showerror("خطا", error_message)
    
    def edit_accounting_record(self):
        """ویرایش رکورد حسابداری انتخاب شده"""
        try:
            selected_item = self.accounting_tree.selection()
            if not selected_item:
                messagebox.showwarning("هشدار", "لطفاً یک رکورد حسابداری را انتخاب کنید")
                return
            
            # دریافت آیتم انتخاب شده
            item = self.accounting_tree.item(selected_item[0])
            record_id = item['values'][0]
            
            # یافتن رکورد حسابداری مربوطه
            accounting_record = next((r for r in self.accounting_records if r['id'] == record_id), None)
            
            if accounting_record:
                # نمایش دیالوگ ویرایش
                dialog = EditAccountingRecordDialog(self, accounting_record)
                
                # اگر رکورد ویرایش شد، به‌روزرسانی لیست
                if dialog.result:
                    logging.info(f"رکورد حسابداری با شناسه {record_id} ویرایش شد")
                    self.search_accounting_records()
        except Exception as e:
            error_message = f"خطا در ویرایش رکورد حسابداری: {str(e)}"
            logging.error(f"{error_message}\n{traceback.format_exc()}")
            messagebox.showerror("خطا", error_message)
    
    def clear_trees(self):
        """پاک کردن هر دو Treeview"""
        self.clear_bank_tree()
        self.clear_accounting_tree()
        self.disable_operation_buttons()
    
    def clear_bank_tree(self):
        """پاک کردن Treeview بانک"""
        for item in self.bank_tree.get_children():
            self.bank_tree.delete(item)
        self.bank_records = []
        self.selected_bank_record = None
    
    def clear_accounting_tree(self):
        """پاک کردن Treeview حسابداری"""
        for item in self.accounting_tree.get_children():
            self.accounting_tree.delete(item)
        self.accounting_records = []
        self.selected_accounting_record = None
    
    def disable_operation_buttons(self):
        """غیرفعال کردن دکمه‌های عملیات"""
        self.edit_bank_button.config(state=tk.DISABLED)
        self.edit_accounting_button.config(state=tk.DISABLED)
        self.quick_reconcile_button.config(state=tk.DISABLED)
        self.deduct_fee_button.config(state=tk.DISABLED)
        self.print_report_button.config(state=tk.DISABLED)
        self.search_button.config(state=tk.DISABLED)
