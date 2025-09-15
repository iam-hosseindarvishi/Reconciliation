"""
Statistics Provider Module
ماژول ارائه‌دهنده آمار - جدا شده از dashboard_tab.py
"""
import logging
import sqlite3
from config.settings import DB_PATH
from database.banks_repository import get_all_banks


class StatisticsProvider:
    """کلاس ارائه‌دهنده آمار برای داشبورد"""
    
    def __init__(self, logger=None):
        self.logger = logger or logging.getLogger(__name__)
    
    def get_bank_statistics(self):
        """
        دریافت آمار بانک‌ها
        
        Returns:
            list: لیست آمار بانک‌ها شامل تعداد رکوردها و درصد مغایرت‌گیری
        """
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            
            # دریافت لیست بانک‌ها
            banks = get_all_banks()
            
            stats = []
            for bank_id, bank_name in banks:
                # تعداد کل رکوردها
                cursor.execute(
                    "SELECT COUNT(*) FROM BankTransactions WHERE bank_id = ?", 
                    (bank_id,)
                )
                total_records = cursor.fetchone()[0]
                
                # تعداد رکوردهای مغایرت‌گیری شده
                cursor.execute(
                    "SELECT COUNT(*) FROM BankTransactions WHERE bank_id = ? AND is_reconciled = 1", 
                    (bank_id,)
                )
                reconciled_records = cursor.fetchone()[0]
                
                # محاسبه آمار
                unreconciled_records = total_records - reconciled_records
                reconciled_percentage = 0
                if total_records > 0:
                    reconciled_percentage = (reconciled_records / total_records) * 100
                
                stats.append({
                    "bank_id": bank_id,
                    "bank_name": bank_name,
                    "total_records": total_records,
                    "reconciled_records": reconciled_records,
                    "unreconciled_records": unreconciled_records,
                    "reconciled_percentage": reconciled_percentage
                })
            
            conn.close()
            self.logger.info(f"آمار {len(stats)} بانک دریافت شد")
            return stats
            
        except Exception as e:
            self.logger.error(f"خطا در دریافت آمار بانک‌ها: {str(e)}")
            raise
    
    def get_accounting_statistics(self):
        """
        دریافت آمار حسابداری
        
        Returns:
            list: لیست آمار حسابداری شامل تعداد رکوردها و درصد مغایرت‌گیری
        """
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            
            # دریافت لیست بانک‌ها
            banks = get_all_banks()
            
            stats = []
            for bank_id, bank_name in banks:
                # تعداد کل رکوردها
                cursor.execute(
                    "SELECT COUNT(*) FROM AccountingTransactions WHERE bank_id = ?", 
                    (bank_id,)
                )
                total_records = cursor.fetchone()[0]
                
                # تعداد رکوردهای مغایرت‌گیری شده
                cursor.execute(
                    "SELECT COUNT(*) FROM AccountingTransactions WHERE bank_id = ? AND is_reconciled = 1", 
                    (bank_id,)
                )
                reconciled_records = cursor.fetchone()[0]
                
                # محاسبه آمار
                unreconciled_records = total_records - reconciled_records
                reconciled_percentage = 0
                if total_records > 0:
                    reconciled_percentage = (reconciled_records / total_records) * 100
                
                stats.append({
                    "bank_id": bank_id,
                    "bank_name": bank_name,
                    "total_records": total_records,
                    "reconciled_records": reconciled_records,
                    "unreconciled_records": unreconciled_records,
                    "reconciled_percentage": reconciled_percentage
                })
            
            conn.close()
            self.logger.info(f"آمار حسابداری {len(stats)} بانک دریافت شد")
            return stats
            
        except Exception as e:
            self.logger.error(f"خطا در دریافت آمار حسابداری: {str(e)}")
            raise
    
    def get_pos_statistics(self):
        """
        دریافت آمار پوز
        
        Returns:
            list: لیست آمار پوز شامل تعداد رکوردها و درصد مغایرت‌گیری
        """
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            
            # دریافت لیست بانک‌ها
            banks = get_all_banks()
            
            stats = []
            for bank_id, bank_name in banks:
                # تعداد کل رکوردها
                cursor.execute(
                    "SELECT COUNT(*) FROM PosTransactions WHERE bank_id = ?", 
                    (bank_id,)
                )
                total_records = cursor.fetchone()[0]
                
                # تعداد رکوردهای مغایرت‌گیری شده
                cursor.execute(
                    "SELECT COUNT(*) FROM PosTransactions WHERE bank_id = ? AND is_reconciled = 1", 
                    (bank_id,)
                )
                reconciled_records = cursor.fetchone()[0]
                
                # محاسبه آمار
                unreconciled_records = total_records - reconciled_records
                reconciled_percentage = 0
                if total_records > 0:
                    reconciled_percentage = (reconciled_records / total_records) * 100
                
                stats.append({
                    "bank_id": bank_id,
                    "bank_name": bank_name,
                    "total_records": total_records,
                    "reconciled_records": reconciled_records,
                    "unreconciled_records": unreconciled_records,
                    "reconciled_percentage": reconciled_percentage
                })
            
            conn.close()
            self.logger.info(f"آمار پوز {len(stats)} بانک دریافت شد")
            return stats
            
        except Exception as e:
            self.logger.error(f"خطا در دریافت آمار پوز: {str(e)}")
            raise
    
    def get_overall_summary(self):
        """
        دریافت خلاصه کلی آمار تمام بخش‌ها
        
        Returns:
            dict: خلاصه کلی شامل جمع کل رکوردها و آمار کلی
        """
        try:
            bank_stats = self.get_bank_statistics()
            accounting_stats = self.get_accounting_statistics()
            pos_stats = self.get_pos_statistics()
            
            # محاسبه جمع کل
            total_bank_records = sum(stat['total_records'] for stat in bank_stats)
            total_accounting_records = sum(stat['total_records'] for stat in accounting_stats)
            total_pos_records = sum(stat['total_records'] for stat in pos_stats)
            
            total_bank_reconciled = sum(stat['reconciled_records'] for stat in bank_stats)
            total_accounting_reconciled = sum(stat['reconciled_records'] for stat in accounting_stats)
            total_pos_reconciled = sum(stat['reconciled_records'] for stat in pos_stats)
            
            # محاسبه درصد کلی
            overall_bank_percentage = 0
            if total_bank_records > 0:
                overall_bank_percentage = (total_bank_reconciled / total_bank_records) * 100
            
            overall_accounting_percentage = 0
            if total_accounting_records > 0:
                overall_accounting_percentage = (total_accounting_reconciled / total_accounting_records) * 100
            
            overall_pos_percentage = 0
            if total_pos_records > 0:
                overall_pos_percentage = (total_pos_reconciled / total_pos_records) * 100
            
            summary = {
                'bank': {
                    'total_records': total_bank_records,
                    'reconciled_records': total_bank_reconciled,
                    'unreconciled_records': total_bank_records - total_bank_reconciled,
                    'reconciled_percentage': overall_bank_percentage
                },
                'accounting': {
                    'total_records': total_accounting_records,
                    'reconciled_records': total_accounting_reconciled,
                    'unreconciled_records': total_accounting_records - total_accounting_reconciled,
                    'reconciled_percentage': overall_accounting_percentage
                },
                'pos': {
                    'total_records': total_pos_records,
                    'reconciled_records': total_pos_reconciled,
                    'unreconciled_records': total_pos_records - total_pos_reconciled,
                    'reconciled_percentage': overall_pos_percentage
                },
                'grand_total': {
                    'total_records': total_bank_records + total_accounting_records + total_pos_records,
                    'reconciled_records': total_bank_reconciled + total_accounting_reconciled + total_pos_reconciled,
                }
            }
            
            summary['grand_total']['unreconciled_records'] = (
                summary['grand_total']['total_records'] - summary['grand_total']['reconciled_records']
            )
            
            if summary['grand_total']['total_records'] > 0:
                summary['grand_total']['reconciled_percentage'] = (
                    summary['grand_total']['reconciled_records'] / summary['grand_total']['total_records']
                ) * 100
            else:
                summary['grand_total']['reconciled_percentage'] = 0
            
            return summary
            
        except Exception as e:
            self.logger.error(f"خطا در دریافت خلاصه کلی آمار: {str(e)}")
            return {}
    
    def get_bank_detailed_stats(self, bank_id):
        """
        دریافت آمار تفصیلی یک بانک خاص
        
        Args:
            bank_id: شناسه بانک
            
        Returns:
            dict: آمار تفصیلی بانک
        """
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            
            # آمار بانک
            cursor.execute("""
                SELECT 
                    COUNT(*) as total,
                    COUNT(CASE WHEN is_reconciled = 1 THEN 1 END) as reconciled,
                    SUM(amount) as total_amount,
                    SUM(CASE WHEN is_reconciled = 1 THEN amount ELSE 0 END) as reconciled_amount
                FROM BankTransactions 
                WHERE bank_id = ?
            """, (bank_id,))
            bank_stats = cursor.fetchone()
            
            # آمار حسابداری
            cursor.execute("""
                SELECT 
                    COUNT(*) as total,
                    COUNT(CASE WHEN is_reconciled = 1 THEN 1 END) as reconciled,
                    SUM(transaction_amount) as total_amount,
                    SUM(CASE WHEN is_reconciled = 1 THEN transaction_amount ELSE 0 END) as reconciled_amount
                FROM AccountingTransactions 
                WHERE bank_id = ?
            """, (bank_id,))
            accounting_stats = cursor.fetchone()
            
            # آمار پوز
            cursor.execute("""
                SELECT 
                    COUNT(*) as total,
                    COUNT(CASE WHEN is_reconciled = 1 THEN 1 END) as reconciled,
                    SUM(amount) as total_amount,
                    SUM(CASE WHEN is_reconciled = 1 THEN amount ELSE 0 END) as reconciled_amount
                FROM PosTransactions 
                WHERE bank_id = ?
            """, (bank_id,))
            pos_stats = cursor.fetchone()
            
            conn.close()
            
            return {
                'bank': {
                    'total_records': bank_stats[0] or 0,
                    'reconciled_records': bank_stats[1] or 0,
                    'total_amount': bank_stats[2] or 0,
                    'reconciled_amount': bank_stats[3] or 0
                },
                'accounting': {
                    'total_records': accounting_stats[0] or 0,
                    'reconciled_records': accounting_stats[1] or 0,
                    'total_amount': accounting_stats[2] or 0,
                    'reconciled_amount': accounting_stats[3] or 0
                },
                'pos': {
                    'total_records': pos_stats[0] or 0,
                    'reconciled_records': pos_stats[1] or 0,
                    'total_amount': pos_stats[2] or 0,
                    'reconciled_amount': pos_stats[3] or 0
                }
            }
            
        except Exception as e:
            self.logger.error(f"خطا در دریافت آمار تفصیلی بانک {bank_id}: {str(e)}")
            return {}
