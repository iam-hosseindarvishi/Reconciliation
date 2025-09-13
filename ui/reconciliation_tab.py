import os
import logging
import threading
import queue
import ttkbootstrap as ttk
from ttkbootstrap.constants import *
from tkinter import StringVar
from tkinter.ttk import Combobox
from ttkbootstrap.scrolled import ScrolledText
from database.banks_repository import get_all_banks
from database.reconciliation.reconciliation_repository import has_unreconciled_transactions, get_unknown_transactions_by_bank as get_unknown_transactions, has_unknown_transactions
from reconciliation.reconciliation_logic import ReconciliationProcess
from reconciliation.unknown_transactions_dialog import UnknownTransactionsDialog
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
        # ScrolledText در ttkbootstrap از state پشتیبانی نمی‌کند
        self.text_widget.insert('end', msg)
        self.text_widget.see('end')

class ReconciliationTab(ttk.Frame):
    def __init__(self, parent):
        super().__init__(parent)
        self.setup_logging()
        self.selected_bank_var = StringVar()
        self.status_var = StringVar(value="منتظر شروع فرآیند مغایرت‌گیری...")
        self.detailed_status_var = StringVar(value="")
        self.create_widgets()
        self.load_banks_to_combobox()
        
    def _update_manual_reconciliation_state(self):
        """به‌روزرسانی وضعیت نمایش مغایرت‌گیری دستی در ماژول ui_state"""
        from utils import ui_state
        value = self.show_manual_reconciliation_var.get()
        ui_state.set_show_manual_reconciliation(value)
        
    def setup_logging(self):
        """راه‌اندازی سیستم لاگینگ"""
        os.makedirs(DATA_DIR, exist_ok=True)
        
        # تنظیمات کلی لاگر
        self.logger = logging.getLogger('reconciliation.tab')
        self.logger.setLevel(logging.INFO)
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        
        # لاگر برای فایل خطاها
        error_handler = logging.FileHandler(os.path.join(DATA_DIR, 'reconciliation_error.txt'), encoding='utf-8')
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(formatter)
        
        # لاگر برای فایل لاگ عمومی
        file_handler = logging.FileHandler(os.path.join(DATA_DIR, 'reconciliation_log.txt'), encoding='utf-8')
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

        main_frame = ttk.Frame(self)
        main_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        # === بخش انتخاب بانک و دکمه شروع ===
        control_frame = ttk.Frame(self)
        control_frame.pack(fill="x", pady=5)
        control_frame.columnconfigure(1, weight=1)

        # === Combobox و Label بانک ===
        ttk.Label(control_frame, text="انتخاب بانک:", style='Default.TLabel').grid(row=0, column=0, sticky="e", padx=5, pady=5)
        # تنظیم فونت کامبوباکس به صورت مستقیم چون استایل ttk روی آن اثر نمی‌کند
        self.bank_combobox = Combobox(control_frame, textvariable=self.selected_bank_var, state="readonly", width=30)
        self.bank_combobox.configure(font=self.default_font)
        self.bank_combobox.grid(row=0, column=1, sticky="w", padx=5, pady=5)
        
        # چک باکس نمایش مغایرت‌گیری دستی
        from utils import ui_state
        self.show_manual_reconciliation_var = ttk.BooleanVar(value=ui_state.get_show_manual_reconciliation())
        self.show_manual_reconciliation_checkbox = ttk.Checkbutton(
            control_frame, 
            text="نمایش مغایرت‌گیری دستی", 
            variable=self.show_manual_reconciliation_var,
            style='Default.TCheckbutton',
            command=self._update_manual_reconciliation_state
        )
        self.show_manual_reconciliation_checkbox.grid(row=0, column=2, sticky="w", padx=5, pady=5)

        # === دکمه شروع ===
        btn_frame = ttk.Frame(control_frame)
        btn_frame.grid(row=0, column=3, sticky="e", padx=5, pady=5)
        ttk.Button(btn_frame, text="شروع مغایرت‌گیری", command=self.start_reconciliation, bootstyle=SUCCESS, width=16, style='Bold.TButton').pack(side="left", padx=5)

        # === فریم وضعیت و نوارهای پیشرفت ===
        progress_frame = ttk.LabelFrame(self, text="وضعیت مغایرت‌گیری", style='Header.TLabelframe')
        progress_frame.pack(fill="x", pady=5, padx=10)
        
        # وضعیت کلی
        ttk.Label(progress_frame, text="وضعیت کلی:", anchor="w", style='Default.TLabel').pack(fill="x", padx=5)
        ttk.Label(progress_frame, textvariable=self.status_var, anchor="w", style='Default.TLabel').pack(fill="x", padx=5)
        
        # نوار پیشرفت کلی
        overall_progress_container = ttk.Frame(progress_frame)
        overall_progress_container.pack(fill="x", padx=10, pady=(0, 10))
        
        self.overall_progressbar = ttk.Progressbar(
            overall_progress_container, 
            mode="determinate",
            maximum=100,
            bootstyle="success-striped"
        )
        self.overall_progressbar.pack(fill="x", ipady=10)  # از ipady برای افزایش ارتفاع استفاده می‌کنیم
        
        # وضعیت جزئی
        ttk.Label(progress_frame, text="وضعیت جزئی:", anchor="w", style='Default.TLabel').pack(fill="x", padx=5)
        ttk.Label(progress_frame, textvariable=self.detailed_status_var, anchor="w", style='Default.TLabel').pack(fill="x", padx=5)
        
        # نوار پیشرفت جزئی
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
        log_frame = ttk.LabelFrame(self, text="لاگ فرآیند", style='Header.TLabelframe')
        log_frame.pack(fill="both", expand=True, pady=5, padx=10)
        
        # برای ScrolledText می‌توانیم مستقیماً از font استفاده کنیم
        self.log_text = ScrolledText(log_frame, height=15, font=self.log_font)  # افزایش ارتفاع
        self.log_text.pack(fill="both", expand=True, padx=10, pady=10)
        
        # اضافه کردن UI handler به logger
        ui_handler = UIHandler(self.log_text)
        ui_handler.setFormatter(logging.Formatter('%(asctime)s - %(message)s'))
        self.logger.addHandler(ui_handler)

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

    # کلاس مدیریت رابط کاربری برای فرآیند مغایرت‌گیری
    class ReconciliationUIHandler:
        def __init__(self, parent):
            self.parent = parent
            self.logger = parent.logger
        
        def _safe_ui_update(self, update_func):
            """Thread-safe UI update wrapper"""
            try:
                if hasattr(self.parent, 'after_idle'):
                    self.parent.after_idle(update_func)
                else:
                    update_func()
            except Exception as e:
                self.logger.warning(f"UI update failed: {e}")
        
        def update_status(self, message):
            """بروزرسانی وضعیت کلی"""
            def _update():
                try:
                    self.parent.status_var.set(message)
                    self.parent.update_idletasks()
                except Exception as e:
                    self.logger.warning(f"Status update failed: {e}")
            self._safe_ui_update(_update)
        
        def update_detailed_status(self, message):
            """بروزرسانی وضعیت جزئی"""
            def _update():
                try:
                    self.parent.detailed_status_var.set(message)
                    self.parent.update_idletasks()
                except Exception as e:
                    self.logger.warning(f"Detailed status update failed: {e}")
            self._safe_ui_update(_update)
        
        def update_progress(self, value):
            """بروزرسانی نوار پیشرفت کلی"""
            def _update():
                try:
                    self.parent.overall_progressbar['value'] = min(100, max(0, value))
                    self.parent.update_idletasks()
                except Exception as e:
                    self.logger.warning(f"Progress update failed: {e}")
            self._safe_ui_update(_update)
        
        def update_detailed_progress(self, value):
            """بروزرسانی نوار پیشرفت جزئی"""
            def _update():
                try:
                    self.parent.detailed_progressbar['value'] = min(100, max(0, value))
                    self.parent.update_idletasks()
                except Exception as e:
                    self.logger.warning(f"Detailed progress update failed: {e}")
            self._safe_ui_update(_update)
        
        def log_info(self, message):
            """ثبت پیام اطلاعاتی در لاگ"""
            self.logger.info(message)
            self.parent.log_text.see('end')
        
        def log_warning(self, message):
            """ثبت پیام هشدار در لاگ"""
            self.logger.warning(message)
            self.parent.log_text.see('end')
        
        def log_error(self, message):
            """ثبت پیام خطا در لاگ"""
            self.logger.error(message)
            self.parent.log_text.see('end')
    
    def start_reconciliation(self):
        """شروع فرآیند مغایرت‌گیری"""
        try:
            # بررسی انتخاب بانک
            if not self.selected_bank_var.get():
                self.logger.error("لطفاً یک بانک انتخاب کنید")
                return
                
            # غیرفعال کردن دکمه شروع
            for widget in self.winfo_children():
                if isinstance(widget, ttk.Button):
                    widget.configure(state='disabled')
            
            # تنظیم وضعیت اولیه
            self.status_var.set("در حال آماده‌سازی فرآیند مغایرت‌گیری...")
            self.detailed_status_var.set("آماده‌سازی داده‌ها...")
            self.overall_progressbar['value'] = 0
            self.detailed_progressbar['value'] = 0
            
            # پاک کردن محتوای ویجت لاگ
            self.log_text.delete('1.0', 'end')
            # ScrolledText در ttkbootstrap نیازی به تغییر state ندارد
            
            # لاگ شروع فرآیند
            bank_name = self.selected_bank_var.get()
            bank_id = self.banks_dict[bank_name]
            self.logger.info(f"شروع فرآیند مغایرت‌گیری برای بانک {bank_name}")
            
            # ایجاد شیء مدیریت رابط کاربری
            ui_handler = self.ReconciliationUIHandler(self)
            
            # اجرای فرآیند مغایرت‌گیری در یک thread جداگانه
            threading.Thread(
                target=self.run_reconciliation_process,
                args=(bank_id, bank_name, ui_handler)
            ).start()
            
        except Exception as e:
            self.logger.error(f"خطا در شروع فرآیند مغایرت‌گیری: {str(e)}")
            # فعال کردن مجدد دکمه‌ها
            for widget in self.winfo_children():
                if isinstance(widget, ttk.Button):
                    widget.configure(state='normal')
    
    def run_reconciliation_process(self, bank_id, bank_name, ui_handler):
        """اجرای فرآیند مغایرت‌گیری"""
        try:
            # بررسی وجود تراکنش‌های مغایرت‌گیری نشده
            if not has_unreconciled_transactions(bank_id):
                ui_handler.log_error("هیچ تراکنش مغایرت‌گیری نشده‌ای برای این بانک وجود ندارد")
                ui_handler.update_status("فرآیند مغایرت‌گیری به پایان رسید - تراکنشی یافت نشد")
                ui_handler.update_progress(100)
                # فعال کردن مجدد دکمه‌ها
                for widget in self.winfo_children():
                    if isinstance(widget, ttk.Button):
                        widget.configure(state='normal')
                return
            # بررسی وجود تراکنش های دارای وضعیت نامخشص
            if has_unknown_transactions(bank_id):
                # نمایش دیالوگ تراکنش های نامشخص
                dialog = UnknownTransactionsDialog(self, bank_id, bank_name, get_unknown_transactions(bank_id))
                if dialog.result:
                    # اگر تغییرات ذخیره شد، فرآیند را مجدد اجرا کنید
                    self.run_reconciliation_process(bank_id, bank_name, ui_handler)
                    return
            # ایجاد و اجرای فرآیند مغایرت‌گیری
            # ایجاد صف برای ارتباط بین تردها
            manual_reconciliation_queue = queue.Queue()
            
            # ایجاد ترد برای پردازش درخواست‌های مغایرت‌یابی دستی
            manual_reconciliation_thread = threading.Thread(
                target=self.process_manual_reconciliation_requests,
                args=(manual_reconciliation_queue,)
            )
            # ترد را به صورت غیر daemon تنظیم می‌کنیم تا برنامه منتظر تکمیل آن بماند
            manual_reconciliation_thread.daemon = False
            manual_reconciliation_thread.start()
            
            # ایجاد و شروع فرآیند مغایرت‌گیری
            process = ReconciliationProcess(self, bank_id, bank_name, ui_handler, manual_reconciliation_queue)
            result = process.start()
            
            # منتظر می‌مانیم تا تمام درخواست‌های مغایرت‌یابی دستی پردازش شوند
            manual_reconciliation_queue.join()
            
            # فعال کردن مجدد دکمه‌ها
            for widget in self.winfo_children():
                if isinstance(widget, ttk.Button):
                    widget.configure(state='normal')
                    
            # نمایش نتیجه
            if result:
                ui_handler.log_info("فرآیند مغایرت‌گیری با موفقیت به پایان رسید")
            else:
                ui_handler.log_warning("فرآیند مغایرت‌گیری با مشکل مواجه شد")
                
        except Exception as e:
            self.logger.error(f"خطا در اجرای فرآیند مغایرت‌گیری: {str(e)}")
            # فعال کردن مجدد دکمه‌ها
            for widget in self.winfo_children():
                if isinstance(widget, ttk.Button):
                    widget.configure(state='normal')
    
    def process_manual_reconciliation_requests(self, manual_reconciliation_queue):
        """پردازش درخواست‌های مغایرت‌یابی دستی"""
        from ui.dialog.manual_reconciliation_dialog import ManualReconciliationDialog
        
        try:
            while True:
                # دریافت درخواست از صف
                request = manual_reconciliation_queue.get()
                
                try:
                    # بررسی تعداد آرگومان‌های دریافتی
                    if isinstance(request, tuple) and len(request) == 4:
                        bank_record, accounting_records, result_queue, transaction_type = request
                    else:
                        self.logger.error(f"فرمت نامعتبر درخواست مغایرت‌یابی دستی: {request}")
                        continue
                    
                    # لاگ کردن اطلاعات
                    self.logger.info(f"درخواست مغایرت‌یابی دستی برای تراکنش بانکی با شناسه {bank_record['id']} دریافت شد")
                    
                    # نمایش دیالوگ مغایرت‌یابی دستی
                    dialog = ManualReconciliationDialog(self, bank_record, accounting_records, transaction_type)
                    selected_match, notes = dialog.show()
                    
                    # ارسال نتیجه به صف
                    if selected_match:
                        self.logger.info(f"مغایرت‌یابی دستی برای تراکنش بانکی {bank_record['id']} با رکورد حسابداری {selected_match['id']} انجام شد")
                        # اضافه کردن توضیحات به رکورد انتخاب شده
                        if notes:
                            selected_match['reconciliation_notes'] = notes
                    else:
                        self.logger.warning(f"مغایرت‌یابی دستی برای تراکنش بانکی {bank_record['id']} انجام نشد")
                    
                    result_queue.put(selected_match)
                except Exception as e:
                    self.logger.error(f"خطا در پردازش درخواست مغایرت‌یابی دستی: {str(e)}")
                    # در صورت خطا، None را به صف نتیجه ارسال می‌کنیم
                    if 'result_queue' in locals():
                        result_queue.put(None)
                finally:
                    # در هر صورت، اعلام می‌کنیم که پردازش درخواست به پایان رسیده است
                    manual_reconciliation_queue.task_done()
                
        except Exception as e:
            self.logger.error(f"خطا در پردازش درخواست مغایرت‌یابی دستی: {str(e)}")
            # در صورت خطا، یک نتیجه خالی به صف ارسال می‌کنیم تا فرآیند اصلی متوقف نشود
            if 'result_queue' in locals():
                result_queue.put(None)