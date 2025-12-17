import json
import time
import threading
import requests
from typing import Dict, List, Optional, Tuple
from queue import Queue
from utils.logger_config import setup_logger
from utils.ai_request_formatter import (
    format_pos_request,
    format_bank_transfer_request,
    format_check_request
)
from database.accounting_repository import get_accounting_by_amount_and_types, update_reconciliation_status as update_accounting_status, update_ai_processed as update_accounting_ai_processed
from database.pos_transactions_repository import update_reconciliation_status as update_pos_status, update_ai_processed as update_pos_ai_processed
from database.bank_transaction_repository import update_bank_transaction_reconciliation_status, update_ai_processed as update_bank_ai_processed
from database.reconciliation_results_repository import create_reconciliation_result
from database.init_db import create_connection
import sqlite3

logger = setup_logger('reconciliation.ai_matcher')

class RateLimiter:
    def __init__(self, limit=5, period=60):
        self.limit = limit
        self.period = period
        self.count = 0
        self.start_time = time.time()
        self.lock = threading.Lock()

    def wait_if_needed(self):
        with self.lock:
            now = time.time()
            elapsed = now - self.start_time
            
            if elapsed >= self.period:
                # Reset
                self.count = 0
                self.start_time = now
                elapsed = 0
            
            if self.count >= self.limit:
                sleep_time = self.period - elapsed
                if sleep_time > 0:
                    logger.info(f"Rate limit reached. Waiting {sleep_time:.2f} seconds...")
                    time.sleep(sleep_time)
                # After sleep, reset
                self.count = 0
                self.start_time = time.time()
            
            self.count += 1

class AIMatcher:
    def __init__(self, n8n_webhook_url: str = None):
        self.ollama_url = "http://localhost:11434/api/chat"
        self.model_name = "gemma3:latest"
        self.limiter = RateLimiter()
        self.ui_callback = None
        
        self.timeout = 300
        self.retry_count = 3
        self.processing_lock = threading.Lock()

    def set_ui_callback(self, callback):
        """تنظیم تابع فراخوانی UI برای تعامل با کاربر"""
        self.ui_callback = callback

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

    def _get_system_prompt(self) -> str:
        return """TASK: You are an accounting reconciliation assistant. Match POS/Bank records with accounting records.
INPUT: You will receive JSON data containing:
- pos_record or bank_record: The transaction to match
- accounting_candidates: List of possible matches
- matching_rules: Rules for matching
CRITICAL INSTRUCTION:
- You MUST ONLY return an ID from the accounting_candidates list
- DO NOT invent or hallucinate IDs
- If no match found, return matched=false and matched_accounting_id=null
- NEVER return an ID that doesn't exist in accounting_candidates
DATA CLEANING:
- transaction_number in accounting_candidates has ".0" suffix (e.g., "506647.0")
- Remove the ".0" suffix before comparison
- Convert "114224.0" → "114224"
MATCHING ALGORITHM (in order of priority):
1. Amount MUST match exactly (REQUIRED)
2. Tracking number: Extract last 6 digits from pos_record.tracking_number
   - Example: "312379114224" → "114224"
   - Must match transaction_number after removing ".0"
   - This is the STRONGEST indicator
3. Card: Last 4 digits must match pattern "ک XXXX" in description
   - Example: card "603799******6073" → last 4 = "6073"
   - Look for "ک 6073" in description
4. Date: ±15 days difference is acceptable
   - Prefer closer dates
SCORING:
- tracking_match = 0.5 (most important)
- card_match = 0.3
- date_match = 0.2 (based on proximity: 0 days = 0.2, 15 days = 0.0)
- Total confidence = sum of scores
STEP BY STEP:
1. Filter candidates by amount (exact match only)
2. For each remaining candidate:
   a. Extract last 6 digits from POS tracking_number
   b. Clean candidate transaction_number (remove .0)
   c. Check if they match → tracking_match
   d. Check if card last 4 digits in description → card_match
   e. Calculate date difference → date_match score
   f. Calculate total confidence
3. Return the candidate with HIGHEST confidence
4. If confidence < 0.6, return matched=false
OUTPUT FORMAT (MUST be valid JSON, NO markdown):
{
  "matched": boolean,
  "matched_accounting_id": number or null (MUST exist in candidates!),
  "confidence": number (0.0-1.0),
  "reason": "explanation in Persian",
  "match_details": {
    "amount_match": boolean,
    "card_match": boolean,
    "tracking_match": boolean,
    "date_difference_days": number,
    "terminal_match": boolean
  }
}
VERIFY BEFORE RESPONDING:
- Check: Is matched_accounting_id in the candidates list? If NO, return matched=false
- Check: Does the logic match the rules?
- Check: Is the output valid JSON (no markdown)?"""

    def _send_to_ollama(self, data: Dict) -> Dict:
        self.limiter.wait_if_needed()
        
        payload = {
            "model": self.model_name,
            "messages": [
                {"role": "system", "content": self._get_system_prompt()},
                {"role": "user", "content": f"DATA TO ANALYZE: {json.dumps(data, ensure_ascii=False)}"}
            ],
            "stream": False,
            "options": {
                "temperature": 0.6,
                "num_ctx":2048
            }
        }
        
        response = requests.post(self.ollama_url, json=payload, timeout=self.timeout)
        response.raise_for_status()
        
        result_json = response.json()
        content = result_json.get("message", {}).get("content", "")
        return self._parse_response(content)

    def _parse_response(self, response_content: str) -> Dict:
        # Clean up potential markdown code blocks
        if response_content.startswith("```json"):
            response_content = response_content[7:]
        if response_content.startswith("```"):
            response_content = response_content[3:]
        if response_content.endswith("```"):
            response_content = response_content[:-3]
        
        return json.loads(response_content.strip())

    def send_to_ai(self, data: Dict) -> Dict:
        """ارسال داده به AI و دریافت نتیجه"""
        with self.processing_lock:
            while True:
                try:
                    transaction_id = data.get('pos_record', data.get('bank_record', {})).get('id')
                    logger.info(f"ارسال تراکنش {transaction_id} به Ollama...")
                    
                    result = self._send_to_ollama(data)
                        
                    logger.info(f"پاسخ موفق از Ollama برای تراکنش {transaction_id}")
      
                    return result

                except Exception as e:
                    logger.error(f"خطا در ارتباط با Ollama: {str(e)}")
                    
                    if self.ui_callback:
                        action = self.ui_callback(f"خطا در ارتباط با Ollama:\n{str(e)}")
                        if action == 'retry':
                            continue
                        elif action == 'cancel':
                            return {
                                "error": "Cancelled by user",
                                "detail": str(e),
                                "matched": False,
                                "confidence": 0
                            }
                    
                    # If no callback or unhandled, return error
                    return {
                        "error": "Request failed",
                        "detail": str(e),
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
            
            if pos_record.get('ai_processed') == 1:
                logger.info(f"تراکنش POS {pos_record.get('id')} قبلاً توسط AI پردازش شده است - پرش می‌شود")
                return False, {
                    "type": "POS",
                    "source_id": pos_record.get('id'),
                    "matched_id": None,
                    "confidence": 0,
                    "status": "already_processed_by_ai",
                    "reason": "تراکنش قبلاً توسط AI پردازش شده است"
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
            
            update_pos_ai_processed(pos_record.get('id'), True)
            for candidate in accounting_candidates:
                update_accounting_ai_processed(candidate.get('id'), True)

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
            
            if bank_record.get('ai_processed') == 1:
                logger.info(f"تراکنش بانکی {transaction_type} {bank_record.get('id')} قبلاً توسط AI پردازش شده است - پرش می‌شود")
                return False, {
                    "type": transaction_type,
                    "source_id": bank_record.get('id'),
                    "matched_id": None,
                    "confidence": 0,
                    "status": "already_processed_by_ai",
                    "reason": "تراکنش قبلاً توسط AI پردازش شده است"
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
            
            update_bank_ai_processed(bank_record.get('id'), True)
            for candidate in accounting_candidates:
                update_accounting_ai_processed(candidate.get('id'), True)

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


