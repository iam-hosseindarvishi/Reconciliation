import ttkbootstrap as ttk
from ttkbootstrap.constants import *
from tkinter import StringVar, filedialog, messagebox
from tkinter.ttk import Combobox
from database.banks_repository import get_all_banks



class DataEntryTab(ttk.Frame):
    def __init__(self, master, *args, **kwargs):
        super().__init__(master, *args, **kwargs)
        self.pos_folder_var = StringVar()
        self.accounting_file_var = StringVar()
        self.bank_file_var = StringVar()
        self.selected_bank_var = StringVar()
        self.status_var = StringVar(value="منتظر شروع فرآیند...")
        self.create_widgets()
        self.load_banks_to_combobox()

    def create_widgets(self):
        PADX = 8
        PADY = 8
        ENTRY_WIDTH = 60

        # بخش پوز
        pos_frame = ttk.LabelFrame(self, text="ورود اطلاعات پوز")
        pos_frame.grid(row=0, column=0, sticky="ew", padx=PADX, pady=(PADY, 0))
        pos_frame.columnconfigure(1, weight=1)
        ttk.Label(pos_frame, text="آدرس پوشه فایل‌های پوز:").grid(row=0, column=0, sticky="w", padx=5, pady=5)
        pos_entry = ttk.Entry(pos_frame, textvariable=self.pos_folder_var, width=ENTRY_WIDTH, state="readonly")
        pos_entry.grid(row=0, column=1, sticky="ew", padx=5, pady=5)
        ttk.Button(pos_frame, text="انتخاب پوشه", command=self.select_pos_folder, bootstyle=PRIMARY, width=14).grid(row=0, column=2, padx=5, pady=5)

        # بخش حسابداری
        acc_frame = ttk.LabelFrame(self, text="ورود اطلاعات حسابداری")
        acc_frame.grid(row=1, column=0, sticky="ew", padx=PADX, pady=(PADY, 0))
        acc_frame.columnconfigure(1, weight=1)
        ttk.Label(acc_frame, text="فایل اکسل سیستم حسابداری:").grid(row=0, column=0, sticky="w", padx=5, pady=5)
        acc_entry = ttk.Entry(acc_frame, textvariable=self.accounting_file_var, width=ENTRY_WIDTH, state="readonly")
        acc_entry.grid(row=0, column=1, sticky="ew", padx=5, pady=5)
        ttk.Button(acc_frame, text="انتخاب فایل", command=self.select_accounting_file, bootstyle=PRIMARY, width=14).grid(row=0, column=2, padx=5, pady=5)

        # بخش بانک
        bank_frame = ttk.LabelFrame(self, text="ورود اطلاعات بانک")
        bank_frame.grid(row=2, column=0, sticky="ew", padx=PADX, pady=(PADY, 0))
        bank_frame.columnconfigure(1, weight=1)
        ttk.Label(bank_frame, text="فایل اکسل بانک:").grid(row=0, column=0, sticky="w", padx=5, pady=5)
        bank_entry = ttk.Entry(bank_frame, textvariable=self.bank_file_var, width=ENTRY_WIDTH, state="readonly")
        bank_entry.grid(row=0, column=1, sticky="ew", padx=5, pady=5)
        ttk.Button(bank_frame, text="انتخاب فایل", command=self.select_bank_file, bootstyle=PRIMARY, width=14).grid(row=0, column=2, padx=5, pady=5)

        # کنترل‌های پایین
        control_frame = ttk.Frame(self)
        control_frame.grid(row=3, column=0, sticky="ew", padx=PADX, pady=(PADY, 0))
        control_frame.columnconfigure(1, weight=1)

        # Combobox و Label بانک
        ttk.Label(control_frame, text="انتخاب بانک:").grid(row=0, column=0, sticky="e", padx=5, pady=5)
        from tkinter.ttk import Combobox
        self.bank_combobox = Combobox(control_frame, textvariable=self.selected_bank_var, state="readonly", width=30)
        self.bank_combobox.grid(row=0, column=1, sticky="w", padx=5, pady=5)

        # دکمه‌های کنترل
        btn_frame = ttk.Frame(control_frame)
        btn_frame.grid(row=0, column=2, sticky="e", padx=5, pady=5)
        ttk.Button(btn_frame, text="شروع فرآیند", command=self.start_process, bootstyle=SUCCESS, width=16).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="پاک کردن ورودی‌ها", command=self.clear_entries, bootstyle=DANGER, width=16).pack(side="left", padx=5)

        # فریم وضعیت و نوار پیشرفت
        status_frame = ttk.Frame(self)
        status_frame.grid(row=4, column=0, sticky="ew", padx=PADX, pady=(PADY, PADY))
        status_frame.columnconfigure(0, weight=1)
        # لیبل وضعیت
        self.status_label = ttk.Label(status_frame, textvariable=self.status_var, anchor="w")
        self.status_label.grid(row=0, column=0, sticky="ew", padx=5, pady=(0, 5))
        # نوار پیشرفت
        from ttkbootstrap import Style
        style = Style()
        self.progressbar = ttk.Progressbar(status_frame, mode="determinate", maximum=100, value=0, bootstyle="info-striped")
        self.progressbar.grid(row=1, column=0, sticky="ew", padx=5, pady=(0, 5))
        self.progressbar.grid_remove()  # در ابتدا مخفی باشد

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
        banks = get_all_banks()
        bank_names = [b[1] for b in banks]
        self.bank_combobox['values'] = bank_names
        if bank_names:
            self.bank_combobox.current(0)

    def start_process(self):
        # نمونه: نمایش نوار پیشرفت و تغییر وضعیت
        self.status_var.set("در حال شروع فرآیند...")
        self.progressbar.grid()  # نمایش نوار پیشرفت
        self.progressbar['value'] = 0
        self.update_idletasks()
        # شبیه‌سازی پیشرفت (در پروژه واقعی: این بخش باید با منطق واقعی جایگزین شود)
        import time
        for i in range(1, 101, 10):
            self.progressbar['value'] = i
            self.status_var.set(f"در حال پردازش... {i}%")
            self.update_idletasks()
            time.sleep(0.05)
        self.status_var.set("فرآیند با موفقیت به پایان رسید.")
        self.progressbar['value'] = 100
        self.update_idletasks()
        time.sleep(0.3)
        # پس از اتمام، نوار پیشرفت را مخفی کن
        self.progressbar.grid_remove()

    def clear_entries(self):
        self.pos_folder_var.set("")
        self.accounting_file_var.set("")
        self.bank_file_var.set("")
        self.selected_bank_var.set("")
        self.bank_combobox.set("")
        self.status_var.set("منتظر شروع فرآیند...")
        self.progressbar['value'] = 0
        self.progressbar.grid_remove()
