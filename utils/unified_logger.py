"""
سیستم Logging یکپارچه برای پروژه Reconciliation
تمام log‌ها در یک فایل واحد ذخیره می‌شوند با سطوح مختلف logging
"""

import os
import logging
import threading
from datetime import datetime
from pathlib import Path
from typing import Optional
from config.settings import DATA_DIR

class UnifiedLogger:
    """کلاس Logger یکپارچه برای کل سیستم"""
    
    _instance: Optional['UnifiedLogger'] = None
    _lock = threading.Lock()
    _initialized = False
    
    def __new__(cls):
        """Singleton pattern برای تضمین یک instance واحد"""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super(UnifiedLogger, cls).__new__(cls)
        return cls._instance
    
    def __init__(self):
        """تنظیمات اولیه logger"""
        if self._initialized:
            return
            
        with self._lock:
            if self._initialized:
                return
                
            self._setup_logger()
            self._initialized = True
    
    def _setup_logger(self):
        """تنظیم logger اصلی"""
        # ایجاد logger اصلی
        self.logger = logging.getLogger('ReconciliationSystem')
        
        # پاک کردن handler های قبلی در صورت وجود
        if self.logger.handlers:
            for handler in self.logger.handlers.copy():
                self.logger.removeHandler(handler)
        
        self.logger.setLevel(logging.DEBUG)
        
        # اطمینان از وجود دایرکتوری data
        os.makedirs(DATA_DIR, exist_ok=True)
        
        # مسیر فایل log واحد
        self.log_file_path = os.path.join(DATA_DIR, 'reconciliation_unified.log')
        
        # فرمت واحد برای تمام log‌ها
        formatter = logging.Formatter(
            '%(asctime)s | %(levelname)-8s | %(module)s.%(funcName)s:%(lineno)d | %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        # File Handler برای ذخیره در فایل
        try:
            file_handler = logging.FileHandler(
                self.log_file_path, 
                mode='a', 
                encoding='utf-8'
            )
            file_handler.setLevel(logging.DEBUG)
            file_handler.setFormatter(formatter)
            self.logger.addHandler(file_handler)
        except Exception as e:
            print(f"خطا در ایجاد file handler: {e}")
        
        # Console Handler برای نمایش در کنسول (فقط WARNING و بالاتر)
        try:
            console_handler = logging.StreamHandler()
            console_handler.setLevel(logging.WARNING)
            console_handler.setFormatter(formatter)
            self.logger.addHandler(console_handler)
        except Exception as e:
            print(f"خطا در ایجاد console handler: {e}")
        
        # نوشتن header اولیه
        self._write_session_header()
    
    def _write_session_header(self):
        """نوشتن header شروع session جدید"""
        separator = "=" * 80
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        header_message = f"""
{separator}
             جلسه جدید سیستم Reconciliation شروع شد
                      زمان: {timestamp}
{separator}
"""
        self.logger.info(header_message)
    
    def debug(self, message: str, module: str = None):
        """ثبت پیام DEBUG"""
        formatted_message = self._format_message(message, module)
        self.logger.debug(formatted_message)
    
    def info(self, message: str, module: str = None):
        """ثبت پیام INFO"""
        formatted_message = self._format_message(message, module)
        self.logger.info(formatted_message)
    
    def warning(self, message: str, module: str = None):
        """ثبت پیام WARNING"""
        formatted_message = self._format_message(message, module)
        self.logger.warning(formatted_message)
    
    def error(self, message: str, module: str = None, exc_info: bool = False):
        """ثبت پیام ERROR"""
        formatted_message = self._format_message(message, module)
        self.logger.error(formatted_message, exc_info=exc_info)
    
    def critical(self, message: str, module: str = None):
        """ثبت پیام CRITICAL"""
        formatted_message = self._format_message(message, module)
        self.logger.critical(formatted_message)
    
    def _format_message(self, message: str, module: str = None) -> str:
        """فرمت کردن پیام با اطلاعات اضافی"""
        if module:
            return f"[{module}] {message}"
        return message
    
    def log_operation_start(self, operation_name: str, details: str = None):
        """ثبت شروع یک عملیات"""
        message = f"🔵 شروع عملیات: {operation_name}"
        if details:
            message += f" | جزئیات: {details}"
        self.info(message)
    
    def log_operation_end(self, operation_name: str, success: bool = True, details: str = None):
        """ثبت پایان یک عملیات"""
        status = "✅ موفق" if success else "❌ ناموفق"
        message = f"{status} | پایان عملیات: {operation_name}"
        if details:
            message += f" | جزئیات: {details}"
        
        if success:
            self.info(message)
        else:
            self.error(message)
    
    def log_reconciliation_summary(self, bank_name: str, reconciliation_type: str, 
                                 total_records: int, matched_records: int, 
                                 unmatched_records: int):
        """ثبت خلاصه نتایج reconciliation"""
        summary = f"""
📊 خلاصه Reconciliation {bank_name} - {reconciliation_type}:
   • کل رکوردها: {total_records:,}
   • تطبیق یافته: {matched_records:,}
   • تطبیق نیافته: {unmatched_records:,}
   • درصد موفقیت: {(matched_records/total_records*100) if total_records > 0 else 0:.1f}%
"""
        self.info(summary)
    
    def log_database_operation(self, operation: str, table: str, affected_rows: int = None):
        """ثبت عملیات پایگاه داده"""
        message = f"💾 عملیات DB: {operation} | جدول: {table}"
        if affected_rows is not None:
            message += f" | تعداد سطرها: {affected_rows:,}"
        self.debug(message)
    
    def log_file_operation(self, operation: str, file_path: str, records_count: int = None):
        """ثبت عملیات فایل"""
        file_name = Path(file_path).name
        message = f"📁 عملیات فایل: {operation} | فایل: {file_name}"
        if records_count is not None:
            message += f" | تعداد رکورد: {records_count:,}"
        self.debug(message)
    
    def log_performance(self, operation: str, duration_seconds: float, records_processed: int = None):
        """ثبت اطلاعات عملکرد"""
        message = f"⏱️ عملکرد: {operation} | مدت زمان: {duration_seconds:.2f}s"
        if records_processed:
            rate = records_processed / duration_seconds if duration_seconds > 0 else 0
            message += f" | تعداد رکورد: {records_processed:,} | نرخ: {rate:.1f} رکورد/ثانیه"
        self.info(message)
    
    def log_user_action(self, action: str, details: str = None):
        """ثبت اقدامات کاربر"""
        message = f"👤 اقدام کاربر: {action}"
        if details:
            message += f" | جزئیات: {details}"
        self.info(message)
    
    def get_log_file_path(self) -> str:
        """دریافت مسیر فایل log"""
        return self.log_file_path
    
    def clear_old_logs(self, days_to_keep: int = 30):
        """پاک کردن log های قدیمی"""
        try:
            log_file = Path(self.log_file_path)
            if log_file.exists():
                file_age_days = (datetime.now() - datetime.fromtimestamp(log_file.stat().st_mtime)).days
                if file_age_days > days_to_keep:
                    # Backup کردن log قدیمی
                    backup_name = f"reconciliation_unified_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
                    backup_path = log_file.parent / backup_name
                    log_file.rename(backup_path)
                    self.info(f"Log قدیمی به {backup_name} منتقل شد")
        except Exception as e:
            self.error(f"خطا در پاک کردن log های قدیمی: {e}")


# Instance واحد برای استفاده در کل پروژه
logger = UnifiedLogger()

# Helper functions برای دسترسی آسان
def log_debug(message: str, module: str = None):
    """Log DEBUG message"""
    logger.debug(message, module)

def log_info(message: str, module: str = None):
    """Log INFO message"""
    logger.info(message, module)

def log_warning(message: str, module: str = None):
    """Log WARNING message"""
    logger.warning(message, module)

def log_error(message: str, module: str = None, exc_info: bool = False):
    """Log ERROR message"""
    logger.error(message, module, exc_info)

def log_critical(message: str, module: str = None):
    """Log CRITICAL message"""
    logger.critical(message, module)

def log_operation_start(operation_name: str, details: str = None):
    """Log operation start"""
    logger.log_operation_start(operation_name, details)

def log_operation_end(operation_name: str, success: bool = True, details: str = None):
    """Log operation end"""
    logger.log_operation_end(operation_name, success, details)

def log_reconciliation_summary(bank_name: str, reconciliation_type: str, 
                             total_records: int, matched_records: int, unmatched_records: int):
    """Log reconciliation summary"""
    logger.log_reconciliation_summary(bank_name, reconciliation_type, 
                                    total_records, matched_records, unmatched_records)

def log_database_operation(operation: str, table: str, affected_rows: int = None):
    """Log database operation"""
    logger.log_database_operation(operation, table, affected_rows)

def log_file_operation(operation: str, file_path: str, records_count: int = None):
    """Log file operation"""
    logger.log_file_operation(operation, file_path, records_count)

def log_performance(operation: str, duration_seconds: float, records_processed: int = None):
    """Log performance metrics"""
    logger.log_performance(operation, duration_seconds, records_processed)

def log_user_action(action: str, details: str = None):
    """Log user action"""
    logger.log_user_action(action, details)