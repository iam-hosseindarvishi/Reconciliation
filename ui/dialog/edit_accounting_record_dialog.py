import tkinter as tk
from tkinter import ttk, messagebox
import decimal
from utils.helpers import gregorian_to_persian, persian_to_gregorian, normalize_shamsi_date
from database.repositories.accounting import update_accounting_transaction_reconciliation_status

class EditAccountingRecordDialog(tk.Toplevel):
    """دیالوگ ویرایش رکورد حسابداری"""
    
    def __init__(self, parent, accounting_record):
        super().__init__(parent)
        self.parent = parent
        self.accounting_record = accounting_record
        self.result = False
        
        # تنظیم عنوان و ویژگی‌های پنجره
        self.title("ویرایش رکورد حسابداری")
        self.geometry("500x400")
        self.resizable(False, False)
        self.configure(bg="#f0f0f0")
        
        # تنظیم به عنوان پنجره مودال
        self.transient(parent)
        self.grab_set()
        
        # حذف دسترسی به پایگاه داده چون از توابع مستقیم استفاده می‌کنیم
        
        # ایجاد ویجت‌ها
        self.create_widgets()
        
        # نمایش اطلاعات فعلی
        self.load_record_data()
        
        # منتظر بستن پنجره می‌مانیم
        self.wait_window(self)
    
    def create_widgets(self):
        """ایجاد ویجت‌های دیالوگ"""
        # فریم اصلی
        main_frame = ttk.Frame(self, padding=10)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # فونت‌ها
        self.default_font = ('B Nazanin', 11)
        
        # === فیلدهای ویرایش ===
        # شناسه (غیرقابل ویرایش)
        ttk.Label(main_frame, text="شناسه:", font=self.default_font).grid(row=0, column=1, sticky="e", padx=5, pady=5)
        self.id_var = tk.StringVar()
        ttk.Entry(main_frame, textvariable=self.id_var, state="readonly", font=self.default_font).grid(row=0, column=0, sticky="ew", padx=5, pady=5)
        
        # شماره پیگیری
        ttk.Label(main_frame, text="شماره پیگیری:", font=self.default_font).grid(row=1, column=1, sticky="e", padx=5, pady=5)
        self.tracking_number_var = tk.StringVar()
        ttk.Entry(main_frame, textvariable=self.tracking_number_var, font=self.default_font).grid(row=1, column=0, sticky="ew", padx=5, pady=5)
        
        # تاریخ (شمسی)
        ttk.Label(main_frame, text="تاریخ (شمسی):", font=self.default_font).grid(row=2, column=1, sticky="e", padx=5, pady=5)
        self.date_var = tk.StringVar()
        ttk.Entry(main_frame, textvariable=self.date_var, font=self.default_font).grid(row=2, column=0, sticky="ew", padx=5, pady=5)
        
        # مبلغ
        ttk.Label(main_frame, text="مبلغ:", font=self.default_font).grid(row=3, column=1, sticky="e", padx=5, pady=5)
        self.amount_var = tk.StringVar()
        ttk.Entry(main_frame, textvariable=self.amount_var, font=self.default_font).grid(row=3, column=0, sticky="ew", padx=5, pady=5)
        
        # نوع تراکنش
        ttk.Label(main_frame, text="نوع تراکنش:", font=self.default_font).grid(row=4, column=1, sticky="e", padx=5, pady=5)
        self.transaction_type_var = tk.StringVar()
        self.transaction_type_combo = ttk.Combobox(main_frame, textvariable=self.transaction_type_var,
                                                  font=self.default_font, state="readonly")
        self.transaction_type_combo['values'] = ['Pos', 'Received Transfer', 'Paid Transfer',
                                                'Received Check', 'Paid Check', 'Bank Fees']
        self.transaction_type_combo.grid(row=4, column=0, sticky="ew", padx=5, pady=5)
        
        # توضیحات
        ttk.Label(main_frame, text="توضیحات:", font=self.default_font).grid(row=5, column=1, sticky="ne", padx=5, pady=5)
        self.description_text = tk.Text(main_frame, height=5, width=30, font=self.default_font)
        self.description_text.grid(row=5, column=0, sticky="ew", padx=5, pady=5)
        
        # === دکمه‌ها ===
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=6, column=0, columnspan=2, pady=10)
        
        ttk.Button(button_frame, text="ذخیره", command=self.save_changes, style='Default.TButton').pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="انصراف", command=self.cancel, style='Default.TButton').pack(side=tk.LEFT, padx=5)
    
    def load_record_data(self):
        """بارگذاری اطلاعات رکورد در فیلدها"""
        # شناسه
        self.id_var.set(str(self.accounting_record['id']))
        
        # شماره پیگیری
        if self.accounting_record.get('transaction_number'):
            self.tracking_number_var.set(str(self.accounting_record['transaction_number']))
        elif self.accounting_record.get('tracking_number'):
            self.tracking_number_var.set(str(self.accounting_record['tracking_number']))
        
        # تاریخ (تبدیل به شمسی)
        date_field = self.accounting_record.get('due_date') or self.accounting_record.get('transaction_date') or self.accounting_record.get('date')
        if date_field:
            shamsi_date = gregorian_to_persian(date_field)
            self.date_var.set(shamsi_date)
        else:
            self.date_var.set('')  # اگر تاریخ وجود نداشت، خالی بگذار
        
        # مبلغ
        amount_field = self.accounting_record.get('transaction_amount') or self.accounting_record.get('amount')
        if amount_field:
            self.amount_var.set(str(amount_field))
        
        # نوع تراکنش
        if self.accounting_record.get('transaction_type'):
            self.transaction_type_var.set(self.accounting_record['transaction_type'])
        
        # توضیحات
        if self.accounting_record.get('description'):
            self.description_text.insert("1.0", self.accounting_record['description'])
    
    def save_changes(self):
        """ذخیره تغییرات"""
        try:
            # دریافت مقادیر از فیلدها
            tracking_number = self.tracking_number_var.get().strip()
            shamsi_date = self.date_var.get().strip()
            amount_str = self.amount_var.get().strip()
            transaction_type = self.transaction_type_var.get().strip()
            description = self.description_text.get("1.0", "end-1c").strip()
            
            # اعتبارسنجی داده‌ها
            if not shamsi_date:
                messagebox.showerror("خطا", "لطفاً تاریخ را وارد کنید")
                return
            
            if not amount_str:
                messagebox.showerror("خطا", "لطفاً مبلغ را وارد کنید")
                return
            
            # تبدیل تاریخ شمسی به میلادی
            try:
                normalized_date = normalize_shamsi_date(shamsi_date)
                gregorian_date = persian_to_gregorian(normalized_date)
            except Exception as e:
                messagebox.showerror("خطا", f"فرمت تاریخ نامعتبر است: {str(e)}")
                return
            
            # تبدیل مبلغ به عدد
            try:
                amount = float(amount_str.replace(',', ''))
            except ValueError:
                messagebox.showerror("خطا", "مبلغ باید عدد باشد")
                return
            
            # ایجاد دیکشنری برای به‌روزرسانی - حفظ همه فیلدها حتی خالی‌ها
            updated_data = {
                'transaction_number': tracking_number,
                'due_date': gregorian_date,
                'transaction_amount': amount,
                'transaction_type': transaction_type,
                'description': description
            }
            
            # به‌روزرسانی رکورد در پایگاه داده
            update_accounting_transaction_reconciliation_status(self.accounting_record['id'], updated_data)
            
            messagebox.showinfo("اطلاعات", "رکورد حسابداری با موفقیت به‌روزرسانی شد")
            self.result = True
            self.destroy()
            
        except Exception as e:
            messagebox.showerror("خطا", f"خطا در به‌روزرسانی رکورد: {str(e)}")
    
    def cancel(self):
        """انصراف و بستن دیالوگ"""
        self.result = False
        self.destroy()