"""
Reconciliation Operations Module
ماژول عملیات مغایرت‌گیری - جدا شده از manual_reconciliation_tab.py
"""
import logging
import decimal
from tkinter import messagebox
from reconciliation.save_reconciliation_result import success_reconciliation_result
from database.bank_transaction_repository import update_bank_transaction_reconciliation_status
from database.repositories.accounting import update_accounting_transaction_reconciliation_status
from database.Helper.db_helpers import deduct_fee


class ReconciliationOperations:
    """کلاس عملیات مغایرت‌گیری"""
    
    def __init__(self, logger=None):
        self.logger = logger or logging.getLogger(__name__)
    
    def quick_reconcile(self, bank_record_id, accounting_record_id):
        """
        مغایرت‌گیری سریع بین رکورد بانک و رکورد حسابداری
        
        Args:
            bank_record_id: شناسه رکورد بانک
            accounting_record_id: شناسه رکورد حسابداری
            
        Returns:
            bool: موفقیت عملیات
        """
        try:
            if not bank_record_id or not accounting_record_id:
                raise ValueError("شناسه رکورد بانک و حسابداری الزامی است")
            
            # تأیید از کاربر
            confirm = messagebox.askyesno(
                "تأیید مغایرت‌گیری", 
                "آیا از مغایرت‌گیری این دو رکورد اطمینان دارید؟"
            )
            
            if not confirm:
                return False
            
            try:
                # ابتدا وضعیت is_reconciled را به‌روزرسانی کنیم
                update_bank_transaction_reconciliation_status(bank_record_id, 1)
                update_accounting_transaction_reconciliation_status(accounting_record_id, 1)
                
                # سپس نتیجه مغایرت‌گیری را ثبت کنیم
                success_reconciliation_result(
                    bank_record_id,  # bank_record_id
                    accounting_record_id,  # acc_record_id
                    None,  # pos_record_id
                    "مغایرت‌گیری دستی از طریق تب مغایرت‌یابی دستی",
                    'manual_match'
                )
                
                messagebox.showinfo("اطلاعات", "مغایرت‌گیری با موفقیت انجام شد")
                self.logger.info(f"مغایرت‌گیری بین رکورد بانک {bank_record_id} و رکورد حسابداری {accounting_record_id} انجام شد")
                
                return True
                
            except Exception as update_error:
                self.logger.error(f"خطا در به‌روزرسانی وضعیت مغایرت‌یابی: {str(update_error)}")
                messagebox.showerror("خطا", f"خطا در به‌روزرسانی وضعیت مغایرت‌یابی: {str(update_error)}")
                return False
                
        except Exception as e:
            error_message = f"خطا در مغایرت‌گیری سریع: {str(e)}"
            self.logger.error(error_message)
            messagebox.showerror("خطا", error_message)
            return False
    
    def deduct_fee_and_reconcile(self, bank_record, accounting_record):
        """
        کسر کارمزد از مبلغ رکورد بانک و انجام مغایرت‌گیری
        
        Args:
            bank_record: رکورد بانک
            accounting_record: رکورد حسابداری
            
        Returns:
            bool: موفقیت عملیات
        """
        try:
            if not bank_record or not accounting_record:
                raise ValueError("رکوردهای بانک و حسابداری الزامی هستند")
            
            bank_id = bank_record['id']
            accounting_id = accounting_record['id']
            
            # محاسبه کارمزد (تفاوت بین مبلغ بانک و مبلغ حسابداری)
            bank_amount = decimal.Decimal(str(bank_record['amount']))
            accounting_amount = decimal.Decimal(str(accounting_record['transaction_amount']))
            
            # اگر مبلغ بانک کوچکتر از مبلغ حسابداری باشد، کارمزد قابل محاسبه نیست
            if bank_amount < accounting_amount:
                messagebox.showwarning(
                    "هشدار", 
                    "مبلغ رکورد بانک باید بزرگتر یا مساوی مبلغ حسابداری باشد تا بتوان کارمزد را محاسبه کرد"
                )
                return False
            
            fee_amount = bank_amount - accounting_amount
            
            # نمایش پیغام تأیید
            confirm = messagebox.askyesno(
                "تأیید کسر کارمزد", 
                f"آیا از کسر کارمزد به مبلغ {fee_amount:,} از مبلغ اصلی اطمینان دارید؟\n" +
                f"مبلغ بانک: {bank_amount:,}\n" +
                f"مبلغ حسابداری: {accounting_amount:,}\n" +
                f"مبلغ کارمزد: {fee_amount:,}"
            )
            
            if not confirm:
                return False
            
            try:
                # کسر کارمزد از مبلغ تراکنش و ایجاد رکورد جدید برای کارمزد
                updated_bank_id, fee_record_id = deduct_fee(
                    bank_id,
                    float(bank_amount),
                    float(fee_amount),
                    f"کارمزد برای رکورد {bank_id}"
                )
                
                if updated_bank_id and fee_record_id:
                    # ثبت مغایرت‌گیری با کارمزد با استفاده از success_reconciliation_result
                    success_reconciliation_result(
                        updated_bank_id,  # bank_record_id
                        accounting_id,  # acc_record_id
                        None,  # pos_record_id
                        f"مغایرت‌گیری دستی با کسر کارمزد به مبلغ {fee_amount:,} ریال",
                        'manual_match_with_fee'
                    )
                    
                    messagebox.showinfo("اطلاعات", "مغایرت‌گیری با کسر کارمزد با موفقیت انجام شد")
                    self.logger.info(f"مغایرت‌گیری با کسر کارمزد {fee_amount} بین رکورد بانک {bank_id} و رکورد حسابداری {accounting_id} انجام شد")
                    
                    return True
                else:
                    messagebox.showerror("خطا", "خطا در کسر کارمزد از تراکنش بانکی")
                    return False
                    
            except Exception as e:
                messagebox.showerror("خطا", f"خطا در کسر کارمزد: {str(e)}")
                self.logger.error(f"خطا در کسر کارمزد: {str(e)}")
                return False
                
        except Exception as e:
            error_message = f"خطا در کسر کارمزد: {str(e)}"
            self.logger.error(error_message)
            messagebox.showerror("خطا", error_message)
            return False
    
    def validate_reconciliation_data(self, bank_record, accounting_record):
        """
        اعتبارسنجی داده‌های مورد نیاز برای مغایرت‌گیری
        
        Args:
            bank_record: رکورد بانک
            accounting_record: رکورد حسابداری
            
        Returns:
            tuple: (bool, str) - نتیجه اعتبارسنجی و پیام خطا
        """
        try:
            if not bank_record:
                return False, "رکورد بانک انتخاب نشده است"
            
            if not accounting_record:
                return False, "رکورد حسابداری انتخاب نشده است"
            
            # بررسی وجود فیلدهای ضروری
            required_bank_fields = ['id', 'amount']
            required_accounting_fields = ['id', 'transaction_amount']
            
            for field in required_bank_fields:
                if field not in bank_record or bank_record[field] is None:
                    return False, f"فیلد {field} در رکورد بانک موجود نیست"
            
            for field in required_accounting_fields:
                if field not in accounting_record or accounting_record[field] is None:
                    return False, f"فیلد {field} در رکورد حسابداری موجود نیست"
            
            # بررسی صحت مبالغ
            try:
                bank_amount = decimal.Decimal(str(bank_record['amount']))
                accounting_amount = decimal.Decimal(str(accounting_record['transaction_amount']))
                
                if bank_amount <= 0:
                    return False, "مبلغ رکورد بانک باید مثبت باشد"
                
                if accounting_amount <= 0:
                    return False, "مبلغ رکورد حسابداری باید مثبت باشد"
                    
            except (ValueError, decimal.InvalidOperation):
                return False, "مبالغ وارد شده نامعتبر هستند"
            
            return True, "داده‌ها معتبر هستند"
            
        except Exception as e:
            return False, f"خطا در اعتبارسنجی: {str(e)}"
    
    def get_reconciliation_summary(self, bank_record, accounting_record):
        """
        دریافت خلاصه‌ای از عملیات مغایرت‌گیری
        
        Args:
            bank_record: رکورد بانک
            accounting_record: رکورد حسابداری
            
        Returns:
            dict: خلاصه عملیات
        """
        try:
            if not bank_record or not accounting_record:
                return {}
            
            bank_amount = decimal.Decimal(str(bank_record['amount']))
            accounting_amount = decimal.Decimal(str(accounting_record['transaction_amount']))
            
            difference = bank_amount - accounting_amount
            
            summary = {
                'bank_id': bank_record['id'],
                'accounting_id': accounting_record['id'],
                'bank_amount': float(bank_amount),
                'accounting_amount': float(accounting_amount),
                'difference': float(difference),
                'has_fee': difference > 0,
                'fee_amount': float(difference) if difference > 0 else 0,
                'can_reconcile': True,
                'reconciliation_type': 'with_fee' if difference > 0 else 'direct'
            }
            
            return summary
            
        except Exception as e:
            self.logger.error(f"خطا در تولید خلاصه مغایرت‌گیری: {str(e)}")
            return {}
    
    def suggest_reconciliation_action(self, bank_record, accounting_record):
        """
        پیشنهاد نوع عملیات مغایرت‌گیری بر اساس داده‌ها
        
        Args:
            bank_record: رکورد بانک
            accounting_record: رکورد حسابداری
            
        Returns:
            str: نوع عملیات پیشنهادی
        """
        try:
            summary = self.get_reconciliation_summary(bank_record, accounting_record)
            
            if not summary:
                return "unknown"
            
            if summary['difference'] == 0:
                return "direct_match"  # مطابقت مستقیم
            elif summary['difference'] > 0:
                return "match_with_fee"  # مطابقت با کسر کارمزد
            else:
                return "amount_mismatch"  # عدم تطبیق مبلغ
                
        except Exception as e:
            self.logger.error(f"خطا در پیشنهاد عملیات مغایرت‌گیری: {str(e)}")
            return "unknown"
