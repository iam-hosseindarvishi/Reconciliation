import requests
import json
import time
import threading
from typing import Dict, List, Optional, Tuple
from queue import Queue
from utils.logger_config import setup_logger
from utils.ai_request_formatter import (
    format_pos_request,
    format_bank_transfer_request,
    format_check_request
)
from database.accounting_repository import get_accounting_by_amount_and_types, update_reconciliation_status as update_accounting_status
from database.pos_transactions_repository import update_reconciliation_status as update_pos_status
from database.bank_transaction_repository import update_bank_transaction_reconciliation_status
from database.reconciliation_results_repository import create_reconciliation_result
from database.init_db import create_connection
import sqlite3

logger = setup_logger('reconciliation.ai_matcher')

class AIMatcher:
    def __init__(self, n8n_webhook_url: str = None):
        self.n8n_webhook_url = "http://localhost:5678/webhook/reconciled"
        #self.n8n_webhook_url = "http://localhost:5678/webhook-test/reconciled"
        self.timeout = 300
        self.retry_count = 3
        self.processing_lock = threading.Lock()

    def validate_matched_id(self, matched_id, accounting_candidates: List[Dict]) -> bool:
        """تایید اینکه matched_id در لیست رکوردهای ارسالی وجود دارد"""
        valid_ids = [candidate.get('id') for candidate in accounting_candidates]
        is_valid = matched_id in valid_ids
        if not is_valid:
            logger.warning(f"matched_id {matched_id} در لیست رکوردهای صحیح یافت نشد. آیدی های صحیح: {valid_ids}")
        return is_valid

    def is_accounting_unreconciled(self, accounting_id: int) -> bool:
        """بررسی کنید که آیا رکورد حسابداری هنوز مغایرت‌نشده است (is_reconciled = 0)"""
        conn = None
        try:
            conn = create_connection()
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT is_reconciled FROM AccountingTransactions WHERE id = ?", (accounting_id,))
            result = cursor.fetchone()
            if result is None:
                logger.warning(f"رکورد حسابداری {accounting_id} در پایگاه داده یافت نشد")
                return False
            is_unreconciled = result['is_reconciled'] == 0
            if not is_unreconciled:
                logger.warning(f"رکورد حسابداری {accounting_id} قبلاً مغایرت‌یابی شده است")
            return is_unreconciled
        except Exception as e:
            logger.error(f"خطا در بررسی وضعیت رکورد حسابداری {accounting_id}: {str(e)}")
            return False
        finally:
            if conn:
                conn.close()

    def is_pos_transaction_unreconciled(self, pos_id: int) -> bool:
        """بررسی کنید که آیا تراکنش POS هنوز مغایرت‌نشده است (is_reconciled = 0)"""
        conn = None
        try:
            conn = create_connection()
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT is_reconciled FROM PosTransactions WHERE id = ?", (pos_id,))
            result = cursor.fetchone()
            if result is None:
                logger.warning(f"تراکنش POS {pos_id} در پایگاه داده یافت نشد")
                return False
            is_unreconciled = result['is_reconciled'] == 0
            if not is_unreconciled:
                logger.warning(f"تراکنش POS {pos_id} قبلاً مغایرت‌یابی شده است")
            return is_unreconciled
        except Exception as e:
            logger.error(f"خطا در بررسی وضعیت تراکنش POS {pos_id}: {str(e)}")
            return False
        finally:
            if conn:
                conn.close()

    def is_bank_transaction_unreconciled(self, bank_id: int) -> bool:
        """بررسی کنید که آیا تراکنش بانکی هنوز مغایرت‌نشده است (is_reconciled = 0)"""
        conn = None
        try:
            from config.settings import DB_PATH
            conn = sqlite3.connect(DB_PATH)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT is_reconciled FROM BankTransactions WHERE id = ?", (bank_id,))
            result = cursor.fetchone()
            if result is None:
                logger.warning(f"تراکنش بانکی {bank_id} در پایگاه داده یافت نشد")
                return False
            is_unreconciled = result['is_reconciled'] == 0
            if not is_unreconciled:
                logger.warning(f"تراکنش بانکی {bank_id} قبلاً مغایرت‌یابی شده است")
            return is_unreconciled
        except Exception as e:
            logger.error(f"خطا در بررسی وضعیت تراکنش بانکی {bank_id}: {str(e)}")
            return False
        finally:
            if conn:
                conn.close()

    def are_accounting_candidates_unreconciled(self, accounting_candidates: List[Dict]) -> bool:
        """بررسی اینکه تمامی رکوردهای حسابداری هنوز مغایرت‌نشده هستند"""
        if not accounting_candidates:
            return True
        
        for candidate in accounting_candidates:
            if not self.is_accounting_unreconciled(candidate.get('id')):
                logger.warning(f"رکورد حسابداری {candidate.get('id')} دیگر معتبر نیست")
                return False
        return True

    def send_to_ai(self, data: Dict) -> Dict:
        """ارسال داده به n8n workflow و دریافت نتیجه - منتظر پاسخ می‌ماند"""
        with self.processing_lock:
            for attempt in range(self.retry_count):
                try:
                    transaction_id = data.get('pos_record', data.get('bank_record', {})).get('id')
                    logger.info(f"ارسال تراکنش {transaction_id} به AI (تلاش {attempt + 1}/{self.retry_count})")
                    
                    response = requests.post(
                        self.n8n_webhook_url,
                        json=data,
                        headers={'Content-Type': 'application/json'},
                        timeout=self.timeout
                    )

                    if response.status_code == 200:
                        logger.info(f"پاسخ موفق از AI برای تراکنش {transaction_id}")
                        result = response.json()
                        if isinstance(result, list) and len(result) > 0:
                            return result[0]
                        return result
                    else:
                        logger.warning(f"پاسخ ناموفق از AI: HTTP {response.status_code}")
                        if attempt < self.retry_count - 1:
                            logger.info(f"منتظر 10 ثانیه قبل از تلاش مجدد...")
                            time.sleep(10)
                            continue
                        return {
                            "error": f"HTTP {response.status_code}",
                            "detail": response.text,
                            "matched": False,
                            "confidence": 0
                        }

                except requests.exceptions.Timeout:
                    logger.warning(f"Timeout در تلاش {attempt + 1}/{self.retry_count} - n8n آماده پاسخ نیست")
                    if attempt < self.retry_count - 1:
                        logger.info(f"منتظر 10 ثانیه قبل از تلاش مجدد...")
                        time.sleep(10)
                        continue
                    return {
                        "error": "Timeout",
                        "detail": "AI طول‌کشید و پاسخ نداد",
                        "matched": False,
                        "confidence": 0
                    }

                except Exception as e:
                    logger.error(f"خطا در ارتباط با AI: {str(e)}")
                    if attempt < self.retry_count - 1:
                        logger.info(f"منتظر 5 ثانیه قبل از تلاش مجدد...")
                        time.sleep(5)
                        continue
                    return {
                        "error": "Request failed",
                        "detail": str(e),
                        "matched": False,
                        "confidence": 0
                    }

            return {
                "error": "Maximum retries exceeded",
                "matched": False,
                "confidence": 0
            }

    def process_pos_transaction(self, pos_record: Dict) -> Tuple[bool, Dict]:
        """پردازش تراکنش POS"""
        try:
            if not self.is_pos_transaction_unreconciled(pos_record.get('id')):
                logger.warning(f"تراکنش POS {pos_record.get('id')} قبلاً مغایرت‌یابی شده است - نیاز به بررسی ندارد")
                return False, {
                    "type": "POS",
                    "source_id": pos_record.get('id'),
                    "matched_id": None,
                    "confidence": 0,
                    "status": "already_reconciled",
                    "reason": "تراکنش قبلاً مغایرت‌یابی شده است"
                }

            amount = pos_record.get('transaction_amount')
            accounting_candidates = get_accounting_by_amount_and_types(
                amount,
                ['Pos', 'Pos_Transfer_Received'],
                pos_record['bank_id']
            )

            if not accounting_candidates:
                logger.info(f"هیچ گزینه تطبیق برای POS {pos_record.get('id')} یافت نشد")
                return False, {
                    "type": "POS",
                    "source_id": pos_record.get('id'),
                    "matched_id": None,
                    "confidence": 0,
                    "status": "no_match",
                    "reason": "هیچ تراکنش حسابداری هم‌مبلغ یافت نشد"
                }

            if not self.are_accounting_candidates_unreconciled(accounting_candidates):
                logger.warning(f"برخی از رکوردهای حسابداری برای POS {pos_record.get('id')} قبلاً مغایرت‌یابی شده‌اند")
                return False, {
                    "type": "POS",
                    "source_id": pos_record.get('id'),
                    "matched_id": None,
                    "confidence": 0,
                    "status": "candidates_reconciled",
                    "reason": "برخی از رکوردهای حسابداری قبلاً مغایرت‌یابی شده‌اند"
                }

            ai_request = format_pos_request(pos_record, accounting_candidates)
            ai_response = self.send_to_ai(ai_request)

            if ai_response.get('error'):
                logger.error(f"خطا در پاسخ AI: {ai_response.get('error')}")
                return False, {
                    "type": "POS",
                    "source_id": pos_record.get('id'),
                    "matched_id": None,
                    "confidence": 0,
                    "status": "error",
                    "reason": f"خطا از AI: {ai_response.get('detail', 'نامشخص')}"
                }

            if ai_response.get('matched'):
                matched_id = ai_response.get('matched_accounting_id')
                
                if not self.validate_matched_id(matched_id, accounting_candidates):
                    logger.warning(f"POS {pos_record.get('id')}: matched_id {matched_id} معتبر نیست - نیاز به بررسی دستی")
                    return False, {
                        "type": "POS",
                        "source_id": pos_record.get('id'),
                        "matched_id": None,
                        "confidence": ai_response.get('confidence', 0),
                        "status": "needs_review",
                        "reason": f"matched_id {matched_id} در لیست رکوردهای صحیح یافت نشد",
                        "suggestions": ai_response.get('suggestions', [])
                    }
                
                if not self.is_accounting_unreconciled(matched_id):
                    logger.warning(f"POS {pos_record.get('id')}: رکورد حسابداری {matched_id} دیگر در دسترس نیست - نیاز به بررسی دستی")
                    return False, {
                        "type": "POS",
                        "source_id": pos_record.get('id'),
                        "matched_id": None,
                        "confidence": ai_response.get('confidence', 0),
                        "status": "needs_review",
                        "reason": f"رکورد حسابداری {matched_id} قبلاً مغایرت‌یابی شده یا حذف شده است",
                        "suggestions": ai_response.get('suggestions', [])
                    }
                
                update_pos_status(pos_record.get('id'), True)
                update_accounting_status(matched_id, True)
                create_reconciliation_result(
                    pos_id=pos_record.get('id'),
                    acc_id=matched_id,
                    bank_record_id=None,
                    description=ai_response.get('reason', ''),
                    type_matched='POS'
                )
                logger.info(f"POS {pos_record.get('id')} با دقت {ai_response.get('confidence')} ذخیره شد")
                return True, {
                    "type": "POS",
                    "source_id": pos_record.get('id'),
                    "matched_id": matched_id,
                    "confidence": ai_response.get('confidence'),
                    "status": "auto_matched",
                    "reason": ai_response.get('reason', '')
                }
            else:
                logger.info(f"POS {pos_record.get('id')} نیاز به بررسی دستی دارد")
                return False, {
                    "type": "POS",
                    "source_id": pos_record.get('id'),
                    "matched_id": None,
                    "confidence": ai_response.get('confidence', 0),
                    "status": "needs_review",
                    "reason": ai_response.get('reason', ''),
                    "suggestions": ai_response.get('suggestions', [])
                }

        except Exception as e:
            logger.error(f"خطا در پردازش POS {pos_record.get('id')}: {str(e)}")
            return False, {
                "type": "POS",
                "source_id": pos_record.get('id'),
                "matched_id": None,
                "confidence": 0,
                "status": "error",
                "reason": str(e)
            }

    def process_bank_transaction(self, bank_record: Dict, transaction_type: str) -> Tuple[bool, Dict]:
        """پردازش تراکنش بانکی"""
        try:
            if not self.is_bank_transaction_unreconciled(bank_record.get('id')):
                logger.warning(f"تراکنش بانکی {transaction_type} {bank_record.get('id')} قبلاً مغایرت‌یابی شده است - نیاز به بررسی ندارد")
                return False, {
                    "type": transaction_type,
                    "source_id": bank_record.get('id'),
                    "matched_id": None,
                    "confidence": 0,
                    "status": "already_reconciled",
                    "reason": "تراکنش قبلاً مغایرت‌یابی شده است"
                }

            amount = bank_record.get('amount')

            if transaction_type == 'Received_Transfer':
                accounting_types = ['Received_Transfer', 'Pos_Transfer_Received']
            elif transaction_type == 'Paid_Transfer':
                accounting_types = ['Paid_Transfer', 'Pos_Transfer_Paid']
            elif transaction_type == 'Received_Check':
                accounting_types = ['Received_Check']
            elif transaction_type == 'Paid_Check':
                accounting_types = ['Paid_Check']
            else:
                accounting_types = []

            accounting_candidates = get_accounting_by_amount_and_types(amount, accounting_types)

            if not accounting_candidates:
                logger.info(f"هیچ گزینه تطبیق برای {transaction_type} {bank_record.get('id')} یافت نشد")
                return False, {
                    "type": transaction_type,
                    "source_id": bank_record.get('id'),
                    "matched_id": None,
                    "confidence": 0,
                    "status": "no_match",
                    "reason": "هیچ تراکنش حسابداری هم‌مبلغ یافت نشد"
                }

            if not self.are_accounting_candidates_unreconciled(accounting_candidates):
                logger.warning(f"برخی از رکوردهای حسابداری برای {transaction_type} {bank_record.get('id')} قبلاً مغایرت‌یابی شده‌اند")
                return False, {
                    "type": transaction_type,
                    "source_id": bank_record.get('id'),
                    "matched_id": None,
                    "confidence": 0,
                    "status": "candidates_reconciled",
                    "reason": "برخی از رکوردهای حسابداری قبلاً مغایرت‌یابی شده‌اند"
                }

            if 'Check' in transaction_type:
                ai_request = format_check_request(bank_record, accounting_candidates, transaction_type)
            else:
                ai_request = format_bank_transfer_request(bank_record, accounting_candidates, transaction_type)

            ai_response = self.send_to_ai(ai_request)

            if ai_response.get('error'):
                logger.error(f"خطا در پاسخ AI: {ai_response.get('error')}")
                return False, {
                    "type": transaction_type,
                    "source_id": bank_record.get('id'),
                    "matched_id": None,
                    "confidence": 0,
                    "status": "error",
                    "reason": f"خطا از AI: {ai_response.get('detail', 'نامشخص')}"
                }

            if ai_response.get('matched'):
                matched_id = ai_response.get('matched_accounting_id')
                
                if not self.validate_matched_id(matched_id, accounting_candidates):
                    logger.warning(f"{transaction_type} {bank_record.get('id')}: matched_id {matched_id} معتبر نیست - نیاز به بررسی دستی")
                    return False, {
                        "type": transaction_type,
                        "source_id": bank_record.get('id'),
                        "matched_id": None,
                        "confidence": ai_response.get('confidence', 0),
                        "status": "needs_review",
                        "reason": f"matched_id {matched_id} در لیست رکوردهای صحیح یافت نشد",
                        "suggestions": ai_response.get('suggestions', [])
                    }
                
                if not self.is_accounting_unreconciled(matched_id):
                    logger.warning(f"{transaction_type} {bank_record.get('id')}: رکورد حسابداری {matched_id} دیگر در دسترس نیست - نیاز به بررسی دستی")
                    return False, {
                        "type": transaction_type,
                        "source_id": bank_record.get('id'),
                        "matched_id": None,
                        "confidence": ai_response.get('confidence', 0),
                        "status": "needs_review",
                        "reason": f"رکورد حسابداری {matched_id} قبلاً مغایرت‌یابی شده یا حذف شده است",
                        "suggestions": ai_response.get('suggestions', [])
                    }
                
                update_bank_transaction_reconciliation_status(bank_record.get('id'), True)
                update_accounting_status(matched_id, True)
                create_reconciliation_result(
                    pos_id=None,
                    acc_id=matched_id,
                    bank_record_id=bank_record.get('id'),
                    description=ai_response.get('reason', ''),
                    type_matched=transaction_type
                )
                logger.info(f"{transaction_type} {bank_record.get('id')} با دقت {ai_response.get('confidence')} ذخیره شد")
                return True, {
                    "type": transaction_type,
                    "source_id": bank_record.get('id'),
                    "matched_id": matched_id,
                    "confidence": ai_response.get('confidence'),
                    "status": "auto_matched",
                    "reason": ai_response.get('reason', '')
                }
            else:
                logger.info(f"{transaction_type} {bank_record.get('id')} نیاز به بررسی دستی دارد")
                return False, {
                    "type": transaction_type,
                    "source_id": bank_record.get('id'),
                    "matched_id": None,
                    "confidence": ai_response.get('confidence', 0),
                    "status": "needs_review",
                    "reason": ai_response.get('reason', ''),
                    "suggestions": ai_response.get('suggestions', [])
                }

        except Exception as e:
            logger.error(f"خطا در پردازش {transaction_type} {bank_record.get('id')}: {str(e)}")
            return False, {
                "type": transaction_type,
                "source_id": bank_record.get('id'),
                "matched_id": None,
                "confidence": 0,
                "status": "error",
                "reason": str(e)
            }

    def set_webhook_url(self, url: str):
        """تنظیم URL webhook n8n"""
        self.n8n_webhook_url = url
        logger.info(f"URL webhook تنظیم شد: {url}")
