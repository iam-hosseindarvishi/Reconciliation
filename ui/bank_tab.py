import ttkbootstrap as ttk
from ttkbootstrap.constants import *
from tkinter import StringVar, messagebox
from database.banks_repository import create_bank, delete_bank, update_bank, get_all_banks
from utils.logger_config import setup_logger

class BankTab(ttk.Frame):
    def __init__(self, master, on_bank_change_callback=None, *args, **kwargs):
        """راه‌اندازی تب مدیریت بانک‌ها"""
        super().__init__(master, *args, **kwargs)
        
        # راه‌اندازی لاگر
        self.logger = setup_logger('ui.bank_tab')
        
        self.bank_name_var = StringVar()
        self.selected_bank_id = None
        self.on_bank_change_callback = on_bank_change_callback  # کالبک برای اطلاع‌رسانی تغییرات
        
        try:
            self.create_widgets()
            self.refresh_bank_list()
            self.logger.info("تب مدیریت بانک‌ها با موفقیت راه‌اندازی شد")
        except Exception as e:
            self.logger.error(f"خطا در راه‌اندازی تب مدیریت بانک‌ها: {str(e)}")
            raise

    def create_widgets(self):
        """ایجاد عناصر گرافیکی تب"""
        try:
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
            
            self.logger.debug("عناصر گرافیکی تب با موفقیت ایجاد شدند")
        except Exception as e:
            self.logger.error(f"خطا در ایجاد عناصر گرافیکی: {str(e)}")
            raise

    def refresh_bank_list(self):
        """به‌روزرسانی لیست بانک‌ها"""
        try:
            # پاک کردن لیست فعلی
            for item in self.bank_list.get_children():
                self.bank_list.delete(item)
            
            # دریافت و نمایش بانک‌های جدید
            banks = get_all_banks()
            for bank in banks:
                self.bank_list.insert("", END, iid=bank[0], values=(bank[1],))
            
            self.logger.debug(f"لیست بانک‌ها با {len(banks)} بانک به‌روزرسانی شد")
        except Exception as e:
            self.logger.error(f"خطا در به‌روزرسانی لیست بانک‌ها: {str(e)}")
            messagebox.showerror("خطا", "خطا در به‌روزرسانی لیست بانک‌ها")
            raise

    def on_add_bank(self):
        """افزودن بانک جدید"""
        try:
            # اعتبارسنجی ورودی
            name = self.bank_name_var.get().strip()
            if not name:
                self.logger.warning("تلاش برای ایجاد بانک با نام خالی")
                messagebox.showwarning("خطا", "نام بانک نمی‌تواند خالی باشد.")
                return
            
            # ایجاد بانک جدید
            create_bank(name)
            self.logger.info(f"بانک جدید با نام '{name}' ایجاد شد")
            
            # پاک کردن فرم و به‌روزرسانی لیست
            self.bank_name_var.set("")
            self.refresh_bank_list()
            
            # فراخوانی کالبک برای اطلاع‌رسانی تغییر
            if self.on_bank_change_callback:
                self.on_bank_change_callback()
            
            messagebox.showinfo("موفقیت", "بانک جدید با موفقیت اضافه شد")
            
        except Exception as e:
            self.logger.error(f"خطا در افزودن بانک: {str(e)}")
            messagebox.showerror("خطا", f"افزودن بانک با خطا مواجه شد:\n{str(e)}")

    def on_select_bank(self, event):
        """انتخاب یک بانک از لیست"""
        try:
            selected = self.bank_list.selection()
            if selected:
                self.selected_bank_id = int(selected[0])
                bank_name = self.bank_list.item(selected[0])["values"][0]
                self.bank_name_var.set(bank_name)
                self.logger.debug(f"بانک '{bank_name}' با شناسه {self.selected_bank_id} انتخاب شد")
        except Exception as e:
            self.logger.error(f"خطا در انتخاب بانک: {str(e)}")
            self.selected_bank_id = None
            self.bank_name_var.set("")

    def on_update_bank(self):
        """به‌روزرسانی اطلاعات بانک"""
        try:
            # بررسی انتخاب بانک
            if self.selected_bank_id is None:
                self.logger.warning("تلاش برای به‌روزرسانی بدون انتخاب بانک")
                messagebox.showwarning("خطا", "ابتدا یک بانک را انتخاب کنید.")
                return
            
            # اعتبارسنجی نام جدید
            name = self.bank_name_var.get().strip()
            if not name:
                self.logger.warning("تلاش برای به‌روزرسانی با نام خالی")
                messagebox.showwarning("خطا", "نام بانک نمی‌تواند خالی باشد.")
                return
            
            # به‌روزرسانی اطلاعات بانک
            update_bank(self.selected_bank_id, name)
            self.logger.info(f"اطلاعات بانک با شناسه {self.selected_bank_id} به‌روزرسانی شد")
            
            # پاک کردن فرم و به‌روزرسانی لیست
            self.bank_name_var.set("")
            self.selected_bank_id = None
            self.refresh_bank_list()
            
            # فراخوانی کالبک برای اطلاع‌رسانی تغییر
            if self.on_bank_change_callback:
                self.on_bank_change_callback()
            
            messagebox.showinfo("موفقیت", "اطلاعات بانک با موفقیت به‌روزرسانی شد")
            
        except Exception as e:
            self.logger.error(f"خطا در به‌روزرسانی بانک: {str(e)}")
            messagebox.showerror("خطا", f"خطا در به‌روزرسانی بانک:\n{str(e)}")

    def on_delete_bank(self):
        """حذف بانک"""
        try:
            # بررسی انتخاب بانک
            if self.selected_bank_id is None:
                self.logger.warning("تلاش برای حذف بدون انتخاب بانک")
                messagebox.showwarning("خطا", "ابتدا یک بانک را انتخاب کنید.")
                return
            
            # تأیید حذف
            bank_name = self.bank_name_var.get()
            if not messagebox.askyesno("تایید", f"آیا از حذف بانک '{bank_name}' مطمئن هستید؟"):
                self.logger.info(f"درخواست حذف بانک {bank_name} لغو شد")
                return
            
            # حذف بانک
            delete_bank(self.selected_bank_id)
            self.logger.info(f"بانک '{bank_name}' با شناسه {self.selected_bank_id} حذف شد")
            
            # پاک کردن فرم و به‌روزرسانی لیست
            self.bank_name_var.set("")
            self.selected_bank_id = None
            self.refresh_bank_list()
            
            # فراخوانی کالبک برای اطلاع‌رسانی تغییر
            if self.on_bank_change_callback:
                self.on_bank_change_callback()
            
            messagebox.showinfo("موفقیت", "بانک با موفقیت حذف شد")
            
        except Exception as e:
            self.logger.error(f"خطا در حذف بانک: {str(e)}")
            messagebox.showerror("خطا", f"خطا در حذف بانک:\n{str(e)}")
