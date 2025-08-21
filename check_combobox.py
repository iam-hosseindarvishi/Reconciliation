import tkinter as tk
from tkinter import ttk
from database.banks_repository import get_all_banks

# ایجاد پنجره اصلی
root = tk.Tk()
root.title("بررسی کامبوباکس")
root.geometry("400x200")

# تنظیم فونت
default_font = ('B Nazanin', 11)

# ایجاد متغیر برای کامبوباکس
selected_bank_var = tk.StringVar()

# ایجاد کامبوباکس
ttk.Label(root, text="انتخاب بانک:").pack(pady=10)
bank_combobox = ttk.Combobox(root, textvariable=selected_bank_var, state="readonly", width=30)
bank_combobox.pack(pady=10)

# بارگذاری بانک‌ها
banks = get_all_banks()
bank_names = [bank['bank_name'] for bank in banks]
print("مقادیر کامبوباکس:", bank_names)
bank_combobox['values'] = bank_names

# تنظیم مقدار پیش‌فرض
if bank_names:
    bank_combobox.current(0)
    selected_bank_var.set(bank_names[0])
    print("مقدار انتخاب شده:", selected_bank_var.get())

# نمایش مقدار انتخاب شده
def show_selected():
    print("مقدار انتخاب شده:", selected_bank_var.get())
    selected_label.config(text=f"بانک انتخاب شده: {selected_bank_var.get()}")

ttk.Button(root, text="نمایش مقدار انتخاب شده", command=show_selected).pack(pady=10)
selected_label = ttk.Label(root, text="")
selected_label.pack(pady=10)

# اجرای حلقه اصلی
root.mainloop()