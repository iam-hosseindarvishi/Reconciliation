import sys
import os
import logging
import time
from unittest.mock import MagicMock

# Mock database modules to avoid connection errors if DB is missing
sys.modules['database.accounting_repository'] = MagicMock()
sys.modules['database.pos_transactions_repository'] = MagicMock()
sys.modules['database.bank_transaction_repository'] = MagicMock()
sys.modules['database.reconciliation_results_repository'] = MagicMock()
sys.modules['database.init_db'] = MagicMock()
# sys.modules['sqlite3'] = MagicMock() # sqlite3 is standard lib, usually fine

# Add current directory to path
sys.path.append(os.getcwd())

try:
    from reconciliation.ai_matcher import AIMatcher
except ImportError as e:
    print(f"Import Error: {e}")
    sys.exit(1)

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def test_providers():
    print("Initializing AIMatcher...")
    matcher = AIMatcher()
    
    dummy_data = {
        "pos_record": {
            "id": 123,
            "transaction_amount": 100000,
            "tracking_number": "123456",
            "description": "Test POS Transaction"
        },
        "accounting_candidates": [
            {
                "id": 1,
                "transaction_number": "123456.0",
                "amount": 100000,
                "description": "Test Accounting Record"
            },
            {
                "id": 2,
                "transaction_number": "999999.0",
                "amount": 100000,
                "description": "Wrong Record"
            }
        ]
    }

    print("\n--- Testing Kimi AI ---")
    matcher.current_provider = 'kimi'
    try:
        start = time.time()
        result = matcher.send_to_ai(dummy_data)
        duration = time.time() - start
        print(f"Kimi Result (took {duration:.2f}s):", result)
    except Exception as e:
        print("Kimi Failed:", e)

    print("\n--- Testing Gemini AI ---")
    matcher.current_provider = 'gemini'
    try:
        start = time.time()
        result = matcher.send_to_ai(dummy_data)
        duration = time.time() - start
        print(f"Gemini Result (took {duration:.2f}s):", result)
    except Exception as e:
        print("Gemini Failed:", e)

    print("\n--- Testing Rate Limiter (Simulation) ---")
    # We will simulate 6 requests to check if it waits
    # We'll use a mock send method to avoid actual API calls and save tokens/time
    
    original_send_kimi = matcher._send_to_kimi
    
    def mock_send(data):
        matcher.kimi_limiter.wait_if_needed()
        return {"matched": False}
    
    matcher._send_to_kimi = mock_send
    matcher.current_provider = 'kimi'
    
    # Reset limiter for test
    matcher.kimi_limiter.count = 0
    matcher.kimi_limiter.start_time = time.time()
    # Reduce period for testing
    matcher.kimi_limiter.period = 5 
    
    print("Sending 6 requests (Limit is 5 per 5 seconds)...")
    start_total = time.time()
    for i in range(6):
        req_start = time.time()
        matcher.send_to_ai(dummy_data)
        print(f"Request {i+1} completed at {time.time() - start_total:.2f}s")
    
    print(f"Total time for 6 requests: {time.time() - start_total:.2f}s")
    
    # Restore
    matcher._send_to_kimi = original_send_kimi

if __name__ == "__main__":
    test_providers()
