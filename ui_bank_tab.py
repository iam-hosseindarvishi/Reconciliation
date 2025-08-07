import ttkbootstrap as ttk
from ttkbootstrap.constants import *
from tkinter import StringVar, messagebox
from bank_manager import add_bank, delete_bank, update_bank, get_all_banks

class BankTab(ttk.Frame):
    def __init__(self, master, *args, **kwargs):
        super().__init__(master, *args, **kwargs)
        self.bank_name_var = StringVar()
        self.selected_bank_id = None
        self.create_widgets()
        self.refresh_bank_list()

    def create_widgets(self):
        ttk.Label(self, text="نام بانک:").pack(pady=5)
        ttk.Entry(self, textvariable=self.bank_name_var, width=40).pack()

        btn_frame = ttk.Frame(self)
        btn_frame.pack(pady=5)
        ttk.Button(btn_frame, text="افزودن", command=self.on_add_bank, bootstyle=SUCCESS).pack(side=LEFT, padx=5)
        ttk.Button(btn_frame, text="ویرایش", command=self.on_update_bank, bootstyle=WARNING).pack(side=LEFT, padx=5)
        ttk.Button(btn_frame, text="حذف", command=self.on_delete_bank, bootstyle=DANGER).pack(side=LEFT, padx=5)

        self.bank_list = ttk.Treeview(self, columns=("name",), show="headings", height=10)
        self.bank_list.heading("name", text="نام بانک")
        self.bank_list.pack(fill=BOTH, expand=True, padx=10, pady=10)
        self.bank_list.bind("<<TreeviewSelect>>", self.on_select_bank)

    def refresh_bank_list(self):
        for item in self.bank_list.get_children():
            self.bank_list.delete(item)
        for bank in get_all_banks():
            self.bank_list.insert("", END, iid=bank[0], values=(bank[1],))

    def on_add_bank(self):
        name = self.bank_name_var.get().strip()
        if not name:
            messagebox.showwarning("خطا", "نام بانک نمی‌تواند خالی باشد.")
            return
        try:
            add_bank(name)
            self.bank_name_var.set("")
            self.refresh_bank_list()
        except Exception as e:
            messagebox.showerror("خطا", f"افزودن بانک با خطا مواجه شد:\n{e}")

    def on_select_bank(self, event):
        selected = self.bank_list.selection()
        if selected:
            self.selected_bank_id = int(selected[0])
            self.bank_name_var.set(self.bank_list.item(selected[0])["values"][0])

    def on_update_bank(self):
        if self.selected_bank_id is None:
            messagebox.showwarning("خطا", "ابتدا یک بانک را انتخاب کنید.")
            return
        name = self.bank_name_var.get().strip()
        try:
            update_bank(self.selected_bank_id, name)
            self.bank_name_var.set("")
            self.selected_bank_id = None
            self.refresh_bank_list()
        except Exception as e:
            messagebox.showerror("خطا", f"خطا در به‌روزرسانی بانک:\n{e}")

    def on_delete_bank(self):
        if self.selected_bank_id is None:
            messagebox.showwarning("خطا", "ابتدا یک بانک را انتخاب کنید.")
            return
        if messagebox.askyesno("تایید", "آیا از حذف بانک مطمئن هستید؟"):
            delete_bank(self.selected_bank_id)
            self.bank_name_var.set("")
            self.selected_bank_id = None
            self.refresh_bank_list()
