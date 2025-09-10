import os
import logging
import ttkbootstrap as ttk
from ttkbootstrap.constants import *
from tkinter import StringVar, messagebox, filedialog
import pandas as pd
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors

from database.banks_repository import get_all_banks
from database.bank_fees_repository import collect_bank_fees, get_bank_fees
from utils.logger_config import setup_logger
from config.settings import DEFAULT_FONT, DEFAULT_FONT_SIZE

class BankFeesTab(ttk.Frame):
    def __init__(self, master, *args, **kwargs):
        """راه‌اندازی تب جمع‌آوری کارمزد"""
        super().__init__(master, *args, **kwargs)
        
        # راه‌اندازی لاگر
        self.logger = setup_logger('ui.bank_fees_tab')
        
        self.selected_bank_id = None
        self.bank_var = StringVar()
        
        try:
            self.create_widgets()
            self.load_banks()
            self.logger.info("تب جمع‌آوری کارمزد با موفقیت راه‌اندازی شد")
        except Exception as e:
            self.logger.error(f"خطا در راه‌اندازی تب جمع‌آوری کارمزد: {str(e)}")
            raise

    def create_widgets(self):
        """ایجاد عناصر گرافیکی تب"""
        try:
            # فریم انتخاب بانک و دکمه‌ها
            control_frame = ttk.Frame(self)
            control_frame.pack(fill=X, padx=10, pady=10)
            
            # انتخاب بانک
            ttk.Label(control_frame, text="انتخاب بانک:").pack(side=LEFT, padx=5)
            self.bank_combo = ttk.Combobox(control_frame, textvariable=self.bank_var, state="readonly", width=30)
            self.bank_combo.pack(side=LEFT, padx=5)
            self.bank_combo.bind("<<ComboboxSelected>>", self.on_bank_selected)
            
            # دکمه جمع‌آوری کارمزد
            ttk.Button(control_frame, text="جمع‌آوری کارمزد", command=self.on_collect_fees, bootstyle=SUCCESS).pack(side=LEFT, padx=5)
            
            # فریم خروجی‌ها
            export_frame = ttk.Frame(self)
            export_frame.pack(fill=X, padx=10, pady=5)
            
            ttk.Button(export_frame, text="خروجی اکسل", command=self.export_to_excel, bootstyle=INFO).pack(side=LEFT, padx=5)
            ttk.Button(export_frame, text="خروجی PDF", command=self.export_to_pdf, bootstyle=INFO).pack(side=LEFT, padx=5)
            
            # لیست کارمزدها
            list_frame = ttk.Frame(self)
            list_frame.pack(fill=BOTH, expand=True, padx=10, pady=10)
            
            # عنوان لیست
            ttk.Label(list_frame, text="لیست کارمزدهای تجمیع شده", font=(DEFAULT_FONT, DEFAULT_FONT_SIZE + 2)).pack(pady=5)
            
            # جدول نمایش کارمزدها
            columns = ("id", "bank_name", "fee_date", "total_amount", "transaction_count", "created_at")
            self.fees_list = ttk.Treeview(list_frame, columns=columns, show="headings", height=15)
            
            # تنظیم عناوین ستون‌ها
            self.fees_list.heading("id", text="شناسه")
            self.fees_list.heading("bank_name", text="نام بانک")
            self.fees_list.heading("fee_date", text="تاریخ")
            self.fees_list.heading("total_amount", text="مبلغ کل")
            self.fees_list.heading("transaction_count", text="تعداد تراکنش")
            self.fees_list.heading("created_at", text="تاریخ ثبت")
            
            # تنظیم عرض ستون‌ها
            self.fees_list.column("id", width=50)
            self.fees_list.column("bank_name", width=150)
            self.fees_list.column("fee_date", width=100)
            self.fees_list.column("total_amount", width=150)
            self.fees_list.column("transaction_count", width=100)
            self.fees_list.column("created_at", width=150)
            
            # اسکرول‌بار
            scrollbar = ttk.Scrollbar(list_frame, orient=VERTICAL, command=self.fees_list.yview)
            self.fees_list.configure(yscrollcommand=scrollbar.set)
            
            # قرار دادن جدول و اسکرول‌بار
            self.fees_list.pack(side=LEFT, fill=BOTH, expand=True)
            scrollbar.pack(side=RIGHT, fill=Y)
            
            self.logger.debug("عناصر گرافیکی تب با موفقیت ایجاد شدند")
        except Exception as e:
            self.logger.error(f"خطا در ایجاد عناصر گرافیکی: {str(e)}")
            raise

    def load_banks(self):
        """بارگذاری لیست بانک‌ها در کامبوباکس"""
        try:
            banks = get_all_banks()
            bank_names = [bank['bank_name'] for bank in banks]
            self.banks_data = {bank['bank_name']: bank['id'] for bank in banks}
            
            self.bank_combo['values'] = bank_names
            if bank_names:
                self.bank_combo.current(0)
                self.on_bank_selected(None)
                
            self.logger.debug("لیست بانک‌ها با موفقیت بارگذاری شد")
        except Exception as e:
            self.logger.error(f"خطا در بارگذاری لیست بانک‌ها: {str(e)}")
            messagebox.showerror("خطا", f"خطا در بارگذاری لیست بانک‌ها: {str(e)}")

    def on_bank_selected(self, event):
        """رویداد انتخاب بانک از کامبوباکس"""
        try:
            selected_bank_name = self.bank_var.get()
            if selected_bank_name in self.banks_data:
                self.selected_bank_id = self.banks_data[selected_bank_name]
                self.refresh_fees_list()
                self.logger.debug(f"بانک {selected_bank_name} با شناسه {self.selected_bank_id} انتخاب شد")
        except Exception as e:
            self.logger.error(f"خطا در انتخاب بانک: {str(e)}")

    def on_collect_fees(self):
        """رویداد دکمه جمع‌آوری کارمزد"""
        if not self.selected_bank_id:
            messagebox.showwarning("هشدار", "لطفاً ابتدا یک بانک را انتخاب کنید")
            return
            
        try:
            # جمع‌آوری کارمزدها
            rows_affected = collect_bank_fees(self.selected_bank_id)
            
            if rows_affected > 0:
                messagebox.showinfo("موفقیت", f"کارمزدهای بانک با موفقیت جمع‌آوری شدند. {rows_affected} رکورد پردازش شد.")
                # به‌روزرسانی لیست
                self.refresh_fees_list()
            else:
                messagebox.showinfo("اطلاعات", "هیچ کارمزد جدیدی برای جمع‌آوری یافت نشد.")
                
            self.logger.info(f"جمع‌آوری کارمزدهای بانک با شناسه {self.selected_bank_id} انجام شد. {rows_affected} رکورد پردازش شد.")
        except Exception as e:
            self.logger.error(f"خطا در جمع‌آوری کارمزدها: {str(e)}")
            messagebox.showerror("خطا", f"خطا در جمع‌آوری کارمزدها: {str(e)}")

    def refresh_fees_list(self):
        """به‌روزرسانی لیست کارمزدهای تجمیع شده"""
        try:
            # پاک کردن لیست فعلی
            for item in self.fees_list.get_children():
                self.fees_list.delete(item)
                
            # دریافت کارمزدهای تجمیع شده برای بانک انتخاب شده
            fees = get_bank_fees(self.selected_bank_id)
            
            # وارد کردن ماژول تبدیل تاریخ
            from utils.helpers import gregorian_to_persian
            
            # افزودن به لیست
            for fee in fees:
                # تبدیل تاریخ‌ها به شمسی
                persian_fee_date = gregorian_to_persian(fee['fee_date'])
                persian_created_at = gregorian_to_persian(fee['created_at'])
                
                self.fees_list.insert("", END, values=(
                    fee['id'],
                    fee['bank_name'],
                    persian_fee_date,
                    f"{fee['total_amount']:,} ریال",
                    fee['transaction_count'],
                    persian_created_at
                ))
                
            self.logger.debug(f"لیست کارمزدها با موفقیت به‌روزرسانی شد. {len(fees)} رکورد نمایش داده شد.")
        except Exception as e:
            self.logger.error(f"خطا در به‌روزرسانی لیست کارمزدها: {str(e)}")
            messagebox.showerror("خطا", f"خطا در به‌روزرسانی لیست کارمزدها: {str(e)}")

    def export_to_excel(self):
        """خروجی گرفتن به فرمت اکسل"""
        try:
            if not self.fees_list.get_children():
                messagebox.showwarning("هشدار", "لیست کارمزدها خالی است")
                return
                
            # انتخاب مسیر ذخیره فایل
            file_path = filedialog.asksaveasfilename(
                defaultextension=".xlsx",
                filetypes=[("Excel files", "*.xlsx")],
                title="ذخیره فایل اکسل"
            )
            
            if not file_path:
                return
                
            # استخراج داده‌ها از لیست
            data = []
            columns = ["شناسه", "نام بانک", "تاریخ", "مبلغ کل", "تعداد تراکنش", "تاریخ ثبت"]
            
            for item_id in self.fees_list.get_children():
                values = self.fees_list.item(item_id, 'values')
                data.append(values)
                
            # ایجاد دیتافریم و ذخیره به اکسل
            df = pd.DataFrame(data, columns=columns)
            df.to_excel(file_path, index=False)
            
            messagebox.showinfo("موفقیت", f"فایل اکسل با موفقیت در مسیر زیر ذخیره شد:\n{file_path}")
            self.logger.info(f"خروجی اکسل با موفقیت در مسیر {file_path} ذخیره شد")
        except Exception as e:
            self.logger.error(f"خطا در ایجاد خروجی اکسل: {str(e)}")
            messagebox.showerror("خطا", f"خطا در ایجاد خروجی اکسل: {str(e)}")

    def export_to_pdf(self):
        """خروجی گرفتن به فرمت PDF"""
        try:
            if not self.fees_list.get_children():
                messagebox.showwarning("هشدار", "لیست کارمزدها خالی است")
                return
                
            # انتخاب مسیر ذخیره فایل
            file_path = filedialog.asksaveasfilename(
                defaultextension=".pdf",
                filetypes=[("PDF files", "*.pdf")],
                title="ذخیره فایل PDF"
            )
            
            if not file_path:
                return
                
            # استخراج داده‌ها از لیست
            data = [["شناسه", "نام بانک", "تاریخ", "مبلغ کل", "تعداد تراکنش", "تاریخ ثبت"]]
            
            for item_id in self.fees_list.get_children():
                values = self.fees_list.item(item_id, 'values')
                data.append(values)
                
            # ایجاد فایل PDF
            doc = SimpleDocTemplate(file_path, pagesize=A4)
            elements = []
            
            # استایل‌ها
            styles = getSampleStyleSheet()
            title_style = styles['Heading1']
            
            # عنوان
            title = Paragraph("گزارش کارمزدهای تجمیع شده", title_style)
            elements.append(title)
            
            # جدول
            table = Table(data)
            table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                ('GRID', (0, 0), (-1, -1), 1, colors.black)
            ]))
            
            elements.append(table)
            
            # ساخت PDF
            doc.build(elements)
            
            messagebox.showinfo("موفقیت", f"فایل PDF با موفقیت در مسیر زیر ذخیره شد:\n{file_path}")
            self.logger.info(f"خروجی PDF با موفقیت در مسیر {file_path} ذخیره شد")
        except Exception as e:
            self.logger.error(f"خطا در ایجاد خروجی PDF: {str(e)}")
            messagebox.showerror("خطا", f"خطا در ایجاد خروجی PDF: {str(e)}")