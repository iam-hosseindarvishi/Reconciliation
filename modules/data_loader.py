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
            # خواندن فایل اکسل بانک با engine مناسب
            engine = 'xlrd' if file_path.endswith('.xls') else 'openpyxl'
            df = pd.read_excel(file_path, engine=engine)
            
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
            
            # استخراج شماره پیگیری سوئیچ
            df['Extracted_Switch_Tracking_ID'] = df['Description_Bank'].apply(
                lambda x: self._extract_switch_tracking_id(x)
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
            
            # بررسی تمام فایل‌های اکسل در پوشه
            for file in os.listdir(folder_path):
                if file.endswith(('.xlsx', '.xls')):
                    file_path = os.path.join(folder_path, file)
                    logger.info(f"بارگذاری فایل پوز: {file}")
                    
                    # خواندن فایل اکسل پوز با engine مناسب
                    engine = 'xlrd' if file_path.endswith('.xls') else 'openpyxl'
                    df = pd.read_excel(file_path, engine=engine)
                    logger.info(f"ستون‌های فایل '{file}': {df.columns.tolist()}")
                    logger.info(f"تعداد ردیف‌ها در فایل '{file}': {len(df)}")
                    
                    # بررسی وجود ستون شماره پیگیری
                    if 'شماره پیگیری' not in df.columns:
                        logger.warning(f"ستون 'شماره پیگیری' در فایل '{file}' یافت نشد. این ستون برای مغایرت‌گیری ضروری است.")
                        logger.info(f"ستون‌های موجود در فایل: {df.columns.tolist()}")
                    
                    # نگاشت نام ستون‌ها
                    column_mapping = {
                        'ردیف': 'Row_ID',
                        'شناسه شعبه مشتری': 'Terminal_ID',
                        'شناسه پایانه': 'Terminal_Identifier',
                        'شماره پیگیری': 'POS_Tracking_Number',
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
                    
                    # اگر ستون شماره پیگیری وجود نداشت، مقدار None قرار می‌دهیم
                    if 'POS_Tracking_Number' not in df.columns:
                        df['POS_Tracking_Number'] = None
                        logger.warning(f"ستون POS_Tracking_Number برای فایل '{file}' با مقدار None ایجاد شد.")

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
            # خواندن فایل اکسل حسابداری با engine مناسب
            engine = 'xlrd' if file_path.endswith('.xls') else 'openpyxl'
            df = pd.read_excel(file_path, engine=engine)
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
        تعیین نوع تراکنش بانک بر اساس توضیحات، واریز/برداشت و واریزکننده/دریافت‌کننده.
        """
        description = str(row.get('Description_Bank', '')).lower()
        payer_receiver = str(row.get('Payer_Receiver', '')).lower()
        deposit_amount = row.get('Deposit_Amount')
        withdrawal_amount = row.get('Withdrawal_Amount')
        
        # تبدیل مقادیر به عدد برای جلوگیری از خطای مقایسه
        try:
            deposit_amount = float(deposit_amount) if pd.notna(deposit_amount) and str(deposit_amount).strip() != '' else 0
        except (ValueError, TypeError):
            deposit_amount = 0
            
        try:
            withdrawal_amount = float(withdrawal_amount) if pd.notna(withdrawal_amount) and str(withdrawal_amount).strip() != '' else 0
        except (ValueError, TypeError):
            withdrawal_amount = 0

        # 1. تشخیص واریز پوز (اولین اولویت)
        if payer_receiver == "مرکزشاپرک" and deposit_amount > 0:
            return "POS Deposit"

        # 2. تشخیص انتقال (پایا، پل، واریز انتقالی)
        transfer_keywords = ["انتقال", "حواله", "پايا", "پل","انتقالKYOS","انتقالMOB","انتقال IB", "واريز انتقالي","انتقالPAYMENT","انتقالATM"]
        is_transfer = any(keyword in description for keyword in transfer_keywords)
        if not is_transfer:
            is_transfer= 'واريزتجمعي' in description and 'نام واریز کننده:' in description
            
        if is_transfer:
            if deposit_amount > 0:
                return "Received Transfer"
            elif withdrawal_amount > 0:
                return "Paid Transfer"
        
        # 3. تشخیص چک (شامل چکاوک)
        check_keywords = ["چک", "چکاوک","وصول چكاوك","واريز انتقالي با چ","در-چک","چك انتقالي","چك"]
        is_check = any(keyword in description for keyword in check_keywords)
        
        if is_check:
            if deposit_amount > 0:
                return "Received Check"
            elif withdrawal_amount > 0:
                return "Paid Check"

        # 4. تشخیص کارمزد (Commission)
        commission_keywords=["كارمزدPOS","کارمزد"]
        if any(keyword in description for keyword in commission_keywords):
             if withdrawal_amount > 0:
                return "Bank Commission"
             elif deposit_amount > 0:
                 return "Commission Refund" # اگر کارمزد برگشت داده شده باشد

        # 5. سایر موارد
        if deposit_amount > 0:
            return "Other Deposit"
        elif withdrawal_amount > 0:
            return "Other Withdrawal"
            
        return "Other"
    
    def _extract_switch_tracking_id(self, description: str) -> Optional[str]:
        """
        استخراج شماره پیگیری سوئیچ از متن توضیحات.
        مثال: "شماره پیگیری سوئیچ: 670781" -> "670781"
        """
        if not description or not isinstance(description, str):
            return None
        
        # الگوی regex برای یافتن "شماره پیگیری سوئیچ:" و سپس 6 رقم (یا بیشتر)
        match = re.search(r'شماره پیگیری سوئیچ:\s*(\d+)', description, re.IGNORECASE)
        if match:
            return match.group(1)
        return None
    
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