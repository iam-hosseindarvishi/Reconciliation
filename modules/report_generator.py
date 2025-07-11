#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
ماژول تولید گزارش
این ماژول مسئول تولید گزارش‌های PDF از نتایج مغایرت‌گیری است.
"""

import os
import time
from datetime import datetime
from typing import Dict, List, Optional, Any

from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

from modules.database_manager import DatabaseManager
from modules.utils import format_currency, convert_gregorian_to_jalali_str
from modules.logger import get_logger

# ایجاد شیء لاگر
logger = get_logger(__name__)

# تنظیمات مسیرها
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPORTS_DIR = os.path.join(BASE_DIR, 'reports')
FONTS_DIR = os.path.join(BASE_DIR, 'config', 'fonts')

# اطمینان از وجود دایرکتوری گزارش‌ها
os.makedirs(REPORTS_DIR, exist_ok=True)

# ثبت فونت‌های فارسی
def register_fonts():
    """
    ثبت فونت‌های فارسی برای استفاده در گزارش‌ها
    """
    try:
        # اطمینان از وجود دایرکتوری فونت‌ها
        os.makedirs(FONTS_DIR, exist_ok=True)
        
        # مسیر فونت‌ها
        vazir_path = os.path.join(FONTS_DIR, 'Vazir.ttf')
        vazir_bold_path = os.path.join(FONTS_DIR, 'Vazir-Bold.ttf')
        
        # بررسی وجود فونت‌ها
        if not os.path.exists(vazir_path) or not os.path.exists(vazir_bold_path):
            logger.warning("فونت‌های فارسی یافت نشد. از فونت‌های پیش‌فرض استفاده می‌شود.")
            return False
        
        # ثبت فونت‌ها
        pdfmetrics.registerFont(TTFont('Vazir', vazir_path))
        pdfmetrics.registerFont(TTFont('Vazir-Bold', vazir_bold_path))
        
        logger.info("فونت‌های فارسی با موفقیت ثبت شدند.")
        return True
    except Exception as e:
        logger.error(f"خطا در ثبت فونت‌های فارسی: {str(e)}")
        return False


class ReportGenerator:
    """
    کلاس تولید گزارش‌های PDF
    """
    
    def __init__(self, db_manager: DatabaseManager):
        """
        مقداردهی اولیه کلاس ReportGenerator
        
        پارامترها:
            db_manager: نمونه‌ای از کلاس DatabaseManager
        """
        self.db_manager = db_manager
        self.fonts_registered = register_fonts()
        
        # ایجاد استایل‌های پاراگراف
        self.styles = getSampleStyleSheet()
        
        # استایل عنوان
        self.title_style = ParagraphStyle(
            'Title',
            parent=self.styles['Title'],
            fontName='Vazir-Bold' if self.fonts_registered else 'Helvetica-Bold',
            fontSize=16,
            alignment=1,  # وسط‌چین
            spaceAfter=12
        )
        
        # استایل سرفصل
        self.heading_style = ParagraphStyle(
            'Heading',
            parent=self.styles['Heading2'],
            fontName='Vazir-Bold' if self.fonts_registered else 'Helvetica-Bold',
            fontSize=14,
            alignment=1,  # وسط‌چین
            spaceAfter=10
        )
        
        # استایل متن عادی
        self.normal_style = ParagraphStyle(
            'Normal',
            parent=self.styles['Normal'],
            fontName='Vazir' if self.fonts_registered else 'Helvetica',
            fontSize=10,
            alignment=2,  # راست‌چین
            firstLineIndent=20
        )
        
        # استایل جدول
        self.table_style = TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('FONTNAME', (0, 0), (-1, 0), 'Vazir-Bold' if self.fonts_registered else 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
            ('BACKGROUND', (0, 1), (-1, -1), colors.white),
            ('FONTNAME', (0, 1), (-1, -1), 'Vazir' if self.fonts_registered else 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 10),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('LEFTPADDING', (0, 0), (-1, -1), 6),
            ('RIGHTPADDING', (0, 0), (-1, -1), 6),
        ])
    
    def generate_unmatched_bank_report(self) -> str:
        """
        تولید گزارش تراکنش‌های بانکی مغایرت‌گیری نشده
        
        خروجی:
            مسیر فایل PDF تولید شده
        """
        try:
            # دریافت داده‌ها
            unmatched_bank_transactions = self.db_manager.get_unreconciled_bank_transactions()
            
            if not unmatched_bank_transactions:
                logger.warning("هیچ تراکنش بانکی مغایرت‌گیری نشده‌ای یافت نشد.")
                return ""
            
            # ایجاد نام فایل
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            file_name = f"unmatched_bank_{timestamp}.pdf"
            file_path = os.path.join(REPORTS_DIR, file_name)
            
            # ایجاد داکیومنت PDF
            doc = SimpleDocTemplate(
                file_path,
                pagesize=A4,
                rightMargin=30,
                leftMargin=30,
                topMargin=30,
                bottomMargin=30
            )
            
            # لیست عناصر
            elements = []
            
            # عنوان گزارش
            title = Paragraph("گزارش تراکنش‌های بانکی مغایرت‌گیری نشده", self.title_style)
            elements.append(title)
            elements.append(Spacer(1, 20))
            
            # تاریخ گزارش
            report_date = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            jalali_date = convert_gregorian_to_jalali_str(report_date, '%Y-%m-%d %H:%M:%S', '%Y/%m/%d %H:%M:%S')
            date_text = Paragraph(f"تاریخ گزارش: {jalali_date}", self.normal_style)
            elements.append(date_text)
            elements.append(Spacer(1, 20))
            
            # آمار
            stats = self.db_manager.get_reconciliation_statistics()
            stats_text = Paragraph(
                f"تعداد کل تراکنش‌های بانکی: {stats.get('total_bank', 0)}<br/>"
                f"تعداد تراکنش‌های مغایرت‌گیری شده: {stats.get('reconciled_bank', 0)}<br/>"
                f"تعداد تراکنش‌های مغایرت‌گیری نشده: {stats.get('unreconciled_bank', 0)}",
                self.normal_style
            )
            elements.append(stats_text)
            elements.append(Spacer(1, 20))
            
            # داده‌های جدول
            table_data = [
                ["ردیف", "تاریخ", "مبلغ واریز", "مبلغ برداشت", "توضیحات", "نوع تراکنش", "شناسه پیگیری"]
            ]
            
            for i, tx in enumerate(unmatched_bank_transactions, 1):
                deposit = format_currency(tx.get('Deposit_Amount', 0)) if tx.get('Deposit_Amount') else ""
                withdrawal = format_currency(tx.get('Withdrawal_Amount', 0)) if tx.get('Withdrawal_Amount') else ""
                
                row = [
                    str(i),
                    tx.get('Date', ''),
                    deposit,
                    withdrawal,
                    tx.get('Description_Bank', '')[:50],  # محدود کردن طول توضیحات
                    tx.get('Transaction_Type_Bank', ''),
                    tx.get('Bank_Tracking_ID', '')
                ]
                table_data.append(row)
            
            # ایجاد جدول
            table = Table(table_data, repeatRows=1)
            table.setStyle(self.table_style)
            
            elements.append(table)
            
            # ساخت PDF
            doc.build(elements)
            
            logger.info(f"گزارش تراکنش‌های بانکی مغایرت‌گیری نشده با موفقیت در {file_path} ذخیره شد.")
            return file_path
            
        except Exception as e:
            logger.error(f"خطا در تولید گزارش تراکنش‌های بانکی مغایرت‌گیری نشده: {str(e)}")
            return ""
    
    def generate_unmatched_accounting_report(self) -> str:
        """
        تولید گزارش ورودی‌های حسابداری مغایرت‌گیری نشده
        
        خروجی:
            مسیر فایل PDF تولید شده
        """
        try:
            # دریافت داده‌ها
            unmatched_accounting_entries = self.db_manager.get_unreconciled_accounting_entries()
            
            if not unmatched_accounting_entries:
                logger.warning("هیچ ورودی حسابداری مغایرت‌گیری نشده‌ای یافت نشد.")
                return ""
            
            # ایجاد نام فایل
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            file_name = f"unmatched_accounting_{timestamp}.pdf"
            file_path = os.path.join(REPORTS_DIR, file_name)
            
            # ایجاد داکیومنت PDF
            doc = SimpleDocTemplate(
                file_path,
                pagesize=A4,
                rightMargin=30,
                leftMargin=30,
                topMargin=30,
                bottomMargin=30
            )
            
            # لیست عناصر
            elements = []
            
            # عنوان گزارش
            title = Paragraph("گزارش ورودی‌های حسابداری مغایرت‌گیری نشده", self.title_style)
            elements.append(title)
            elements.append(Spacer(1, 20))
            
            # تاریخ گزارش
            report_date = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            jalali_date = convert_gregorian_to_jalali_str(report_date, '%Y-%m-%d %H:%M:%S', '%Y/%m/%d %H:%M:%S')
            date_text = Paragraph(f"تاریخ گزارش: {jalali_date}", self.normal_style)
            elements.append(date_text)
            elements.append(Spacer(1, 20))
            
            # آمار
            stats = self.db_manager.get_reconciliation_statistics()
            stats_text = Paragraph(
                f"تعداد کل ورودی‌های حسابداری: {stats.get('total_accounting', 0)}<br/>"
                f"تعداد ورودی‌های مغایرت‌گیری شده: {stats.get('reconciled_accounting', 0)}<br/>"
                f"تعداد ورودی‌های مغایرت‌گیری نشده: {stats.get('unreconciled_accounting', 0)}",
                self.normal_style
            )
            elements.append(stats_text)
            elements.append(Spacer(1, 20))
            
            # داده‌های جدول
            table_data = [
                ["ردیف", "نوع", "شماره", "بدهکار", "بستانکار", "تاریخ سررسید", "توضیحات"]
            ]
            
            for i, entry in enumerate(unmatched_accounting_entries, 1):
                debit = format_currency(entry.get('Debit', 0)) if entry.get('Debit') else ""
                credit = format_currency(entry.get('Credit', 0)) if entry.get('Credit') else ""
                
                row = [
                    str(i),
                    entry.get('Entry_Type_Acc', ''),
                    entry.get('Account_Reference_Suffix', ''),
                    debit,
                    credit,
                    entry.get('Due_Date', ''),
                    entry.get('Description_Notes_Acc', '')[:50]  # محدود کردن طول توضیحات
                ]
                table_data.append(row)
            
            # ایجاد جدول
            table = Table(table_data, repeatRows=1)
            table.setStyle(self.table_style)
            
            elements.append(table)
            
            # ساخت PDF
            doc.build(elements)
            
            logger.info(f"گزارش ورودی‌های حسابداری مغایرت‌گیری نشده با موفقیت در {file_path} ذخیره شد.")
            return file_path
            
        except Exception as e:
            logger.error(f"خطا در تولید گزارش ورودی‌های حسابداری مغایرت‌گیری نشده: {str(e)}")
            return ""
    
    def generate_pos_not_in_accounting_report(self) -> str:
        """
        تولید گزارش تراکنش‌های پوز که در حسابداری نیستند
        
        خروجی:
            مسیر فایل PDF تولید شده
        """
        try:
            # دریافت داده‌ها
            unmatched_pos_transactions = self.db_manager.get_unreconciled_pos_transactions()
            
            if not unmatched_pos_transactions:
                logger.warning("هیچ تراکنش پوز مغایرت‌گیری نشده‌ای یافت نشد.")
                return ""
            
            # ایجاد نام فایل
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            file_name = f"pos_not_in_accounting_{timestamp}.pdf"
            file_path = os.path.join(REPORTS_DIR, file_name)
            
            # ایجاد داکیومنت PDF
            doc = SimpleDocTemplate(
                file_path,
                pagesize=A4,
                rightMargin=30,
                leftMargin=30,
                topMargin=30,
                bottomMargin=30
            )
            
            # لیست عناصر
            elements = []
            
            # عنوان گزارش
            title = Paragraph("گزارش تراکنش‌های پوز که در حسابداری نیستند", self.title_style)
            elements.append(title)
            elements.append(Spacer(1, 20))
            
            # تاریخ گزارش
            report_date = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            jalali_date = convert_gregorian_to_jalali_str(report_date, '%Y-%m-%d %H:%M:%S', '%Y/%m/%d %H:%M:%S')
            date_text = Paragraph(f"تاریخ گزارش: {jalali_date}", self.normal_style)
            elements.append(date_text)
            elements.append(Spacer(1, 20))
            
            # آمار
            stats = self.db_manager.get_reconciliation_statistics()
            stats_text = Paragraph(
                f"تعداد کل تراکنش‌های پوز: {stats.get('total_pos', 0)}<br/>"
                f"تعداد تراکنش‌های مغایرت‌گیری شده: {stats.get('reconciled_pos', 0)}<br/>"
                f"تعداد تراکنش‌های مغایرت‌گیری نشده: {stats.get('unreconciled_pos', 0)}",
                self.normal_style
            )
            elements.append(stats_text)
            elements.append(Spacer(1, 20))
            
            # داده‌های جدول
            table_data = [
                ["ردیف", "تاریخ", "ساعت", "مبلغ", "شماره کارت", "شناسه ترمینال", "شماره پیگیری"]
            ]
            
            for i, tx in enumerate(unmatched_pos_transactions, 1):
                amount = format_currency(tx.get('Transaction_Amount', 0)) if tx.get('Transaction_Amount') else ""
                
                row = [
                    str(i),
                    tx.get('Transaction_Date', ''),
                    tx.get('Transaction_Time', ''),
                    amount,
                    tx.get('Card_Number', '')[-4:] if tx.get('Card_Number') else "",  # فقط 4 رقم آخر
                    tx.get('Terminal_ID', ''),
                    tx.get('POS_Tracking_Number', '')
                ]
                table_data.append(row)
            
            # ایجاد جدول
            table = Table(table_data, repeatRows=1)
            table.setStyle(self.table_style)
            
            elements.append(table)
            
            # ساخت PDF
            doc.build(elements)
            
            logger.info(f"گزارش تراکنش‌های پوز که در حسابداری نیستند با موفقیت در {file_path} ذخیره شد.")
            return file_path
            
        except Exception as e:
            logger.error(f"خطا در تولید گزارش تراکنش‌های پوز که در حسابداری نیستند: {str(e)}")
            return ""
    
    def generate_accounting_pos_not_in_pos_report(self) -> str:
        """
        تولید گزارش ورودی‌های حسابداری پوز که در تراکنش‌های پوز نیستند
        
        خروجی:
            مسیر فایل PDF تولید شده
        """
        try:
            # دریافت داده‌ها
            unmatched_accounting_entries = self.db_manager.get_unreconciled_accounting_entries()
            
            # فیلتر کردن ورودی‌های مرتبط با پوز
            pos_accounting_entries = [e for e in unmatched_accounting_entries 
                                    if "پوز دریافتنی" in str(e.get('Entry_Type_Acc', '')) or 
                                    "پوز" in str(e.get('Description_Notes_Acc', ''))]
            
            if not pos_accounting_entries:
                logger.warning("هیچ ورودی حسابداری پوز مغایرت‌گیری نشده‌ای یافت نشد.")
                return ""
            
            # ایجاد نام فایل
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            file_name = f"accounting_pos_not_in_pos_{timestamp}.pdf"
            file_path = os.path.join(REPORTS_DIR, file_name)
            
            # ایجاد داکیومنت PDF
            doc = SimpleDocTemplate(
                file_path,
                pagesize=A4,
                rightMargin=30,
                leftMargin=30,
                topMargin=30,
                bottomMargin=30
            )
            
            # لیست عناصر
            elements = []
            
            # عنوان گزارش
            title = Paragraph("گزارش ورودی‌های حسابداری پوز که در تراکنش‌های پوز نیستند", self.title_style)
            elements.append(title)
            elements.append(Spacer(1, 20))
            
            # تاریخ گزارش
            report_date = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            jalali_date = convert_gregorian_to_jalali_str(report_date, '%Y-%m-%d %H:%M:%S', '%Y/%m/%d %H:%M:%S')
            date_text = Paragraph(f"تاریخ گزارش: {jalali_date}", self.normal_style)
            elements.append(date_text)
            elements.append(Spacer(1, 20))
            
            # آمار
            stats_text = Paragraph(
                f"تعداد ورودی‌های حسابداری پوز مغایرت‌گیری نشده: {len(pos_accounting_entries)}",
                self.normal_style
            )
            elements.append(stats_text)
            elements.append(Spacer(1, 20))
            
            # داده‌های جدول
            table_data = [
                ["ردیف", "نوع", "شماره", "مبلغ", "تاریخ سررسید", "پسوند کارت", "توضیحات"]
            ]
            
            for i, entry in enumerate(pos_accounting_entries, 1):
                amount = format_currency(entry.get('Debit', 0)) if entry.get('Debit') else format_currency(entry.get('Credit', 0))
                
                row = [
                    str(i),
                    entry.get('Entry_Type_Acc', ''),
                    entry.get('Account_Reference_Suffix', ''),
                    amount,
                    entry.get('Due_Date', ''),
                    entry.get('Extracted_Card_Suffix_Acc', ''),
                    entry.get('Description_Notes_Acc', '')[:50]  # محدود کردن طول توضیحات
                ]
                table_data.append(row)
            
            # ایجاد جدول
            table = Table(table_data, repeatRows=1)
            table.setStyle(self.table_style)
            
            elements.append(table)
            
            # ساخت PDF
            doc.build(elements)
            
            logger.info(f"گزارش ورودی‌های حسابداری پوز که در تراکنش‌های پوز نیستند با موفقیت در {file_path} ذخیره شد.")
            return file_path
            
        except Exception as e:
            logger.error(f"خطا در تولید گزارش ورودی‌های حسابداری پوز که در تراکنش‌های پوز نیستند: {str(e)}")
            return ""
    
    def generate_duplicate_accounting_entries_report(self) -> str:
        """
        تولید گزارش ورودی‌های حسابداری تکراری
        
        خروجی:
            مسیر فایل PDF تولید شده
        """
        try:
            # دریافت داده‌ها
            self.db_manager.connect()
            
            # جستجوی ورودی‌های تکراری بر اساس مبلغ و تاریخ
            self.db_manager.cursor.execute('''
                SELECT a1.id, a1.Entry_Type_Acc, a1.Account_Reference_Suffix, a1.Debit, a1.Credit, 
                       a1.Due_Date, a1.Description_Notes_Acc
                FROM AccountingEntries a1
                JOIN AccountingEntries a2 ON 
                    ((a1.Debit IS NOT NULL AND a1.Debit = a2.Debit) OR 
                     (a1.Credit IS NOT NULL AND a1.Credit = a2.Credit)) AND
                    a1.Due_Date = a2.Due_Date AND
                    a1.id <> a2.id
                GROUP BY a1.id
                ORDER BY a1.Due_Date, a1.Debit, a1.Credit
            ''')
            
            columns = [desc[0] for desc in self.db_manager.cursor.description]
            duplicate_entries = [dict(zip(columns, row)) for row in self.db_manager.cursor.fetchall()]
            
            self.db_manager.disconnect()
            
            if not duplicate_entries:
                logger.warning("هیچ ورودی حسابداری تکراری یافت نشد.")
                return ""
            
            # ایجاد نام فایل
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            file_name = f"duplicate_accounting_entries_{timestamp}.pdf"
            file_path = os.path.join(REPORTS_DIR, file_name)
            
            # ایجاد داکیومنت PDF
            doc = SimpleDocTemplate(
                file_path,
                pagesize=A4,
                rightMargin=30,
                leftMargin=30,
                topMargin=30,
                bottomMargin=30
            )
            
            # لیست عناصر
            elements = []
            
            # عنوان گزارش
            title = Paragraph("گزارش ورودی‌های حسابداری تکراری", self.title_style)
            elements.append(title)
            elements.append(Spacer(1, 20))
            
            # تاریخ گزارش
            report_date = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            jalali_date = convert_gregorian_to_jalali_str(report_date, '%Y-%m-%d %H:%M:%S', '%Y/%m/%d %H:%M:%S')
            date_text = Paragraph(f"تاریخ گزارش: {jalali_date}", self.normal_style)
            elements.append(date_text)
            elements.append(Spacer(1, 20))
            
            # آمار
            stats_text = Paragraph(
                f"تعداد ورودی‌های حسابداری تکراری: {len(duplicate_entries)}",
                self.normal_style
            )
            elements.append(stats_text)
            elements.append(Spacer(1, 20))
            
            # داده‌های جدول
            table_data = [
                ["ردیف", "شناسه", "نوع", "شماره", "بدهکار", "بستانکار", "تاریخ سررسید", "توضیحات"]
            ]
            
            for i, entry in enumerate(duplicate_entries, 1):
                debit = format_currency(entry.get('Debit', 0)) if entry.get('Debit') else ""
                credit = format_currency(entry.get('Credit', 0)) if entry.get('Credit') else ""
                
                row = [
                    str(i),
                    str(entry.get('id', '')),
                    entry.get('Entry_Type_Acc', ''),
                    entry.get('Account_Reference_Suffix', ''),
                    debit,
                    credit,
                    entry.get('Due_Date', ''),
                    entry.get('Description_Notes_Acc', '')[:50]  # محدود کردن طول توضیحات
                ]
                table_data.append(row)
            
            # ایجاد جدول
            table = Table(table_data, repeatRows=1)
            table.setStyle(self.table_style)
            
            elements.append(table)
            
            # ساخت PDF
            doc.build(elements)
            
            logger.info(f"گزارش ورودی‌های حسابداری تکراری با موفقیت در {file_path} ذخیره شد.")
            return file_path
            
        except Exception as e:
            logger.error(f"خطا در تولید گزارش ورودی‌های حسابداری تکراری: {str(e)}")
            return ""
    
    def generate_reconciliation_summary_report(self) -> str:
        """
        تولید گزارش خلاصه مغایرت‌گیری
        
        خروجی:
            مسیر فایل PDF تولید شده
        """
        try:
            # دریافت آمار
            stats = self.db_manager.get_reconciliation_statistics()
            
            # ایجاد نام فایل
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            file_name = f"reconciliation_summary_{timestamp}.pdf"
            file_path = os.path.join(REPORTS_DIR, file_name)
            
            # ایجاد داکیومنت PDF
            doc = SimpleDocTemplate(
                file_path,
                pagesize=A4,
                rightMargin=30,
                leftMargin=30,
                topMargin=30,
                bottomMargin=30
            )
            
            # لیست عناصر
            elements = []
            
            # عنوان گزارش
            title = Paragraph("گزارش خلاصه مغایرت‌گیری", self.title_style)
            elements.append(title)
            elements.append(Spacer(1, 20))
            
            # تاریخ گزارش
            report_date = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            jalali_date = convert_gregorian_to_jalali_str(report_date, '%Y-%m-%d %H:%M:%S', '%Y/%m/%d %H:%M:%S')
            date_text = Paragraph(f"تاریخ گزارش: {jalali_date}", self.normal_style)
            elements.append(date_text)
            elements.append(Spacer(1, 20))
            
            # آمار بانک
            bank_heading = Paragraph("آمار تراکنش‌های بانکی", self.heading_style)
            elements.append(bank_heading)
            elements.append(Spacer(1, 10))
            
            bank_stats = [
                ["عنوان", "تعداد", "درصد"],
                ["کل تراکنش‌ها", str(stats.get('total_bank', 0)), "100%"],
                ["مغایرت‌گیری شده", str(stats.get('reconciled_bank', 0)), 
                 f"{stats.get('reconciled_bank', 0) / stats.get('total_bank', 1) * 100:.1f}%" if stats.get('total_bank', 0) > 0 else "0%"],
                ["مغایرت‌گیری نشده", str(stats.get('unreconciled_bank', 0)), 
                 f"{stats.get('unreconciled_bank', 0) / stats.get('total_bank', 1) * 100:.1f}%" if stats.get('total_bank', 0) > 0 else "0%"]
            ]
            
            bank_table = Table(bank_stats, colWidths=[200, 100, 100])
            bank_table.setStyle(self.table_style)
            elements.append(bank_table)
            elements.append(Spacer(1, 20))
            
            # آمار پوز
            pos_heading = Paragraph("آمار تراکنش‌های پوز", self.heading_style)
            elements.append(pos_heading)
            elements.append(Spacer(1, 10))
            
            pos_stats = [
                ["عنوان", "تعداد", "درصد"],
                ["کل تراکنش‌ها", str(stats.get('total_pos', 0)), "100%"],
                ["مغایرت‌گیری شده", str(stats.get('reconciled_pos', 0)), 
                 f"{stats.get('reconciled_pos', 0) / stats.get('total_pos', 1) * 100:.1f}%" if stats.get('total_pos', 0) > 0 else "0%"],
                ["مغایرت‌گیری نشده", str(stats.get('unreconciled_pos', 0)), 
                 f"{stats.get('unreconciled_pos', 0) / stats.get('total_pos', 1) * 100:.1f}%" if stats.get('total_pos', 0) > 0 else "0%"]
            ]
            
            pos_table = Table(pos_stats, colWidths=[200, 100, 100])
            pos_table.setStyle(self.table_style)
            elements.append(pos_table)
            elements.append(Spacer(1, 20))
            
            # آمار حسابداری
            acc_heading = Paragraph("آمار ورودی‌های حسابداری", self.heading_style)
            elements.append(acc_heading)
            elements.append(Spacer(1, 10))
            
            acc_stats = [
                ["عنوان", "تعداد", "درصد"],
                ["کل ورودی‌ها", str(stats.get('total_accounting', 0)), "100%"],
                ["مغایرت‌گیری شده", str(stats.get('reconciled_accounting', 0)), 
                 f"{stats.get('reconciled_accounting', 0) / stats.get('total_accounting', 1) * 100:.1f}%" if stats.get('total_accounting', 0) > 0 else "0%"],
                ["مغایرت‌گیری نشده", str(stats.get('unreconciled_accounting', 0)), 
                 f"{stats.get('unreconciled_accounting', 0) / stats.get('total_accounting', 1) * 100:.1f}%" if stats.get('total_accounting', 0) > 0 else "0%"]
            ]
            
            acc_table = Table(acc_stats, colWidths=[200, 100, 100])
            acc_table.setStyle(self.table_style)
            elements.append(acc_table)
            
            # ساخت PDF
            doc.build(elements)
            
            logger.info(f"گزارش خلاصه مغایرت‌گیری با موفقیت در {file_path} ذخیره شد.")
            return file_path
            
        except Exception as e:
            logger.error(f"خطا در تولید گزارش خلاصه مغایرت‌گیری: {str(e)}")
            return ""