import ttkbootstrap as ttk
from ttkbootstrap.constants import *
from tkinter import StringVar, Toplevel
from tkinter.ttk import Combobox
from utils.constants import MELLAT_TRANSACTION_TYPES, KESHAVARZI_TRANSACTION_TYPES, MELLAT_BANK_NAME, KESHAVARZI_BANK_NAME
from database.reconciliation.reconciliation_repository import update_transaction_type
from utils.logger_config import setup_logger
from utils.helpers import gregorian_to_persian

# راه‌اندازی لاگر
logger = setup_logger('reconciliation.unknown_transactions_dialog')

class UnknownTransactionsDialog:
    def __init__(self, parent, bank_id, bank_name, transactions):
        """ایجاد دیالوگ تراکنش‌های نامشخص
        
        Args:
            parent: پنجره والد
            bank_id: شناسه بانک
            bank_name: نام بانک
            transactions: لیست تراکنش‌های نامشخص
        """
        self.parent = parent
        self.bank_id = bank_id
        self.bank_name = bank_name
        self.transactions = transactions
        self.transaction_types = {}
        self.result = False  # نتیجه دیالوگ (آیا تغییرات ذخیره شده‌اند یا خیر)
        
        # تعیین انواع تراکنش‌های مجاز بر اساس بانک
        if bank_name == MELLAT_BANK_NAME:
            self.available_types = MELLAT_TRANSACTION_TYPES
        elif bank_name == KESHAVARZI_BANK_NAME:
            self.available_types = KESHAVARZI_TRANSACTION_TYPES
        else:
            # حالت پیش‌فرض
            self.available_types = {**MELLAT_TRANSACTION_TYPES, **KESHAVARZI_TRANSACTION_TYPES}
            # حذف موارد تکراری
            self.available_types = {k: v for k, v in self.available_types.items()}
        
        # حذف UNKNOWN از لیست انواع تراکنش‌های مجاز
        if 'UNKNOWN' in self.available_types:
            del self.available_types['UNKNOWN']
        
        self.create_dialog()
    
    def create_dialog(self):
        """ایجاد رابط کاربری دیالوگ"""
        self.dialog = Toplevel(self.parent)
        self.dialog.title(f"دسته‌بندی تراکنش‌های نامشخص - بانک {self.bank_name}")
        self.dialog.geometry("900x600")
        self.dialog.resizable(True, True)
        self.dialog.transient(self.parent)  # وابسته به پنجره والد
        self.dialog.grab_set()  # مسدود کردن پنجره والد
        
        # تنظیم فونت‌ها
        self.default_font = ("B Nazanin", 12, "bold")
        self.header_font = ("B Nazanin", 14, "bold")
        self.button_font = ("B Nazanin", 12, "bold")
        
        # فریم اصلی
        main_frame = ttk.Frame(self.dialog, padding=10)
        main_frame.pack(fill="both", expand=True)
        
        # عنوان
        ttk.Label(
            main_frame, 
            text=f"لطفاً نوع تراکنش‌های نامشخص را مشخص کنید ({len(self.transactions)} تراکنش)", 
            font=self.header_font
        ).pack(pady=10)
        
        # فریم جدول
        table_frame = ttk.Frame(main_frame)
        table_frame.pack(fill="both", expand=True, pady=10)
        
        # ایجاد جدول (Treeview)
        columns = (
            "id", "date", "amount", "description", 
            "reference", "type"
        )
        
        self.tree = ttk.Treeview(
            table_frame, 
            columns=columns,
            show="headings",
            height=20
        )
        
        # تنظیم عرض ستون‌ها
        self.tree.column("id", width=50)
        self.tree.column("date", width=100)
        self.tree.column("amount", width=100)
        self.tree.column("description", width=400)
        self.tree.column("type", width=150)
        
        # تنظیم عناوین ستون‌ها
        self.tree.heading("id", text="شناسه")
        self.tree.heading("date", text="تاریخ")
        self.tree.heading("amount", text="مبلغ")
        self.tree.heading("description", text="شرح")
        # self.tree.heading("reference", text="شماره مرجع")
        self.tree.heading("type", text="نوع تراکنش")
        
        # اضافه کردن اسکرول‌بار
        scrollbar = ttk.Scrollbar(table_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        
        # قرار دادن جدول و اسکرول‌بار
        self.tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # پر کردن جدول با داده‌ها
        self.populate_table()
        
        # فریم دکمه‌ها
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill="x", pady=10)
        
        # دکمه ذخیره و ادامه
        ttk.Button(
            button_frame, 
            text="ذخیره و ادامه", 
            command=self.save_and_continue,
            bootstyle=SUCCESS,
            width=20,
            style="Bold.TButton"
        ).pack(side="left", padx=5)
        
        # دکمه انصراف
        ttk.Button(
            button_frame, 
            text="انصراف", 
            command=self.cancel,
            bootstyle=DANGER,
            width=15,
            style="Bold.TButton"
        ).pack(side="right", padx=5)
        
        # منتظر بستن دیالوگ
        self.parent.wait_window(self.dialog)
    
    def populate_table(self):
        """پر کردن جدول با داده‌های تراکنش‌های نامشخص"""
        for transaction in self.transactions:
            # تبدیل تاریخ میلادی به شمسی
            persian_date = gregorian_to_persian(transaction["transaction_date"])
            
            # افزودن ردیف به جدول
            item_id = self.tree.insert(
                "", "end",
                values=(
                    transaction["id"],
                    persian_date,
                    f"{transaction['amount']:,}",
                    transaction["description"],
                    transaction["reference_number"],
                    ""
                )
            )
            
            # ایجاد کامبوباکس برای انتخاب نوع تراکنش
            self.create_type_combobox(item_id, transaction["id"])
    
    def create_type_combobox(self, item_id, transaction_id):
        """ایجاد کامبوباکس برای انتخاب نوع تراکنش
        
        Args:
            item_id: شناسه آیتم در جدول
            transaction_id: شناسه تراکنش در دیتابیس
        """
        # ایجاد متغیر برای ذخیره انتخاب کاربر
        var = StringVar()
        self.transaction_types[transaction_id] = var
        
        # ایجاد کامبوباکس
        combo = Combobox(
            self.tree,
            textvariable=var,
            values=list(self.available_types.values()),
            state="readonly",
            font=self.default_font,
            width=15
        )
        
        # تنظیم موقعیت کامبوباکس در جدول
        bbox = self.tree.bbox(item_id, "type")
        if bbox:  # اگر آیتم قابل مشاهده است
            x, y, width, height = bbox
            combo.place(x=x, y=y, width=width, height=height)
        
        # ذخیره کامبوباکس برای دسترسی بعدی
        if not hasattr(self, "combos"):
            self.combos = []
        self.combos.append((combo, item_id, "type"))
        
        # تنظیم رویداد برای بروزرسانی موقعیت کامبوباکس‌ها هنگام اسکرول
        if not hasattr(self, "has_scroll_binding"):
            self.tree.bind("<Configure>", self.update_combobox_positions)
            self.has_scroll_binding = True
    
    def update_combobox_positions(self, event=None):
        """بروزرسانی موقعیت کامبوباکس‌ها هنگام اسکرول"""
        if hasattr(self, "combos"):
            for combo, item_id, column in self.combos:
                bbox = self.tree.bbox(item_id, column)
                if bbox:  # اگر آیتم قابل مشاهده است
                    x, y, width, height = bbox
                    combo.place(x=x, y=y, width=width, height=height)
                else:  # اگر آیتم قابل مشاهده نیست
                    combo.place_forget()
    
    def save_and_continue(self):
        """ذخیره تغییرات و ادامه فرآیند"""
        try:
            # بررسی اینکه آیا همه تراکنش‌ها دسته‌بندی شده‌اند
            missing_types = []
            for transaction_id, var in self.transaction_types.items():
                if not var.get():
                    missing_types.append(transaction_id)
            
            if missing_types:
                ttk.messagebox.showwarning(
                    "خطا",
                    f"لطفاً نوع تمام تراکنش‌ها را مشخص کنید. {len(missing_types)} تراکنش دسته‌بندی نشده است."
                )
                return
            
            # ذخیره تغییرات در دیتابیس
            for transaction_id, var in self.transaction_types.items():
                # یافتن کلید بر اساس مقدار
                transaction_type_key = None
                for key, value in self.available_types.items():
                    if value == var.get():
                        transaction_type_key = key
                        break
                
                if transaction_type_key:
                    update_transaction_type(transaction_id, transaction_type_key)
            
            logger.info(f"{len(self.transaction_types)} تراکنش نامشخص با موفقیت دسته‌بندی شد")
            self.result = True
            self.dialog.destroy()
            
        except Exception as e:
            logger.error(f"خطا در ذخیره تغییرات: {str(e)}")
            ttk.messagebox.showerror(
                "خطا",
                f"خطا در ذخیره تغییرات: {str(e)}"
            )
    
    def cancel(self):
        """انصراف از فرآیند"""
        self.result = False
        self.dialog.destroy()