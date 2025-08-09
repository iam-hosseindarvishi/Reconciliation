import os
import logging
import threading
import ttkbootstrap as ttk
from ttkbootstrap.constants import *
from tkinter import StringVar, filedialog, font
from tkinter.ttk import Combobox
from ttkbootstrap.scrolled import ScrolledText
from database.banks_repository import get_all_banks
from utils.mellat_bank_processor import process_mellat_bank_file
from utils.pos_excel_importer import process_pos_files
from utils.accounting_excel_importer import import_accounting_excel
from config.settings import (
    DATA_DIR, DEFAULT_FONT, DEFAULT_FONT_SIZE,
    HEADER_FONT_SIZE, BUTTON_FONT_SIZE
)



# کلاس برای نمایش لاگ‌ها در UI
class UIHandler(logging.Handler):
    def __init__(self, text_widget):
        super().__init__()
        self.text_widget = text_widget
        
    def emit(self, record):
        msg = self.format(record) + '\n'
        self.text_widget.insert('end', msg)
        self.text_widget.see('end')

class DataEntryTab(ttk.Frame):
    def __init__(self, parent):
        super().__init__(parent)
        self.setup_logging()
        self.pos_folder_var = StringVar()
        self.accounting_file_var = StringVar()
        self.bank_file_var = StringVar()
        self.selected_bank_var = StringVar()
        self.status_var = StringVar(value="منتظر شروع فرآیند...")
        self.create_widgets()
        self.load_banks_to_combobox()
        
        # ذخیره مقدار انتخاب شده قبلی
        self.previous_bank_selection = None
        
    def setup_logging(self):
        """راه‌اندازی سیستم لاگینگ"""
        os.makedirs(DATA_DIR, exist_ok=True)
        
        # تنظیمات کلی لاگر
        self.logger = logging.getLogger('reconciliation')
        self.logger.setLevel(logging.INFO)
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        
        # لاگر برای فایل خطاها
        error_handler = logging.FileHandler(os.path.join(DATA_DIR, 'error.txt'), encoding='utf-8')
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(formatter)
        
        # لاگر برای فایل لاگ عمومی
        file_handler = logging.FileHandler(os.path.join(DATA_DIR, 'Log.txt'), encoding='utf-8')
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
        ENTRY_WIDTH = 60

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

        main_frame = ttk.Frame(self)
        main_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        # === بخش پوز ===
        pos_frame = ttk.LabelFrame(self, text="ورود اطلاعات پوز", style='Header.TLabelframe')
        pos_frame.pack(fill="x", pady=5)
        pos_frame.columnconfigure(1, weight=1)
        ttk.Label(pos_frame, text="آدرس پوشه فایل‌های پوز:", style='Default.TLabel').grid(row=0, column=0, sticky="w", padx=5, pady=5)
        pos_entry = ttk.Entry(pos_frame, textvariable=self.pos_folder_var, width=ENTRY_WIDTH, state="readonly", style='Default.TEntry')
        pos_entry.grid(row=0, column=1, sticky="ew", padx=5, pady=5)
        ttk.Button(pos_frame, text="انتخاب پوشه", command=self.select_pos_folder, bootstyle=PRIMARY, width=14, style='Bold.TButton').grid(row=0, column=2, padx=5, pady=5)

        # === بخش حسابداری ===
        acc_frame = ttk.LabelFrame(self, text="ورود اطلاعات حسابداری", style='Header.TLabelframe')
        acc_frame.pack(fill="x", pady=5)
        acc_frame.columnconfigure(1, weight=1)
        ttk.Label(acc_frame, text="فایل اکسل سیستم حسابداری:", style='Default.TLabel').grid(row=0, column=0, sticky="w", padx=5, pady=5)
        acc_entry = ttk.Entry(acc_frame, textvariable=self.accounting_file_var, width=ENTRY_WIDTH, state="readonly", style='Default.TEntry')
        acc_entry.grid(row=0, column=1, sticky="ew", padx=5, pady=5)
        ttk.Button(acc_frame, text="انتخاب فایل", command=self.select_accounting_file, bootstyle=PRIMARY, width=14, style='Bold.TButton').grid(row=0, column=2, padx=5, pady=5)

        # === بخش بانک ===
        bank_frame = ttk.LabelFrame(self, text="ورود اطلاعات بانک", style='Header.TLabelframe')
        bank_frame.pack(fill="x", pady=5)
        bank_frame.columnconfigure(1, weight=1)
        ttk.Label(bank_frame, text="فایل اکسل بانک:", style='Default.TLabel').grid(row=0, column=0, sticky="w", padx=5, pady=5)
        bank_entry = ttk.Entry(bank_frame, textvariable=self.bank_file_var, width=ENTRY_WIDTH, state="readonly", style='Default.TEntry')
        bank_entry.grid(row=0, column=1, sticky="ew", padx=5, pady=5)
        ttk.Button(bank_frame, text="انتخاب فایل", command=self.select_bank_file, bootstyle=PRIMARY, width=14, style='Bold.TButton').grid(row=0, column=2, padx=5, pady=5)

        # === کنترل‌های پایین ===
        control_frame = ttk.Frame(self)
        control_frame.pack(fill="x", pady=5)
        control_frame.columnconfigure(1, weight=1)

        # === Combobox و Label بانک ===
        ttk.Label(control_frame, text="انتخاب بانک:", style='Default.TLabel').grid(row=0, column=0, sticky="e", padx=5, pady=5)
        # تنظیم فونت کامبوباکس به صورت مستقیم چون استایل ttk روی آن اثر نمی‌کند
        self.bank_combobox = Combobox(control_frame, textvariable=self.selected_bank_var, state="readonly", width=30)
        self.bank_combobox.configure(font=self.default_font)
        self.bank_combobox.grid(row=0, column=1, sticky="w", padx=5, pady=5)

        # === دکمه‌های کنترل ===
        btn_frame = ttk.Frame(control_frame)
        btn_frame.grid(row=0, column=2, sticky="e", padx=5, pady=5)
        ttk.Button(btn_frame, text="شروع فرآیند", command=self.start_process, bootstyle=SUCCESS, width=16, style='Bold.TButton').pack(side="left", padx=5)
        ttk.Button(btn_frame, text="پاک کردن ورودی‌ها", command=self.clear_entries, bootstyle=DANGER, width=16, style='Bold.TButton').pack(side="left", padx=5)

        # === فریم وضعیت و نوارهای پیشرفت ===
        progress_frame = ttk.LabelFrame(self, text="پیشرفت عملیات", style='Header.TLabelframe')
        progress_frame.pack(fill="x", pady=5, padx=10)
        
        # نوار پیشرفت کلی
        ttk.Label(progress_frame, text="پیشرفت کلی:", anchor="w", style='Default.TLabel').pack(fill="x", padx=5)
        
        overall_progress_container = ttk.Frame(progress_frame)
        overall_progress_container.pack(fill="x", padx=10, pady=(0, 10))
        
        self.overall_progressbar = ttk.Progressbar(
            overall_progress_container, 
            mode="determinate",
            maximum=100,
            bootstyle="success-striped"
        )
        self.overall_progressbar.pack(fill="x", ipady=10)  # از ipady برای افزایش ارتفاع استفاده می‌کنیم
        
        # نوار پیشرفت جزئی
        ttk.Label(progress_frame, text="پیشرفت جزئی:", anchor="w", style='Default.TLabel').pack(fill="x", padx=5)
        
        detailed_progress_container = ttk.Frame(progress_frame)
        detailed_progress_container.pack(fill="x", padx=10, pady=(0, 10))
        
        self.detailed_progressbar = ttk.Progressbar(
            detailed_progress_container,
            mode="determinate",
            maximum=100,
            bootstyle="info-striped"
        )
        self.detailed_progressbar.pack(fill="x", ipady=10)  # از ipady برای افزایش ارتفاع استفاده می‌کنیم
        
        # === کادر لاگ ===
        log_frame = ttk.LabelFrame(self, text="گزارش عملیات", style='Header.TLabelframe')
        log_frame.pack(fill="both", expand=True, pady=5, padx=10)
        
        # برای ScrolledText می‌توانیم مستقیماً از font استفاده کنیم
        self.log_text = ScrolledText(log_frame, height=15, font=self.log_font)  # افزایش ارتفاع
        self.log_text.pack(fill="both", expand=True, padx=10, pady=10)
        
        # اضافه کردن UI handler به logger
        ui_handler = UIHandler(self.log_text)
        ui_handler.setFormatter(logging.Formatter('%(asctime)s - %(message)s'))
        self.logger.addHandler(ui_handler)

    def select_pos_folder(self):
        folder = filedialog.askdirectory(title="انتخاب پوشه فایل‌های پوز")
        if folder:
            self.pos_folder_var.set(folder)

    def select_accounting_file(self):
        file = filedialog.askopenfilename(title="انتخاب فایل اکسل حسابداری", filetypes=[("Excel files", "*.xlsx *.xls")])
        if file:
            self.accounting_file_var.set(file)

    def select_bank_file(self):
        file = filedialog.askopenfilename(title="انتخاب فایل اکسل بانک", filetypes=[("Excel files", "*.xlsx *.xls")])
        if file:
            self.bank_file_var.set(file)

    def load_banks_to_combobox(self):
        """بارگذاری لیست بانک‌ها در کامبوباکس"""
        try:
            # ذخیره انتخاب فعلی
            current_selection = self.selected_bank_var.get()
            
            banks = get_all_banks()
            self.banks_dict = {bank[1]: bank[0] for bank in banks}  # نام بانک: شناسه
            self.bank_combobox['values'] = list(self.banks_dict.keys())
            
            # اگر انتخاب قبلی وجود داشته و هنوز در لیست هست، آن را حفظ کن
            if current_selection and current_selection in self.banks_dict:
                self.selected_bank_var.set(current_selection)
            # در غیر این صورت، اولین مورد را انتخاب کن اگر لیست خالی نیست
            elif self.banks_dict:
                self.bank_combobox.current(0)
        except Exception as e:
            self.logger.error(f"خطا در بارگذاری لیست بانک‌ها: {str(e)}")

    def validate_inputs(self):
        """اعتبارسنجی ورودی‌ها"""
        if not self.selected_bank_var.get():
            self.logger.error("لطفاً یک بانک انتخاب کنید")
            return False
            
        # حداقل یکی از فایل‌ها باید انتخاب شده باشد
        has_pos = bool(self.pos_folder_var.get())
        has_accounting = bool(self.accounting_file_var.get())
        has_bank = bool(self.bank_file_var.get())
        
        if not (has_pos or has_accounting or has_bank):
            self.logger.error("لطفاً حداقل یکی از موارد زیر را انتخاب کنید:\n- پوشه فایل‌های پوز\n- فایل حسابداری\n- فایل بانک")
            return False
            
        return True

    def process_thread(self):
        """اجرای فرآیند پردازش در thread جداگانه"""
        try:
            bank_name = self.selected_bank_var.get()
            bank_id = self.banks_dict[bank_name]
            
            # تعیین تعداد مراحل بر اساس ورودی‌های انتخاب شده
            has_pos = bool(self.pos_folder_var.get())
            has_accounting = bool(self.accounting_file_var.get())
            has_bank = bool(self.bank_file_var.get())
            
            total_steps = sum([has_pos, has_accounting, has_bank])
            current_step = 0

            self.logger.info(f"شروع پردازش برای بانک {bank_name}")

            # پردازش فایل‌های پوز
            if has_pos:
                try:
                    pos_folder_path = self.pos_folder_var.get()
                    self.logger.info(f"شروع پردازش فایل‌های پوز با مسیر: {pos_folder_path}")
                    self.update_progress_bars((current_step / total_steps) * 100, 0)
                    pos_result = process_pos_files(pos_folder_path, bank_id)
                    self.logger.info(f"پردازش پوز: {pos_result['files_processed']} فایل پردازش شد")
                    current_step += 1
                    self.update_progress_bars((current_step / total_steps) * 100, 100)
                except Exception as e:
                    self.logger.error(f"خطا در پردازش فایل‌های پوز: {str(e)}")

            # پردازش فایل حسابداری
            if has_accounting:
                try:
                    self.logger.info("شروع پردازش فایل حسابداری...")
                    self.update_progress_bars((current_step / total_steps) * 100, 0)
                    acc_result = import_accounting_excel(self.accounting_file_var.get(), bank_id)
                    self.logger.info(f"پردازش حسابداری: {acc_result['transactions_saved']} تراکنش ذخیره شد")
                    current_step += 1
                    self.update_progress_bars((current_step / total_steps) * 100, 100)
                except Exception as e:
                    self.logger.error(f"خطا در پردازش فایل حسابداری: {str(e)}")

            # پردازش فایل بانک
            if has_bank:
                try:
                    self.logger.info("شروع پردازش فایل بانک...")
                    self.update_progress_bars((current_step / total_steps) * 100, 0)
                    bank_result = process_mellat_bank_file(self.bank_file_var.get(), bank_id)
                    self.logger.info(f"پردازش بانک: {bank_result['processed']} تراکنش پردازش شد")
                    current_step += 1
                    self.update_progress_bars(100, 100)
                except Exception as e:
                    self.logger.error(f"خطا در پردازش فایل بانک: {str(e)}")

            self.update_status("عملیات پردازش به پایان رسید")
            self.logger.info("عملیات پردازش به پایان رسید")

        except Exception as e:
            self.logger.error(f"خطای کلی در فرآیند پردازش: {str(e)}")
            self.update_status("خطا در پردازش")
    
    def update_progress_bars(self, overall_value, detailed_value):
        """به‌روزرسانی نوارهای پیشرفت در thread اصلی"""
        self.after(0, lambda: self.overall_progressbar.configure(value=overall_value))
        self.after(0, lambda: self.detailed_progressbar.configure(value=detailed_value))

    def update_status(self, status):
        """به‌روزرسانی وضعیت در thread اصلی"""
        self.after(0, lambda: self.status_var.set(status))

    def start_process(self):
        """شروع فرآیند پردازش"""
        if not self.validate_inputs():
            return

        # غیرفعال کردن دکمه‌ها
        for widget in self.winfo_children():
            if isinstance(widget, ttk.Button):
                widget.configure(state='disabled')

        # تنظیم وضعیت اولیه
        self.status_var.set("در حال پردازش...")
        self.overall_progressbar['value'] = 0
        self.detailed_progressbar['value'] = 0

        # شروع thread جدید
        process_thread = threading.Thread(target=self.process_thread)
        process_thread.daemon = True  # thread با بسته شدن برنامه متوقف می‌شود
        process_thread.start()

        # چک کردن وضعیت thread و فعال کردن مجدد دکمه‌ها
        def check_thread():
            if process_thread.is_alive():
                self.after(100, check_thread)
            else:
                # فعال کردن مجدد دکمه‌ها
                for widget in self.winfo_children():
                    if isinstance(widget, ttk.Button):
                        widget.configure(state='normal')

        self.after(100, check_thread)

    def clear_entries(self):
        """پاک کردن تمام ورودی‌ها"""
        self.pos_folder_var.set("")
        self.accounting_file_var.set("")
        self.bank_file_var.set("")
        if self.banks_dict:
            self.bank_combobox.current(0)
        else:
            self.selected_bank_var.set("")
        self.status_var.set("منتظر شروع فرآیند...")
        self.overall_progressbar['value'] = 0
        self.detailed_progressbar['value'] = 0
        self.logger.info("تمام ورودی‌ها پاک شدند")
