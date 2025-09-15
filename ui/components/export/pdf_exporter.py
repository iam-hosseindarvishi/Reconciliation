"""
PDF Export Module
جدا شده از report_tab.py برای ماژولار کردن کد
"""
import os
import logging
from tkinter import filedialog, messagebox
from datetime import datetime
import tempfile

try:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    from reportlab.lib.enums import TA_RIGHT, TA_CENTER
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False

try:
    from bidi.algorithm import get_display
    from arabic_reshaper import reshape
    import jdatetime
    RTL_SUPPORT_AVAILABLE = True
except ImportError:
    RTL_SUPPORT_AVAILABLE = False


class PDFExporter:
    """کلاس صدور اطلاعات به فایل PDF"""
    
    def __init__(self, logger=None):
        self.logger = logger or logging.getLogger(__name__)
    
    def export_to_pdf(self, data, columns, selected_table, selected_bank, table_data):
        """صدور گزارش به فایل PDF"""
        try:
            if not data:
                messagebox.showwarning("هشدار", "هیچ داده‌ای برای صدور وجود ندارد")
                return False
            
            # بررسی وجود کتابخانه‌های مورد نیاز
            if not REPORTLAB_AVAILABLE:
                self._show_missing_libraries_error()
                return False
            
            # دریافت مسیر ذخیره فایل
            file_path = filedialog.asksaveasfilename(
                defaultextension=".pdf",
                filetypes=[("PDF files", "*.pdf")],
                title="ذخیره فایل PDF"
            )
            
            if not file_path:
                return False
            
            # ثبت فونت فارسی
            if not self._register_persian_font():
                return False
            
            # ایجاد PDF
            self._create_pdf(file_path, selected_table, selected_bank, table_data)
            
            self.logger.info(f"گزارش با موفقیت به فایل {file_path} صادر شد")
            messagebox.showinfo("موفقیت", "گزارش با موفقیت به PDF صادر شد")
            return True
            
        except Exception as e:
            error_msg = f"خطا در صدور به PDF: {str(e)}"
            self.logger.error(error_msg)
            messagebox.showerror("خطا", error_msg)
            return False
    
    def _show_missing_libraries_error(self):
        """نمایش خطای کتابخانه‌های گمشده"""
        error_msg = (
            "برای صدور به PDF با پشتیبانی فارسی نیاز به نصب کتابخانه‌های زیر دارید:\n\n"
            "pip install -r requirements_pdf_persian.txt\n\n"
            "یا:\n\n"
            "pip install reportlab python-bidi arabic-reshaper jdatetime"
        )
        messagebox.showerror("خطا", error_msg)
    
    def _register_persian_font(self):
        """ثبت فونت فارسی"""
        try:
            font_path = os.path.join(
                os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
                "assets", "fonts", "Vazir.ttf"
            )
            
            if not os.path.exists(font_path):
                self.logger.error(f"فایل فونت در مسیر {font_path} یافت نشد")
                messagebox.showerror("خطا", f"فایل فونت در مسیر {font_path} یافت نشد")
                return False
            
            self.logger.info(f"فایل فونت در مسیر {font_path} یافت شد")
            pdfmetrics.registerFont(TTFont('Vazir', font_path))
            return True
            
        except Exception as e:
            self.logger.error(f"خطا در ثبت فونت: {str(e)}")
            messagebox.showerror("خطا", f"خطا در ثبت فونت: {str(e)}")
            return False
    
    def _create_pdf(self, file_path, selected_table, selected_bank, table_data):
        """ایجاد فایل PDF"""
        # ایجاد استایل‌های متن
        styles = getSampleStyleSheet()
        styles.add(ParagraphStyle(name='RTL', fontName='Vazir', alignment=TA_RIGHT))
        
        # ایجاد داکیومنت PDF
        doc = SimpleDocTemplate(file_path, pagesize=landscape(A4))
        elements = []
        
        # اضافه کردن عنوان و تاریخ
        self._add_title_and_date(elements, styles, selected_table, selected_bank)
        
        # ایجاد جدول
        self._add_data_table(elements, table_data)
        
        # اضافه کردن پاورقی
        self._add_footer(elements, styles, len(table_data))
        
        # ساخت PDF
        doc.build(elements)
    
    def _add_title_and_date(self, elements, styles, selected_table, selected_bank):
        """اضافه کردن عنوان و تاریخ به PDF"""
        # عنوان گزارش
        title_style = ParagraphStyle(
            'Title',
            parent=styles['Title'],
            fontName='Vazir',
            alignment=TA_RIGHT,
            fontSize=16
        )
        
        report_title = f"گزارش {selected_table}"
        if selected_bank != "همه موارد":
            report_title += f" - بانک {selected_bank}"
        
        formatted_title = self._format_persian_text(report_title)
        elements.append(Paragraph(formatted_title, title_style))
        elements.append(Spacer(1, 20))
        
        # تاریخ گزارش
        date_style = ParagraphStyle(
            'Date',
            parent=styles['Normal'],
            fontName='Vazir',
            alignment=TA_RIGHT,
            fontSize=10
        )
        
        report_date = self._get_jalali_date()
        formatted_date_text = self._format_persian_text(f"تاریخ گزارش: {report_date}")
        elements.append(Paragraph(formatted_date_text, date_style))
        elements.append(Spacer(1, 20))
    
    def _add_data_table(self, elements, table_data):
        """اضافه کردن جدول داده‌ها به PDF"""
        if not table_data:
            return
        
        # ایجاد داده‌های جدول
        table_data_formatted = []
        
        # فرض می‌کنیم ردیف اول عنوان ستون‌هاست
        if table_data:
            # هدر جدول
            header_row = [self._format_persian_text(str(cell)) for cell in table_data[0]]
            table_data_formatted.append(header_row)
            
            # ردیف‌های داده
            for row in table_data[1:]:
                data_row = []
                for cell in row:
                    formatted_value = self._format_persian_text(str(cell) if cell is not None else "")
                    data_row.append(formatted_value)
                table_data_formatted.append(data_row)
        
        # ایجاد جدول
        table = Table(table_data_formatted, repeatRows=1)
        
        # استایل جدول
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
            ('ALIGN', (0, 0), (-1, -1), 'RIGHT'),
            ('FONTNAME', (0, 0), (-1, -1), 'Vazir'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ]))
        
        elements.append(table)
    
    def _add_footer(self, elements, styles, record_count):
        """اضافه کردن پاورقی به PDF"""
        elements.append(Spacer(1, 20))
        footer_style = ParagraphStyle(
            'Footer',
            parent=styles['Normal'],
            fontName='Vazir',
            alignment=TA_RIGHT,
            fontSize=10
        )
        formatted_footer_text = self._format_persian_text(f"تعداد رکوردها: {record_count}")
        elements.append(Paragraph(formatted_footer_text, footer_style))
    
    def _format_persian_text(self, text):
        """تنظیم متن فارسی برای نمایش صحیح در PDF"""
        if not text or not isinstance(text, str):
            return str(text) if text is not None else ""
        
        if RTL_SUPPORT_AVAILABLE:
            try:
                # Reshape Arabic/Persian characters
                reshaped_text = reshape(text)
                # Apply bidirectional algorithm
                display_text = get_display(reshaped_text)
                return display_text
            except Exception as e:
                self.logger.warning(f"خطا در تنظیم متن فارسی: {str(e)}")
                return text
        else:
            # Fallback: at least reverse the string for basic RTL support
            try:
                # Simple reversal for Persian text (not perfect but better than nothing)
                import re
                if re.search(r'[\u0600-\u06FF]', text):
                    return text[::-1]  # Simple reversal for Persian characters
                return text
            except:
                return text
    
    def _get_jalali_date(self):
        """دریافت تاریخ جلالی فعلی"""
        if RTL_SUPPORT_AVAILABLE:
            try:
                gregorian_date = datetime.now()
                jalali_date = jdatetime.datetime.fromgregorian(datetime=gregorian_date)
                return jalali_date.strftime("%Y/%m/%d %H:%M:%S")
            except Exception as e:
                self.logger.warning(f"خطا در تبدیل تاریخ جلالی: {str(e)}")
        
        # Fallback to Gregorian date
        return datetime.now().strftime("%Y/%m/%d %H:%M:%S")
