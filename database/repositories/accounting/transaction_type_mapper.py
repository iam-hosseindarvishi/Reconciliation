"""
Transaction Type Mapping Utility
ماژول نگاشت انواع تراکنش - جدا شده از accounting_repository.py
"""
from utils.logger_config import setup_logger

# راه‌اندازی لاگر
logger = setup_logger('database.accounting_repository.transaction_type_mapper')


class TransactionTypeMapper:
    """کلاس برای نگاشت انواع تراکنش‌ها بین سیستم قدیم و جدید"""
    
    # نگاشت انواع تراکنش‌ها برای سازگاری با سیستم جدید
    TYPE_MAPPING = {
        'Pos': 'Pos / Received Transfer',
        'Received Transfer': 'Pos / Received Transfer',
        'Received_Transfer': 'Pos / Received Transfer',  # پشتیبانی از underscore
        'Paid Transfer': 'Pos / Paid Transfer',
        'Paid_Transfer': 'Pos / Paid Transfer',  # پشتیبانی از underscore
        'Received_Check': '',  # چک‌ها نگاشت جداگانه‌ای ندارند
        'Paid_Check': '',
        'Bank_Fees': ''
    }
    
    @classmethod
    def get_new_system_type(cls, transaction_type):
        """
        دریافت نوع تراکنش در سیستم جدید
        
        Args:
            transaction_type: نوع تراکنش در سیستم قدیم
            
        Returns:
            str: نوع تراکنش در سیستم جدید یا رشته خالی
        """
        new_type = cls.TYPE_MAPPING.get(transaction_type, '')
        if new_type:
            logger.debug(f"نوع تراکنش '{transaction_type}' به '{new_type}' نگاشت شد")
        return new_type
    
    @classmethod
    def get_both_types(cls, transaction_type):
        """
        دریافت هر دو نوع تراکنش (قدیم و جدید) برای جستجو
        
        Args:
            transaction_type: نوع تراکنش اصلی
            
        Returns:
            tuple: (نوع اصلی, نوع جدید)
        """
        new_type = cls.get_new_system_type(transaction_type)
        return transaction_type, new_type
    
    @classmethod
    def create_type_condition_sql(cls, transaction_type, param_placeholder="?"):
        """
        ایجاد شرط SQL برای جستجوی بر اساس نوع تراکنش
        
        پشتیبانی از هر دو فرمت space و underscore
        
        Args:
            transaction_type: نوع تراکنش
            param_placeholder: placeholder برای پارامتر SQL (معمولاً "?")
            
        Returns:
            tuple: (شرط SQL, لیست پارامترها)
        """
        # دریافت نوع جدید اگر وجود دارد
        original_type, new_type = cls.get_both_types(transaction_type)
        
        # ساخت لیست تمام حالات ممکن
        possible_types = [original_type]
        
        # اضافه کردن نوع جدید اگر وجود دارد
        if new_type:
            possible_types.append(new_type)
        
        # اضافه کردن فرمت‌های مختلف فقط اگر نوع اصلی فاقد فاصله باشد
        # و فقط برای مواردی که نیاز به تبدیل بین underscore و space دارند
        if ' ' not in transaction_type and '_' in transaction_type:
            # اگر نوع ورودی دارای underscore است، فضای خالی را هم اضافه کن
            type_with_space = transaction_type.replace('_', ' ')
            if type_with_space != original_type:
                possible_types.append(type_with_space)
        elif ' ' in transaction_type and '/' not in transaction_type:
            # اگر نوع ورودی دارای فضای خالی است (اما نه '/')، underscore را هم اضافه کن
            type_with_underscore = transaction_type.replace(' ', '_')
            if type_with_underscore != original_type:
                possible_types.append(type_with_underscore)
        
        # حذف تکراری‌ها و خالی‌ها
        possible_types = list(set([t for t in possible_types if t]))
        
        if len(possible_types) == 1:
            sql_condition = f"transaction_type = {param_placeholder}"
            params = possible_types
        else:
            placeholders = ' OR '.join([f"transaction_type = {param_placeholder}" for _ in possible_types])
            sql_condition = f"({placeholders})"
            params = possible_types
        
        logger.debug(f"شرط SQL ایجاد شد: {sql_condition} با پارامترها: {params}")
        return sql_condition, params
    
    @classmethod
    def is_pos_related_type(cls, transaction_type):
        """
        بررسی اینکه آیا نوع تراکنش مربوط به پوز است یا نه
        
        Args:
            transaction_type: نوع تراکنش
            
        Returns:
            bool: True اگر مربوط به پوز باشد
        """
        pos_related_types = ['Pos', 'Received Transfer', 'Pos / Received Transfer']
        is_pos = transaction_type in pos_related_types
        logger.debug(f"نوع تراکنش '{transaction_type}' {'مربوط به پوز است' if is_pos else 'مربوط به پوز نیست'}")
        return is_pos
    
    @classmethod
    def is_transfer_related_type(cls, transaction_type):
        """
        بررسی اینکه آیا نوع تراکنش مربوط به انتقال است یا نه
        
        Args:
            transaction_type: نوع تراکنش
            
        Returns:
            bool: True اگر مربوط به انتقال باشد
        """
        transfer_related_types = [
            'Received Transfer', 'Paid Transfer',
            'Pos / Received Transfer', 'Pos / Paid Transfer'
        ]
        is_transfer = transaction_type in transfer_related_types
        logger.debug(f"نوع تراکنش '{transaction_type}' {'مربوط به انتقال است' if is_transfer else 'مربوط به انتقال نیست'}")
        return is_transfer
    
    @classmethod
    def get_all_supported_types(cls):
        """
        دریافت تمام انواع تراکنش‌های پشتیبانی شده
        
        Returns:
            list: لیست تمام انواع تراکنش‌ها
        """
        all_types = list(cls.TYPE_MAPPING.keys()) + list(cls.TYPE_MAPPING.values())
        # حذف تکراری‌ها
        unique_types = list(set(all_types))
        logger.debug(f"انواع تراکنش‌های پشتیبانی شده: {unique_types}")
        return unique_types
    
    @classmethod
    def normalize_transaction_type(cls, transaction_type):
        """
        نرمال‌سازی نوع تراکنش
        
        Args:
            transaction_type: نوع تراکنش ورودی
            
        Returns:
            str: نوع تراکنش نرمال شده
        """
        if not transaction_type:
            return transaction_type
        
        # حذف فاصله‌های اضافی
        normalized = transaction_type.strip()
        
        # بررسی معادل بودن با انواع موجود
        for original, mapped in cls.TYPE_MAPPING.items():
            if normalized.lower() == original.lower() or normalized.lower() == mapped.lower():
                logger.debug(f"نوع تراکنش '{transaction_type}' به '{original}' نرمال شد")
                return original
        
        logger.debug(f"نوع تراکنش '{transaction_type}' نرمال نشد")
        return normalized
