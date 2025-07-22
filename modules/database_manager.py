#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
ماژول مدیریت پایگاه داده
این ماژول مسئول ایجاد، اتصال و مدیریت پایگاه داده SQLite است.
"""

import os
import sqlite3
from typing import Dict, List, Optional, Tuple, Any
import pandas as pd

from modules.logger import get_logger

# ایجاد شیء لاگر
logger = get_logger(__name__)


class DatabaseManager:
    _instance = None

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(DatabaseManager, cls).__new__(cls)
        return cls._instance
    """
    کلاس مدیریت پایگاه داده SQLite
    """
    
    def __init__(self, db_path: str = None):
        """
        مقداردهی اولیه کلاس DatabaseManager

        پارامترها:
            db_path: مسیر فایل پایگاه داده (اختیاری)
        """
        if not hasattr(self, 'initialized'):  # جلوگیری از مقداردهی مجدد
            # تنظیم مسیر پیش‌فرض پایگاه داده اگر مسیر ارائه نشده باشد
            if db_path is None:
                base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                db_path = os.path.join(base_dir, 'data', 'reconciliation_db.sqlite')
            
            self.db_path = db_path
            self.connection = None
            self.cursor = None
            self.connect()
            self.initialized = True
    
    def connect(self) -> None:
        """
        ایجاد اتصال به پایگاه داده
        """
        try:
            # اطمینان از وجود دایرکتوری پایگاه داده
            os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
            
            # ایجاد اتصال به پایگاه داده
            self.connection = sqlite3.connect(self.db_path)
            self.cursor = self.connection.cursor()
            logger.info(f"اتصال به پایگاه داده برقرار شد: {self.db_path}")
        except Exception as e:
            logger.error(f"خطا در اتصال به پایگاه داده: {str(e)}")
            raise
    
    def disconnect(self) -> None:
        """
        قطع اتصال از پایگاه داده
        """
        if self.connection:
            self.connection.close()
            self.connection = None
            self.cursor = None
            logger.info("اتصال به پایگاه داده قطع شد.")
    
    def setup_database(self) -> None:
        """
        ایجاد جداول پایگاه داده در صورت عدم وجود
        """
        try:
            if not self.connection:
                self.connect()
            
            # ایجاد جدول بانک‌ها
            self.cursor.execute('''
                CREATE TABLE IF NOT EXISTS Banks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    BankName TEXT UNIQUE NOT NULL,
                    BankCode TEXT UNIQUE
                )
            ''')
            
            # ایجاد جدول تراکنش‌های بانک
            self.cursor.execute('''
                CREATE TABLE IF NOT EXISTS BankTransactions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    BankID INTEGER NOT NULL,
                    Description_Bank TEXT,
                    Payer_Receiver TEXT,
                    Bank_Tracking_ID TEXT UNIQUE,
                    Shaparak_Deposit_Tracking_ID_Raw TEXT,
                    Balance REAL,
                    Deposit_Amount REAL,
                    Withdrawal_Amount REAL,
                    Branch_Code TEXT,
                    Time TEXT,
                    Date TEXT,
                    Extracted_Shaparak_Terminal_ID TEXT,
                    Extracted_Switch_Tracking_ID TEXT,
                    Transaction_Type_Bank TEXT,
                    is_reconciled BOOLEAN DEFAULT 0,
                    FOREIGN KEY (BankID) REFERENCES Banks(id)
                )
            ''')
            
            # ایجاد جدول تراکنش‌های پوز
            self.cursor.execute('''
                CREATE TABLE IF NOT EXISTS PosTransactions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    BankID INTEGER NOT NULL,
                    POS_Tracking_Number TEXT,
                    Card_Number TEXT,
                    Terminal_ID TEXT,
                    Terminal_Name TEXT,
                    Terminal_Identifier TEXT,
                    Transaction_Type TEXT,
                    Transaction_Amount REAL,
                    Transaction_Date TEXT,
                    Transaction_Time TEXT,
                    Transaction_Status TEXT,
                    is_reconciled BOOLEAN DEFAULT 0,
                    FOREIGN KEY (BankID) REFERENCES Banks(id),
                    UNIQUE(POS_Tracking_Number, Terminal_ID)
                )
            ''')
            
            # ایجاد جدول ورودی‌های حسابداری
            self.cursor.execute('''
                CREATE TABLE IF NOT EXISTS AccountingEntries (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    BankID INTEGER NOT NULL,
                    Entry_Type_Acc TEXT,
                    Account_Reference_Suffix TEXT UNIQUE,
                    Price REAL,
                    Description_Notes_Acc TEXT,
                    Due_Date TEXT,
                    Person_Name TEXT,
                    Delivery_Date TEXT,
                    Date_Of_Receipt TEXT Null,
                    Extracted_Card_Suffix_Acc TEXT,
                    is_reconciled BOOLEAN DEFAULT 0,
                    FOREIGN KEY (BankID) REFERENCES Banks(id)
                )
            ''')
            
            # ایجاد جدول نتایج مغایرت‌گیری
            self.cursor.execute('''
                CREATE TABLE IF NOT EXISTS ReconciliationResults (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    bank_transaction_id INTEGER,
                    pos_transaction_id INTEGER,
                    accounting_entry_id INTEGER,
                    reconciliation_type TEXT,
                    reconciliation_date TEXT,
                    notes TEXT,
                    FOREIGN KEY (bank_transaction_id) REFERENCES BankTransactions(id),
                    FOREIGN KEY (pos_transaction_id) REFERENCES PosTransactions(id),
                    FOREIGN KEY (accounting_entry_id) REFERENCES AccountingEntries(id)
                )
            ''')
            
            self.connection.commit()
            logger.info("جداول پایگاه داده با موفقیت ایجاد شدند.")
            
        except Exception as e:
            logger.error(f"خطا در راه‌اندازی پایگاه داده: {str(e)}")
            raise
        finally:
            pass  # اتصال را باز نگه می‌داریم
    
    def insert_bank_transactions(self, df: pd.DataFrame, bank_id: int) -> int:
        """
        درج داده‌های تراکنش بانک در پایگاه داده
        
        پارامترها:
            df: دیتافریم حاوی داده‌های تراکنش بانک
            bank_id: شناسه بانک
            
        خروجی:
            تعداد رکوردهای درج شده
        """
        try:
            if not self.connection:
                self.connect()
            inserted_count = 0
            
            for _, row in df.iterrows():
                try:
                    # تبدیل مقادیر عددی بزرگ به رشته برای جلوگیری از خطای SQLite
                    def safe_convert_to_float(value):
                        if pd.isna(value) or value is None:
                            return None
                        try:
                            float_val = float(value)
                            # بررسی محدوده SQLite INTEGER (حداکثر 9223372036854775807)
                            if abs(float_val) > 9223372036854775807:
                                return None  # مقدار خیلی بزرگ - None قرار می‌دهیم
                            return float_val
                        except (ValueError, TypeError, OverflowError):
                            return None
                    
                    balance = safe_convert_to_float(row.get('Balance'))
                    deposit_amount = safe_convert_to_float(row.get('Deposit_Amount'))
                    withdrawal_amount = safe_convert_to_float(row.get('Withdrawal_Amount'))
                    
                    self.cursor.execute('''
                        INSERT OR IGNORE INTO BankTransactions (
                            BankID, Description_Bank, Payer_Receiver, Bank_Tracking_ID,
                            Shaparak_Deposit_Tracking_ID_Raw, Balance, Deposit_Amount,
                            Withdrawal_Amount, Branch_Code, Time, Date,
                            Extracted_Shaparak_Terminal_ID, Extracted_Switch_Tracking_ID, Transaction_Type_Bank, is_reconciled
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        bank_id,
                        row.get('Description_Bank'),
                        row.get('Payer_Receiver'),
                        str(row.get('Bank_Tracking_ID')) if row.get('Bank_Tracking_ID') is not None else None,
                        str(row.get('Shaparak_Deposit_Tracking_ID_Raw')) if row.get('Shaparak_Deposit_Tracking_ID_Raw') is not None else None,
                        balance,
                        deposit_amount,
                        withdrawal_amount,
                        row.get('Branch_Code'),
                        row.get('Time'),
                        row.get('Date'),
                        row.get('Extracted_Shaparak_Terminal_ID'),
                        row.get('Extracted_Switch_Tracking_ID'),
                        row.get('Transaction_Type_Bank'),
                        False
                    ))
                    
                    if self.cursor.rowcount > 0:
                        inserted_count += 1
                        
                except sqlite3.IntegrityError:
                    # رکورد تکراری - نادیده گرفتن
                    logger.warning(f"رکورد تکراری بانک با شناسه پیگیری {row.get('Bank_Tracking_ID')} نادیده گرفته شد.")
                except Exception as e:
                    logger.error(f"خطا در درج رکورد بانک: {str(e)}")
            
            self.connection.commit()
            logger.info(f"{inserted_count} رکورد بانک با موفقیت درج شد.")
            return inserted_count
            
        except Exception as e:
            logger.error(f"خطا در درج داده‌های بانک: {str(e)}")
            raise
        finally:
            pass  # اتصال را باز نگه می‌داریم
    
    def insert_pos_transactions(self, df: pd.DataFrame, bank_id: int) -> int:
        """
        درج داده‌های تراکنش پوز در پایگاه داده
        
        پارامترها:
            df: دیتافریم حاوی داده‌های تراکنش پوز
            bank_id: شناسه بانک
            
        خروجی:
            تعداد رکوردهای درج شده
        """
        try:
            if not self.connection:
                self.connect()
            inserted_count = 0
            
            for _, row in df.iterrows():
                try:
                    # تبدیل مقادیر عددی بزرگ برای جلوگیری از خطای SQLite
                    def safe_convert_to_float(value):
                        if pd.isna(value) or value is None:
                            return None
                        try:
                            float_val = float(value)
                            if abs(float_val) > 9223372036854775807:
                                return None
                            return float_val
                        except (ValueError, TypeError, OverflowError):
                            return None
                    
                    transaction_amount = safe_convert_to_float(row.get('Transaction_Amount'))
                    
                    self.cursor.execute('''
                        INSERT OR IGNORE INTO PosTransactions (
                            BankID, POS_Tracking_Number, Card_Number, Terminal_ID,
                            Terminal_Name, Terminal_Identifier, Transaction_Type,
                            Transaction_Amount, Transaction_Date, Transaction_Time,
                            Transaction_Status, is_reconciled
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        bank_id,
                        str(row.get('POS_Tracking_Number')) if row.get('POS_Tracking_Number') is not None else None,
                        str(row.get('Card_Number')) if row.get('Card_Number') is not None else None,
                        str(row.get('Terminal_ID')) if row.get('Terminal_ID') is not None else None,
                        row.get('Terminal_Name'),
                        row.get('Terminal_Identifier'),
                        row.get('Transaction_Type'),
                        transaction_amount,
                        row.get('Transaction_Date'),
                        row.get('Transaction_Time'),
                        row.get('Transaction_Status'),
                        False
                    ))
                    
                    if self.cursor.rowcount > 0:
                        inserted_count += 1
                        
                except sqlite3.IntegrityError:
                    # رکورد تکراری - نادیده گرفتن
                    logger.warning(f"رکورد تکراری پوز با شناسه پیگیری {row.get('POS_Tracking_Number')} و ترمینال {row.get('Terminal_ID')} نادیده گرفته شد.")
                except Exception as e:
                    logger.error(f"خطا در درج رکورد پوز: {str(e)}")
            
            self.connection.commit()
            logger.info(f"{inserted_count} رکورد پوز با موفقیت درج شد.")
            return inserted_count
            
        except Exception as e:
            logger.error(f"خطا در درج داده‌های پوز: {str(e)}")
            raise
        finally:
            pass  # اتصال را باز نگه می‌داریم
    
    def insert_accounting_entries(self, df: pd.DataFrame, bank_id: int) -> int:
        """
        درج داده‌های حسابداری در پایگاه داده
        
        پارامترها:
            df: دیتافریم حاوی داده‌های حسابداری
            bank_id: شناسه بانک
            
        خروجی:
            تعداد رکوردهای درج شده
        """
        try:
            if not self.connection:
                self.connect()
            inserted_count = 0
            
            for _, row in df.iterrows():
                try:
                    # تبدیل مقادیر عددی بزرگ برای جلوگیری از خطای SQLite
                    def safe_convert_to_float(value):
                        if pd.isna(value) or value is None:
                            return None
                        try:
                            float_val = float(value)
                            if abs(float_val) > 9223372036854775807:
                                return None
                            return float_val
                        except (ValueError, TypeError, OverflowError):
                            return None
                    
                    price = safe_convert_to_float(row.get('Price'))
                    
                    self.cursor.execute('''
                        INSERT OR IGNORE INTO AccountingEntries (
                            BankID, Entry_Type_Acc, Account_Reference_Suffix, Price,
                            Due_Date, Person_Name, Delivery_Date, Date_Of_Receipt,
                            Description_Notes_Acc, Extracted_Card_Suffix_Acc, is_reconciled
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        bank_id,
                        row.get('Entry_Type_Acc'),
                        str(row.get('Account_Reference_Suffix')) if row.get('Account_Reference_Suffix') is not None else None,
                        price,
                        row.get('Due_Date'),
                        row.get('Person_Name'),
                        row.get('Delivery_Date'),
                        row.get('Date_Of_Receipt'),
                        row.get('Description_Notes_Acc'),
                        row.get('Extracted_Card_Suffix_Acc'),
                        False
                    ))
                    
                    if self.cursor.rowcount > 0:
                        inserted_count += 1
                        
                except sqlite3.IntegrityError:
                    # رکورد تکراری - نادیده گرفتن
                    logger.warning(f"رکورد تکراری حسابداری با شماره {row.get('Account_Reference_Suffix')} نادیده گرفته شد.")
                except Exception as e:
                    logger.error(f"خطا در درج رکورد حسابداری: {str(e)}")
            
            self.connection.commit()
            logger.info(f"{inserted_count} رکورد حسابداری با موفقیت درج شد.")
            return inserted_count
            
        except Exception as e:
            logger.error(f"خطا در درج داده‌های حسابداری: {str(e)}")
            raise
        finally:
            pass  # اتصال را باز نگه می‌داریم
    
    def get_unreconciled_bank_transactions(self, bank_id: int = None) -> List[Dict[str, Any]]:
        """
        دریافت تراکنش‌های بانکی مغایرت‌گیری نشده
        
        پارامترها:
            bank_id: شناسه بانک (اختیاری - اگر مشخص نشود، همه بانک‌ها)
        
        خروجی:
            لیستی از دیکشنری‌های حاوی اطلاعات تراکنش‌های بانکی
        """
        try:
            self.connect()
            if bank_id:
                self.cursor.execute('''
                    SELECT * FROM BankTransactions WHERE is_reconciled = 0 AND BankID = ?
                ''', (bank_id,))
            else:
                self.cursor.execute('''
                    SELECT * FROM BankTransactions WHERE is_reconciled = 0
                ''')
            columns = [desc[0] for desc in self.cursor.description]
            result = [dict(zip(columns, row)) for row in self.cursor.fetchall()]
            return result
        except Exception as e:
            logger.error(f"خطا در دریافت تراکنش‌های بانکی مغایرت‌گیری نشده: {str(e)}")
            raise
        finally:
            self.disconnect()
    
    def get_unreconciled_pos_transactions(self, bank_id: int = None) -> List[Dict[str, Any]]:
        """
        دریافت تراکنش‌های پوز مغایرت‌گیری نشده
        
        پارامترها:
            bank_id: شناسه بانک (اختیاری - اگر مشخص نشود، همه بانک‌ها)
        
        خروجی:
            لیستی از دیکشنری‌های حاوی اطلاعات تراکنش‌های پوز
        """
        try:
            self.connect()
            if bank_id:
                self.cursor.execute('''
                    SELECT * FROM PosTransactions WHERE is_reconciled = 0 AND BankID = ?
                ''', (bank_id,))
            else:
                self.cursor.execute('''
                    SELECT * FROM PosTransactions WHERE is_reconciled = 0
                ''')
            columns = [desc[0] for desc in self.cursor.description]
            result = [dict(zip(columns, row)) for row in self.cursor.fetchall()]
            return result
        except Exception as e:
            logger.error(f"خطا در دریافت تراکنش‌های پوز مغایرت‌گیری نشده: {str(e)}")
            raise
        finally:
            self.disconnect()
    
    def get_unreconciled_accounting_entries(self, bank_id: int = None) -> List[Dict[str, Any]]:
        """
        دریافت ورودی‌های حسابداری مغایرت‌گیری نشده
        
        پارامترها:
            bank_id: شناسه بانک (اختیاری - اگر مشخص نشود، همه بانک‌ها)
        
        خروجی:
            لیستی از دیکشنری‌های حاوی اطلاعات ورودی‌های حسابداری
        """
        try:
            self.connect()
            if bank_id:
                self.cursor.execute('''
                    SELECT * FROM AccountingEntries WHERE is_reconciled = 0 AND BankID = ?
                ''', (bank_id,))
            else:
                self.cursor.execute('''
                    SELECT * FROM AccountingEntries WHERE is_reconciled = 0
                ''')
            columns = [desc[0] for desc in self.cursor.description]
            result = [dict(zip(columns, row)) for row in self.cursor.fetchall()]
            return result
        except Exception as e:
            logger.error(f"خطا در دریافت ورودی‌های حسابداری مغایرت‌گیری نشده: {str(e)}")
            raise
        finally:
            self.disconnect()
    
    def update_reconciliation_status(self, table: str, record_id: int, is_reconciled: bool) -> bool:
        """
        به‌روزرسانی وضعیت مغایرت‌گیری یک رکورد
        
        پارامترها:
            table: نام جدول (BankTransactions, PosTransactions, AccountingEntries)
            record_id: شناسه رکورد
            is_reconciled: وضعیت مغایرت‌گیری
            
        خروجی:
            موفقیت عملیات
        """
        try:
            logger.info(f"🏷️ شروع به‌روزرسانی وضعیت مغایرت‌گیری")
            logger.info(f"📊 جدول: {table}, رکورد ID: {record_id}, وضعیت: {is_reconciled}")
            
            self.connect()
            logger.info(f"🔗 اتصال به دیتابیس برقرار شد")
            
            # بررسی اعتبار نام جدول
            valid_tables = ['BankTransactions', 'PosTransactions', 'AccountingEntries']
            if table not in valid_tables:
                logger.error(f"❌ نام جدول نامعتبر: {table}")
                return False
            
            logger.info(f"💾 اجرای کوئری UPDATE برای جدول {table}...")
            self.cursor.execute(f'''
                UPDATE {table} SET is_reconciled = ? WHERE id = ?
            ''', (is_reconciled, record_id))
            
            logger.info(f"💾 کامیت تغییرات...")
            self.connection.commit()
            
            affected_rows = self.cursor.rowcount
            logger.info(f"📊 تعداد رکوردهای تأثیر یافته: {affected_rows}")
            
            if affected_rows > 0:
                logger.info(f"✅ وضعیت مغایرت‌گیری با موفقیت به‌روزرسانی شد")
                return True
            else:
                logger.warning(f"⚠️ هیچ رکوردی تأثیر نپذیرفت - ممکن است رکورد وجود نداشته باشد")
                return False
            
        except Exception as e:
            logger.error(f"❌ خطا در به‌روزرسانی وضعیت مغایرت‌گیری: {str(e)}")
            logger.error(f"🔍 جزئیات خطا: table={table}, record_id={record_id}, is_reconciled={is_reconciled}")
            return False
        finally:
            logger.info(f"🔌 قطع اتصال از دیتابیس")
            self.disconnect()
    
    def update_bank_transaction_reconciled_status(self, transaction_id: int, is_reconciled: bool) -> bool:
        """
        به‌روزرسانی وضعیت مغایرت‌گیری تراکنش بانکی
        
        پارامترها:
            transaction_id: شناسه تراکنش بانکی
            is_reconciled: وضعیت مغایرت‌گیری
            
        خروجی:
            موفقیت عملیات
        """
        return self.update_reconciliation_status('BankTransactions', transaction_id, is_reconciled)
    
    def update_accounting_entry_reconciled_status(self, entry_id: int, is_reconciled: bool) -> bool:
        """
        به‌روزرسانی وضعیت مغایرت‌گیری ورودی حسابداری
        
        پارامترها:
            entry_id: شناسه ورودی حسابداری
            is_reconciled: وضعیت مغایرت‌گیری
            
        خروجی:
            موفقیت عملیات
        """
        return self.update_reconciliation_status('AccountingEntries', entry_id, is_reconciled)
    
    def insert_reconciliation_result(self, bank_transaction_id: Optional[int] = None, 
                                   accounting_entry_id: Optional[int] = None,
                                   pos_transaction_id: Optional[int] = None,
                                   reconciliation_type: str = "Match",
                                   reconciliation_date: str = None,
                                   notes: str = None) -> bool:
        """
        درج نتیجه مغایرت‌گیری در جدول ReconciliationResults
        
        پارامترها:
            bank_transaction_id: شناسه تراکنش بانکی (اختیاری)
            accounting_entry_id: شناسه ورودی حسابداری (اختیاری)
            pos_transaction_id: شناسه تراکنش پوز (اختیاری)
            reconciliation_type: نوع مغایرت‌گیری
            reconciliation_date: تاریخ مغایرت‌گیری (اختیاری)
            notes: یادداشت‌ها (اختیاری)
            
        خروجی:
            موفقیت عملیات
        """
        try:
            if reconciliation_date is None:
                from datetime import datetime
                reconciliation_date = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            return self.record_reconciliation_result(
                bank_id=bank_transaction_id,
                pos_id=pos_transaction_id,
                accounting_id=accounting_entry_id,
                reconciliation_type=reconciliation_type,
                notes=notes
            )
        except Exception as e:
            logger.error(f"خطا در درج نتیجه مغایرت‌گیری: {str(e)}")
            return False
    
    def record_reconciliation_result(self, bank_id: Optional[int], pos_id: Optional[int], 
                                    accounting_id: Optional[int], reconciliation_type: str, 
                                    notes: str = None) -> bool:
        """
        ثبت نتیجه مغایرت‌گیری
        
        پارامترها:
            bank_id: شناسه رکورد بانک (اختیاری)
            pos_id: شناسه رکورد پوز (اختیاری)
            accounting_id: شناسه رکورد حسابداری (اختیاری)
            reconciliation_type: نوع مغایرت‌گیری
            notes: یادداشت‌ها (اختیاری)
            
        خروجی:
            موفقیت عملیات
        """
        try:
            logger.info(f"🗄️ شروع ثبت نتیجه مغایرت‌گیری در دیتابیس")
            logger.info(f"📊 پارامترهای ورودی: bank_id={bank_id}, pos_id={pos_id}, accounting_id={accounting_id}")
            logger.info(f"📝 نوع مغایرت‌گیری: {reconciliation_type}")
            logger.info(f"📄 یادداشت: {notes}")
            
            self.connect()
            logger.info(f"🔗 اتصال به دیتابیس برقرار شد")
            
            from datetime import datetime
            reconciliation_date = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            logger.info(f"⏰ تاریخ مغایرت‌گیری: {reconciliation_date}")
            
            logger.info(f"💾 درج رکورد در جدول ReconciliationResults...")
            self.cursor.execute('''
                INSERT INTO ReconciliationResults (
                    bank_transaction_id, pos_transaction_id, accounting_entry_id,
                    reconciliation_type, reconciliation_date, notes
                ) VALUES (?, ?, ?, ?, ?, ?)
            ''', (bank_id, pos_id, accounting_id, reconciliation_type, reconciliation_date, notes))
            
            logger.info(f"💾 کامیت تغییرات...")
            self.connection.commit()
            
            logger.info(f"✅ نتیجه مغایرت‌گیری با موفقیت ثبت شد: نوع={reconciliation_type}, بانک={bank_id}, پوز={pos_id}, حسابداری={accounting_id}")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ خطا در ثبت نتیجه مغایرت‌گیری: {str(e)}")
            logger.error(f"🔍 جزئیات خطا: bank_id={bank_id}, pos_id={pos_id}, accounting_id={accounting_id}, type={reconciliation_type}")
            if self.connection:
                logger.info(f"🔄 رولبک تغییرات...")
                self.connection.rollback()
            return False
        finally:
            logger.info(f"🔌 قطع اتصال از دیتابیس")
            self.disconnect()
    
    def get_reconciliation_statistics(self) -> Dict[str, int]:
        """
        دریافت آمار مغایرت‌گیری
        
        خروجی:
            دیکشنری حاوی آمار مغایرت‌گیری
        """
        try:
            self.connect()
            stats = {}
            
            # تعداد کل رکوردها
            self.cursor.execute("SELECT COUNT(*) FROM BankTransactions")
            stats['total_bank'] = self.cursor.fetchone()[0]
            
            self.cursor.execute("SELECT COUNT(*) FROM PosTransactions")
            stats['total_pos'] = self.cursor.fetchone()[0]
            
            self.cursor.execute("SELECT COUNT(*) FROM AccountingEntries")
            stats['total_accounting'] = self.cursor.fetchone()[0]
            
            # تعداد رکوردهای مغایرت‌گیری شده
            self.cursor.execute("SELECT COUNT(*) FROM BankTransactions WHERE is_reconciled = 1")
            stats['reconciled_bank'] = self.cursor.fetchone()[0]
            
            self.cursor.execute("SELECT COUNT(*) FROM PosTransactions WHERE is_reconciled = 1")
            stats['reconciled_pos'] = self.cursor.fetchone()[0]
            
            self.cursor.execute("SELECT COUNT(*) FROM AccountingEntries WHERE is_reconciled = 1")
            stats['reconciled_accounting'] = self.cursor.fetchone()[0]
            
            # تعداد رکوردهای مغایرت‌گیری نشده
            stats['unreconciled_bank'] = stats['total_bank'] - stats['reconciled_bank']
            stats['unreconciled_pos'] = stats['total_pos'] - stats['reconciled_pos']
            stats['unreconciled_accounting'] = stats['total_accounting'] - stats['reconciled_accounting']
            
            return stats
            
        except Exception as e:
            logger.error(f"خطا در دریافت آمار مغایرت‌گیری: {str(e)}")
            return {}
        finally:
            self.disconnect()
    
    def add_bank(self, bank_name: str, bank_code: str = None) -> bool:
        """
        افزودن بانک جدید
        
        پارامترها:
            bank_name: نام بانک
            bank_code: کد بانک (اختیاری)
            
        خروجی:
            موفقیت عملیات
        """
        try:
            self.connect()
            
            self.cursor.execute('''
                INSERT INTO Banks (BankName, BankCode) VALUES (?, ?)
            ''', (bank_name, bank_code))
            
            self.connection.commit()
            logger.info(f"بانک '{bank_name}' با موفقیت اضافه شد.")
            return True
            
        except Exception as e:
            logger.error(f"خطا در افزودن بانک: {str(e)}")
            return False
        finally:
            self.disconnect()
    
    def get_pos_transactions_by_terminal(self, bank_id: int, terminal_id: str) -> List[Dict[str, Any]]:
        """
        دریافت تراکنش‌های پوز بر اساس شناسه ترمینال
        
        پارامترها:
            bank_id: شناسه بانک
            terminal_id: شناسه ترمینال
            
        خروجی:
            لیست تراکنش‌های پوز
        """
        try:
            self.connect()
            self.cursor.execute('''
                SELECT * FROM PosTransactions 
                WHERE BankID = ? AND Terminal_ID = ? AND is_reconciled = 0
            ''', (bank_id, terminal_id))
            columns = [desc[0] for desc in self.cursor.description]
            result = [dict(zip(columns, row)) for row in self.cursor.fetchall()]
            return result
        except Exception as e:
            logger.error(f"خطا در دریافت تراکنش‌های پوز بر اساس ترمینال: {str(e)}")
            return []
        finally:
            self.disconnect()
    
    def get_pos_transactions_by_terminal_date(self, bank_id: int, terminal_id: str, transaction_date: str) -> List[Dict[str, Any]]:
        """
        دریافت تراکنش‌های پوز بر اساس شناسه ترمینال و تاریخ
        
        پارامترها:
            bank_id: شناسه بانک
            terminal_id: شناسه ترمینال
            transaction_date: تاریخ تراکنش
            
        خروجی:
            لیست تراکنش‌های پوز
        """
        try:
            self.connect()
            self.cursor.execute('''
                SELECT * FROM PosTransactions 
                WHERE BankID = ? AND Terminal_ID = ? AND Transaction_Date = ? AND is_reconciled = 0
            ''', (bank_id, terminal_id, transaction_date))
            columns = [desc[0] for desc in self.cursor.description]
            result = [dict(zip(columns, row)) for row in self.cursor.fetchall()]
            return result
        except Exception as e:
            logger.error(f"خطا در دریافت تراکنش‌های پوز بر اساس ترمینال و تاریخ: {str(e)}")
            return []
        finally:
            self.disconnect()
    
    def get_unreconciled_bank_transfers(self, bank_id: int) -> List[Dict[str, Any]]:
        """
        دریافت حواله‌های بانکی مغایرت‌گیری نشده
        
        پارامترها:
            bank_id: شناسه بانک
            
        خروجی:
            لیست حواله‌های بانکی مغایرت‌گیری نشده
        """
        try:
            self.connect()
            
            self.cursor.execute('''
                SELECT * FROM BankTransactions 
                WHERE BankID = ? 
                AND is_reconciled = 0 
                AND (Transaction_Type_Bank = 'Received Transfer' OR Transaction_Type_Bank = 'Paid Transfer')
                ORDER BY Date DESC
            ''', (bank_id,))
            
            columns = [desc[0] for desc in self.cursor.description]
            result = [dict(zip(columns, row)) for row in self.cursor.fetchall()]
            
            logger.info(f"دریافت حواله‌های مغایرت‌گیری نشده برای بانک {bank_id}: {len(result)} رکورد")
            
            return result
            
        except Exception as e:
            logger.error(f"خطا در دریافت حواله‌های مغایرت‌گیری نشده: {str(e)}")
            return []
        finally:
            self.disconnect()
    
    def search_accounting_entries_for_transfer(self, bank_id: int, normalized_date: str, 
                                             target_amount: float, target_entry_type: str) -> List[Dict[str, Any]]:
        """
        جستجوی ورودی‌های حسابداری برای مغایرت‌گیری حواله‌ها
        
        پارامترها:
            bank_id: شناسه بانک
            normalized_date: تاریخ نرمال‌سازی شده (فرمت YYYYMMDD)
            target_amount: مبلغ هدف
            target_entry_type: نوع ورودی حسابداری هدف
            
        خروجی:
            لیست ورودی‌های حسابداری مطابق
        """
        try:
            self.connect()
            
            # تبدیل ستون Due_Date به فرمت YYYYMMDD برای مقایسه
            # فرض می‌کنیم Due_Date در فرمت YYYY/MM/DD ذخیره شده است
            self.cursor.execute('''
                SELECT * FROM AccountingEntries 
                WHERE BankID = ? 
                AND is_reconciled = 0 
                AND REPLACE(Due_Date, '/', '') = ? 
                AND Price = ? 
                AND Entry_Type_Acc = ?
            ''', (bank_id, normalized_date, target_amount, target_entry_type))
            
            columns = [desc[0] for desc in self.cursor.description]
            result = [dict(zip(columns, row)) for row in self.cursor.fetchall()]
            
            logger.info(f"جستجوی ورودی‌های حسابداری: بانک={bank_id}, تاریخ={normalized_date}, مبلغ={target_amount}, نوع={target_entry_type}")
            logger.info(f"تعداد نتایج یافت شده: {len(result)}")
            
            return result
            
        except Exception as e:
            logger.error(f"خطا در جستجوی ورودی‌های حسابداری برای حواله: {str(e)}")
            return []
        finally:
            self.disconnect()

    def get_matching_accounting_entries_for_transfer(self, bank_id: int, normalized_bank_date: str, 
                                                   target_amount: float, target_acc_entry_type: str) -> List[Dict[str, Any]]:
        """
        بازیابی ورودی‌های حسابداری مغایرت‌گیری نشده برای حواله/فیش
        
        پارامترها:
            bank_id: شناسه بانک
            normalized_bank_date: تاریخ نرمال‌سازی شده بانک (فرمت YYYYMMDD)
            target_amount: مبلغ هدف
            target_acc_entry_type: نوع ورودی حسابداری هدف
            
        خروجی:
            لیست ورودی‌های حسابداری مطابق
        """
        try:
            self.connect()
            
            # جستجوی ورودی‌های حسابداری مطابق با شرایط
            # استفاده از Due_Date به عنوان تاریخ تراکنش حسابداری
            self.cursor.execute('''
                SELECT * FROM AccountingEntries 
                WHERE is_reconciled = 0 
                AND BankID = ? 
                AND Due_Date = ? 
                AND Price = ? 
                AND Entry_Type_Acc = ?
            ''', (bank_id, normalized_bank_date, target_amount, target_acc_entry_type))
            
            columns = [desc[0] for desc in self.cursor.description]
            result = [dict(zip(columns, row)) for row in self.cursor.fetchall()]
            
            logger.info(f"بازیابی ورودی‌های حسابداری برای حواله: بانک={bank_id}, تاریخ={normalized_bank_date}, مبلغ={target_amount}, نوع={target_acc_entry_type}")
            logger.info(f"تعداد نتایج یافت شده: {len(result)}")
            
            return result
            
        except Exception as e:
            logger.error(f"خطا در بازیابی ورودی‌های حسابداری برای حواله: {str(e)}")
            return []
        finally:
            self.disconnect()
            
    def get_unreconciled_transfer_transactions(self, bank_id: int) -> List[Dict[str, Any]]:
        """
        بازیابی تراکنش‌های حواله/فیش مغایرت‌گیری نشده از بانک
        
        پارامترها:
            bank_id: شناسه بانک
            
        خروجی:
            لیست تراکنش‌های حواله مغایرت‌گیری نشده
        """
        try:
            self.connect()
            
            self.cursor.execute('''
                SELECT * FROM BankTransactions 
                WHERE is_reconciled = 0 
                AND BankID = ? 
                AND Transaction_Type_Bank IN ('Received Transfer', 'Paid Transfer')
                ORDER BY Date, id
            ''', (bank_id,))
            
            columns = [description[0] for description in self.cursor.description]
            rows = self.cursor.fetchall()
            
            result = [dict(zip(columns, row)) for row in rows]
            
            logger.info(f"بازیابی {len(result)} تراکنش حواله مغایرت‌گیری نشده برای بانک {bank_id}")
            return result
            
        except Exception as e:
            logger.error(f"خطا در بازیابی تراکنش‌های حواله مغایرت‌گیری نشده: {str(e)}")
            return []
        finally:
            self.disconnect()

    def get_all_banks(self) -> List[Dict[str, Any]]:
        """
        دریافت تمام بانک‌ها
        
        خروجی:
            لیستی از دیکشنری‌های حاوی اطلاعات بانک‌ها
        """
        try:
            self.connect()
            self.cursor.execute('''
                SELECT * FROM Banks ORDER BY BankName
            ''')
            columns = [desc[0] for desc in self.cursor.description]
            result = [dict(zip(columns, row)) for row in self.cursor.fetchall()]
            return result
        except Exception as e:
            logger.error(f"خطا در دریافت لیست بانک‌ها: {str(e)}")
            return []
        finally:
            self.disconnect()
    
    def update_bank(self, bank_id: int, bank_name: str, bank_code: str = None) -> bool:
        """
        به‌روزرسانی اطلاعات بانک
        
        پارامترها:
            bank_id: شناسه بانک
            bank_name: نام جدید بانک
            bank_code: کد جدید بانک (اختیاری)
            
        خروجی:
            موفقیت عملیات
        """
        try:
            self.connect()
            
            self.cursor.execute('''
                UPDATE Banks SET BankName = ?, BankCode = ? WHERE id = ?
            ''', (bank_name, bank_code, bank_id))
            
            self.connection.commit()
            return self.cursor.rowcount > 0
            
        except Exception as e:
            logger.error(f"خطا در به‌روزرسانی بانک: {str(e)}")
            return False
        finally:
            self.disconnect()
    
    def delete_bank(self, bank_id: int) -> bool:
        """
        حذف بانک
        
        پارامترها:
            bank_id: شناسه بانک
            
        خروجی:
            موفقیت عملیات
        """
        try:
            self.connect()
            
            # بررسی وجود تراکنش‌های مرتبط با این بانک
            self.cursor.execute('''
                SELECT COUNT(*) FROM BankTransactions WHERE BankID = ?
            ''', (bank_id,))
            bank_transactions_count = self.cursor.fetchone()[0]
            
            self.cursor.execute('''
                SELECT COUNT(*) FROM PosTransactions WHERE BankID = ?
            ''', (bank_id,))
            pos_transactions_count = self.cursor.fetchone()[0]
            
            self.cursor.execute('''
                SELECT COUNT(*) FROM AccountingEntries WHERE BankID = ?
            ''', (bank_id,))
            accounting_entries_count = self.cursor.fetchone()[0]
            
            total_related_records = bank_transactions_count + pos_transactions_count + accounting_entries_count
            
            if total_related_records > 0:
                logger.warning(f"نمی‌توان بانک را حذف کرد. {total_related_records} رکورد مرتبط وجود دارد.")
                return False
            
            self.cursor.execute('''
                DELETE FROM Banks WHERE id = ?
            ''', (bank_id,))
            
            self.connection.commit()
            return self.cursor.rowcount > 0
            
        except Exception as e:
            logger.error(f"خطا در حذف بانک: {str(e)}")
            return False
        finally:
            self.disconnect()
    
    def clear_all_data_except_banks(self) -> bool:
        """
        پاک کردن کلیه داده‌ها به استثنای جدول بانک‌ها
        
        خروجی:
            موفقیت عملیات
        """
        try:
            self.connect()
            
            # حذف داده‌های جداول به ترتیب (به دلیل foreign key constraints)
            self.cursor.execute('DELETE FROM ReconciliationResults')
            self.cursor.execute('DELETE FROM BankTransactions')
            self.cursor.execute('DELETE FROM PosTransactions')
            self.cursor.execute('DELETE FROM AccountingEntries')
            
            self.connection.commit()
            logger.info("کلیه داده‌ها به استثنای بانک‌ها با موفقیت حذف شدند.")
            return True
            
        except Exception as e:
            logger.error(f"خطا در پاک کردن کلیه داده‌ها: {str(e)}")
            return False
        finally:
            self.disconnect()
    
    def clear_reconciled_data(self) -> bool:
        """
        حذف اطلاعات مغایرت‌گیری شده
        
        خروجی:
            موفقیت عملیات
        """
        try:
            self.connect()
            
            # حذف نتایج مغایرت‌گیری
            self.cursor.execute('DELETE FROM ReconciliationResults')
            
            # حذف رکوردهای مغایرت‌گیری شده از جداول
            self.cursor.execute('DELETE FROM BankTransactions WHERE is_reconciled = 1')
            self.cursor.execute('DELETE FROM PosTransactions WHERE is_reconciled = 1')
            self.cursor.execute('DELETE FROM AccountingEntries WHERE is_reconciled = 1')
            
            self.connection.commit()
            logger.info("اطلاعات مغایرت‌گیری شده با موفقیت حذف شدند.")
            return True
            
        except Exception as e:
            logger.error(f"خطا در حذف اطلاعات مغایرت‌گیری شده: {str(e)}")
            return False
        finally:
            self.disconnect()
    
    def get_latest_accounting_entry_date(self) -> Optional[str]:
        """
        دریافت تاریخ آخرین رکورد جدول اطلاعات حسابداری
        
        خروجی:
            تاریخ آخرین رکورد یا None در صورت عدم وجود رکورد
        """
        try:
            self.connect()
            
            self.cursor.execute('''
                SELECT MAX(Due_Date) FROM AccountingEntries
            ''')
            
            result = self.cursor.fetchone()
            return result[0] if result and result[0] else None
            
        except Exception as e:
            logger.error(f"خطا در دریافت تاریخ آخرین رکورد حسابداری: {str(e)}")
            return None
        finally:
            self.disconnect()
    
    def get_latest_bank_transaction_date(self) -> Optional[str]:
        """
        دریافت تاریخ آخرین رکورد جدول تراکنش‌های بانکی
        
        خروجی:
            تاریخ آخرین رکورد یا None در صورت عدم وجود رکورد
        """
        try:
            self.connect()
            
            self.cursor.execute('''
                SELECT MAX(Date) FROM BankTransactions
            ''')
            
            result = self.cursor.fetchone()
            return result[0] if result and result[0] else None
            
        except Exception as e:
            logger.error(f"خطا در دریافت تاریخ آخرین رکورد بانکی: {str(e)}")
            return None
        finally:
            self.disconnect()
    
    def get_latest_pos_transaction_date(self) -> Optional[str]:
        """
        دریافت تاریخ آخرین تراکنش پوز
        
        خروجی:
            تاریخ آخرین تراکنش یا None در صورت عدم وجود رکورد
        """
        try:
            self.connect()
            
            self.cursor.execute('''
                SELECT MAX(Transaction_Date) FROM PosTransactions
            ''')
            
            result = self.cursor.fetchone()
            return result[0] if result and result[0] else None
            
        except Exception as e:
            logger.error(f"خطا در دریافت تاریخ آخرین تراکنش پوز: {str(e)}")
            return None
        finally:
            self.disconnect()
    
    def get_reconciled_transactions(self) -> List[Dict[str, Any]]:
        """
        دریافت تراکنش‌های تطبیق داده شده از جدول ReconciliationResults
        
        خروجی:
            لیستی از دیکشنری‌های حاوی اطلاعات تراکنش‌های تطبیق داده شده
        """
        try:
            self.connect()
            
            self.cursor.execute('''
                SELECT 
                    id,
                    bank_transaction_id,
                    pos_transaction_id,
                    accounting_entry_id,
                    reconciliation_type,
                    reconciliation_date,
                    notes
                FROM ReconciliationResults
                ORDER BY reconciliation_date DESC
            ''')
            
            columns = [desc[0] for desc in self.cursor.description]
            result = [dict(zip(columns, row)) for row in self.cursor.fetchall()]
            
            # تبدیل شناسه‌ها به نوع رکورد و شناسه رکورد برای نمایش بهتر
            formatted_result = []
            for row in result:
                formatted_row = {
                    'record_type_1': '',
                    'record_id_1': '',
                    'record_type_2': '',
                    'record_id_2': '',
                    'reconciliation_date': row['reconciliation_date'],
                    'reconciliation_method': row['reconciliation_type']
                }
                
                # تعیین نوع رکورد اول
                if row['bank_transaction_id']:
                    formatted_row['record_type_1'] = 'بانک'
                    formatted_row['record_id_1'] = str(row['bank_transaction_id'])
                elif row['pos_transaction_id']:
                    formatted_row['record_type_1'] = 'پوز'
                    formatted_row['record_id_1'] = str(row['pos_transaction_id'])
                elif row['accounting_entry_id']:
                    formatted_row['record_type_1'] = 'حسابداری'
                    formatted_row['record_id_1'] = str(row['accounting_entry_id'])
                
                # تعیین نوع رکورد دوم (اگر وجود داشته باشد)
                if row['accounting_entry_id'] and (row['bank_transaction_id'] or row['pos_transaction_id']):
                    formatted_row['record_type_2'] = 'حسابداری'
                    formatted_row['record_id_2'] = str(row['accounting_entry_id'])
                
                formatted_result.append(formatted_row)
            
            return formatted_result
            
        except Exception as e:
            logger.error(f"خطا در دریافت تراکنش‌های تطبیق داده شده: {str(e)}")
            return []
        finally:
            self.disconnect()
    
    def search_accounting_entries_for_check(self, bank_id: int, normalized_date: str, 
                                           amount: float, entry_type: str) -> List[Dict[str, Any]]:
        """
        جستجوی ورودی‌های حسابداری برای چک‌ها (بر اساس Date_Of_Receipt)
        
        پارامترها:
            bank_id: شناسه بانک
            normalized_date: تاریخ نرمال‌سازی شده (فرمت YYYYMMDD)
            amount: مبلغ
            entry_type: نوع ورودی حسابداری
            
        خروجی:
            لیست ورودی‌های حسابداری مطابق
        """
        try:
            self.connect()
            
            # تبدیل ستون Date_Of_Receipt به فرمت YYYYMMDD برای مقایسه
            self.cursor.execute('''
                SELECT * FROM AccountingEntries 
                WHERE BankID = ? 
                AND is_reconciled = 0 
                AND REPLACE(Date_Of_Receipt, '/', '') = ? 
                AND Price = ? 
                AND Entry_Type_Acc = ?
            ''', (bank_id, normalized_date, amount, entry_type))
            
            columns = [desc[0] for desc in self.cursor.description]
            result = [dict(zip(columns, row)) for row in self.cursor.fetchall()]
            
            logger.info(f"جستجوی ورودی‌های حسابداری چک: بانک={bank_id}, تاریخ={normalized_date}, مبلغ={amount}, نوع={entry_type}")
            logger.info(f"تعداد نتایج یافت شده: {len(result)}")
            
            return result
            
        except Exception as e:
            logger.error(f"خطا در جستجوی ورودی‌های حسابداری برای چک: {str(e)}")
            return []
        finally:
            self.disconnect()
    
    def get_pos_transactions_for_terminal(self, bank_id: int, terminal_id: str, date: str) -> List[Dict[str, Any]]:
        """
        دریافت تراکنش‌های پوز برای ترمینال و تاریخ مشخص
        
        پارامترها:
            bank_id: شناسه بانک
            terminal_id: شناسه ترمینال
            date: تاریخ (فرمت YYYY/MM/DD)
            
        خروجی:
            لیست تراکنش‌های پوز
        """
        try:
            self.connect()
            
            self.cursor.execute('''
                SELECT * FROM PosTransactions 
                WHERE BankID = ? 
                AND Terminal_ID = ? 
                AND Transaction_Date = ? 
                AND is_reconciled = 0
                ORDER BY Transaction_Time
            ''', (bank_id, terminal_id, date))
            
            columns = [desc[0] for desc in self.cursor.description]
            result = [dict(zip(columns, row)) for row in self.cursor.fetchall()]
            
            logger.info(f"دریافت تراکنش‌های پوز: بانک={bank_id}, ترمینال={terminal_id}, تاریخ={date}")
            logger.info(f"تعداد تراکنش‌ها: {len(result)}")
            
            return result
            
        except Exception as e:
            logger.error(f"خطا در دریافت تراکنش‌های پوز برای ترمینال: {str(e)}")
            return []
        finally:
            self.disconnect()
    
    def get_accounting_entry_by_id(self, entry_id: int) -> Optional[Dict[str, Any]]:
        """
        دریافت ورودی حسابداری بر اساس شناسه
        
        پارامترها:
            entry_id: شناسه ورودی حسابداری
            
        خروجی:
            ورودی حسابداری یا None
        """
        try:
            self.connect()
            
            self.cursor.execute('''
                SELECT * FROM AccountingEntries WHERE id = ?
            ''', (entry_id,))
            
            row = self.cursor.fetchone()
            if row:
                columns = [desc[0] for desc in self.cursor.description]
                return dict(zip(columns, row))
            
            return None
            
        except Exception as e:
            logger.error(f"خطا در دریافت ورودی حسابداری: {str(e)}")
            return None
        finally:
            self.disconnect()
    
    def get_pos_transactions_for_date(self, bank_id: int, terminal_id: str, date: str) -> List[Dict[str, Any]]:
        """
        دریافت تراکنش‌های پوز برای تاریخ مشخص
        
        پارامترها:
            bank_id: شناسه بانک
            terminal_id: شناسه ترمینال
            date: تاریخ (فرمت YYYY/MM/DD)
            
        خروجی:
            لیست تراکنش‌های پوز
        """
        return self.get_pos_transactions_for_terminal(bank_id, terminal_id, date)
    
    def get_unreconciled_check_transactions(self, bank_id: int) -> List[Dict[str, Any]]:
        """
        بازیابی تراکنش‌های چک مغایرت‌گیری نشده از بانک
        
        پارامترها:
            bank_id: شناسه بانک
            
        خروجی:
            لیست تراکنش‌های چک مغایرت‌گیری نشده
        """
        try:
            self.connect()
            
            self.cursor.execute('''
                SELECT * FROM BankTransactions 
                WHERE is_reconciled = 0 
                AND BankID = ? 
                AND Transaction_Type_Bank IN ('Received Check', 'Paid Check')
                ORDER BY Date, id
            ''', (bank_id,))
            
            columns = [description[0] for description in self.cursor.description]
            rows = self.cursor.fetchall()
            
            result = [dict(zip(columns, row)) for row in rows]
            
            logger.info(f"بازیابی {len(result)} تراکنش چک مغایرت‌گیری نشده برای بانک {bank_id}")
            return result
            
        except Exception as e:
            logger.error(f"خطا در بازیابی تراکنش‌های چک مغایرت‌گیری نشده: {str(e)}")
            return []
        finally:
            self.disconnect()
    
    def get_unreconciled_pos_deposits(self, bank_id: int) -> List[Dict[str, Any]]:
        """
        بازیابی تراکنش‌های واریز پوز مغایرت‌گیری نشده از بانک
        
        پارامترها:
            bank_id: شناسه بانک
            
        خروجی:
            لیست تراکنش‌های واریز پوز مغایرت‌گیری نشده
        """
        try:
            self.connect()
            
            self.cursor.execute('''
                SELECT * FROM BankTransactions 
                WHERE is_reconciled = 0 
                AND BankID = ? 
                AND Transaction_Type_Bank = 'POS Deposit'
                ORDER BY Date, id
            ''', (bank_id,))
            
            columns = [description[0] for description in self.cursor.description]
            rows = self.cursor.fetchall()
            
            result = [dict(zip(columns, row)) for row in rows]
            
            logger.info(f"بازیابی {len(result)} تراکنش واریز پوز مغایرت‌گیری نشده برای بانک {bank_id}")
            return result
            
        except Exception as e:
            logger.error(f"خطا در بازیابی تراکنش‌های واریز پوز مغایرت‌گیری نشده: {str(e)}")
            return []
        finally:
            self.disconnect()
    
    def get_total_bank_transactions(self, bank_id: int) -> int:
        """
        دریافت تعداد کل تراکنش‌های بانکی
        
        پارامترها:
            bank_id: شناسه بانک
            
        خروجی:
            تعداد کل تراکنش‌های بانکی
        """
        try:
            self.connect()
            
            self.cursor.execute('''
                SELECT COUNT(*) FROM BankTransactions WHERE BankID = ?
            ''', (bank_id,))
            
            result = self.cursor.fetchone()
            return result[0] if result else 0
            
        except Exception as e:
            logger.error(f"خطا در دریافت تعداد کل تراکنش‌های بانکی: {str(e)}")
            return 0
        finally:
            self.disconnect()
    
    def get_reconciled_bank_transactions_count(self, bank_id: int) -> int:
        """
        دریافت تعداد تراکنش‌های بانکی مغایرت‌گیری شده
        
        پارامترها:
            bank_id: شناسه بانک
            
        خروجی:
            تعداد تراکنش‌های بانکی مغایرت‌گیری شده
        """
        try:
            self.connect()
            
            self.cursor.execute('''
                SELECT COUNT(*) FROM BankTransactions 
                WHERE BankID = ? AND is_reconciled = 1
            ''', (bank_id,))
            
            result = self.cursor.fetchone()
            return result[0] if result else 0
            
        except Exception as e:
            logger.error(f"خطا در دریافت تعداد تراکنش‌های بانکی مغایرت‌گیری شده: {str(e)}")
            return 0
        finally:
            self.disconnect()
    
    def calculate_pos_sum_for_date(self, terminal_id: str, date: str, bank_id: int) -> float:
        """
        محاسبه مجموع تراکنش‌های پوز برای تاریخ مشخص
        
        پارامترها:
            terminal_id: شناسه ترمینال
            date: تاریخ (فرمت YYYY/MM/DD)
            bank_id: شناسه بانک
            
        خروجی:
            مجموع مبالغ تراکنش‌های پوز
        """
        try:
            self.connect()
            
            self.cursor.execute('''
                SELECT SUM(Transaction_Amount) FROM PosTransactions 
                WHERE Terminal_ID = ? 
                AND Transaction_Date = ? 
                AND BankID = ?
            ''', (terminal_id, date, bank_id))
            
            result = self.cursor.fetchone()
            return result[0] if result[0] is not None else 0.0
            
        except Exception as e:
            logger.error(f"خطا در محاسبه مجموع پوز: {str(e)}")
            return 0.0
        finally:
            self.disconnect()
    
    def get_pos_transactions_for_date(self, terminal_id: str, date: str, bank_id: int) -> List[Dict[str, Any]]:
        """
        دریافت تراکنش‌های پوز برای تاریخ مشخص
        
        پارامترها:
            terminal_id: شناسه ترمینال
            date: تاریخ (فرمت YYYY/MM/DD)
            bank_id: شناسه بانک
            
        خروجی:
            لیست تراکنش‌های پوز
        """
        try:
            self.connect()
            
            self.cursor.execute('''
                SELECT * FROM PosTransactions 
                WHERE Terminal_ID = ? 
                AND Transaction_Date = ? 
                AND BankID = ? 
                AND is_reconciled = 0
                ORDER BY id
            ''', (terminal_id, date, bank_id))
            
            columns = [desc[0] for desc in self.cursor.description]
            result = [dict(zip(columns, row)) for row in self.cursor.fetchall()]
            
            return result
            
        except Exception as e:
            logger.error(f"خطا در دریافت تراکنش‌های پوز برای تاریخ: {str(e)}")
            return []
        finally:
            self.disconnect()
    
    def reconcile_all_pos_for_date(self, terminal_id: str, date: str, bank_id: int) -> bool:
        """
        علامت‌گذاری همه تراکنش‌های پوز برای تاریخ مشخص به عنوان مغایرت‌گیری شده
        
        پارامترها:
            terminal_id: شناسه ترمینال
            date: تاریخ (فرمت YYYY/MM/DD)
            bank_id: شناسه بانک
            
        خروجی:
            True در صورت موفقیت
        """
        try:
            self.connect()
            
            self.cursor.execute('''
                UPDATE PosTransactions 
                SET is_reconciled = 1 
                WHERE Terminal_ID = ? 
                AND Transaction_Date = ? 
                AND BankID = ?
            ''', (terminal_id, date, bank_id))
            
            self.connection.commit()
            
            logger.info(f"همه تراکنش‌های پوز برای تاریخ {date} علامت‌گذاری شدند")
            return True
            
        except Exception as e:
            logger.error(f"خطا در علامت‌گذاری تراکنش‌های پوز: {str(e)}")
            return False
        finally:
            self.disconnect()
    
    def get_reconciliation_summary_data(self) -> List[Dict[str, Any]]:
        """
        دریافت آمار مغایرت‌گیری به صورت لیست برای نمایش در جدول
        
        خروجی:
            لیستی از دیکشنری‌های حاوی آمار مغایرت‌گیری
        """
        try:
            stats = self.get_reconciliation_statistics()
            
            summary_data = [
                {
                    'record_type': 'تراکنش‌های بانکی',
                    'total_count': stats.get('total_bank', 0),
                    'reconciled_count': stats.get('reconciled_bank', 0),
                    'unreconciled_count': stats.get('unreconciled_bank', 0),
                    'reconciliation_percentage': f"{stats.get('reconciled_bank', 0) / stats.get('total_bank', 1) * 100:.1f}%" if stats.get('total_bank', 0) > 0 else "0%"
                },
                {
                    'record_type': 'تراکنش‌های پوز',
                    'total_count': stats.get('total_pos', 0),
                    'reconciled_count': stats.get('reconciled_pos', 0),
                    'unreconciled_count': stats.get('unreconciled_pos', 0),
                    'reconciliation_percentage': f"{stats.get('reconciled_pos', 0) / stats.get('total_pos', 1) * 100:.1f}%" if stats.get('total_pos', 0) > 0 else "0%"
                },
                {
                    'record_type': 'ورودی‌های حسابداری',
                    'total_count': stats.get('total_accounting', 0),
                    'reconciled_count': stats.get('reconciled_accounting', 0),
                    'unreconciled_count': stats.get('unreconciled_accounting', 0),
                    'reconciliation_percentage': f"{stats.get('reconciled_accounting', 0) / stats.get('total_accounting', 1) * 100:.1f}%" if stats.get('total_accounting', 0) > 0 else "0%"
                }
            ]
            
            return summary_data
            
        except Exception as e:
            logger.error(f"خطا در دریافت آمار خلاصه مغایرت‌گیری: {str(e)}")
            return []