import json
from utils.logger_config import setup_logger

logger = setup_logger('utils.ai_request_formatter')

def format_pos_request(pos_record, accounting_candidates):
    """فرمت کردن درخواست POS برای n8n"""
    try:
        request_data = {
            "transaction_type": "pos",
            "pos_record": {
                "id": pos_record.get('id'),
                "terminal_number": pos_record.get('terminal_number'),
                "terminal_id": pos_record.get('terminal_id'),
                "card_number": pos_record.get('card_number', ''),
                "transaction_date": str(pos_record.get('transaction_date', '')),
                "transaction_amount": pos_record.get('transaction_amount'),
                "tracking_number": str(pos_record.get('tracking_number', ''))
            },
            "accounting_candidates": [
                {
                    "id": candidate.get('id'),
                    "transaction_number": str(candidate.get('transaction_number', '')),
                    "transaction_amount": candidate.get('transaction_amount'),
                    "due_date": str(candidate.get('due_date', '')),
                    "customer_name": candidate.get('customer_name', ''),
                    "description": candidate.get('description', '')
                }
                for candidate in accounting_candidates
            ],
            "matching_rules": {
                "amount": "must match exactly",
                "card": "last 4 digits should match if available in description",
                "tracking": "last 6 digits of POS tracking should match accounting transaction_number",
                "date": "accounting date usually equal to POS date, but can vary ±15 days",
                "terminal": "terminal_id might appear in accounting description for sum of day"
            },
            "confidence_guidelines": {
                "0.95_plus": "Amount + Tracking + Date all match perfectly (0-1 day difference)",
                "0.85_0.94": "Amount + Tracking match perfectly, Date within ±3 days",
                "0.75_0.84": "Amount + Tracking match, Date within ±7 days, missing 1 optional field",
                "0.65_0.74": "Amount matches, Tracking matches but Date difference > 7 days",
                "below_0.65": "Only amount matches or multiple fields missing"
            }
        }
        logger.info(f"درخواست POS فرمت شد برای ترمینال {pos_record.get('terminal_number')}")
        return request_data
    except Exception as e:
        logger.error(f"خطا در فرمت کردن درخواست POS: {str(e)}")
        raise

def format_bank_transfer_request(bank_record, accounting_candidates, transaction_type):
    """فرمت کردن درخواست انتقال بانکی برای n8n"""
    try:
        request_data = {
            "transaction_type": transaction_type,
            "bank_record": {
                "id": bank_record.get('id'),
                "transaction_date": str(bank_record.get('transaction_date', '')),
                "transaction_time": bank_record.get('transaction_time', ''),
                "amount": bank_record.get('amount'),
                "description": bank_record.get('description', ''),
                "reference_number": str(bank_record.get('reference_number', '')),
                "extracted_tracking_number": str(bank_record.get('extracted_tracking_number', '')),
                "source_card_number": str(bank_record.get('source_card_number', '')),
                "depositor_name": bank_record.get('depositor_name', '')
            },
            "accounting_candidates": [
                {
                    "id": candidate.get('id'),
                    "transaction_number": str(candidate.get('transaction_number', '')),
                    "transaction_amount": candidate.get('transaction_amount'),
                    "due_date": str(candidate.get('due_date', '')),
                    "customer_name": candidate.get('customer_name', ''),
                    "description": candidate.get('description', '')
                }
                for candidate in accounting_candidates
            ],
            "matching_rules": {
                "amount": "bank amount might include fee (1000-50000 Rials more)",
                "tracking": "extracted_tracking_number should match transaction_number (last digits)",
                "card": "source_card_number (last 4) should appear in description",
                "date": "dates can differ by 1-2 days due to registration delays",
                "name": "depositor_name should match customer_name if available"
            },
            "confidence_guidelines": {
                "0.95_plus": "Amount exact match + Tracking match + Date within 1 day",
                "0.85_0.94": "Amount exact match + Tracking match, Date within ±2 days",
                "0.75_0.84": "Amount (with fee) + Tracking match, Date within ±3 days",
                "0.65_0.74": "Amount match + tracking match but Date > 3 days, or missing name confirmation",
                "below_0.65": "Only amount matches or tracking missing"
            }
        }
        logger.info(f"درخواست انتقال بانکی فرمت شد برای مبلغ {bank_record.get('amount')}")
        return request_data
    except Exception as e:
        logger.error(f"خطا در فرمت کردن درخواست انتقال بانکی: {str(e)}")
        raise

def format_check_request(bank_record, accounting_candidates, transaction_type):
    """فرمت کردن درخواست چک برای n8n"""
    try:
        request_data = {
            "transaction_type": transaction_type,
            "bank_record": {
                "id": bank_record.get('id'),
                "transaction_date": str(bank_record.get('transaction_date', '')),
                "amount": bank_record.get('amount'),
                "description": bank_record.get('description', ''),
                "extracted_tracking_number": str(bank_record.get('extracted_tracking_number', ''))
            },
            "accounting_candidates": [
                {
                    "id": candidate.get('id'),
                    "transaction_number": str(candidate.get('transaction_number', '')),
                    "transaction_amount": candidate.get('transaction_amount'),
                    "due_date": str(candidate.get('due_date', '')),
                    "collection_date": str(candidate.get('collection_date', '')),
                    "customer_name": candidate.get('customer_name', ''),
                    "description": candidate.get('description', '')
                }
                for candidate in accounting_candidates
            ],
            "matching_rules": {
                "amount": "must match exactly",
                "check_number": "extracted_tracking_number must match transaction_number",
                "date": "bank transaction_date should match collection_date (not due_date!)"
            },
            "confidence_guidelines": {
                "0.95_plus": "Amount exact + Check number exact + Date matches collection_date",
                "0.85_0.94": "Amount exact + Check number match, Date within ±1 day",
                "0.75_0.84": "Amount exact + Check number match, Date within ±3 days",
                "0.65_0.74": "Amount exact + Check number match, Date difference ±5 days",
                "below_0.65": "Only amount matches or multiple fields missing"
            }
        }
        logger.info(f"درخواست چک فرمت شد برای مبلغ {bank_record.get('amount')}")
        return request_data
    except Exception as e:
        logger.error(f"خطا در فرمت کردن درخواست چک: {str(e)}")
        raise
