from tkinter import ttk
import tkinter as tk

class ManualReconciliationDialog(tk.Toplevel):
    def __init__(self, parent, matches):
        super().__init__(parent)
        self.title("انتخاب رکورد حسابداری")
        self.geometry("800x400")
        self.matches = matches
        self.selected_match = None

        self.create_widgets()
        self.populate_table()

    def create_widgets(self):
        self.tree = ttk.Treeview(self, columns=("ID", "Date", "Amount", "Description"), show='headings')
        self.tree.heading("ID", text="شناسه")
        self.tree.heading("Date", text="تاریخ")
        self.tree.heading("Amount", text="مبلغ")
        self.tree.heading("Description", text="توضیحات")
        self.tree.pack(expand=True, fill='both')

        self.select_button = tk.Button(self, text="انتخاب و تایید", command=self.on_select)
        self.select_button.pack(pady=10)

    def populate_table(self):
        for match in self.matches:
            self.tree.insert("", "end", values=(match['id'], match['date'], match['amount'], match['description']))

    def on_select(self):
        selected_item = self.tree.selection()
        if selected_item:
            item = self.tree.item(selected_item)
            selected_id = item['values'][0]
            self.selected_match = next((m for m in self.matches if m['id'] == selected_id), None)
            self.destroy()

    def show(self):
        self.grab_set()
        self.wait_window()
        return self.selected_match