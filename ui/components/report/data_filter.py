"""
Data Filter Module
جدا شده از report_tab.py برای ماژولار کردن کد
"""
import logging
from datetime import datetime
import jdatetime
from tkinter import messagebox
import re


class DataFilter:
    """کلاس فیلتر و جستجوی داده‌ها"""
    
    def __init__(self, logger=None):
        self.logger = logger or logging.getLogger(__name__)
    
    def filter_data(self, data, filters):
        """
        فیلتر کردن داده‌ها بر اساس فیلترهای ارسالی
        
        Args:
            data: لیست داده‌ها
            filters: دیکشنری شامل فیلترهای مختلف
        
        Returns:
            list: داده‌های فیلتر شده
        """
        try:
            if not data:
                return []
            
            filtered_data = data.copy()
            
            # فیلتر بانک
            if filters.get('bank') and filters['bank'] != 'همه موارد':
                filtered_data = self._filter_by_bank(filtered_data, filters['bank'])
            
            # فیلتر تاریخ
            if filters.get('date_from') or filters.get('date_to'):
                filtered_data = self._filter_by_date_range(
                    filtered_data, 
                    filters.get('date_from'), 
                    filters.get('date_to')
                )
            
            # فیلتر مبلغ
            if filters.get('amount_from') is not None or filters.get('amount_to') is not None:
                filtered_data = self._filter_by_amount_range(
                    filtered_data, 
                    filters.get('amount_from'), 
                    filters.get('amount_to')
                )
            
            # فیلتر نوع تراکنش
            if filters.get('transaction_type'):
                filtered_data = self._filter_by_transaction_type(
                    filtered_data, 
                    filters['transaction_type']
                )
            
            # فیلتر وضعیت
            if filters.get('status'):
                filtered_data = self._filter_by_status(filtered_data, filters['status'])
            
            # فیلتر متنی
            if filters.get('search_text'):
                filtered_data = self._filter_by_text_search(
                    filtered_data, 
                    filters['search_text']
                )
            
            self.logger.info(f"تعداد {len(filtered_data)} رکورد پس از فیلتر باقی ماند")
            return filtered_data
            
        except Exception as e:
            self.logger.error(f"خطا در فیلتر کردن داده‌ها: {str(e)}")
            return data
    
    def _filter_by_bank(self, data, bank_name):
        """فیلتر بر اساس نام بانک"""
        return [item for item in data if item.get('bank_name', '') == bank_name]
    
    def _filter_by_date_range(self, data, date_from, date_to):
        """فیلتر بر اساس بازه تاریخ"""
        filtered_data = []
        
        for item in data:
            transaction_date = item.get('transaction_date', '')
            if not transaction_date:
                continue
            
            try:
                # تبدیل تاریخ تراکنش
                item_date = self._parse_date(transaction_date)
                if not item_date:
                    continue
                
                # بررسی تاریخ شروع
                if date_from:
                    start_date = self._parse_date(date_from)
                    if start_date and item_date < start_date:
                        continue
                
                # بررسی تاریخ پایان
                if date_to:
                    end_date = self._parse_date(date_to)
                    if end_date and item_date > end_date:
                        continue
                
                filtered_data.append(item)
                
            except Exception as e:
                self.logger.debug(f"خطا در پردازش تاریخ {transaction_date}: {str(e)}")
                continue
        
        return filtered_data
    
    def _filter_by_amount_range(self, data, amount_from, amount_to):
        """فیلتر بر اساس بازه مبلغ"""
        filtered_data = []
        
        for item in data:
            try:
                amount = float(item.get('amount', 0))
                
                # بررسی حد پایین
                if amount_from is not None and amount < amount_from:
                    continue
                
                # بررسی حد بالا
                if amount_to is not None and amount > amount_to:
                    continue
                
                filtered_data.append(item)
                
            except (ValueError, TypeError):
                continue
        
        return filtered_data
    
    def _filter_by_transaction_type(self, data, transaction_type):
        """فیلتر بر اساس نوع تراکنش"""
        if transaction_type == 'همه موارد':
            return data
        
        return [item for item in data 
                if item.get('transaction_type', '') == transaction_type]
    
    def _filter_by_status(self, data, status):
        """فیلتر بر اساس وضعیت"""
        if status == 'همه موارد':
            return data
        
        return [item for item in data if item.get('status', '') == status]
    
    def _filter_by_text_search(self, data, search_text):
        """فیلتر بر اساس جستجوی متنی"""
        if not search_text.strip():
            return data
        
        search_text = search_text.strip().lower()
        filtered_data = []
        
        # فیلدهایی که در آن‌ها جستجو می‌شود
        search_fields = [
            'transaction_id', 'description', 'reference_number', 
            'account_number', 'bank_name', 'transaction_type'
        ]
        
        for item in data:
            found = False
            
            for field in search_fields:
                field_value = str(item.get(field, '')).lower()
                if search_text in field_value:
                    found = True
                    break
            
            if found:
                filtered_data.append(item)
        
        return filtered_data
    
    def search_advanced(self, data, search_criteria):
        """
        جستجوی پیشرفته با معیارهای متعدد
        
        Args:
            data: لیست داده‌ها
            search_criteria: دیکشنری شامل معیارهای جستجو
        """
        try:
            if not data or not search_criteria:
                return data
            
            results = data.copy()
            
            # جستجو بر اساس ID
            if search_criteria.get('transaction_id'):
                results = self._search_by_id(results, search_criteria['transaction_id'])
            
            # جستجو بر اساس الگو
            if search_criteria.get('pattern'):
                results = self._search_by_pattern(results, search_criteria['pattern'])
            
            # جستجو بر اساس مبلغ دقیق
            if search_criteria.get('exact_amount'):
                results = self._search_by_exact_amount(results, search_criteria['exact_amount'])
            
            # جستجو بر اساس تاریخ دقیق
            if search_criteria.get('exact_date'):
                results = self._search_by_exact_date(results, search_criteria['exact_date'])
            
            # جستجو با regex
            if search_criteria.get('regex_pattern'):
                results = self._search_by_regex(results, search_criteria['regex_pattern'])
            
            return results
            
        except Exception as e:
            self.logger.error(f"خطا در جستجوی پیشرفته: {str(e)}")
            return data
    
    def _search_by_id(self, data, transaction_id):
        """جستجو بر اساس شناسه تراکنش"""
        return [item for item in data 
                if str(item.get('transaction_id', '')).lower() == str(transaction_id).lower()]
    
    def _search_by_pattern(self, data, pattern):
        """جستجو بر اساس الگوی متنی"""
        pattern = pattern.lower()
        results = []
        
        for item in data:
            # جستجو در تمام فیلدهای متنی
            for key, value in item.items():
                if isinstance(value, str) and pattern in value.lower():
                    results.append(item)
                    break
        
        return results
    
    def _search_by_exact_amount(self, data, amount):
        """جستجو بر اساس مبلغ دقیق"""
        try:
            target_amount = float(amount)
            return [item for item in data 
                    if abs(float(item.get('amount', 0)) - target_amount) < 0.01]
        except ValueError:
            return []
    
    def _search_by_exact_date(self, data, date_str):
        """جستجو بر اساس تاریخ دقیق"""
        target_date = self._parse_date(date_str)
        if not target_date:
            return []
        
        results = []
        for item in data:
            item_date = self._parse_date(item.get('transaction_date', ''))
            if item_date and item_date.date() == target_date.date():
                results.append(item)
        
        return results
    
    def _search_by_regex(self, data, pattern):
        """جستجو با استفاده از Regular Expression"""
        try:
            regex = re.compile(pattern, re.IGNORECASE)
            results = []
            
            for item in data:
                found = False
                for key, value in item.items():
                    if isinstance(value, str) and regex.search(value):
                        results.append(item)
                        found = True
                        break
                
            return results
            
        except re.error as e:
            self.logger.error(f"خطا در الگوی regex: {str(e)}")
            return []
    
    def _parse_date(self, date_str):
        """تبدیل رشته تاریخ به datetime object"""
        if not date_str:
            return None
        
        # فرمت‌های مختلف تاریخ
        formats = [
            '%Y/%m/%d %H:%M:%S',
            '%Y/%m/%d',
            '%Y-%m-%d %H:%M:%S',
            '%Y-%m-%d',
            '%d/%m/%Y',
            '%d-%m-%Y'
        ]
        
        # تلاش برای تبدیل تاریخ جلالی
        try:
            jalali_date = jdatetime.datetime.strptime(date_str, '%Y/%m/%d')
            return jalali_date.togregorian()
        except:
            pass
        
        # تلاش برای تبدیل تاریخ میلادی
        for fmt in formats:
            try:
                return datetime.strptime(date_str, fmt)
            except ValueError:
                continue
        
        return None
    
    def sort_data(self, data, sort_column, ascending=True):
        """مرتب‌سازی داده‌ها بر اساس ستون مشخص"""
        try:
            if not data or not sort_column:
                return data
            
            # تعیین کلید مرتب‌سازی
            def sort_key(item):
                value = item.get(sort_column, '')
                
                # مرتب‌سازی عددی
                if sort_column in ['amount', 'balance']:
                    try:
                        return float(value) if value else 0
                    except ValueError:
                        return 0
                
                # مرتب‌سازی تاریخ
                if 'date' in sort_column.lower():
                    parsed_date = self._parse_date(str(value))
                    return parsed_date if parsed_date else datetime.min
                
                # مرتب‌سازی متنی
                return str(value).lower()
            
            sorted_data = sorted(data, key=sort_key, reverse=not ascending)
            self.logger.info(f"داده‌ها بر اساس {sort_column} مرتب شدند")
            return sorted_data
            
        except Exception as e:
            self.logger.error(f"خطا در مرتب‌سازی: {str(e)}")
            return data
    
    def get_unique_values(self, data, column):
        """دریافت مقادیر یکتا از یک ستون"""
        try:
            if not data:
                return []
            
            unique_values = set()
            for item in data:
                value = item.get(column)
                if value is not None:
                    unique_values.add(str(value))
            
            return sorted(list(unique_values))
            
        except Exception as e:
            self.logger.error(f"خطا در دریافت مقادیر یکتا: {str(e)}")
            return []
    
    def get_data_statistics(self, data):
        """محاسبه آمار کلی داده‌ها"""
        try:
            if not data:
                return {}
            
            stats = {
                'total_records': len(data),
                'unique_banks': len(self.get_unique_values(data, 'bank_name')),
                'unique_transaction_types': len(self.get_unique_values(data, 'transaction_type'))
            }
            
            # آمار مبالغ
            amounts = []
            for item in data:
                try:
                    amount = float(item.get('amount', 0))
                    amounts.append(amount)
                except ValueError:
                    continue
            
            if amounts:
                stats.update({
                    'total_amount': sum(amounts),
                    'avg_amount': sum(amounts) / len(amounts),
                    'min_amount': min(amounts),
                    'max_amount': max(amounts)
                })
            
            # آمار تاریخ
            dates = []
            for item in data:
                date = self._parse_date(item.get('transaction_date', ''))
                if date:
                    dates.append(date)
            
            if dates:
                stats.update({
                    'earliest_date': min(dates),
                    'latest_date': max(dates),
                    'date_range_days': (max(dates) - min(dates)).days
                })
            
            return stats
            
        except Exception as e:
            self.logger.error(f"خطا در محاسبه آمار: {str(e)}")
            return {}
