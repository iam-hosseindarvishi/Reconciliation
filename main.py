import ttkbootstrap as ttk
from config.settings import WINDOW_WIDTH, WINDOW_HEIGHT, WINDOW_RESIZABLE
from database.init_db import init_db
from ui.bank_tab import BankTab

init_db()

app = ttk.Window(themename="cosmo")
app.title("مدیریت مغایرت‌گیری")
app.geometry(f"{WINDOW_WIDTH}x{WINDOW_HEIGHT}")
app.resizable(WINDOW_RESIZABLE, WINDOW_RESIZABLE)

notebook = ttk.Notebook(app)
notebook.pack(fill="both", expand=True)

# افزودن تب مدیریت بانک‌ها
bank_tab = BankTab(notebook)
notebook.add(bank_tab, text="مدیریت بانک‌ها")

# (در آینده: افزودن تب‌های دیگر)

app.mainloop()
