"""
Dashboard Operations Module
ماژول عملیات داشبورد - جدا شده از dashboard_tab.py
"""
import os
import logging
import sqlite3
import threading
import tempfile
import webbrowser
from datetime import datetime
from tkinter import messagebox
from config.settings import DB_PATH


class DashboardOperations:
    """کلاس عملیات داشبورد شامل حذف رکوردها و تولید گزارش"""
    
    def __init__(self, logger=None, status_callback=None):
        self.logger = logger or logging.getLogger(__name__)
        self.status_callback = status_callback  # callback برای به‌روزرسانی وضعیت
        self.statistics_refresh_callback = None  # callback برای به‌روزرسانی آمار
    
    def set_statistics_refresh_callback(self, callback):
        """تنظیم callback برای به‌روزرسانی آمار"""
        self.statistics_refresh_callback = callback
    
    def delete_all_records(self):
        """
        حذف کل رکوردها از تمامی جداول
        
        Returns:
            bool: موفقیت عملیات
        """
        try:
            # نمایش پیام تأیید
            confirm = messagebox.askyesno(
                "تأیید حذف", 
                "آیا از حذف کل رکوردها از تمامی جداول اطمینان دارید؟ این عمل غیرقابل بازگشت است!",
                icon='warning'
            )
            
            if not confirm:
                return False
            
            # اجرای در یک thread جداگانه برای جلوگیری از انسداد UI
            threading.Thread(target=self._delete_all_records_thread, daemon=True).start()
            return True
            
        except Exception as e:
            error_msg = f"خطا در شروع حذف کل رکوردها: {str(e)}"
            self.logger.error(error_msg)
            self._update_status(error_msg)
            messagebox.showerror("خطا", error_msg)
            return False
    
    def _delete_all_records_thread(self):
        """حذف کل رکوردها در thread جداگانه"""
        try:
            self.logger.info("در حال حذف کل رکوردها...")
            self._update_status("در حال حذف کل رکوردها...")
            
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            
            # حذف رکوردها از جداول با ترتیب صحیح (به دلیل foreign key constraints)
            tables_to_clear = [
                "ReconciliationResults",
                "BankTransactions", 
                "AccountingTransactions",
                "PosTransactions"
            ]
            
            total_deleted = 0
            for table in tables_to_clear:
                cursor.execute(f"SELECT COUNT(*) FROM {table}")
                count_before = cursor.fetchone()[0]
                
                cursor.execute(f"DELETE FROM {table}")
                
                cursor.execute(f"SELECT COUNT(*) FROM {table}")
                count_after = cursor.fetchone()[0]
                
                deleted_count = count_before - count_after
                total_deleted += deleted_count
                
                self.logger.info(f"حذف {deleted_count} رکورد از جدول {table}")
            
            # ریست کردن شمارنده‌های خودکار
            cursor.execute("""
                DELETE FROM sqlite_sequence 
                WHERE name IN ('ReconciliationResults', 'BankTransactions', 'AccountingTransactions', 'PosTransactions')
            """)
            
            conn.commit()
            conn.close()
            
            success_msg = f"تعداد {total_deleted} رکورد از کل رکوردها با موفقیت حذف شدند"
            self.logger.info(success_msg)
            self._update_status(success_msg)
            
            # به‌روزرسانی آمار
            if self.statistics_refresh_callback:
                self.statistics_refresh_callback()
            
            # نمایش پیام موفقیت
            messagebox.showinfo("موفقیت", success_msg)
            
        except Exception as e:
            error_msg = f"خطا در حذف کل رکوردها: {str(e)}"
            self.logger.error(error_msg)
            self._update_status(error_msg)
            messagebox.showerror("خطا", error_msg)
    
    def delete_reconciled_records(self):
        """
        حذف رکوردهای مغایرت‌گیری شده از تمامی جداول
        
        Returns:
            bool: موفقیت عملیات
        """
        try:
            # نمایش پیام تأیید
            confirm = messagebox.askyesno(
                "تأیید حذف", 
                "آیا از حذف رکوردهای مغایرت‌گیری شده از تمامی جداول اطمینان دارید؟ این عمل غیرقابل بازگشت است!",
                icon='warning'
            )
            
            if not confirm:
                return False
            
            # اجرای در thread جداگانه
            threading.Thread(target=self._delete_reconciled_records_thread, daemon=True).start()
            return True
            
        except Exception as e:
            error_msg = f"خطا در شروع حذف رکوردهای مغایرت‌گیری شده: {str(e)}"
            self.logger.error(error_msg)
            self._update_status(error_msg)
            messagebox.showerror("خطا", error_msg)
            return False
    
    def _delete_reconciled_records_thread(self):
        """حذف رکوردهای مغایرت‌گیری شده در thread جداگانه"""
        try:
            self.logger.info("در حال حذف رکوردهای مغایرت‌گیری شده...")
            self._update_status("در حال حذف رکوردهای مغایرت‌گیری شده...")
            
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            
            # دریافت شناسه‌های رکوردهای مغایرت‌گیری شده
            cursor.execute("SELECT id FROM BankTransactions WHERE is_reconciled = 1")
            bank_ids = [row[0] for row in cursor.fetchall()]
            
            cursor.execute("SELECT id FROM AccountingTransactions WHERE is_reconciled = 1")
            accounting_ids = [row[0] for row in cursor.fetchall()]
            
            cursor.execute("SELECT id FROM PosTransactions WHERE is_reconciled = 1")
            pos_ids = [row[0] for row in cursor.fetchall()]
            
            total_deleted = 0
            
            # حذف رکوردهای مرتبط از جدول نتایج مغایرت‌گیری
            if bank_ids:
                placeholders = ", ".join(["?" for _ in bank_ids])
                cursor.execute(f"DELETE FROM ReconciliationResults WHERE bank_record_id IN ({placeholders})", bank_ids)
                total_deleted += cursor.rowcount
            
            if accounting_ids:
                placeholders = ", ".join(["?" for _ in accounting_ids])
                cursor.execute(f"DELETE FROM ReconciliationResults WHERE acc_id IN ({placeholders})", accounting_ids)
                total_deleted += cursor.rowcount
            
            if pos_ids:
                placeholders = ", ".join(["?" for _ in pos_ids])
                cursor.execute(f"DELETE FROM ReconciliationResults WHERE pos_id IN ({placeholders})", pos_ids)
                total_deleted += cursor.rowcount
            
            # حذف رکوردهای مغایرت‌گیری شده از جداول اصلی
            cursor.execute("DELETE FROM BankTransactions WHERE is_reconciled = 1")
            bank_deleted = cursor.rowcount
            total_deleted += bank_deleted
            
            cursor.execute("DELETE FROM AccountingTransactions WHERE is_reconciled = 1")
            accounting_deleted = cursor.rowcount
            total_deleted += accounting_deleted
            
            cursor.execute("DELETE FROM PosTransactions WHERE is_reconciled = 1")
            pos_deleted = cursor.rowcount
            total_deleted += pos_deleted
            
            conn.commit()
            conn.close()
            
            success_msg = f"تعداد {total_deleted} رکورد مغایرت‌گیری شده حذف شد (بانک: {bank_deleted}, حسابداری: {accounting_deleted}, پوز: {pos_deleted})"
            self.logger.info(success_msg)
            self._update_status(success_msg)
            
            # به‌روزرسانی آمار
            if self.statistics_refresh_callback:
                self.statistics_refresh_callback()
            
            # نمایش پیام موفقیت
            messagebox.showinfo("موفقیت", success_msg)
            
        except Exception as e:
            error_msg = f"خطا در حذف رکوردهای مغایرت‌گیری شده: {str(e)}"
            self.logger.error(error_msg)
            self._update_status(error_msg)
            messagebox.showerror("خطا", error_msg)
    
    def generate_statistical_report(self, bank_stats, accounting_stats, pos_stats):
        """
        تولید گزارش آماری HTML
        
        Args:
            bank_stats: آمار بانک‌ها
            accounting_stats: آمار حسابداری  
            pos_stats: آمار پوز
            
        Returns:
            bool: موفقیت عملیات
        """
        try:
            self.logger.info("در حال تولید گزارش آماری...")
            self._update_status("در حال تولید گزارش آماری...")
            
            # ایجاد محتوای HTML
            html_content = self._create_html_report(bank_stats, accounting_stats, pos_stats)
            
            # ایجاد فایل موقت
            with tempfile.NamedTemporaryFile(
                delete=False, 
                suffix='.html', 
                mode='w', 
                encoding='utf-8'
            ) as f:
                f.write(html_content)
                temp_file_path = f.name
            
            # باز کردن فایل در مرورگر
            webbrowser.open('file://' + os.path.realpath(temp_file_path))
            
            success_msg = "گزارش آماری با موفقیت تولید و باز شد"
            self.logger.info(success_msg)
            self._update_status(success_msg)
            
            return True
            
        except Exception as e:
            error_msg = f"خطا در تولید گزارش آماری: {str(e)}"
            self.logger.error(error_msg)
            self._update_status(error_msg)
            messagebox.showerror("خطا", error_msg)
            return False
    
    def _create_html_report(self, bank_stats, accounting_stats, pos_stats):
        """ایجاد محتوای HTML گزارش"""
        try:
            # تاریخ گزارش
            report_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            # ایجاد ردیف‌های جدول بانک
            bank_rows = self._create_table_rows(bank_stats)
            
            # ایجاد ردیف‌های جدول حسابداری
            accounting_rows = self._create_table_rows(accounting_stats)
            
            # ایجاد ردیف‌های جدول پوز
            pos_rows = self._create_table_rows(pos_stats)
            
            # محاسبه آمار کلی
            total_stats = self._calculate_total_stats(bank_stats, accounting_stats, pos_stats)
            
            html_template = """<!DOCTYPE html>
<html dir="rtl">
<head>
    <meta charset="UTF-8">
    <title>گزارش آماری سیستم مغایرت‌گیری</title>
    <style>
        body { 
            font-family: 'Tahoma', 'Arial', sans-serif; 
            direction: rtl; 
            margin: 20px;
            line-height: 1.6;
        }
        .container {
            max-width: 1200px;
            margin: 0 auto;
        }
        table { 
            width: 100%; 
            border-collapse: collapse; 
            margin: 20px 0;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        th, td { 
            border: 1px solid #ddd; 
            padding: 12px; 
            text-align: center; 
        }
        th { 
            background-color: #f8f9fa; 
            font-weight: bold;
            color: #495057;
        }
        tr:nth-child(even) {
            background-color: #f8f9fa;
        }
        tr:hover {
            background-color: #e9ecef;
        }
        h1, h2, h3 { 
            text-align: center; 
            color: #343a40;
        }
        h1 {
            border-bottom: 3px solid #007bff;
            padding-bottom: 10px;
        }
        h2 {
            color: #007bff;
            border-right: 4px solid #007bff;
            padding-right: 10px;
        }
        .report-header { 
            margin-bottom: 30px; 
            text-align: center;
            background-color: #f8f9fa;
            padding: 20px;
            border-radius: 8px;
        }
        .report-footer { 
            margin-top: 30px; 
            text-align: center; 
            color: #6c757d;
            border-top: 1px solid #dee2e6;
            padding-top: 20px;
        }
        .section { 
            margin-bottom: 40px;
            background-color: #fff;
            padding: 20px;
            border-radius: 8px;
            border: 1px solid #dee2e6;
        }
        .summary-card {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 20px;
            border-radius: 8px;
            margin: 20px 0;
        }
        .summary-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
            margin-top: 15px;
        }
        .summary-item {
            background: rgba(255,255,255,0.1);
            padding: 10px;
            border-radius: 4px;
            text-align: center;
        }
        @media print {
            body { width: 21cm; height: 29.7cm; margin: 0; }
            .no-print { display: none; }
            button { display: none; }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="report-header">
            <h1>گزارش آماری سیستم مغایرت‌گیری</h1>
            <p><strong>تاریخ تولید گزارش:</strong> {report_date}</p>
        </div>
        
        <div class="summary-card">
            <h2>خلاصه آمار کلی</h2>
            <div class="summary-grid">
                <div class="summary-item">
                    <h3>کل رکوردها</h3>
                    <p>{total_records}</p>
                </div>
                <div class="summary-item">
                    <h3>مغایرت‌گیری شده</h3>
                    <p>{total_reconciled}</p>
                </div>
                <div class="summary-item">
                    <h3>مغایرت‌گیری نشده</h3>
                    <p>{total_unreconciled}</p>
                </div>
                <div class="summary-item">
                    <h3>درصد کلی</h3>
                    <p>{total_percentage:.1f}%</p>
                </div>
            </div>
        </div>
        
        <div class="section">
            <h2>📊 آمار بانک‌ها</h2>
            <table>
                <thead>
                    <tr>
                        <th>نام بانک</th>
                        <th>تعداد کل رکوردها</th>
                        <th>مغایرت‌گیری شده</th>
                        <th>مغایرت‌گیری نشده</th>
                        <th>درصد مغایرت‌گیری</th>
                    </tr>
                </thead>
                <tbody>
                    {bank_rows}
                </tbody>
            </table>
        </div>
        
        <div class="section">
            <h2>📋 آمار حسابداری</h2>
            <table>
                <thead>
                    <tr>
                        <th>نام بانک</th>
                        <th>تعداد کل رکوردها</th>
                        <th>مغایرت‌گیری شده</th>
                        <th>مغایرت‌گیری نشده</th>
                        <th>درصد مغایرت‌گیری</th>
                    </tr>
                </thead>
                <tbody>
                    {accounting_rows}
                </tbody>
            </table>
        </div>
        
        <div class="section">
            <h2>💳 آمار پوز</h2>
            <table>
                <thead>
                    <tr>
                        <th>نام بانک</th>
                        <th>تعداد کل رکوردها</th>
                        <th>مغایرت‌گیری شده</th>
                        <th>مغایرت‌گیری نشده</th>
                        <th>درصد مغایرت‌گیری</th>
                    </tr>
                </thead>
                <tbody>
                    {pos_rows}
                </tbody>
            </table>
        </div>
        
        <div class="report-footer">
            <p>🏢 <strong>سیستم مغایرت‌گیری</strong></p>
            <p>این گزارش به صورت خودکار تولید شده است</p>
        </div>
        
        <div class="no-print" style="text-align: center; margin-top: 30px;">
            <button onclick="window.print()" 
                    style="background: #007bff; color: white; border: none; padding: 12px 24px; 
                           border-radius: 4px; cursor: pointer; font-size: 16px;">
                📄 چاپ گزارش
            </button>
        </div>
    </div>
</body>
</html>"""
            
            return html_template.format(
                report_date=report_date,
                bank_rows=bank_rows,
                accounting_rows=accounting_rows,
                pos_rows=pos_rows,
                total_records=total_stats['total_records'],
                total_reconciled=total_stats['total_reconciled'],
                total_unreconciled=total_stats['total_unreconciled'],
                total_percentage=total_stats['total_percentage']
            )
            
        except Exception as e:
            self.logger.error(f"خطا در ایجاد محتوای HTML: {str(e)}")
            raise
    
    def _create_table_rows(self, stats_data):
        """ایجاد ردیف‌های جدول HTML"""
        rows = ""
        for stat in stats_data:
            rows += f"""<tr>
                <td><strong>{stat['bank_name']}</strong></td>
                <td>{stat['total_records']:,}</td>
                <td style="color: #28a745; font-weight: bold;">{stat['reconciled_records']:,}</td>
                <td style="color: #dc3545; font-weight: bold;">{stat['unreconciled_records']:,}</td>
                <td>
                    <div style="background: linear-gradient(90deg, #28a745 {stat['reconciled_percentage']:.0f}%, #e9ecef {stat['reconciled_percentage']:.0f}%); 
                                padding: 4px 8px; border-radius: 4px; color: #000;">
                        {stat['reconciled_percentage']:.1f}%
                    </div>
                </td>
            </tr>"""
        return rows
    
    def _calculate_total_stats(self, bank_stats, accounting_stats, pos_stats):
        """محاسبه آمار کلی"""
        try:
            total_bank = sum(stat['total_records'] for stat in bank_stats)
            total_accounting = sum(stat['total_records'] for stat in accounting_stats)
            total_pos = sum(stat['total_records'] for stat in pos_stats)
            
            reconciled_bank = sum(stat['reconciled_records'] for stat in bank_stats)
            reconciled_accounting = sum(stat['reconciled_records'] for stat in accounting_stats)
            reconciled_pos = sum(stat['reconciled_records'] for stat in pos_stats)
            
            total_records = total_bank + total_accounting + total_pos
            total_reconciled = reconciled_bank + reconciled_accounting + reconciled_pos
            total_unreconciled = total_records - total_reconciled
            
            total_percentage = 0
            if total_records > 0:
                total_percentage = (total_reconciled / total_records) * 100
            
            return {
                'total_records': total_records,
                'total_reconciled': total_reconciled,
                'total_unreconciled': total_unreconciled,
                'total_percentage': total_percentage
            }
            
        except Exception as e:
            self.logger.error(f"خطا در محاسبه آمار کلی: {str(e)}")
            return {
                'total_records': 0,
                'total_reconciled': 0,
                'total_unreconciled': 0,
                'total_percentage': 0
            }
    
    def _update_status(self, message):
        """به‌روزرسانی وضعیت از طریق callback"""
        if self.status_callback:
            self.status_callback(message)
    
    def get_database_info(self):
        """دریافت اطلاعات پایگاه داده"""
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            
            # اندازه فایل دیتابیس
            db_size = os.path.getsize(DB_PATH)
            db_size_mb = db_size / (1024 * 1024)
            
            # تعداد جداول
            cursor.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table'")
            table_count = cursor.fetchone()[0]
            
            # آخرین زمان به‌روزرسانی
            last_modified = datetime.fromtimestamp(os.path.getmtime(DB_PATH))
            
            conn.close()
            
            return {
                'file_path': DB_PATH,
                'size_bytes': db_size,
                'size_mb': db_size_mb,
                'table_count': table_count,
                'last_modified': last_modified
            }
            
        except Exception as e:
            self.logger.error(f"خطا در دریافت اطلاعات پایگاه داده: {str(e)}")
            return {}
