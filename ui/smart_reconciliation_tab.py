import os
import logging
import threading
import ttkbootstrap as ttk
from ttkbootstrap.constants import *
from tkinter import StringVar, messagebox
from tkinter.ttk import Combobox, Treeview, Scrollbar
from ttkbootstrap.scrolled import ScrolledText
from config.settings import (
    DATA_DIR, DEFAULT_FONT, DEFAULT_FONT_SIZE,
    HEADER_FONT_SIZE, BUTTON_FONT_SIZE
)
from database.banks_repository import get_all_banks
from database.pos_transactions_repository import get_unreconciled_transactions_by_bank
from database.bank_transaction_repository import (
    get_unreconciled_by_type as get_bank_unreconciled_by_type
)
from reconciliation.ai_matcher import AIMatcher
from utils.logger_config import setup_logger

logger = setup_logger('ui.smart_reconciliation_tab')

class UIHandler(logging.Handler):
    def __init__(self, text_widget):
        super().__init__()
        self.text_widget = text_widget

    def emit(self, record):
        msg = self.format(record) + '\n'
        self.text_widget.insert('end', msg)
        self.text_widget.see('end')

class SmartReconciliationTab(ttk.Frame):
    def __init__(self, parent):
        super().__init__(parent)
        self.setup_logging()
        self.selected_bank_var = StringVar()
        self.n8n_webhook_url = "http://localhost:5678/webhook/reconcile"
        self.ai_matcher = AIMatcher(self.n8n_webhook_url)
        self.ai_matcher.set_ui_callback(self.ask_user_action)
        self.is_processing = False
        self.results = []
        self.create_widgets()
        self.load_banks_to_combobox()

    def ask_user_action(self, error_msg):
        """نمایش خطا به کاربر و دریافت تصمیم"""
        result_container = {}
        event = threading.Event()
        
        def show_dialog():
            # Create a custom Toplevel dialog
            dialog = ttk.Toplevel(self)
            dialog.title("خطا در ارتباط با هوش مصنوعی")
            dialog.geometry("500x300")
            dialog.resizable(False, False)
            
            # Center the dialog relative to parent
            try:
                x = self.winfo_rootx() + (self.winfo_width() // 2) - 250
                y = self.winfo_rooty() + (self.winfo_height() // 2) - 150
                dialog.geometry(f"+{x}+{y}")
            except:
                pass
            
            ttk.Label(dialog, text="خطایی در ارتباط با سرویس هوش مصنوعی رخ داده است:", font=self.default_font).pack(pady=10, padx=10, anchor="w")
            
            msg_frame = ttk.Frame(dialog)
            msg_frame.pack(fill="both", expand=True, padx=10, pady=5)
            
            txt = ScrolledText(msg_frame, height=5, font=self.log_font)
            txt.pack(fill="both", expand=True)
            txt.insert("end", error_msg)
            txt.text.configure(state="disabled")
            
            btn_frame = ttk.Frame(dialog)
            btn_frame.pack(fill="x", pady=20, padx=10)
            
            def on_retry():
                result_container['action'] = 'retry'
                dialog.destroy()
                event.set()
                
            def on_cancel():
                result_container['action'] = 'cancel'
                dialog.destroy()
                event.set()
            
            ttk.Button(btn_frame, text="تلاش مجدد", command=on_retry, bootstyle="primary").pack(side="left", padx=5, expand=True, fill="x")
            ttk.Button(btn_frame, text="انصراف", command=on_cancel, bootstyle="danger").pack(side="left", padx=5, expand=True, fill="x")
            
            dialog.protocol("WM_DELETE_WINDOW", on_cancel)
            dialog.transient(self)
            dialog.grab_set()
            
        self.after(0, show_dialog)
        event.wait()
        return result_container.get('action', 'cancel')

    def setup_logging(self):
        """راه‌اندازی سیستم لاگینگ"""
        os.makedirs(DATA_DIR, exist_ok=True)

        self.logger = logging.getLogger('smart_reconciliation.tab')
        self.logger.setLevel(logging.INFO)
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')

        error_handler = logging.FileHandler(
            os.path.join(DATA_DIR, 'smart_reconciliation_error.txt'), encoding='utf-8'
        )
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(formatter)

        file_handler = logging.FileHandler(
            os.path.join(DATA_DIR, 'smart_reconciliation_log.txt'), encoding='utf-8'
        )
        file_handler.setLevel(logging.INFO)
        file_handler.setFormatter(formatter)

        self.logger.addHandler(error_handler)
        self.logger.addHandler(file_handler)

    def create_widgets(self):
        PADX = 8
        PADY = 8

        self.default_font = (DEFAULT_FONT, DEFAULT_FONT_SIZE, 'bold')
        self.header_font = (DEFAULT_FONT, HEADER_FONT_SIZE, 'bold')
        self.button_font = (DEFAULT_FONT, BUTTON_FONT_SIZE, 'bold')
        self.log_font = (DEFAULT_FONT, DEFAULT_FONT_SIZE - 1, 'bold')

        style = ttk.Style()
        style.configure('Header.TLabelframe', font=self.header_font)
        style.configure('Header.TLabelframe.Label', font=self.header_font)
        style.configure('Default.TLabel', font=self.default_font)
        style.configure('Bold.TButton', font=self.button_font)

        main_frame = ttk.Frame(self)
        main_frame.pack(fill="both", expand=True, padx=10, pady=10)

        control_frame = ttk.Frame(self)
        control_frame.pack(fill="x", pady=5)
        control_frame.columnconfigure(1, weight=1)

        ttk.Label(control_frame, text="انتخاب بانک:", style='Default.TLabel').grid(
            row=0, column=0, sticky="e", padx=5, pady=5
        )
        self.bank_combobox = Combobox(
            control_frame, textvariable=self.selected_bank_var, state="readonly", width=30
        )
        self.bank_combobox.configure(font=self.default_font)
        self.bank_combobox.grid(row=0, column=1, sticky="w", padx=5, pady=5)

        btn_frame = ttk.Frame(control_frame)
        btn_frame.grid(row=0, column=2, sticky="e", padx=5, pady=5)

        ttk.Button(
            btn_frame,
            text="شروع مغایرت‌یابی هوشمند",
            command=self.start_smart_reconciliation,
            bootstyle=SUCCESS,
            width=20,
            style='Bold.TButton'
        ).pack(side="left", padx=5)

        ttk.Button(
            btn_frame,
            text="تنظیم Webhook",
            command=self.set_webhook,
            width=12,
            style='Bold.TButton'
        ).pack(side="left", padx=5)

        self.stop_button = ttk.Button(
            btn_frame,
            text="توقف فرآیند",
            command=self.stop_reconciliation,
            bootstyle=DANGER,
            width=12,
            style='Bold.TButton',
            state="disabled"
        )
        self.stop_button.pack(side="left", padx=5)

        progress_frame = ttk.LabelFrame(self, text="وضعیت مغایرت‌یابی هوشمند", style='Header.TLabelframe')
        progress_frame.pack(fill="x", pady=5, padx=10)

        ttk.Label(progress_frame, text="وضعیت کلی:", anchor="w", style='Default.TLabel').pack(fill="x", padx=5)
        self.status_var = StringVar(value="منتظر شروع فرآیند...")
        ttk.Label(progress_frame, textvariable=self.status_var, anchor="w", style='Default.TLabel').pack(
            fill="x", padx=5
        )

        progress_container = ttk.Frame(progress_frame)
        progress_container.pack(fill="x", padx=10, pady=(0, 10))

        self.progressbar = ttk.Progressbar(
            progress_container, mode="determinate", maximum=100, bootstyle="success-striped"
        )
        self.progressbar.pack(fill="x", ipady=10)

        ttk.Label(progress_frame, text="وضعیت جزئی:", anchor="w", style='Default.TLabel').pack(fill="x", padx=5)
        self.detailed_status_var = StringVar(value="")
        ttk.Label(progress_frame, textvariable=self.detailed_status_var, anchor="w", style='Default.TLabel').pack(
            fill="x", padx=5
        )

        results_frame = ttk.LabelFrame(self, text="نتایج", style='Header.TLabelframe')
        results_frame.pack(fill="both", expand=True, pady=5, padx=10)

        self.create_results_table(results_frame)

        log_frame = ttk.LabelFrame(self, text="لاگ فرآیند", style='Header.TLabelframe')
        log_frame.pack(fill="both", expand=True, pady=5, padx=10)

        self.log_text = ScrolledText(log_frame, height=10, font=self.log_font)
        self.log_text.pack(fill="both", expand=True, padx=10, pady=10)

        ui_handler = UIHandler(self.log_text)
        ui_handler.setFormatter(logging.Formatter('%(asctime)s - %(message)s'))
        self.logger.addHandler(ui_handler)

    def create_results_table(self, parent):
        """ایجاد جدول نتایج"""
        columns = ('نوع', 'شناسه اصلی', 'شناسه تطبیق', 'اطمینان', 'دلیل', 'وضعیت')
        self.results_tree = Treeview(parent, columns=columns, height=8, show='headings')

        for col in columns:
            self.results_tree.heading(col, text=col)
            self.results_tree.column(col, width=100)

        self.results_tree.column('دلیل', width=200)

        scrollbar = Scrollbar(parent, orient='vertical', command=self.results_tree.yview)
        self.results_tree.configure(yscroll=scrollbar.set)

        self.results_tree.pack(side='left', fill='both', expand=True)
        scrollbar.pack(side='right', fill='y')

    def load_banks_to_combobox(self):
        """بارگذاری لیست بانک‌ها"""
        try:
            current_selection = self.selected_bank_var.get()
            banks = get_all_banks()
            self.banks_dict = {bank[1]: bank[0] for bank in banks}
            self.bank_combobox['values'] = list(self.banks_dict.keys())

            if current_selection and current_selection in self.banks_dict:
                self.selected_bank_var.set(current_selection)
            elif self.banks_dict:
                self.bank_combobox.current(0)
        except Exception as e:
            self.logger.error(f"خطا در بارگذاری لیست بانک‌ها: {str(e)}")

    def set_webhook(self):
        """تنظیم URL webhook n8n"""
        from tkinter import simpledialog
        url = simpledialog.askstring(
            "تنظیم Webhook",
            "آدرس webhook n8n را وارد کنید:",
            initialvalue=self.n8n_webhook_url
        )
        if url:
            self.n8n_webhook_url = url
            self.ai_matcher.set_webhook_url(url)
            self.logger.info(f"Webhook تنظیم شد: {url}")
            messagebox.showinfo("موفق", "Webhook با موفقیت تنظیم شد")

    def stop_reconciliation(self):
        """توقف فرآیند مغایرت‌یابی هوشمند"""
        if self.is_processing:
            self.is_processing = False
            self.logger.warning("درخواست توقف فرآیند از سوی کاربر")
            self.update_status("فرآیند متوقف شد...")
            self.stop_button.config(state="disabled")
        else:
            messagebox.showinfo("اطلاعات", "فرآیند درحال اجرا نیست")

    def start_smart_reconciliation(self):
        """شروع فرآیند مغایرت‌یابی هوشمند"""
        try:
            if not self.selected_bank_var.get():
                messagebox.showerror("خطا", "لطفاً یک بانک انتخاب کنید")
                return

            if self.is_processing:
                messagebox.showwarning("هشدار", "فرآیند درحال اجرا است")
                return

            self.is_processing = True
            self.results = []
            self.results_tree.delete(*self.results_tree.get_children())
            self.log_text.delete('1.0', 'end')

            self.stop_button.config(state="normal")

            bank_name = self.selected_bank_var.get()
            bank_id = self.banks_dict[bank_name]

            self.logger.info(f"شروع فرآیند مغایرت‌یابی هوشمند برای {bank_name}")

            threading.Thread(
                target=self.run_smart_reconciliation,
                args=(bank_id, bank_name),
                daemon=True
            ).start()

        except Exception as e:
            self.logger.error(f"خطا در شروع فرآیند: {str(e)}")
            self.is_processing = False
            self.stop_button.config(state="disabled")

    def run_smart_reconciliation(self, bank_id, bank_name):
        """اجرای فرآیند مغایرت‌یابی هوشمند"""
        try:
            self.update_status("در حال بارگذاری تراکنش‌های POS...")
            pos_transactions = get_unreconciled_transactions_by_bank(bank_id)
            self.logger.info(f"تعداد {len(pos_transactions)} تراکنش POS مغایرت‌نشده یافت شد")

            self.update_status("در حال بارگذاری تراکنش‌های بانک...")
            bank_transfers_received = get_bank_unreconciled_by_type('Received_Transfer')
            bank_transfers_paid = get_bank_unreconciled_by_type('Paid_Transfer')
            checks_received = get_bank_unreconciled_by_type('Received_Check')
            checks_paid = get_bank_unreconciled_by_type('Paid_Check')

            total_records = (
                len(pos_transactions) + len(bank_transfers_received) +
                len(bank_transfers_paid) + len(checks_received) + len(checks_paid)
            )

            if total_records == 0:
                self.update_status("هیچ تراکنش مغایرت‌نشده‌ای یافت نشد")
                self.logger.warning("هیچ تراکنشی برای پردازش یافت نشد")
                self.is_processing = False
                return

            processed = 0

            for idx, pos in enumerate(pos_transactions):
                if not self.is_processing:
                    break
                self.update_status(f"در حال پردازش POS... ({idx + 1}/{len(pos_transactions)})")
                self.update_progress((processed / total_records) * 100)

                success, result = self.ai_matcher.process_pos_transaction(pos)
                self.results.append(result)
                self.add_result_to_table(result)
                processed += 1

            for idx, transfer in enumerate(bank_transfers_received):
                if not self.is_processing:
                    break
                self.update_status(f"در حال پردازش انتقال دریافتی... ({idx + 1}/{len(bank_transfers_received)})")
                self.update_progress((processed / total_records) * 100)

                success, result = self.ai_matcher.process_bank_transaction(
                    transfer, 'Received_Transfer'
                )
                self.results.append(result)
                self.add_result_to_table(result)
                processed += 1

            for idx, transfer in enumerate(bank_transfers_paid):
                if not self.is_processing:
                    break
                self.update_status(f"در حال پردازش انتقال پرداختی... ({idx + 1}/{len(bank_transfers_paid)})")
                self.update_progress((processed / total_records) * 100)

                success, result = self.ai_matcher.process_bank_transaction(
                    transfer, 'Paid_Transfer'
                )
                self.results.append(result)
                self.add_result_to_table(result)
                processed += 1

            for idx, check in enumerate(checks_received):
                if not self.is_processing:
                    break
                self.update_status(f"در حال پردازش چک دریافتی... ({idx + 1}/{len(checks_received)})")
                self.update_progress((processed / total_records) * 100)

                success, result = self.ai_matcher.process_bank_transaction(
                    check, 'Received_Check'
                )
                self.results.append(result)
                self.add_result_to_table(result)
                processed += 1

            for idx, check in enumerate(checks_paid):
                if not self.is_processing:
                    break
                self.update_status(f"در حال پردازش چک پرداختی... ({idx + 1}/{len(checks_paid)})")
                self.update_progress((processed / total_records) * 100)

                success, result = self.ai_matcher.process_bank_transaction(
                    check, 'Paid_Check'
                )
                self.results.append(result)
                self.add_result_to_table(result)
                processed += 1

            auto_matched = sum(1 for r in self.results if r.get('status') == 'auto_matched')
            needs_review = sum(1 for r in self.results if r.get('status') == 'needs_review')
            errors = sum(1 for r in self.results if r.get('status') == 'error')

            summary = f"فرآیند به پایان رسید: {auto_matched} ذخیره خودکار، {needs_review} نیاز به بررسی، {errors} خطا"
            self.update_status(summary)
            self.update_progress(100)
            self.logger.info(summary)

        except Exception as e:
            self.logger.error(f"خطا در اجرای فرآیند: {str(e)}")
            self.update_status(f"خطا: {str(e)}")
        finally:
            self.is_processing = False
            self.after_idle(lambda: self.stop_button.config(state="disabled"))

    def update_status(self, message):
        """بروزرسانی وضعیت"""
        try:
            self.after_idle(lambda: self.status_var.set(message))
        except:
            pass

    def update_progress(self, value):
        """بروزرسانی نوار پیشرفت"""
        try:
            self.after_idle(lambda: setattr(self.progressbar, 'value', min(100, max(0, int(value)))))
        except:
            pass

    def add_result_to_table(self, result):
        """اضافه کردن نتیجه به جدول"""
        try:
            status_icon = {
                'auto_matched': '✅ ذخیره شد',
                'needs_review': '⚠️ نیاز به بررسی',
                'error': '❌ خطا',
                'no_match': '❓ تطبیق نیافت'
            }
            status_text = status_icon.get(result.get('status'), result.get('status', ''))

            confidence_text = f"{int(result.get('confidence', 0) * 100)}%"

            self.after_idle(
                lambda: self.results_tree.insert(
                    '',
                    'end',
                    values=(
                        result.get('type', ''),
                        result.get('source_id', ''),
                        result.get('matched_id', '-'),
                        confidence_text,
                        result.get('reason', '')[:50],
                        status_text
                    )
                )
            )
        except:
            pass
