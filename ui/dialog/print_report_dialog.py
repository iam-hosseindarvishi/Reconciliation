import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import os
import tempfile
from datetime import datetime
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from utils.helpers import gregorian_to_persian

class PrintReportDialog(tk.Toplevel):
    """دیالوگ چاپ گزارش مغایرت‌یابی دستی"""
    
    def __init__(self, parent, bank_record, accounting_records):
        super().__init__(parent)
        self.parent = parent
        self.bank_record = bank_record
        self.accounting_records = accounting_records
        
        # تنظیم عنوان و ویژگی‌های پنجره
        self.title("چاپ گزارش مغایرت‌یابی دستی")
        self.geometry("500x400")
        self.resizable(False, False)
        self.configure(bg="#f0f0f0")
        
        # تنظیم به عنوان پنجره مودال
        self.transient(parent)
        self.grab_set()
        
        # ایجاد ویجت‌ها
        self.create_widgets()
        
        # منتظر بستن پنجره می‌مانیم
        self.wait_window(self)
    
    def create_widgets(self):
        """ایجاد ویجت‌های دیالوگ"""
        # فریم اصلی
        main_frame = ttk.Frame(self, padding=10)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # فونت‌ها
        self.default_font = ('B Nazanin', 11)
        
        # عنوان
        title_label = ttk.Label(main_frame, text="گزارش مغایرت‌یابی دستی", font=('B Nazanin', 14, 'bold'))
        title_label.pack(pady=10)
        
        # فریم اطلاعات رکورد بانک
        bank_frame = ttk.LabelFrame(main_frame, text="اطلاعات رکورد بانک", padding=5)
        bank_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # نمایش اطلاعات رکورد بانک
        bank_info = f"شماره پیگیری: {self.bank_record.get('tracking_number', 'نامشخص')}\n"
        bank_info += f"تاریخ: {gregorian_to_persian(self.bank_record['date'])}\n"
        bank_info += f"مبلغ: {self.bank_record['amount']:,} ریال\n"
        bank_info += f"توضیحات: {self.bank_record.get('description', '')}\n"
        
        bank_info_label = ttk.Label(bank_frame, text=bank_info, font=self.default_font, justify=tk.RIGHT)
        bank_info_label.pack(anchor=tk.W, padx=5, pady=5)
        
        # فریم اطلاعات رکوردهای حسابداری
        accounting_frame = ttk.LabelFrame(main_frame, text="اطلاعات رکوردهای حسابداری", padding=5)
        accounting_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # ایجاد اسکرول برای لیست رکوردهای حسابداری
        scroll = ttk.Scrollbar(accounting_frame)
        scroll.pack(side=tk.RIGHT, fill=tk.Y)
        
        # لیست رکوردهای حسابداری
        self.accounting_list = tk.Text(accounting_frame, font=self.default_font, yscrollcommand=scroll.set, height=10)
        self.accounting_list.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        scroll.config(command=self.accounting_list.yview)
        
        # نمایش اطلاعات رکوردهای حسابداری
        for i, record in enumerate(self.accounting_records, 1):
            record_info = f"\n{i}. شماره پیگیری: {record.get('tracking_number', 'نامشخص')}\n"
            record_info += f"   تاریخ: {gregorian_to_persian(record['date'])}\n"
            record_info += f"   مبلغ: {record['amount']:,} ریال\n"
            record_info += f"   نوع تراکنش: {record.get('transaction_type', 'نامشخص')}\n"
            record_info += f"   توضیحات: {record.get('description', '')}\n"
            
            self.accounting_list.insert(tk.END, record_info)
        
        self.accounting_list.config(state=tk.DISABLED)  # غیرقابل ویرایش کردن متن
        
        # فریم دکمه‌ها
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(pady=10)
        
        # دکمه‌های چاپ و انصراف
        ttk.Button(button_frame, text="چاپ PDF", command=self.print_pdf, style='Default.TButton').pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="انصراف", command=self.destroy, style='Default.TButton').pack(side=tk.LEFT, padx=5)
    
    def print_pdf(self):
        """ایجاد و ذخیره فایل PDF"""
        try:
            # دریافت مسیر ذخیره فایل از کاربر
            file_path = filedialog.asksaveasfilename(
                defaultextension=".pdf",
                filetypes=[("PDF files", "*.pdf")],
                title="ذخیره گزارش به صورت PDF"
            )
            
            if not file_path:  # اگر کاربر انصراف داد
                return
            
            # ثبت فونت فارسی
            font_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "assets", "fonts", "BNazanin.ttf")
            pdfmetrics.registerFont(TTFont('BNazanin', font_path))
            
            # ایجاد فایل PDF
            c = canvas.Canvas(file_path, pagesize=A4)
            width, height = A4
            
            # تنظیم فونت و اندازه
            c.setFont('BNazanin', 16)
            
            # عنوان گزارش
            c.drawRightString(width - 50, height - 50, "گزارش مغایرت‌یابی دستی")
            c.setFont('BNazanin', 12)
            c.drawRightString(width - 50, height - 70, f"تاریخ گزارش: {gregorian_to_persian(datetime.now().strftime('%Y-%m-%d'))}")
            
            # خط جداکننده
            c.line(50, height - 80, width - 50, height - 80)
            
            # اطلاعات رکورد بانک
            c.setFont('BNazanin', 14)
            c.drawRightString(width - 50, height - 100, "اطلاعات رکورد بانک:")
            c.setFont('BNazanin', 12)
            
            y_position = height - 120
            c.drawRightString(width - 50, y_position, f"شماره پیگیری: {self.bank_record.get('tracking_number', 'نامشخص')}")
            y_position -= 20
            c.drawRightString(width - 50, y_position, f"تاریخ: {gregorian_to_persian(self.bank_record['date'])}")
            y_position -= 20
            c.drawRightString(width - 50, y_position, f"مبلغ: {self.bank_record['amount']:,} ریال")
            y_position -= 20
            
            # توضیحات ممکن است طولانی باشد، آن را به چند خط تقسیم می‌کنیم
            description = self.bank_record.get('description', '')
            if description:
                c.drawRightString(width - 50, y_position, "توضیحات:")
                y_position -= 20
                
                # تقسیم توضیحات به خطوط کوتاه‌تر
                words = description.split()
                line = ""
                for word in words:
                    test_line = line + " " + word if line else word
                    if c.stringWidth(test_line, 'BNazanin', 12) < width - 100:
                        line = test_line
                    else:
                        c.drawRightString(width - 70, y_position, line)
                        y_position -= 20
                        line = word
                
                if line:  # آخرین خط
                    c.drawRightString(width - 70, y_position, line)
                    y_position -= 20
            
            # خط جداکننده
            y_position -= 10
            c.line(50, y_position, width - 50, y_position)
            y_position -= 20
            
            # اطلاعات رکوردهای حسابداری
            c.setFont('BNazanin', 14)
            c.drawRightString(width - 50, y_position, "اطلاعات رکوردهای حسابداری:")
            c.setFont('BNazanin', 12)
            y_position -= 30
            
            # نمایش اطلاعات هر رکورد حسابداری
            for i, record in enumerate(self.accounting_records, 1):
                # بررسی نیاز به صفحه جدید
                if y_position < 100:
                    c.showPage()
                    c.setFont('BNazanin', 12)
                    y_position = height - 50
                
                c.drawRightString(width - 50, y_position, f"{i}. شماره پیگیری: {record.get('tracking_number', 'نامشخص')}")
                y_position -= 20
                c.drawRightString(width - 70, y_position, f"تاریخ: {gregorian_to_persian(record['date'])}")
                y_position -= 20
                c.drawRightString(width - 70, y_position, f"مبلغ: {record['amount']:,} ریال")
                y_position -= 20
                c.drawRightString(width - 70, y_position, f"نوع تراکنش: {record.get('transaction_type', 'نامشخص')}")
                y_position -= 20
                
                # توضیحات رکورد حسابداری
                description = record.get('description', '')
                if description:
                    c.drawRightString(width - 70, y_position, "توضیحات:")
                    y_position -= 20
                    
                    # تقسیم توضیحات به خطوط کوتاه‌تر
                    words = description.split()
                    line = ""
                    for word in words:
                        test_line = line + " " + word if line else word
                        if c.stringWidth(test_line, 'BNazanin', 12) < width - 120:
                            line = test_line
                        else:
                            c.drawRightString(width - 90, y_position, line)
                            y_position -= 20
                            line = word
                    
                    if line:  # آخرین خط
                        c.drawRightString(width - 90, y_position, line)
                        y_position -= 20
                
                y_position -= 10  # فاصله بین رکوردها
            
            # ذخیره فایل PDF
            c.save()
            
            messagebox.showinfo("اطلاعات", f"گزارش با موفقیت در مسیر زیر ذخیره شد:\n{file_path}")
            
        except Exception as e:
            messagebox.showerror("خطا", f"خطا در ایجاد فایل PDF:\n{str(e)}")