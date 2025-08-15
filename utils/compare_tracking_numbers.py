# file: utils/compare_tracking_numbers.py

def compare_tracking_numbers(bank_tracking_number, accounting_tracking_number):
    """
    Compares two tracking numbers by matching the last digits of the bank tracking number.

    Args:
        bank_tracking_number (str): The full tracking number from the bank.
        accounting_tracking_number (str): The possibly shorter tracking number from the accounting system.

    Returns:
        bool: True if the last digits match, False otherwise.
    """
    if not isinstance(bank_tracking_number, str) or not isinstance(accounting_tracking_number, str):
        return False

    len_acc = len(accounting_tracking_number)

    if len(bank_tracking_number) >= len_acc:
        # Get the last 'len_acc' digits from the bank tracking number
        last_digits_of_bank = bank_tracking_number[-len_acc:]
        return last_digits_of_bank == accounting_tracking_number

    return False

# Example usage:
# bank_num = "460813739"
# acc_num1 = "3739"
# acc_num2 = "13739"
# print(f"Comparing '{bank_num}' and '{acc_num1}': {compare_tracking_numbers(bank_num, acc_num1)}")  # Output: True
# print(f"Comparing '{bank_num}' and '{acc_num2}': {compare_tracking_numbers(bank_num, acc_num2)}")  # Output: True
