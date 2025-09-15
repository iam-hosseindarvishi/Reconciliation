from tkinter import ttk, StringVar, Entry, Text
import tkinter as tk
from tkinter import messagebox
import ttkbootstrap as ttk
from ttkbootstrap.constants import *
from config.settings import DEFAULT_FONT, DEFAULT_FONT_SIZE
import decimal

class ManualReconciliationDialog(tk.Toplevel):
    def __init__(self, parent, bank_record, accounting_records, transaction_type):
        super().__init__(parent)
        self.title("مغایرت‌یابی دستی")
        self.geometry("1200x700")
        self.bank_record = bank_record
        self.accounting_records = accounting_records
        self.transaction_type = transaction_type
        self.selected_match = None
        self.notes = ""
        
        # تنظیم فونت‌ها
        self.default_font = (DEFAULT_FONT, DEFAULT_FONT_SIZE, 'bold')
        self.button_font = (DEFAULT_FONT, DEFAULT_FONT_SIZE, 'bold')
        
        # متغیر برای جستجو
        self.search_var = StringVar()
        self.search_var.trace("w", self.filter_records)
        
        self.create_widgets()
        self.populate_bank_info()
        self.populate_accounting_table()
        
        # مرکزی کردن پنجره
        self.update_idletasks()
        width = self.winfo_width()
        height = self.winfo_height()
        x = (self.winfo_screenwidth() // 2) - (width // 2)
        y = (self.winfo_screenheight() // 2) - (height // 2)
        self.geometry('{}x{}+{}+{}'.format(width, height, x, y))

    def create_widgets(self):
        # فریم اصلی
        main_frame = ttk.Frame(self)
        main_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        # فریم بالایی برای اطلاعات رکورد بانک
        bank_frame = ttk.LabelFrame(main_frame, text="اطلاعات رکورد بانک", padding=10)
        bank_frame.pack(fill="x", padx=5, pady=5)
        
        # اطلاعات رکورد بانک
        bank_info_frame = ttk.Frame(bank_frame)
        bank_info_frame.pack(fill="x")
        
        # ستون اول اطلاعات بانک
        bank_col1 = ttk.Frame(bank_info_frame)
        bank_col1.pack(side="left", fill="x", expand=True)
        
        ttk.Label(bank_col1, text="شناسه:", font=self.default_font).grid(row=0, column=0, sticky="e", padx=5, pady=2)
        self.bank_id_label = ttk.Label(bank_col1, text="", font=self.default_font)
        self.bank_id_label.grid(row=0, column=1, sticky="w", padx=5, pady=2)
        
        ttk.Label(bank_col1, text="تاریخ:", font=self.default_font).grid(row=1, column=0, sticky="e", padx=5, pady=2)
        self.bank_date_label = ttk.Label(bank_col1, text="", font=self.default_font)
        self.bank_date_label.grid(row=1, column=1, sticky="w", padx=5, pady=2)
        
        ttk.Label(bank_col1, text="مبلغ:", font=self.default_font).grid(row=2, column=0, sticky="e", padx=5, pady=2)
        self.bank_amount_label = ttk.Label(bank_col1, text="", font=self.default_font)
        self.bank_amount_label.grid(row=2, column=1, sticky="w", padx=5, pady=2)
        
        # ستون دوم اطلاعات بانک
        bank_col2 = ttk.Frame(bank_info_frame)
        bank_col2.pack(side="left", fill="x", expand=True)
        
        ttk.Label(bank_col2, text="نوع تراکنش:", font=self.default_font).grid(row=0, column=0, sticky="e", padx=5, pady=2)
        self.bank_type_label = ttk.Label(bank_col2, text="", font=self.default_font)
        self.bank_type_label.grid(row=0, column=1, sticky="w", padx=5, pady=2)
        
        ttk.Label(bank_col2, text="شماره پیگیری:", font=self.default_font).grid(row=1, column=0, sticky="e", padx=5, pady=2)
        self.bank_tracking_label = ttk.Label(bank_col2, text="", font=self.default_font)
        self.bank_tracking_label.grid(row=1, column=1, sticky="w", padx=5, pady=2)
        
        ttk.Label(bank_col2, text="توضیحات:", font=self.default_font).grid(row=2, column=0, sticky="e", padx=5, pady=2)
        self.bank_desc_label = ttk.Label(bank_col2, text="", font=self.default_font)
        self.bank_desc_label.grid(row=2, column=1, sticky="w", padx=5, pady=2)
        
        # فریم میانی برای جستجو و لیست رکوردهای حسابداری
        accounting_frame = ttk.LabelFrame(main_frame, text="رکوردهای حسابداری", padding=10)
        accounting_frame.pack(fill="both", expand=True, padx=5, pady=5)
        
        # فریم جستجو
        search_frame = ttk.Frame(accounting_frame)
        search_frame.pack(fill="x", padx=5, pady=5)
        
        ttk.Label(search_frame, text="جستجو:", font=self.default_font).pack(side="right", padx=5)
        search_entry = ttk.Entry(search_frame, textvariable=self.search_var, font=self.default_font, width=30)
        search_entry.pack(side="right", padx=5)
        
        # جدول رکوردهای حسابداری
        self.accounting_tree = ttk.Treeview(accounting_frame, 
                                          columns=("ID", "Date", "Amount", "Type", "Tracking", "Description"), 
                                          show='headings',
                                          height=10)
        self.accounting_tree.heading("ID", text="شناسه")
        self.accounting_tree.heading("Date", text="تاریخ")
        self.accounting_tree.heading("Amount", text="مبلغ")
        self.accounting_tree.heading("Type", text="نوع")
        self.accounting_tree.heading("Tracking", text="شماره پیگیری")
        self.accounting_tree.heading("Description", text="توضیحات")
        
        self.accounting_tree.column("ID", width=50)
        self.accounting_tree.column("Date", width=100)
        self.accounting_tree.column("Amount", width=100)
        self.accounting_tree.column("Type", width=100)
        self.accounting_tree.column("Tracking", width=100)
        self.accounting_tree.column("Description", width=300)
        
        # اسکرول بار برای جدول
        scrollbar = ttk.Scrollbar(accounting_frame, orient="vertical", command=self.accounting_tree.yview)
        self.accounting_tree.configure(yscrollcommand=scrollbar.set)
        
        self.accounting_tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # فریم پایینی برای توضیحات و دکمه‌ها
        bottom_frame = ttk.Frame(main_frame)
        bottom_frame.pack(fill="x", padx=5, pady=5)
        
        # فریم توضیحات
        notes_frame = ttk.LabelFrame(bottom_frame, text="توضیحات مغایرت‌یابی", padding=10)
        notes_frame.pack(fill="x", padx=5, pady=5)
        
        self.notes_text = Text(notes_frame, height=3, font=self.default_font)
        self.notes_text.pack(fill="x", padx=5, pady=5)
        
        # فریم دکمه‌ها
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill="x", padx=5, pady=10)
        
        # دکمه حذف رکورد
        self.delete_button = ttk.Button(button_frame, text="حذف رکورد انتخاب شده", 
                                      command=self.on_delete, bootstyle=DANGER, width=20)
        self.delete_button.pack(side="right", padx=5)
        
        # دکمه کسر کارمزد (فقط برای تراکنش‌های پرداختی)
        if self.transaction_type == 'Paid_Transfer':
            self.fee_button = ttk.Button(button_frame, text="کسر کارمزد از مبلغ اصلی", 
                                        command=self.on_deduct_fee, bootstyle=INFO, width=20)
            self.fee_button.pack(side="right", padx=5)
        
        # دکمه انصراف
        self.cancel_button = ttk.Button(button_frame, text="انصراف", 
                                      command=self.on_cancel, bootstyle=SECONDARY, width=15)
        self.cancel_button.pack(side="right", padx=5)
        
        # دکمه تایید
        self.confirm_button = ttk.Button(button_frame, text="تایید مغایرت‌یابی", 
                                       command=self.on_confirm, bootstyle=SUCCESS, width=15)
        self.confirm_button.pack(side="right", padx=5)

    def populate_bank_info(self):
        """پر کردن اطلاعات رکورد بانک"""
        from utils.helpers import gregorian_to_persian
        
        self.bank_id_label.config(text=str(self.bank_record.get('id', '')))
        # تبدیل تاریخ میلادی به شمسی
        gregorian_date = str(self.bank_record.get('transaction_date', ''))
        persian_date = gregorian_to_persian(gregorian_date)
        self.bank_date_label.config(text=persian_date if persian_date else gregorian_date)
        self.bank_amount_label.config(text=f"{self.bank_record.get('amount', 0):,}")
        self.bank_type_label.config(text=self.transaction_type)
        self.bank_tracking_label.config(text=str(self.bank_record.get('tracking_number', '')))
        self.bank_desc_label.config(text=str(self.bank_record.get('description', '')))

    def populate_accounting_table(self, filtered_records=None):
        """پر کردن جدول رکوردهای حسابداری"""
        from utils.helpers import gregorian_to_persian
        
        # پاک کردن جدول قبلی
        for item in self.accounting_tree.get_children():
            self.accounting_tree.delete(item)
        
        # استفاده از رکوردهای فیلتر شده یا همه رکوردها
        records = filtered_records if filtered_records is not None else self.accounting_records
        
        # اضافه کردن رکوردها به جدول
        for record in records:
            # تبدیل تاریخ میلادی به شمسی
            gregorian_date = str(record.get('due_date', ''))
            persian_date = gregorian_to_persian(gregorian_date)
            
            self.accounting_tree.insert("", "end", values=(
                record.get('id', ''),
                persian_date if persian_date else gregorian_date,
                f"{record.get('transaction_amount', 0):,}",
                record.get('transaction_type', ''),
                record.get('transaction_number', ''),
                record.get('description', '')
            ))

    def filter_records(self, *args):
        """فیلتر کردن رکوردها بر اساس متن جستجو"""
        search_text = self.search_var.get().lower()
        if not search_text:
            self.populate_accounting_table()
            return
        
        filtered = []
        for record in self.accounting_records:
            # جستجو در تمام فیلدهای رکورد
            if any(search_text in str(value).lower() for value in record.values()):
                filtered.append(record)
        
        self.populate_accounting_table(filtered)

    def on_delete(self):
        """حذف رکورد انتخاب شده از جدول"""
        selected_item = self.accounting_tree.selection()
        if not selected_item:
            messagebox.showwarning("هشدار", "لطفاً یک رکورد را انتخاب کنید")
            return
        
        # حذف از جدول
        self.accounting_tree.delete(selected_item)
        
        # حذف از لیست رکوردها
        item = self.accounting_tree.item(selected_item)
        selected_id = item['values'][0]
        self.accounting_records = [r for r in self.accounting_records if r['id'] != selected_id]

    def on_confirm(self):
        """تایید مغایرت‌یابی"""
        selected_item = self.accounting_tree.selection()
        if not selected_item:
            messagebox.showwarning("هشدار", "لطفاً یک رکورد حسابداری را انتخاب کنید")
            return
        
        # دریافت رکورد انتخاب شده
        item = self.accounting_tree.item(selected_item)
        selected_id = item['values'][0]
        self.selected_match = next((r for r in self.accounting_records if r['id'] == selected_id), None)
        
        # دریافت توضیحات
        self.notes = self.notes_text.get("1.0", "end-1c")
        
        # علامت‌گذاری هر دو رکورد به عنوان مغایرت‌یابی شده
        try:
            from database.reconciliation.reconciliation_repository import set_reconciliation_status
            from reconciliation.save_reconciliation_result import success_reconciliation_result
            from database.bank_transaction_repository import create_bank_transaction
            
            # علامت‌گذاری رکوردها به عنوان مغایرت‌یابی شده
            set_reconciliation_status(self.bank_record['id'], self.selected_match['id'], 1)
            
            # ذخیره نتیجه مغایرت‌یابی در جدول result
            description = f"Match by user: {self.notes}" if self.notes else "Match by user"
            success_reconciliation_result(
                self.bank_record['id'], 
                self.selected_match['id'], 
                None, 
                description, 
                self.transaction_type
            )
            
            # اگر کارمزد جدا شده باشد، یک رکورد جدید برای کارمزد ایجاد می‌کنیم
            if hasattr(self.bank_record, 'fee_amount') and self.bank_record['fee_amount'] > 0:
                # ایجاد رکورد جدید برای کارمزد بانکی
                fee_data = {
                    'bank_id': self.bank_record['bank_id'],
                    'transaction_date': self.bank_record['transaction_date'],
                    'transaction_time': self.bank_record['transaction_time'] if 'transaction_time' in self.bank_record else None,
                    'amount': self.bank_record['fee_amount'],
                    'description': f"bank fee from transfer by user",
                    'reference_number': self.bank_record.get('reference_number', ''),
                    'extracted_terminal_id': self.bank_record.get('extracted_terminal_id', ''),
                    'extracted_tracking_number': self.bank_record.get('extracted_tracking_number', ''),
                    'transaction_type': 'Bank_Fee',
                    'source_card_number': self.bank_record.get('source_card_number', ''),
                    'is_reconciled': 0  # علامت‌گذاری به عنوان مغایرت‌یابی شده
                }
                
                # ایجاد رکورد کارمزد در دیتابیس
                create_bank_transaction(fee_data)
                
        except Exception as e:
            messagebox.showerror("خطا", f"خطا در ثبت نتیجه مغایرت‌یابی: {str(e)}")
        
        self.destroy()

    def on_deduct_fee(self):
        """کسر کارمزد از مبلغ اصلی"""
        selected_item = self.accounting_tree.selection()
        if not selected_item:
            messagebox.showwarning("هشدار", "لطفاً یک رکورد حسابداری را انتخاب کنید")
            return
        
        # دریافت رکورد انتخاب شده
        item = self.accounting_tree.item(selected_item)
        selected_id = item['values'][0]
        accounting_record = next((r for r in self.accounting_records if r['id'] == selected_id), None)
        
        if not accounting_record:
            return
        
        # محاسبه کارمزد (تفاوت بین مبلغ بانک و مبلغ حسابداری)
        bank_amount = decimal.Decimal(str(self.bank_record['amount']))
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
            self.bank_record['fee_amount'] = float(fee_amount)
            self.bank_record['original_amount'] = float(bank_amount)
            
            # به‌روزرسانی توضیحات
            tracking_number = self.bank_record.get('tracking_number', self.bank_record.get('reference_number', 'نامشخص'))
            fee_note = f"کارمزد تراکنش {tracking_number} به مبلغ {fee_amount:,}"
            current_notes = self.notes_text.get("1.0", "end-1c")
            if current_notes:
                self.notes_text.delete("1.0", "end")
                self.notes_text.insert("1.0", current_notes + "\n" + fee_note)
            else:
                self.notes_text.insert("1.0", fee_note)
            
            messagebox.showinfo("اطلاعات", "کارمزد با موفقیت از مبلغ اصلی کسر شد")

    def on_cancel(self):
        """انصراف از مغایرت‌یابی"""
        self.selected_match = None
        self.destroy()

    def show(self):
        """نمایش دیالوگ و بازگرداندن نتیجه"""
        self.grab_set()
        self.wait_window()
        return self.selected_match, self.notes