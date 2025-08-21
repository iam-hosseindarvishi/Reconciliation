import tkinter as tk
from tkinter import ttk, messagebox
import os
import queue
import threading
import decimal
from tkinter.ttk import Combobox
from datetime import datetime
import logging
from utils.helpers import gregorian_to_persian, persian_to_gregorian
from database.banks_repository import get_all_banks
from database.bank_transaction_repository import get_unreconciled_transactions_by_bank as get_unreconciled_bank_records
from database.accounting_repository import get_transactions_by_date_and_type as get_unreconciled_accounting_records_by_date
from database.reconciliation_results_repository import create_reconciliation_result as save_reconciliation_result
from ui.dialog.manual_reconciliation_dialog import ManualReconciliationDialog
from ui.dialog.edit_bank_record_dialog import EditBankRecordDialog
from ui.dialog.edit_accounting_record_dialog import EditAccountingRecordDialog
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import tempfile
import subprocess

class ManualReconciliationTab(ttk.Frame):
    """تب مغایرت‌یابی دستی"""
    
    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent
        
        # تنظیم فونت‌ها
        self.default_font = ('B Nazanin', 11)
        self.header_font = ('B Nazanin', 12, 'bold')
        
        # ایجاد متغیرهای مورد نیاز
        self.selected_bank_var = tk.StringVar()
        
        # ایجاد ویجت‌ها
        self.create_widgets()
        
        # ایجاد ویجت‌ها
        self.create_widgets()
        
        # بارگذاری لیست بانک‌ها
        self.load_banks_to_combobox()
        
        # متغیرهای داده
        self.bank_records = []
        self.accounting_records = []
        self.selected_bank_record = None
        self.selected_accounting_record = None
    
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
        self.bank_combobox.configure(font=self.default_font)
        self.bank_combobox.pack(side=tk.RIGHT, padx=5)
        self.bank_combobox.bind("<<ComboboxSelected>>", lambda event: self.show_bank_records())
        
        # دکمه نمایش اطلاعات
        self.show_data_button = ttk.Button(top_frame, text="نمایش اطلاعات", command=self.show_bank_records)
        self.show_data_button.pack(side=tk.RIGHT, padx=5)
        
        # اضافه کردن رویداد تغییر مقدار کامبوباکس
        self.bank_combobox.bind("<<ComboboxSelected>>", lambda event: self.show_bank_records())
        
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
                                     columns=("id", "tracking_number", "date", "amount", "description", "status"),
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
        self.bank_tree.heading("status", text="وضعیت")
        
        # تنظیم عرض ستون‌ها
        self.bank_tree.column("id", width=50, anchor=tk.CENTER)
        self.bank_tree.column("tracking_number", width=120, anchor=tk.CENTER)
        self.bank_tree.column("date", width=100, anchor=tk.CENTER)
        self.bank_tree.column("amount", width=120, anchor=tk.CENTER)
        self.bank_tree.column("description", width=200)
        self.bank_tree.column("status", width=100, anchor=tk.CENTER)
        
        self.bank_tree.pack(fill=tk.BOTH, expand=True)
        
        # رویداد انتخاب آیتم در Treeview بانک
        self.bank_tree.bind("<<TreeviewSelect>>", self.on_bank_record_selected)
        
        # دکمه ویرایش رکورد بانک
        bank_buttons_frame = ttk.Frame(bank_frame)
        bank_buttons_frame.pack(fill=tk.X, pady=5)
        
        self.edit_bank_button = ttk.Button(bank_buttons_frame, text="ویرایش رکورد", command=self.edit_bank_record)
        self.edit_bank_button.pack(side=tk.RIGHT, padx=5)
        
        # === بخش جستجو ===
        search_frame = ttk.Frame(main_frame)
        search_frame.pack(fill=tk.X, pady=5)
        
        self.search_button = ttk.Button(search_frame, text="جستجوی رکوردهای حسابداری", command=self.search_accounting_records)
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
                                          columns=("id", "tracking_number", "date", "amount", "description", "type"),
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
        
        # تنظیم عرض ستون‌ها
        self.accounting_tree.column("id", width=50, anchor=tk.CENTER)
        self.accounting_tree.column("tracking_number", width=120, anchor=tk.CENTER)
        self.accounting_tree.column("date", width=100, anchor=tk.CENTER)
        self.accounting_tree.column("amount", width=120, anchor=tk.CENTER)
        self.accounting_tree.column("description", width=200)
        self.accounting_tree.column("type", width=100, anchor=tk.CENTER)
        
        self.accounting_tree.pack(fill=tk.BOTH, expand=True)
        
        # === بخش دکمه‌های عملیات ===
        operations_frame = ttk.Frame(main_frame)
        operations_frame.pack(fill=tk.X, pady=5)
        
        # دکمه مغایرت‌گیری سریع
        self.quick_reconcile_button = ttk.Button(operations_frame, text="مغایرت‌گیری سریع", command=self.quick_reconcile)
        self.quick_reconcile_button.pack(side=tk.RIGHT, padx=5)
        
        # دکمه کسر کارمزد
        self.deduct_fee_button = ttk.Button(operations_frame, text="کسر کارمزد", command=self.deduct_fee)
        self.deduct_fee_button.pack(side=tk.RIGHT, padx=5)
        
        # دکمه چاپ گزارش
        self.print_report_button = ttk.Button(operations_frame, text="چاپ گزارش", command=self.print_report)
        self.print_report_button.pack(side=tk.RIGHT, padx=5)
        
        # دکمه حذف رکورد حسابداری
        self.delete_accounting_button = ttk.Button(operations_frame, text="حذف رکورد حسابداری", command=self.delete_accounting_record)
        self.delete_accounting_button.pack(side=tk.RIGHT, padx=5)
        
        # دکمه حذف رکورد بانک
        self.delete_bank_button = ttk.Button(operations_frame, text="حذف رکورد بانک", command=self.delete_bank_record)
        self.delete_bank_button.pack(side=tk.RIGHT, padx=5)
        
        # دکمه ویرایش رکورد حسابداری
        self.edit_accounting_button = ttk.Button(operations_frame, text="ویرایش رکورد حسابداری", command=self.edit_accounting_record)
        self.edit_accounting_button.pack(side=tk.RIGHT, padx=5)
        
        # غیرفعال کردن دکمه‌های عملیات در ابتدا
        self.disable_operation_buttons()
    
    def load_banks_to_combobox(self):
        """بارگذاری لیست بانک‌ها در کامبوباکس"""
        banks = get_all_banks()
        bank_names = [bank['bank_name'] for bank in banks]  # استفاده از نام ستون برای دسترسی به نام بانک
        
        # بررسی و نمایش تعداد بانک‌ها در لاگ
        print(f"تعداد بانک‌ها: {len(banks)}")
        for bank in banks:
            print(f"بانک: {bank['bank_name']} (شناسه: {bank['id']})")
            
        self.bank_combobox['values'] = bank_names
        if bank_names:
            self.bank_combobox.current(0)
            # تنظیم متغیر انتخاب شده با مقدار اولیه
            self.selected_bank_var.set(bank_names[0])
            # نمایش رکوردهای بانک انتخاب شده به صورت خودکار
            self.show_bank_records()
    
    def show_bank_records(self):
        """نمایش رکوردهای مغایرت‌گیری نشده بانک انتخاب شده"""
        selected_bank = self.selected_bank_var.get()
        if not selected_bank:
            messagebox.showwarning("هشدار", "لطفاً یک بانک را انتخاب کنید")
            return
        
        # پاک کردن داده‌های قبلی
        self.clear_trees()
        
        # دریافت شناسه بانک بر اساس نام بانک
        banks = get_all_banks()
        bank_id = None
        for bank in banks:
            if bank['bank_name'] == selected_bank:  # مقایسه با نام بانک
                bank_id = bank['id']  # شناسه بانک
                break
        
        if not bank_id:
            messagebox.showwarning("هشدار", "بانک انتخاب شده یافت نشد")
            return
        
        # دریافت رکوردهای مغایرت‌گیری نشده بانک
        self.bank_records = get_unreconciled_bank_records(bank_id)
        
        # نمایش رکوردها در Treeview
        for record in self.bank_records:
            # تبدیل تاریخ میلادی به شمسی
            shamsi_date = gregorian_to_persian(record['transaction_date'])
            
            # فرمت‌بندی مبلغ
            amount = f"{record['amount']:,}"
            
            # وضعیت
            status = "مغایرت‌گیری نشده"
            
            self.bank_tree.insert("", tk.END, values=(
                record['id'],
                record.get('extracted_tracking_number', ''),
                shamsi_date,
                amount,
                record.get('description', ''),
                status
            ))
        
        # نمایش پیام مناسب
        if not self.bank_records:
            messagebox.showinfo("اطلاعات", f"هیچ رکورد مغایرت‌گیری نشده‌ای برای بانک {selected_bank} یافت نشد")
        else:
            messagebox.showinfo("اطلاعات", f"تعداد {len(self.bank_records)} رکورد مغایرت‌گیری نشده برای بانک {selected_bank} یافت شد")
    
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
        self.delete_bank_button.config(state=tk.NORMAL)
        self.search_button.config(state=tk.NORMAL)
        
        # پاک کردن لیست رکوردهای حسابداری
        self.clear_accounting_tree()
    
    def search_accounting_records(self):
        """جستجوی رکوردهای حسابداری مرتبط با رکورد بانک انتخاب شده"""
        if not self.selected_bank_record:
            messagebox.showwarning("هشدار", "لطفاً یک رکورد بانک را انتخاب کنید")
            return
        
        # پاک کردن لیست قبلی
        self.clear_accounting_tree()
        
        # دریافت تاریخ رکورد بانک
        bank_date = self.selected_bank_record['transaction_date']
        
        # دریافت نوع تراکنش بانک (دریافتی یا پرداختی)
        transaction_type = 'received' if self.selected_bank_record['amount'] > 0 else 'paid'
        
        # دریافت رکوردهای حسابداری مغایرت‌گیری نشده در تاریخ رکورد بانک
        self.accounting_records = get_unreconciled_accounting_records_by_date(
            [bank_date], 
            transaction_type=transaction_type
        )
        
        # نمایش رکوردها در Treeview
        for record in self.accounting_records:
            # تبدیل تاریخ میلادی به شمسی
            shamsi_date = gregorian_to_persian(record['transaction_date'])
            
            # فرمت‌بندی مبلغ
            amount = f"{record['transaction_amount']:,}"
            
            # نوع تراکنش
            type_text = "دریافتی" if record['transaction_type'] == 'received' else "پرداختی"
            
            self.accounting_tree.insert("", tk.END, values=(
                record['id'],
                record.get('tracking_number', ''),
                shamsi_date,
                amount,
                record.get('description', ''),
                type_text
            ))
        
        # فعال کردن دکمه‌های عملیات
        if self.accounting_records:
            self.quick_reconcile_button.config(state=tk.NORMAL)
            self.deduct_fee_button.config(state=tk.NORMAL)
            self.print_report_button.config(state=tk.NORMAL)
            self.edit_accounting_button.config(state=tk.NORMAL)
            self.delete_accounting_button.config(state=tk.NORMAL)
        else:
            messagebox.showinfo("اطلاعات", "هیچ رکورد حسابداری مغایرت‌گیری نشده‌ای در تاریخ مورد نظر یافت نشد")
    
    def quick_reconcile(self):
        """مغایرت‌گیری سریع بین رکورد بانک و رکورد حسابداری انتخاب شده"""
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
            save_reconciliation_result(
                None,  # pos_id
                accounting_id, 
                bank_id,
                "مغایرت‌گیری دستی از طریق تب مغایرت‌یابی دستی",
                'manual_match'
            )
            
            messagebox.showinfo("اطلاعات", "مغایرت‌گیری با موفقیت انجام شد")
            
            # به‌روزرسانی لیست‌ها
            self.show_bank_records()
            self.clear_accounting_tree()
            self.disable_operation_buttons()
    
    def deduct_fee(self):
        """کسر کارمزد از مبلغ رکورد بانک"""
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
            # اضافه کردن اطلاعات کارمزد به رکورد بانک
            bank_record['fee_amount'] = float(fee_amount)
            bank_record['original_amount'] = float(bank_amount)
            
            # ثبت مغایرت‌گیری با کارمزد
            self.reconciliation_repo.mark_as_reconciled_with_fee(
                bank_id, 
                accounting_id, 
                float(fee_amount),
                'manual_match_with_fee',
                notes=f"مغایرت‌گیری دستی با کسر کارمزد به مبلغ {fee_amount:,} ریال"
            )
            
            messagebox.showinfo("اطلاعات", "مغایرت‌گیری با کسر کارمزد با موفقیت انجام شد")
            
            # به‌روزرسانی لیست‌ها
            self.show_bank_records()
            self.clear_accounting_tree()
            self.disable_operation_buttons()
    
    def print_report(self):
        """چاپ گزارش به صورت PDF"""
        selected_bank_item = self.bank_tree.selection()
        
        if not selected_bank_item:
            messagebox.showwarning("هشدار", "لطفاً یک رکورد بانک را انتخاب کنید")
            return
        
        # دریافت رکورد بانک انتخاب شده
        bank_item = self.bank_tree.item(selected_bank_item[0])
        bank_id = bank_item['values'][0]
        bank_record = next((r for r in self.bank_records if r['id'] == bank_id), None)
        
        if not bank_record:
            return
        
        # ایجاد فایل PDF موقت
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as temp_file:
            pdf_path = temp_file.name
        
        # ثبت فونت فارسی
        pdfmetrics.registerFont(TTFont('BNazanin', 'fonts/BNazanin.ttf'))
        
        # ایجاد PDF
        c = canvas.Canvas(pdf_path, pagesize=A4)
        c.setFont('BNazanin', 12)
        
        # عنوان گزارش
        c.drawRightString(500, 800, "گزارش مغایرت‌یابی دستی")
        c.drawRightString(500, 780, f"تاریخ: {gregorian_to_persian(datetime.now().strftime('%Y-%m-%d'))}")
        
        # اطلاعات رکورد بانک
        c.drawRightString(500, 750, "اطلاعات رکورد بانک:")
        c.drawRightString(500, 730, f"شناسه: {bank_record['id']}")
        c.drawRightString(500, 710, f"شماره پیگیری: {bank_record.get('tracking_number', 'نامشخص')}")
        c.drawRightString(500, 690, f"تاریخ: {gregorian_to_persian(bank_record['date'])}")
        c.drawRightString(500, 670, f"مبلغ: {bank_record['amount']:,} ریال")
        c.drawRightString(500, 650, f"توضیحات: {bank_record.get('description', '')}")
        
        # اطلاعات رکوردهای حسابداری
        c.drawRightString(500, 620, "رکوردهای حسابداری مرتبط:")
        
        y_position = 600
        for i, record in enumerate(self.accounting_records, 1):
            c.drawRightString(500, y_position, f"رکورد {i}:")
            c.drawRightString(480, y_position - 20, f"شناسه: {record['id']}")
            c.drawRightString(480, y_position - 40, f"شماره پیگیری: {record.get('tracking_number', 'نامشخص')}")
            c.drawRightString(480, y_position - 60, f"تاریخ: {gregorian_to_persian(record['transaction_date'])}")
            c.drawRightString(480, y_position - 80, f"مبلغ: {record['transaction_amount']:,} ریال")
            c.drawRightString(480, y_position - 100, f"توضیحات: {record.get('description', '')}")
            
            y_position -= 120
            
            # اگر به پایین صفحه رسیدیم، صفحه جدید ایجاد کنیم
            if y_position < 100:
                c.showPage()
                c.setFont('BNazanin', 12)
                y_position = 750
        
        c.save()
        
        # باز کردن فایل PDF
        try:
            subprocess.Popen([pdf_path], shell=True)
        except Exception as e:
            messagebox.showerror("خطا", f"خطا در باز کردن فایل PDF: {str(e)}")
    
    def delete_accounting_record(self):
        """حذف رکورد حسابداری انتخاب شده"""
        selected_item = self.accounting_tree.selection()
        if not selected_item:
            messagebox.showwarning("هشدار", "لطفاً یک رکورد حسابداری را انتخاب کنید")
            return
        
        # دریافت آیتم انتخاب شده
        item = self.accounting_tree.item(selected_item[0])
        record_id = item['values'][0]
        
        # تأیید از کاربر
        confirm = messagebox.askyesno(
            "تأیید حذف", 
            "آیا از حذف این رکورد حسابداری اطمینان دارید؟\n" +
            "این عملیات غیرقابل بازگشت است!"
        )
        
        if confirm:
            # حذف رکورد
            self.accounting_repo.delete_accounting_record(record_id)
            
            messagebox.showinfo("اطلاعات", "رکورد حسابداری با موفقیت حذف شد")
            
            # به‌روزرسانی لیست
            self.search_accounting_records()
    
    def delete_bank_record(self):
        """حذف رکورد بانک انتخاب شده"""
        selected_item = self.bank_tree.selection()
        if not selected_item:
            messagebox.showwarning("هشدار", "لطفاً یک رکورد بانک را انتخاب کنید")
            return
        
        # دریافت آیتم انتخاب شده
        item = self.bank_tree.item(selected_item[0])
        record_id = item['values'][0]
        
        # تأیید از کاربر
        confirm = messagebox.askyesno(
            "تأیید حذف", 
            "آیا از حذف این رکورد بانک اطمینان دارید؟\n" +
            "این عملیات غیرقابل بازگشت است!"
        )
        
        if confirm:
            # حذف رکورد
            self.bank_transaction_repo.delete_bank_record(record_id)
            
            messagebox.showinfo("اطلاعات", "رکورد بانک با موفقیت حذف شد")
            
            # به‌روزرسانی لیست
            self.show_bank_records()
            self.clear_accounting_tree()
            self.disable_operation_buttons()
    
    def edit_bank_record(self):
        """ویرایش رکورد بانک انتخاب شده"""
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
                self.show_bank_records()
    
    def edit_accounting_record(self):
        """ویرایش رکورد حسابداری انتخاب شده"""
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
                self.search_accounting_records()
    
    def clear_trees(self):
        """پاک کردن هر دو Treeview"""
        self.clear_bank_tree()
        self.clear_accounting_tree()
        self.disable_operation_buttons()
    
    def clear_bank_tree(self):
        """پاک کردن Treeview بانک"""
        for item in self.bank_tree.get_children():
            self.bank_tree.delete(item)
    
    def clear_accounting_tree(self):
        """پاک کردن Treeview حسابداری"""
        for item in self.accounting_tree.get_children():
            self.accounting_tree.delete(item)
        self.accounting_records = []
    
    def disable_operation_buttons(self):
        """غیرفعال کردن دکمه‌های عملیات"""
        self.edit_bank_button.config(state=tk.DISABLED)
        self.edit_accounting_button.config(state=tk.DISABLED)
        self.quick_reconcile_button.config(state=tk.DISABLED)
        self.deduct_fee_button.config(state=tk.DISABLED)
        self.print_report_button.config(state=tk.DISABLED)
        self.delete_accounting_button.config(state=tk.DISABLED)
        self.delete_bank_button.config(state=tk.DISABLED)
        self.search_button.config(state=tk.DISABLED)