import logging
from database.reconciliation.reconciliation_repository import (
    has_unreconciled_transactions,
    get_unknown_transactions_by_bank
)
from database.reconciliation.reconciliation_repository import get_categorized_unreconciled_transactions
from reconciliation.unknown_transactions_dialog import UnknownTransactionsDialog
from reconciliation.mellat_reconciliation import reconcile_mellat_pos
from reconciliation.mellat_reconciliation.mellat_received_transfer_reconciliation import reconcile_mellat_received_transfer
from reconciliation.mellat_reconciliation.mellat_paid_transfer_reconciliation import reconcile_mellat_paid_transfer
from utils.logger_config import setup_logger
from utils.constants import KESHAVARZI_TRANSACTION_TYPES, MELLAT_BANK
# راه‌اندازی لاگر
logger = setup_logger('reconciliation.reconciliation_logic')

class ReconciliationProcess:
    """کلاس اصلی برای مدیریت فرآیند مغایرت‌گیری"""
    
    def __init__(self, parent, bank_id, bank_name, ui_handler, manual_reconciliation_queue):
        """مقداردهی اولیه
        
        Args:
            parent: پنجره والد برای نمایش دیالوگ‌ها
            bank_id: شناسه بانک
            bank_name: نام بانک
            ui_handler: شیء برای مدیریت رابط کاربری (نوارهای پیشرفت، وضعیت و لاگ)
            manual_reconciliation_queue: صف برای ارتباط بین تردها
        """
        self.parent = parent
        self.bank_id = bank_id
        self.bank_name = bank_name
        self.ui = ui_handler
        self.manual_reconciliation_queue = manual_reconciliation_queue
    
    def start(self):
        """شروع فرآیند مغایرت‌گیری"""
        try:
            # بررسی وضعیت نمایش مغایرت‌گیری دستی
            from utils import ui_state
            show_manual_reconciliation = ui_state.get_show_manual_reconciliation()
            
            # گام 1: بررسی وجود تراکنش‌های مغایرت‌گیری نشده
            self.ui.update_status("در حال بررسی تراکنش‌های مغایرت‌گیری نشده...")
            self.ui.update_progress(10)
            
            if not has_unreconciled_transactions(self.bank_id):
                self.ui.log_error("هیچ تراکنش مغایرت‌گیری نشده‌ای برای این بانک وجود ندارد")
                self.ui.update_status("فرآیند مغایرت‌گیری به پایان رسید - تراکنشی یافت نشد")
                self.ui.update_progress(100)
                return False
            
            # گام 2: بررسی و دسته‌بندی تراکنش‌های نامشخص
            self.ui.update_status("در حال بررسی تراکنش‌های نامشخص...")
            self.ui.update_detailed_status("دریافت تراکنش‌های نامشخص از دیتابیس...")
            self.ui.update_detailed_progress(20)
            
            unknown_transactions = get_unknown_transactions_by_bank(self.bank_id)
            
            if unknown_transactions:
                self.ui.log_info(f"{len(unknown_transactions)} تراکنش نامشخص یافت شد")
                self.ui.update_detailed_status("در حال نمایش دیالوگ دسته‌بندی تراکنش‌های نامشخص...")
                
                # نمایش دیالوگ دسته‌بندی تراکنش‌های نامشخص
                dialog = UnknownTransactionsDialog(
                    self.parent,
                    self.bank_id,
                    self.bank_name,
                    unknown_transactions
                )
                
                # اگر کاربر دیالوگ را لغو کرد، فرآیند را متوقف کن
                if not dialog.result:
                    self.ui.log_warning("فرآیند مغایرت‌گیری توسط کاربر لغو شد")
                    self.ui.update_status("فرآیند مغایرت‌گیری لغو شد")
                    return False
                
                # بررسی مجدد تراکنش‌های نامشخص
                unknown_transactions = get_unknown_transactions_by_bank(self.bank_id)
                if unknown_transactions:
                    self.ui.log_warning(f"هنوز {len(unknown_transactions)} تراکنش نامشخص وجود دارد")
                    self.ui.update_status("فرآیند مغایرت‌گیری به دلیل وجود تراکنش‌های نامشخص متوقف شد")
                    return False
            
            # گام 3: دریافت تراکنش‌های دسته‌بندی شده
            self.ui.update_status("در حال دریافت تراکنش‌های دسته‌بندی شده...")
            self.ui.update_detailed_status("دریافت تراکنش‌ها از دیتابیس...")
            self.ui.update_detailed_progress(40)
            
            categorized_transactions = get_categorized_unreconciled_transactions(self.bank_id)
            
            # گام 4: انجام فرآیند مغایرت‌گیری
            self.ui.update_status("در حال انجام فرآیند مغایرت‌گیری...")
            self.ui.update_progress(50)
            
            # اینجا منطق اصلی مغایرت‌گیری پیاده‌سازی می‌شود
            # برای هر نوع تراکنش، فرآیند مغایرت‌گیری متفاوتی انجام می‌شود
            
            # به عنوان مثال، برای تراکنش‌های POS
            # به عنوان مثال، برای تراکنش\u200cهای POS
            # به عنوان مثال، برای تراکنش‌های POS
            if KESHAVARZI_TRANSACTION_TYPES['RECEIVED_POS'] in categorized_transactions:
                
                if self.bank_id == MELLAT_BANK['id']:  # ID for Mellat Bank
                    self.ui.update_detailed_status("در حال مغایرت‌گیری تراکنش‌های POS بانک ملت...")
                    self.ui.update_detailed_progress(60)
                    # فقط اگر چک‌باکس مغایرت‌گیری دستی فعال باشد، از صف استفاده می‌کنیم
                    from utils import ui_state
                    if ui_state.get_show_manual_reconciliation():
                        reconcile_mellat_pos(categorized_transactions[KESHAVARZI_TRANSACTION_TYPES['RECEIVED_POS']], self.ui, self.manual_reconciliation_queue)
                    else:
                        # اجرای مغایرت‌گیری بدون استفاده از صف مغایرت‌گیری دستی
                        reconcile_mellat_pos(categorized_transactions[KESHAVARZI_TRANSACTION_TYPES['RECEIVED_POS']], self.ui, None)
                else:
                    self.ui.update_detailed_status("در حال مغایرت‌گیری تراکنش‌های POS...")
                    self.ui.update_detailed_progress(60)
                    self.reconcile_pos_transactions(categorized_transactions[KESHAVARZI_TRANSACTION_TYPES['RECEIVED_POS']])
                self.ui.update_detailed_status("در حال مغایرت\u200cگیری تراکنش\u200cهای POS...")
                
                self.ui.update_detailed_progress(60)
            
            # برای تراکنش‌های چک
            if KESHAVARZI_TRANSACTION_TYPES['RECEIVED_CHECK'] in categorized_transactions:
                self.ui.update_detailed_status("در حال مغایرت‌گیری تراکنش‌های چک دریافتی...")
                self.ui.update_detailed_progress(70)
            
            if KESHAVARZI_TRANSACTION_TYPES['PAID_CHECK'] in categorized_transactions:
                self.ui.update_detailed_status("در حال مغایرت‌گیری تراکنش‌های چک پرداختی...")
                self.ui.update_detailed_progress(80)
            
            # برای تراکنش‌های انتقال
            if KESHAVARZI_TRANSACTION_TYPES['RECEIVED_TRANSFER'] in categorized_transactions:
                self.ui.update_detailed_status("در حال مغایرت‌گیری تراکنش‌های انتقال دریافتی...")
                self.ui.update_detailed_progress(85)
                if(self.bank_id == MELLAT_BANK['id']):
                    # بررسی وضعیت چک‌باکس مغایرت‌گیری دستی
                    from utils import ui_state
                    if ui_state.get_show_manual_reconciliation():
                        reconcile_mellat_received_transfer(categorized_transactions[KESHAVARZI_TRANSACTION_TYPES['RECEIVED_TRANSFER']], self.ui, self.manual_reconciliation_queue)
                    else:
                        # اجرای مغایرت‌گیری بدون استفاده از صف مغایرت‌گیری دستی
                        reconcile_mellat_received_transfer(categorized_transactions[KESHAVARZI_TRANSACTION_TYPES['RECEIVED_TRANSFER']], self.ui, None)
            
            if KESHAVARZI_TRANSACTION_TYPES['PAID_TRANSFER'] in categorized_transactions:
                self.ui.update_detailed_status("در حال مغایرت‌گیری تراکنش‌های انتقال پرداختی...")
                self.ui.update_detailed_progress(90)
                if(self.bank_id == MELLAT_BANK['id']):
                    # بررسی وضعیت چک‌باکس مغایرت‌گیری دستی
                    from utils import ui_state
                    if ui_state.get_show_manual_reconciliation():
                        reconcile_mellat_paid_transfer(categorized_transactions[KESHAVARZI_TRANSACTION_TYPES['PAID_TRANSFER']], self.ui, self.manual_reconciliation_queue)
                    else:
                        # اجرای مغایرت‌گیری بدون استفاده از صف مغایرت‌گیری دستی
                        reconcile_mellat_paid_transfer(categorized_transactions[KESHAVARZI_TRANSACTION_TYPES['PAID_TRANSFER']], self.ui, None)
            
            # برای کارمزدهای بانکی
            if KESHAVARZI_TRANSACTION_TYPES['BANK_FEES'] in categorized_transactions:
                self.ui.update_detailed_status("در حال مغایرت‌گیری کارمزدهای بانکی...")
                self.ui.update_detailed_progress(95)
                self.reconcile_bank_fees(categorized_transactions[KESHAVARZI_TRANSACTION_TYPES['BANK_FEES']])
            
            # گام 5: تولید گزارش
            self.ui.update_status("در حال تولید گزارش مغایرت‌گیری...")
            self.ui.update_detailed_status("ایجاد گزارش نهایی...")
            self.ui.update_detailed_progress(100)
            self.ui.update_progress(100)
            
            self.ui.log_info("فرآیند مغایرت‌گیری با موفقیت به پایان رسید")
            self.ui.update_status("فرآیند مغایرت‌گیری با موفقیت به پایان رسید")
            
            return True
            
        except Exception as e:
            logger.error(f"خطا در فرآیند مغایرت‌گیری: {str(e)}")
            self.ui.log_error(f"خطا در فرآیند مغایرت‌گیری: {str(e)}")
            self.ui.update_status("فرآیند مغایرت‌گیری با خطا مواجه شد")
            return False
    
    
    def reconcile_bank_fees(self, transactions):
        """مغایرت‌گیری کارمزدهای بانکی"""
        # پیاده‌سازی منطق مغایرت‌گیری کارمزدهای بانکی
        self.ui.log_info(f"مغایرت‌گیری {len(transactions)} تراکنش کارمزد بانکی")
        # در اینجا منطق اصلی مغایرت‌گیری کارمزدهای بانکی پیاده‌سازی می‌شود