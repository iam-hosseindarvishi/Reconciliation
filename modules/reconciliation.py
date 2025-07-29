#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Main reconciliation module
This module contains the ReconciliationEngine class, which coordinates all reconciliation operations.
The algorithm is rewritten based on the steps of preparation, iterative processing, date normalization, and reconciliation types.
"""

from typing import Dict, List, Optional, Any

from modules.database_manager import DatabaseManager
from modules.logger import get_logger
import modules.utils as utils

# Create logger object
logger = get_logger(__name__)

class ReconciliationEngine:
    """
    Main reconciliation engine
    This class coordinates all reconciliation operations
    """
    
    def __init__(self, db_manager: DatabaseManager):
        """
        Class constructor
        
        Parameters:
            db_manager: An instance of the DatabaseManager class
        """
        self.db_manager = db_manager
        
        # Callback for manual reconciliation
        self.ui_callback_manual_reconciliation_needed = None
        
        logger.info("Reconciliation engine started")
    
    def start_reconciliation(self, selected_bank_id: int) -> Dict[str, Any]:
        """
        Start the reconciliation process based on the new algorithm
        
        Parameters:
            selected_bank_id: ID of the selected bank
            
        Returns:
            Reconciliation results
        """
        logger.info(f"🚀 Starting reconciliation process for bank {selected_bank_id}")
        
        # Preparation step: Get unreconciled bank transactions
        bank_transactions = self.db_manager.get_unreconciled_bank_transactions(selected_bank_id)
        logger.info(f"📊 Number of unreconciled bank transactions: {len(bank_transactions)}")
        
        if not bank_transactions:
            logger.info("No unreconciled bank transactions found")
            return {"message": "No unreconciled bank transactions found"}
        
        # Processing statistics
        processed_count = 0
        successful_matches = 0
        
        # Iterative processing: Each bank transaction is processed individually
        for bank_record in bank_transactions:
            transaction_type = bank_record.get('Transaction_Type_Bank', '')
            transaction_id = bank_record.get('id')
            
            logger.info(f"🔄 Processing transaction {transaction_id} - Type: {transaction_type}")
            
            try:
                success = self._process_transaction_by_type(bank_record, transaction_type, selected_bank_id)
                
                if success:
                    successful_matches += 1
                    self.db_manager.update_reconciliation_status('BankTransactions', transaction_id, True)
                    logger.info(f"✅ Transaction {transaction_id} processed and marked as reconciled successfully")
                else:
                    logger.warning(f"⚠️ Transaction {transaction_id} not processed")
                    
                processed_count += 1
                
            except Exception as e:
                logger.error(f"❌ Error processing transaction {transaction_id}: {str(e)}")
                # Do not mark as reconciled in case of error, just log and continue
                processed_count += 1
                continue
        
        # Final report
        result = {
            "total_transactions": len(bank_transactions),
            "processed_count": processed_count,
            "successful_matches": successful_matches,
            "failed_count": processed_count - successful_matches,
            "message": f"Processing complete. {successful_matches} out of {processed_count} transactions were successfully reconciled."
        }
        
        logger.info(f"📈 Final reconciliation results: {result}")
        return result

    def start_reconciliation_selective(self, selected_bank_id: int, selected_types: list) -> Dict[str, Any]:
        """
        Start selective reconciliation process
        
        Parameters:
            selected_bank_id: ID of the selected bank
            selected_types: List of reconciliation types to execute
            
        Returns:
            Reconciliation results
        """
        logger.info(f"🚀 Starting selective reconciliation for bank {selected_bank_id} with types: {selected_types}")
        
        bank_transactions = self.db_manager.get_unreconciled_bank_transactions(selected_bank_id)
        logger.info(f"📊 Number of unreconciled bank transactions: {len(bank_transactions)}")

        if not bank_transactions:
            logger.info("No unreconciled bank transactions found")
            return {"message": "No unreconciled bank transactions found"}

        processed_count = 0
        successful_matches = 0

        for bank_record in bank_transactions:
            transaction_type = bank_record.get('Transaction_Type_Bank', '').strip()
            transaction_id = bank_record.get('id')

            if transaction_type not in selected_types:
                logger.debug(f"Ignoring transaction {transaction_id} of type {transaction_type} as it's not in selected types.")
                continue

            logger.info(f"🔄 Processing transaction {transaction_id} - Type: {transaction_type}")

            try:
                success = self._process_transaction_by_type(bank_record, transaction_type, selected_bank_id)
                if success:
                    successful_matches += 1
                    self.db_manager.update_reconciliation_status('BankTransactions', transaction_id, True)
                    logger.info(f"✅ Transaction {transaction_id} processed and marked as reconciled successfully")
                else:
                    logger.warning(f"⚠️ Transaction {transaction_id} not processed")
                processed_count += 1
            except Exception as e:
                logger.error(f"❌ Error processing transaction {transaction_id}: {str(e)}")
                # Do not mark as reconciled in case of error, just log and continue
                processed_count += 1
                continue

        result = {
            "total_transactions": len(bank_transactions),
            "processed_count": processed_count,
            "successful_matches": successful_matches,
            "failed_count": processed_count - successful_matches,
            "message": f"Selective processing complete. {successful_matches} out of {processed_count} transactions were successfully reconciled."
        }

        logger.info(f"📈 Final selective reconciliation results: {result}")
        return result
    
    def _process_transaction_by_type(self, bank_record: Dict[str, Any], transaction_type: str, selected_bank_id: int) -> bool:
        """
        Process transaction based on its type
        
        Parameters:
            bank_record: Bank transaction record
            transaction_type: Transaction type
            selected_bank_id: ID of the selected bank
            
        Returns:
            Success of the operation
        """
        transaction_type = transaction_type.strip().lower()
        
        if transaction_type in ["received transfer", "paid transfer"]:
            # Transfers/Receipts
            return self._reconcile_transfers(bank_record, selected_bank_id)
            
        elif transaction_type in ["received check", "paid check"]:
            # Checks
            return self._reconcile_checks(bank_record, selected_bank_id)
            
        elif transaction_type == "pos deposit":
            # POS Deposits
            return self._reconcile_pos_deposits(bank_record, selected_bank_id)
            
        else:
            logger.warning(f"Unknown transaction type: {transaction_type}")
            # Do not mark as reconciled, just log and return False
            return False
    
    def _reconcile_transfers(self, bank_record: Dict[str, Any], selected_bank_id: int) -> bool:
        """
        Reconcile transfers/receipts
        
        Parameters:
            bank_record: Bank transaction record
            selected_bank_id: ID of the selected bank
            
        Returns:
            Success of the operation
        """
        transaction_type = bank_record.get('Transaction_Type_Bank', '')
        transaction_id = bank_record.get('id')
        
        logger.info(f"🔄 Reconciling transfer {transaction_id} - Type: {transaction_type}")
        
        # Determine target amount and accounting entry type
        if transaction_type == 'Received Transfer':
            target_amount = bank_record.get('Deposit_Amount')
            target_acc_entry_type = 'Received Transfer/Voucher'
        elif transaction_type == 'Paid Transfer':
            target_amount = bank_record.get('Withdrawal_Amount')
            target_acc_entry_type = 'Paid Transfer/Voucher'
        else:
            logger.warning(f"⚠️ Unknown transfer transaction type: {transaction_type}")
            return False
            
        if not target_amount:
            logger.warning(f"⚠️ Transfer transaction amount for {transaction_id} is missing")
            self._finalize_discrepancy(
                bank_record['id'], None, None, 
                "Discrepancy - Transfer", 
                "Transfer/Receipt: Transaction amount is missing"
            )
            return False
            
        # Normalize bank date
        bank_date = bank_record.get('Date', '')
        normalized_bank_date = utils.convert_date_format(bank_date, 'YYYY/MM/DD', 'YYYYMMDD')
        
        if not normalized_bank_date:
            logger.warning(f"⚠️ Transfer transaction date for {transaction_id} is not convertible: {bank_date}")
            self._finalize_discrepancy(
                bank_record['id'], None, None, 
                "Discrepancy - Transfer", 
                "Transfer/Receipt: Transaction date is not convertible"
            )
            return False
            
        # Initial search in accounting entries
        found_acc_records = self._search_accounting_entries_for_transfer(
            selected_bank_id, normalized_bank_date, target_amount, target_acc_entry_type
        )
        
        # Process based on the number of results found
        if len(found_acc_records) == 1:
            # Unique match
            matching_acc_record = found_acc_records[0]
            self._finalize_reconciliation(
                bank_record['id'], 
                matching_acc_record['id'], 
                None, 
                "Match - Transfer", 
                "Transfer/Receipt: Unique match"
            )
            logger.info(f"✅ Unique match for transfer transaction {transaction_id}")
            return True
            
        elif len(found_acc_records) > 1:
            # Multiple matches - Secondary filter by tracking number
            filtered_records = self._filter_by_tracking_number(bank_record, found_acc_records)
            
            if len(filtered_records) == 1:
                # Unique match after filter
                matching_acc_record = filtered_records[0]
                self._finalize_reconciliation(
                    bank_record['id'], 
                    matching_acc_record['id'], 
                    None, 
                    "Match - Transfer (Filtered)", 
                    "Transfer/Receipt: Match after tracking number filter"
                )
                logger.info(f"✅ Match after filter for transfer transaction {transaction_id}")
                return True
                
            else:
                # Requires manual reconciliation or discrepancy logging
                if (hasattr(self, 'ui_callback_manual_reconciliation_needed') and 
                    self.ui_callback_manual_reconciliation_needed):
                    self.ui_callback_manual_reconciliation_needed(bank_record, found_acc_records, 'transfer')
                    logger.info(f"🔧 Sending to manual reconciliation for transfer transaction {transaction_id}")
                    return True  # Waiting for user selection
                else:
                    self._finalize_discrepancy(
                        bank_record['id'], None, None, 
                        "Discrepancy - Transfer", 
                        f"Transfer/Receipt: Multiple matches ({len(found_acc_records)}) found"
                    )
                    logger.warning(f"⚠️ Multiple matches for transfer transaction {transaction_id}")
                    return False
                    
        else:
            # No match found
            self._finalize_discrepancy(
                bank_record['id'], None, None, 
                "Discrepancy - Transfer", 
                "Transfer/Receipt: Not found in accounting"
            )
            logger.warning(f"⚠️ No match found for transfer transaction {transaction_id}")
            return False
    
    def _reconcile_checks(self, bank_record: Dict[str, Any], selected_bank_id: int) -> bool:
        """
        Reconcile checks
        
        Parameters:
            bank_record: Bank transaction record
            selected_bank_id: ID of the selected bank
            
        Returns:
            Success of the operation
        """
        transaction_type = bank_record.get('Transaction_Type_Bank', '')
        transaction_id = bank_record.get('id')
        
        logger.info(f"🔄 Reconciling check {transaction_id} - Type: {transaction_type}")
        
        # Determine target amount and accounting entry type
        if transaction_type == 'Received Check':
            target_amount = bank_record.get('Deposit_Amount')
            target_acc_entry_type = 'Received Check'
        elif transaction_type == 'Paid Check':
            target_amount = bank_record.get('Withdrawal_Amount')
            target_acc_entry_type = 'Paid Check'
        else:
            logger.warning(f"⚠️ Unknown check transaction type: {transaction_type}")
            return False
            
        if not target_amount:
            logger.warning(f"⚠️ Check transaction amount for {transaction_id} is missing")
            self._finalize_discrepancy(
                bank_record['id'], None, None, 
                "Discrepancy - Check", 
                "Check: Transaction amount is missing"
            )
            return False
            
        # Normalize bank date
        bank_date = bank_record.get('Date', '')
        normalized_bank_date = utils.convert_date_format(bank_date, 'YYYY/MM/DD', 'YYYYMMDD')
        
        if not normalized_bank_date:
            logger.warning(f"⚠️ Check transaction date for {transaction_id} is not convertible: {bank_date}")
            self._finalize_discrepancy(
                bank_record['id'], None, None, 
                "Discrepancy - Check", 
                "Check: Transaction date is not convertible"
            )
            return False
            
        # Initial search in accounting entries (based on Date_Of_Receipt)
        # Search for unreconciled check transactions
        check_transactions = self.db_manager.get_unreconciled_check_transactions(selected_bank_id)

        # Filter accounting entries based on check transactions
        found_acc_records = self._filter_accounting_entries_for_check(
            check_transactions, selected_bank_id, normalized_date, target_amount, target_acc_entry_type
        )
        
        # Filter by check number
        if found_acc_records:
            filtered_records = self._filter_by_check_number(bank_record, found_acc_records)
        else:
            filtered_records = []
        
        # Process based on the number of results found
        if len(filtered_records) == 1:
            # Unique match
            matching_acc_record = filtered_records[0]
            self._finalize_reconciliation(
                bank_record['id'], 
                matching_acc_record['id'], 
                None, 
                "Match - Check", 
                "Check: Unique match"
            )
            logger.info(f"✅ Unique match for check transaction {transaction_id}")
            return True
            
        elif len(filtered_records) > 1:
            # Multiple matches - Requires manual reconciliation
            if (hasattr(self, 'ui_callback_manual_reconciliation_needed') and 
                self.ui_callback_manual_reconciliation_needed):
                self.ui_callback_manual_reconciliation_needed(bank_record, filtered_records, 'check')
                logger.info(f"🔧 Sending to manual reconciliation for check transaction {transaction_id}")
                return True  # Waiting for user selection
            else:
                self._finalize_discrepancy(
                    bank_record['id'], None, None, 
                    "Discrepancy - Check", 
                    f"Check: Multiple matches ({len(filtered_records)}) found"
                )
                logger.warning(f"⚠️ Multiple matches for check transaction {transaction_id}")
                return False
                
        else:
            # No match found
            self._finalize_discrepancy(
                bank_record['id'], None, None, 
                "Discrepancy - Check", 
                "Check: Not found in accounting"
            )
            logger.warning(f"⚠️ No match found for check transaction {transaction_id}")
            return False
    
    def _reconcile_pos_deposits(self, bank_record: Dict[str, Any], selected_bank_id: int) -> bool:
        """
        Reconcile POS deposits
        
        Parameters:
            bank_record: Bank transaction record
            selected_bank_id: ID of the selected bank
            
        Returns:
            Success of the operation
        """
        transaction_id = bank_record.get('id')
        terminal_id = bank_record.get('Extracted_Shaparak_Terminal_ID')
        
        logger.info(f"🔄 Reconciling POS {transaction_id} - Terminal: {terminal_id}")
        
        if not terminal_id:
            logger.warning(f"⚠️ Terminal ID for POS transaction {transaction_id} is missing")
            self._finalize_discrepancy(
                bank_record['id'], None, None, 
                "Discrepancy - POS", 
                "POS: Terminal ID is missing"
            )
            return False
        
        # Get terminal details
        terminal_details = self._get_terminal_details(terminal_id)
        if not terminal_details:
            logger.warning(f"⚠️ Terminal details for {terminal_id} not found")
            self._finalize_discrepancy(
                bank_record['id'], None, None, 
                "Discrepancy - POS", 
                f"POS: Terminal details for {terminal_id} not found"
            )
            return False
            
        # Normalize bank date
        bank_date = bank_record.get('Date', '')
        normalized_bank_date = utils.convert_date_format(bank_date, 'YYYY/MM/DD', 'YYYYMMDD')
        
        if not normalized_bank_date:
            logger.warning(f"⚠️ POS transaction date for {transaction_id} is not convertible: {bank_date}")
            self._finalize_discrepancy(
                bank_record['id'], None, None, 
                "Discrepancy - POS", 
                "POS: Transaction date is not convertible"
            )
            return False
            
        # Search in POS transactions
        target_amount = bank_record.get('Deposit_Amount')
        found_pos_records = self._search_pos_transactions(
            terminal_id, normalized_bank_date, target_amount
        )
        
        # Process based on the number of results found
        if len(found_pos_records) == 1:
            # Unique match
            matching_pos_record = found_pos_records[0]
            self._finalize_reconciliation(
                bank_record['id'], 
                None, 
                matching_pos_record['id'], 
                "Match - POS", 
                "POS: Unique match"
            )
            logger.info(f"✅ Unique match for POS transaction {transaction_id}")
            return True
            
        elif len(found_pos_records) > 1:
            # Multiple matches - Requires manual reconciliation
            if (hasattr(self, 'ui_callback_manual_reconciliation_needed') and 
                self.ui_callback_manual_reconciliation_needed):
                self.ui_callback_manual_reconciliation_needed(bank_record, found_pos_records, 'pos')
                logger.info(f"🔧 Sending to manual reconciliation for POS transaction {transaction_id}")
                return True  # Waiting for user selection
            else:
                self._finalize_discrepancy(
                    bank_record['id'], None, None, 
                    "Discrepancy - POS", 
                    f"POS: Multiple matches ({len(found_pos_records)}) found"
                )
                logger.warning(f"⚠️ Multiple matches for POS transaction {transaction_id}")
                return False
                
        else:
            # No match found
            self._finalize_discrepancy(
                bank_record['id'], None, None, 
                "Discrepancy - POS", 
                "POS: Not found in POS transactions"
            )
            logger.warning(f"⚠️ No match found for POS transaction {transaction_id}")
            return False

    def _finalize_reconciliation(self, bank_id: int, acc_id: Optional[int], pos_id: Optional[int], status: str, notes: str):
        """Finalize a successful reconciliation."""
        logger.info(f"Finalizing reconciliation for bank_id={bank_id}, acc_id={acc_id}, pos_id={pos_id}")
        # Mark bank transaction as reconciled
        self.db_manager.update_bank_transaction_reconciled_status(bank_id, True)
        # Mark accounting entry as reconciled if applicable
        if acc_id is not None:
            self.db_manager.update_accounting_entry_reconciled_status(acc_id, True)
        # Mark POS transaction as reconciled if applicable
        if pos_id is not None:
            self.db_manager.update_pos_transaction_reconciled_status(pos_id, True)
        # Insert result
        self.db_manager.insert_reconciliation_result(bank_id, acc_id, pos_id, status, notes)

    def _finalize_discrepancy(self, bank_id: int, acc_id: Optional[int], pos_id: Optional[int], status: str, notes: str):
        """Finalize a discrepancy."""
        logger.warning(f"Finalizing discrepancy for bank_id={bank_id}, status={status}, notes={notes}")
        # Mark bank transaction as reconciled (with discrepancy)
        self.db_manager.update_bank_transaction_reconciled_status(bank_id, True)
        # Insert result with discrepancy status
        self.db_manager.insert_reconciliation_result(bank_id, acc_id, pos_id, status, notes)

    def _mark_bank_record_reconciled(self, bank_id: int, notes: str):
        """Mark a bank record as reconciled with a specific note."""
        logger.info(f"Marking bank record {bank_id} as reconciled. Notes: {notes}")
        self.db_manager.update_bank_transaction_reconciled_status(bank_id, True)
        self.db_manager.insert_reconciliation_result(bank_id, None, None, "Reconciled - System", notes)

    def _search_accounting_entries_for_transfer(self, bank_id: int, date: str, amount: float, entry_type: str) -> List[Dict[str, Any]]:
        """Search for matching accounting entries for a transfer."""
        logger.debug(f"Searching for transfer in accounting: bank_id={bank_id}, date={date}, amount={amount}, type={entry_type}")
        return self.db_manager.find_matching_accounting_entries(bank_id, date, amount, entry_type, date_field='Due_Date')

    def _filter_by_tracking_number(self, bank_record: Dict[str, Any], acc_records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Filter accounting records by tracking number."""
        bank_tracking_no = bank_record.get('Extracted_Tracking_No')
        if not bank_tracking_no:
            return []
        logger.debug(f"Filtering by tracking number: {bank_tracking_no}")
        return [rec for rec in acc_records if str(rec.get('Tracking_No')) == str(bank_tracking_no)]

    def _filter_accounting_entries_for_check(self, check_transactions: List[Dict[str, Any]], selected_bank_id: int, normalized_date: str, amount: float, entry_type: str) -> List[Dict[str, Any]]:
        """
        Filter accounting entries based on check transactions.

        Parameters:
            check_transactions: List of unreconciled check transactions.
            normalized_date: Normalized date (YYYYMMDD).
            amount: Amount to search for.
            entry_type: Type of accounting entry.

        Returns:
            List of matching accounting entries.
        """
        matching_entries = []
        for record in check_transactions:
            # Normalize date for comparison
            record_date = utils.convert_date_format(record.get('Date_Of_Receipt', ''), 'YYYY/MM/DD', 'YYYYMMDD')
            
            if (record_date == normalized_date and
                record.get('Price') == amount and
                record.get('Entry_Type_Acc') == entry_type):
                matching_entries.append(record)
                
        return matching_entries

    def _filter_by_check_number(self, bank_record: Dict[str, Any], acc_records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Filter accounting records by check number."""
        bank_check_no = bank_record.get('Extracted_Check_No')
        if not bank_check_no:
            return []
        logger.debug(f"Filtering by check number: {bank_check_no}")
        return [rec for rec in acc_records if str(rec.get('Check_No')) == str(bank_check_no)]

    def _search_pos_transactions(self, terminal_id: str, date: str, amount: float) -> List[Dict[str, Any]]:
        """Search for matching POS transactions."""
        logger.debug(f"Searching for POS transaction: terminal_id={terminal_id}, date={date}, amount={amount}")
        return self.db_manager.find_matching_pos_transactions(terminal_id, date, amount)

    def _get_terminal_details(self, terminal_id: str) -> Optional[Dict[str, Any]]:
        """Get terminal details from the database."""
        logger.debug(f"Getting details for terminal: {terminal_id}")
        return self.db_manager.get_terminal_by_id(terminal_id)