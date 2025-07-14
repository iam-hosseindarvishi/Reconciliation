#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
ماژول بارگذاری داده‌ها
این ماژول مسئول خواندن و پردازش فایل‌های اکسل بانک، پوز و حسابداری است.
"""

import os
import pandas as pd
from typing import Dict, List, Optional, Tuple
import re
from datetime import datetime, timedelta

from modules.logger import get_logger
from modules.database_manager import DatabaseManager

# ایجاد شیء لاگر
logger = get_logger(__name__)


class DataLoader:
    """
    کلاس اصلی برای بارگذاری داده‌ها از فایل‌های اکسل
    """
    
    def __init__(self):
        """
        مقداردهی اولیه کلاس DataLoader
        """
        self.bank_data = None
        self.pos_data = None
        self.accounting_data = None
        self.db_manager = DatabaseManager()
        
    def load_bank_data(self, file_path: str) -> List[Dict]:
        """
        بارگذاری داده‌های بانک از فایل اکسل و تبدیل به لیست دیکشنری
        
        پارامترها:
            file_path: مسیر فایل اکسل بانک
            
        خروجی:
            لیست دیکشنری‌های حاوی داده‌های بانک
        """
        df = self.load_bank_file(file_path)
        if df is not None and not df.empty:
            # تبدیل دیتافریم به لیست دیکشنری
            return df.to_dict('records')
        return []
    
    def load_pos_data(self, folder_path: str) -> List[Dict]:
        """
        بارگذاری داده‌های پوز از پوشه فایل‌های اکسل و تبدیل به لیست دیکشنری
        
        پارامترها:
            folder_path: مسیر پوشه حاوی فایل‌های اکسل پوز
            
        خروجی:
            لیست دیکشنری‌های حاوی داده‌های پوز
        """
        df = self.load_pos_files(folder_path)
        if df is not None and not df.empty:
            # تبدیل دیتافریم به لیست دیکشنری
            return df.to_dict('records')
        return []
    
    def load_accounting_data(self, file_path: str) -> List[Dict]:
        """
        بارگذاری داده‌های حسابداری از فایل اکسل و تبدیل به لیست دیکشنری
        
        پارامترها:
            file_path: مسیر فایل اکسل حسابداری
            
        خروجی:
            لیست دیکشنری‌های حاوی داده‌های حسابداری
        """
        df = self.load_accounting_file(file_path)
        if df is not None and not df.empty:
            # تبدیل دیتافریم به لیست دیکشنری
            return df.to_dict('records')
        return []
    
    def load_bank_file(self, file_path: str) -> pd.DataFrame:
        """
        بارگذاری فایل اکسل بانک و استخراج اطلاعات مورد نیاز
        
        پارامترها:
            file_path: مسیر فایل اکسل بانک
            
        خروجی:
            دیتافریم پانداس حاوی داده‌های پردازش شده بانک
        """
        try:
            logger.info(f"بارگذاری فایل بانک: {file_path}")
            # خواندن فایل اکسل بانک
            df = pd.read_excel(file_path)
            
            # نگاشت نام ستون‌ها
            column_mapping = {
                'توضیحات': 'Description_Bank',
                'واریز کننده/دریافت کننده': 'Payer_Receiver',
                'پیگیری': 'Bank_Tracking_ID',
                'پیگیری واریز': 'Shaparak_Deposit_Tracking_ID_Raw',
                'مانده': 'Balance',
                'واریز': 'Deposit_Amount',
                'برداشت': 'Withdrawal_Amount',
                'شعبه': 'Branch_Code',
                'زمان': 'Time',
                'تاریخ': 'Date'
            }
            
            # تغییر نام ستون‌ها
            df = df.rename(columns=column_mapping)
            

            # استخراج شناسه ترمینال شاپرک
            df['Extracted_Shaparak_Terminal_ID'] = df.apply(
                lambda row: self._extract_terminal_id(row) if row['Payer_Receiver'] == "مرکزشاپرک" else None, 
                axis=1
            )
            
            # تعیین نوع تراکنش بانک
            df['Transaction_Type_Bank'] = df.apply(self._determine_bank_transaction_type, axis=1)
            
            # افزودن ستون وضعیت مغایرت‌گیری
            df['is_reconciled'] = False
            
            self.bank_data = df
            logger.info(f"فایل بانک با موفقیت بارگذاری شد. تعداد رکوردها: {len(df)}")
            return df
            
        except Exception as e:
            logger.error(f"خطا در بارگذاری فایل بانک: {str(e)}")
            raise
    
    def load_pos_files(self, folder_path: str) -> pd.DataFrame:
        """
        بارگذاری فایل‌های اکسل پوز از یک پوشه و استخراج اطلاعات مورد نیاز
        
        پارامترها:
            folder_path: مسیر پوشه حاوی فایل‌های اکسل پوز
            
        خروجی:
            دیتافریم پانداس حاوی داده‌های پردازش شده پوز
        """
        try:
            logger.info(f"بارگذاری فایل‌های پوز از پوشه: {folder_path}")
            all_dfs = []
            
            # بررسی تمام فایل‌های xlsx در پوشه
            for file in os.listdir(folder_path):
                if file.endswith('.xlsx'):
                    file_path = os.path.join(folder_path, file)
                    logger.info(f"بارگذاری فایل پوز: {file}")
                    
                    # خواندن فایل اکسل پوز
                    df = pd.read_excel(file_path)
                    logger.info(f"ستون‌های فایل '{file}': {df.columns.tolist()}")
                    logger.info(f"تعداد ردیف‌ها در فایل '{file}': {len(df)}")
                    
                    # نگاشت نام ستون‌ها
                    column_mapping = {
                        'ردیف': 'Row_ID',
                        'شناسه شعبه مشتری': 'Terminal_ID',
                        'شناسه پایانه': 'Terminal_Identifier',
                        'شماره پیگیری': 'Pos_Tracking_Number',
                        # 'شماره مرجع': 'Reference_Number',
                        'شماره کارت': 'Card_Number',
                        'نام شعبه مشتری': 'Terminal_Name',
                        'نوع تراکنش': 'Transaction_Type',
                        'مبلغ تراکنش': 'Transaction_Amount',
                        'زمان درخواست تراکنش': 'Transaction_Time',
                        'تاریخ تراکنش': 'Transaction_Date',
                        'تاریخ تایید تراکنش': 'Approval_Date',
                        'شماره درخواست': 'Request_Number',
                        'وضعیت تراکنش': 'Transaction_Status'
                    }

                    # تغییر نام ستون‌ها
                    df = df.rename(columns=column_mapping)

                    # # فیلتر کردن فقط تراکنش‌های خرید
                    # df = df[df['Transaction_Type'] == "خرید"]
                    
                    # افزودن به لیست دیتافریم‌ها
                    all_dfs.append(df)
            
            # ترکیب تمام دیتافریم‌ها
            if all_dfs:
                combined_df = pd.concat(all_dfs, ignore_index=True)
                
                # افزودن ستون وضعیت مغایرت‌گیری
                combined_df['is_reconciled'] = False
                
                self.pos_data = combined_df
                logger.info(f"فایل‌های پوز با موفقیت بارگذاری شدند. تعداد رکوردها: {len(combined_df)}")
                return combined_df
            else:
                logger.warning("هیچ فایل پوز معتبری یافت نشد.")
                return pd.DataFrame()
                
        except Exception as e:
            logger.error(f"خطا در بارگذاری فایل‌های پوز: {str(e)}")
            raise
    
    def load_accounting_file(self, file_path: str) -> pd.DataFrame:
        """
        بارگذاری فایل اکسل حسابداری و استخراج اطلاعات مورد نیاز
        
        پارامترها:
            file_path: مسیر فایل اکسل حسابداری
            
        خروجی:
            دیتافریم پانداس حاوی داده‌های پردازش شده حسابداری
        """
        try:
            logger.info(f"بارگذاری فایل حسابداری: {file_path}")
            df = pd.read_excel(file_path, engine='xlrd')
            logger.info(f"ستون‌های فایل حسابداری: {df.columns.tolist()}")
            

            
            # نگاشت نام ستون‌ها
            column_mapping = {
                'نوع': 'Entry_Type_Acc',
                'شماره': 'Account_Reference_Suffix',
                'Debit': 'Debit',
                'Credit': 'Credit',
                'تاريخ سررسيد': 'Description_Notes_Acc',
                'TotalRemainAmnt': 'Total_Remain_Amnt',
                'totmergedpersonsName': 'Person_Name',
                'chqSTdate': 'Check_Date',
                'chqSTdate_1': 'Due_Date',
                # 'کد نوع چک': 'Cheque_Status_Description'
            }
            
            # تغییر نام ستون‌ها
            df = df.rename(columns=column_mapping)
            
            # استخراج پسوند کارت از توضیحات
            df['Extracted_Card_Suffix_Acc'] = df['Description_Notes_Acc'].apply(
                lambda x: self._extract_card_suffix(x) if isinstance(x, str) else None
            )
            
            # افزودن ستون وضعیت مغایرت‌گیری
            df['is_reconciled'] = False
            
            self.accounting_data = df
            logger.info(f"فایل حسابداری با موفقیت بارگذاری شد. تعداد رکوردها: {len(df)}")
            return df
            
        except Exception as e:
            logger.error(f"خطا در بارگذاری فایل حسابداری: {str(e)}")
            raise
    
    def _extract_terminal_id(self, row) -> Optional[str]:
        """
        استخراج شناسه ترمینال شاپرک از شناسه پیگیری واریز
        
        پارامترها:
            row: سطر دیتافریم
            
        خروجی:
            شناسه ترمینال استخراج شده یا None
        """
        try:
            tracking_id = str(row['Shaparak_Deposit_Tracking_ID_Raw'])
            # استخراج 7 رقم بعد از صفرهای ابتدایی
            match = re.search(r'0{3,}([0-9]{7})', tracking_id)
            if match:
                print(match.group(1))
                return match.group(1)
            return None
        except:
            return None
    
    def _determine_bank_transaction_type(self, row) -> str:
        """
        تعیین نوع تراکنش بانک
        
        پارامترها:
            row: سطر دیتافریم
            
        خروجی:
            نوع تراکنش (واریز پوز، انتقال دریافتی، انتقال پرداختی، چک دریافتی، چک پرداختی، سایر)
        """
        description = str(row.get('Description_Bank', '')).lower()
        payer_receiver = str(row.get('Payer_Receiver', '')).lower()
        
        # تشخیص واریز پوز
        if payer_receiver == "مرکز شاپرک" and pd.notna(row.get('Deposit_Amount')):
            return "POS Deposit"
        
        # تشخیص انتقال
        if "انتقال" in description or "حواله" in description:
            if pd.notna(row.get('Deposit_Amount')):
                return "Received Transfer"
            elif pd.notna(row.get('Withdrawal_Amount')):
                return "Paid Transfer"
        
        # تشخیص چک
        if "چک" in description:
            if pd.notna(row.get('Deposit_Amount')):
                return "Received Check"
            elif pd.notna(row.get('Withdrawal_Amount')):
                return "Paid Check"
        
        # سایر موارد
        return "Other"
    
    def _extract_card_suffix(self, description: str) -> Optional[str]:
        """
        استخراج 4 رقم آخر کارت از توضیحات
        
        پارامترها:
            description: متن توضیحات
            
        خروجی:
            4 رقم آخر کارت یا None
        """
        if not description or not isinstance(description, str):
            return None
            
        # استخراج 4 رقم بعد از "ک"
        match = re.search(r'ک\s*(\d{4})', description)
        if match:
            return match.group(1)
        return None