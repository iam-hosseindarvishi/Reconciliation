"""
HTML Print Module
جدا شده از report_tab.py برای ماژولار کردن کد
"""
import os
import tempfile
import webbrowser
import logging
from tkinter import messagebox
from datetime import datetime
import jdatetime


class HTMLPrinter:
    """کلاس چاپ گزارشات در قالب HTML"""
    
    def __init__(self, logger=None):
        self.logger = logger or logging.getLogger(__name__)
    
    def print_report(self, data, columns, selected_table, selected_bank, table_data):
        """چاپ گزارش در قالب HTML"""
        try:
            if not data:
                messagebox.showwarning("هشدار", "هیچ داده‌ای برای چاپ وجود ندارد")
                return False
            
            # ایجاد محتوای HTML
            html_content = self._create_html_content(
                selected_table, selected_bank, columns, table_data
            )
            
            # ایجاد فایل موقت
            temp_file_path = self._create_temp_file(html_content)
            
            # باز کردن فایل در مرورگر برای چاپ
            webbrowser.open('file://' + os.path.realpath(temp_file_path))
            
            self.logger.info("فایل چاپ با موفقیت ایجاد شد")
            return True
            
        except Exception as e:
            error_msg = f"خطا در چاپ گزارش: {str(e)}"
            self.logger.error(error_msg)
            messagebox.showerror("خطا", error_msg)
            return False
    
    def _create_html_content(self, selected_table, selected_bank, columns, table_data):
        """ایجاد محتوای HTML"""
        # مسیر فونت
        font_path = self._get_font_path()
        
        # ایجاد عنوان گزارش
        report_title = f"گزارش {selected_table}"
        if selected_bank != "همه موارد":
            report_title += f" - بانک {selected_bank}"
        
        # ایجاد تاریخ گزارش
        report_date = self._get_jalali_date()
        
        # ایجاد هدر جدول
        table_header = self._create_table_header(columns)
        
        # ایجاد ردیف‌های جدول
        table_rows = self._create_table_rows(table_data)
        
        # تکمیل محتوای HTML
        html_content = f"""<!DOCTYPE html>
<html dir="rtl">
<head>
    <meta charset="UTF-8">
    <title>گزارش</title>
    <style>
        @font-face {{
            font-family: 'Vazir';
            src: url('file:///{font_path}') format('truetype');
        }}
        body {{ 
            font-family: Vazir, Tahoma, Arial, sans-serif; 
            direction: rtl; 
            margin: 20px;
        }}
        table {{ 
            width: 100%; 
            border-collapse: collapse; 
            margin-top: 20px; 
            font-size: 14px;
        }}
        th, td {{ 
            border: 1px solid #ddd; 
            padding: 8px; 
            text-align: right; 
        }}
        th {{ 
            background-color: #f2f2f2; 
            font-weight: bold;
        }}
        h1, h2 {{ 
            text-align: center; 
            color: #333;
        }}
        .report-header {{ 
            margin-bottom: 20px; 
            border-bottom: 2px solid #ddd;
            padding-bottom: 10px;
        }}
        .report-footer {{ 
            margin-top: 20px; 
            text-align: center; 
            color: #666;
        }}
        @media print {{
            body {{ width: 21cm; height: 29.7cm; margin: 0; }}
            .no-print {{ display: none; }}
            button {{ display: none; }}
        }}
    </style>
</head>
<body>
    <div class="report-header">
        <h1>گزارش سیستم مغایرت‌گیری</h1>
        <h2>{report_title}</h2>
        <p>تاریخ گزارش: {report_date}</p>
    </div>
    
    <table>
        <thead>
            <tr>
                {table_header}
            </tr>
        </thead>
        <tbody>
            {table_rows}
        </tbody>
    </table>
    
    <div class="report-footer">
        <p>تعداد رکوردها: {len(table_data)}</p>
        <p>سیستم مغایرت‌گیری - تولید شده در {report_date}</p>
    </div>
    
    <div class="no-print" style="text-align: center; margin-top: 20px;">
        <button onclick="window.print()" style="padding: 10px 20px; font-size: 16px; background: #007bff; color: white; border: none; border-radius: 5px; cursor: pointer;">چاپ</button>
    </div>
</body>
</html>
"""
        return html_content
    
    def _get_font_path(self):
        """دریافت مسیر فونت"""
        try:
            font_path = os.path.join(
                os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
                "assets", "fonts", "Vazir.ttf"
            )
            return font_path.replace('\\\\', '/')
        except:
            return ""
    
    def _get_jalali_date(self):
        """دریافت تاریخ جلالی فعلی"""
        try:
            gregorian_date = datetime.now()
            jalali_date = jdatetime.datetime.fromgregorian(datetime=gregorian_date)
            return jalali_date.strftime("%Y/%m/%d %H:%M:%S")
        except Exception as e:
            self.logger.warning(f"خطا در تبدیل تاریخ جلالی: {str(e)}")
            return datetime.now().strftime("%Y/%m/%d %H:%M:%S")
    
    def _create_table_header(self, columns):
        """ایجاد هدر جدول HTML"""
        table_header = ""
        for col in columns:
            table_header += f"<th>{col['text']}</th>\\n"
        return table_header
    
    def _create_table_rows(self, table_data):
        """ایجاد ردیف‌های جدول HTML"""
        table_rows = ""
        
        for row in table_data:
            table_rows += "<tr>\\n"
            for cell_value in row:
                # تبدیل مقادیر None به رشته خالی
                display_value = str(cell_value) if cell_value is not None else ""
                # Escape کردن کاراکترهای HTML
                display_value = self._escape_html(display_value)
                table_rows += f"<td>{display_value}</td>\\n"
            table_rows += "</tr>\\n"
        
        return table_rows
    
    def _escape_html(self, text):
        """Escape کردن کاراکترهای HTML"""
        if not isinstance(text, str):
            text = str(text)
        
        # جایگزین کردن کاراکترهای HTML خطرناک
        replacements = {
            '&': '&amp;',
            '<': '&lt;',
            '>': '&gt;',
            '"': '&quot;',
            "'": '&#39;'
        }
        
        for char, replacement in replacements.items():
            text = text.replace(char, replacement)
        
        return text
    
    def _create_temp_file(self, html_content):
        """ایجاد فایل موقت HTML"""
        with tempfile.NamedTemporaryFile(
            delete=False, 
            suffix='.html', 
            mode='w', 
            encoding='utf-8'
        ) as f:
            f.write(html_content)
            return f.name
