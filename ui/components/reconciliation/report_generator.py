"""
Report Generator Module
ماژول تولید گزارش - جدا شده از manual_reconciliation_tab.py
"""
import logging
import tempfile
import subprocess
from datetime import datetime
from tkinter import messagebox
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from utils.helpers import gregorian_to_persian


class ReportGenerator:
    """کلاس تولید گزارشات PDF"""
    
    def __init__(self, banks_dict, logger=None):
        self.banks_dict = banks_dict
        self.logger = logger or logging.getLogger(__name__)
        self._setup_fonts()
    
    def _setup_fonts(self):
        """تنظیم فونت‌های فارسی برای PDF"""
        try:
            # تلاش برای ثبت فونت‌های مختلف فارسی
            font_paths = [
                'fonts/BNazanin.ttf',
                'fonts/Vazir.ttf', 
                'fonts/Tahoma.ttf',
                'assets/fonts/BNazanin.ttf',
                'assets/fonts/Vazir.ttf'
            ]
            
            self.font_registered = False
            self.font_name = 'Helvetica'  # فونت پیش‌فرض
            
            for font_path in font_paths:
                try:
                    pdfmetrics.registerFont(TTFont('PersianFont', font_path))
                    self.font_name = 'PersianFont'
                    self.font_registered = True
                    self.logger.info(f"فونت فارسی از مسیر {font_path} ثبت شد")
                    break
                except Exception as font_error:
                    continue
            
            if not self.font_registered:
                self.logger.warning("فونت فارسی یافت نشد، از فونت پیش‌فرض استفاده می‌شود")
                
        except Exception as e:
            self.logger.error(f"خطا در تنظیم فونت‌ها: {str(e)}")
            self.font_name = 'Helvetica'
            self.font_registered = False
    
    def generate_reconciliation_report(self, bank_record, accounting_records):
        """
        تولید گزارش مغایرت‌گیری برای یک رکورد بانک و رکوردهای حسابداری مرتبط
        
        Args:
            bank_record: رکورد بانک
            accounting_records: لیست رکوردهای حسابداری
            
        Returns:
            str: مسیر فایل PDF تولید شده یا None در صورت خطا
        """
        try:
            if not bank_record:
                messagebox.showwarning("هشدار", "رکورد بانک انتخاب نشده است")
                return None
            
            # ایجاد فایل PDF موقت
            with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as temp_file:
                pdf_path = temp_file.name
            
            # ایجاد PDF
            c = canvas.Canvas(pdf_path, pagesize=A4)
            
            if not self.font_registered:
                messagebox.showwarning(
                    "هشدار", 
                    "فونت فارسی یافت نشد. گزارش ممکن است به درستی نمایش داده نشود."
                )
            
            # تولید محتوای گزارش
            self._generate_report_content(c, bank_record, accounting_records)
            
            c.save()
            
            # باز کردن فایل PDF
            self._open_pdf_file(pdf_path)
            
            self.logger.info(f"گزارش PDF در مسیر {pdf_path} ایجاد شد")
            return pdf_path
            
        except Exception as e:
            error_message = f"خطا در تولید گزارش PDF: {str(e)}"
            self.logger.error(error_message)
            messagebox.showerror("خطا", error_message)
            return None
    
    def _generate_report_content(self, canvas_obj, bank_record, accounting_records):
        """تولید محتوای گزارش PDF"""
        try:
            # تنظیم فونت
            canvas_obj.setFont(self.font_name, 12)
            
            # عنوان گزارش
            y_position = 800
            canvas_obj.drawRightString(500, y_position, "گزارش مغایرت‌یابی دستی")
            
            y_position -= 20
            canvas_obj.drawRightString(
                500, y_position, 
                f"تاریخ: {gregorian_to_persian(datetime.now().strftime('%Y-%m-%d'))}"
            )
            
            # اطلاعات رکورد بانک
            y_position -= 40
            y_position = self._add_bank_record_info(canvas_obj, bank_record, y_position)
            
            # اطلاعات رکوردهای حسابداری
            y_position -= 20
            y_position = self._add_accounting_records_info(canvas_obj, accounting_records, y_position)
            
            # اطلاعات تکمیلی
            self._add_summary_info(canvas_obj, bank_record, accounting_records, y_position)
            
        except Exception as e:
            self.logger.error(f"خطا در تولید محتوای گزارش: {str(e)}")
            raise
    
    def _add_bank_record_info(self, canvas_obj, bank_record, y_position):
        """اضافه کردن اطلاعات رکورد بانک به گزارش"""
        try:
            canvas_obj.drawRightString(500, y_position, "اطلاعات رکورد بانک:")
            y_position -= 20
            
            # شناسه
            canvas_obj.drawRightString(500, y_position, f"شناسه: {bank_record['id']}")
            y_position -= 20
            
            # شماره پیگیری
            tracking_number = bank_record.get('extracted_tracking_number', 'نامشخص')
            canvas_obj.drawRightString(500, y_position, f"شماره پیگیری: {tracking_number}")
            y_position -= 20
            
            # تاریخ
            shamsi_date = gregorian_to_persian(bank_record['transaction_date'])
            canvas_obj.drawRightString(500, y_position, f"تاریخ: {shamsi_date}")
            y_position -= 20
            
            # مبلغ
            canvas_obj.drawRightString(500, y_position, f"مبلغ: {bank_record['amount']:,} ریال")
            y_position -= 20
            
            # توضیحات
            description = bank_record.get('description', '')[:50]  # محدود کردن طول
            canvas_obj.drawRightString(500, y_position, f"توضیحات: {description}")
            y_position -= 20
            
            # نوع تراکنش
            transaction_type = bank_record.get('transaction_type', 'نامشخص')
            canvas_obj.drawRightString(500, y_position, f"نوع تراکنش: {transaction_type}")
            y_position -= 20
            
            # واریز کننده
            depositor = bank_record.get('depositor_name', 'نامشخص')
            canvas_obj.drawRightString(500, y_position, f"واریز کننده: {depositor}")
            y_position -= 20
            
            return y_position
            
        except Exception as e:
            self.logger.error(f"خطا در اضافه کردن اطلاعات رکورد بانک: {str(e)}")
            return y_position - 100  # فاصله پیش‌فرض در صورت خطا
    
    def _add_accounting_records_info(self, canvas_obj, accounting_records, y_position):
        """اضافه کردن اطلاعات رکوردهای حسابداری به گزارش"""
        try:
            canvas_obj.drawRightString(500, y_position, "رکوردهای حسابداری مرتبط:")
            y_position -= 20
            
            if not accounting_records:
                canvas_obj.drawRightString(480, y_position, "هیچ رکورد حسابداری یافت نشد")
                return y_position - 20
            
            for i, record in enumerate(accounting_records, 1):
                # بررسی فضای باقی‌مانده در صفحه
                if y_position < 100:
                    canvas_obj.showPage()
                    canvas_obj.setFont(self.font_name, 12)
                    y_position = 750
                
                # عنوان رکورد
                canvas_obj.drawRightString(500, y_position, f"رکورد {i}:")
                y_position -= 20
                
                # شناسه
                canvas_obj.drawRightString(480, y_position, f"شناسه: {record['id']}")
                y_position -= 20
                
                # شماره پیگیری
                tracking_number = record.get('transaction_number', 'نامشخص')
                canvas_obj.drawRightString(480, y_position, f"شماره پیگیری: {tracking_number}")
                y_position -= 20
                
                # تاریخ
                record_date = record.get('due_date') or record.get('transaction_date', '')
                if record_date:
                    shamsi_date = gregorian_to_persian(record_date)
                    canvas_obj.drawRightString(480, y_position, f"تاریخ: {shamsi_date}")
                y_position -= 20
                
                # مبلغ
                amount = record.get('transaction_amount', 0)
                canvas_obj.drawRightString(480, y_position, f"مبلغ: {amount:,} ریال")
                y_position -= 20
                
                # توضیحات
                description = record.get('description', '')[:50]
                canvas_obj.drawRightString(480, y_position, f"توضیحات: {description}")
                y_position -= 20
                
                # نوع تراکنش
                transaction_type = record.get('transaction_type', '')
                canvas_obj.drawRightString(480, y_position, f"نوع تراکنش: {transaction_type}")
                y_position -= 20
                
                # نام بانک
                bank_id = record.get('bank_id')
                bank_name = self._get_bank_name_by_id(bank_id)
                canvas_obj.drawRightString(480, y_position, f"بانک: {bank_name}")
                y_position -= 20
                
                # سیستم
                system_text = "سیستم جدید" if record.get('is_new_system', 0) == 1 else "سیستم قدیم"
                canvas_obj.drawRightString(480, y_position, f"سیستم: {system_text}")
                y_position -= 40  # فاصله بیشتر بین رکوردها
            
            return y_position
            
        except Exception as e:
            self.logger.error(f"خطا در اضافه کردن اطلاعات رکوردهای حسابداری: {str(e)}")
            return y_position - 100
    
    def _add_summary_info(self, canvas_obj, bank_record, accounting_records, y_position):
        """اضافه کردن اطلاعات خلاصه به گزارش"""
        try:
            if y_position < 150:
                canvas_obj.showPage()
                canvas_obj.setFont(self.font_name, 12)
                y_position = 750
            
            canvas_obj.drawRightString(500, y_position, "خلاصه گزارش:")
            y_position -= 20
            
            # تعداد رکوردهای حسابداری
            canvas_obj.drawRightString(480, y_position, f"تعداد رکوردهای حسابداری یافت شده: {len(accounting_records)}")
            y_position -= 20
            
            # محاسبه مجموع مبالغ حسابداری
            if accounting_records:
                total_accounting_amount = sum(
                    record.get('transaction_amount', 0) for record in accounting_records
                )
                canvas_obj.drawRightString(480, y_position, f"مجموع مبالغ حسابداری: {total_accounting_amount:,} ریال")
                y_position -= 20
                
                # مقایسه با مبلغ بانک
                bank_amount = bank_record.get('amount', 0)
                difference = bank_amount - total_accounting_amount
                
                if difference == 0:
                    canvas_obj.drawRightString(480, y_position, "وضعیت: مطابقت کامل")
                elif difference > 0:
                    canvas_obj.drawRightString(480, y_position, f"اختلاف (احتمال کارمزد): {difference:,} ریال")
                else:
                    canvas_obj.drawRightString(480, y_position, f"اختلاف (مبلغ حسابداری بیشتر): {abs(difference):,} ریال")
                
                y_position -= 20
            
            # تاریخ و زمان تولید گزارش
            canvas_obj.drawRightString(480, y_position, f"زمان تولید گزارش: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            
        except Exception as e:
            self.logger.error(f"خطا در اضافه کردن اطلاعات خلاصه: {str(e)}")
    
    def _get_bank_name_by_id(self, bank_id):
        """دریافت نام بانک بر اساس شناسه"""
        try:
            for bank_name, bid in self.banks_dict.items():
                if bid == bank_id:
                    return bank_name
            return "نامشخص"
        except:
            return "نامشخص"
    
    def _open_pdf_file(self, pdf_path):
        """باز کردن فایل PDF"""
        try:
            subprocess.Popen([pdf_path], shell=True)
            self.logger.info(f"فایل PDF باز شد: {pdf_path}")
        except Exception as e:
            error_message = f"خطا در باز کردن فایل PDF: {str(e)}"
            self.logger.error(error_message)
            messagebox.showerror("خطا", error_message)
    
    def generate_summary_report(self, all_bank_records, all_accounting_records):
        """تولید گزارش خلاصه از تمام رکوردها"""
        try:
            # ایجاد فایل PDF موقت
            with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as temp_file:
                pdf_path = temp_file.name
            
            c = canvas.Canvas(pdf_path, pagesize=A4)
            c.setFont(self.font_name, 12)
            
            # عنوان گزارش خلاصه
            y_position = 800
            c.drawRightString(500, y_position, "گزارش خلاصه مغایرت‌گیری")
            
            y_position -= 20
            c.drawRightString(500, y_position, f"تاریخ: {gregorian_to_persian(datetime.now().strftime('%Y-%m-%d'))}")
            
            # آمار کلی
            y_position -= 40
            c.drawRightString(500, y_position, "آمار کلی:")
            y_position -= 20
            
            c.drawRightString(480, y_position, f"تعداد رکوردهای بانک: {len(all_bank_records)}")
            y_position -= 20
            
            c.drawRightString(480, y_position, f"تعداد رکوردهای حسابداری: {len(all_accounting_records)}")
            y_position -= 20
            
            # محاسبه مجموع مبالغ
            total_bank_amount = sum(record.get('amount', 0) for record in all_bank_records)
            total_accounting_amount = sum(record.get('transaction_amount', 0) for record in all_accounting_records)
            
            c.drawRightString(480, y_position, f"مجموع مبالغ بانک: {total_bank_amount:,} ریال")
            y_position -= 20
            
            c.drawRightString(480, y_position, f"مجموع مبالغ حسابداری: {total_accounting_amount:,} ریال")
            y_position -= 20
            
            difference = total_bank_amount - total_accounting_amount
            c.drawRightString(480, y_position, f"اختلاف کل: {difference:,} ریال")
            
            c.save()
            self._open_pdf_file(pdf_path)
            
            return pdf_path
            
        except Exception as e:
            error_message = f"خطا در تولید گزارش خلاصه: {str(e)}"
            self.logger.error(error_message)
            messagebox.showerror("خطا", error_message)
            return None
