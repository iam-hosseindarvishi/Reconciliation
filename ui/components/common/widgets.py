"""
Common UI Widgets Module
کامپوننت‌های مشترک UI برای استفاده در اجزای مختلف
"""
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import jdatetime
from datetime import datetime
import logging


class PersianDatePicker(tk.Frame):
    """ویجت انتخاب تاریخ فارسی"""
    
    def __init__(self, parent, **kwargs):
        super().__init__(parent, **kwargs)
        
        self.selected_date = None
        self._setup_ui()
    
    def _setup_ui(self):
        """راه‌اندازی رابط کاربری"""
        # Year dropdown
        tk.Label(self, text="سال:").pack(side=tk.LEFT, padx=2)
        
        self.year_var = tk.StringVar()
        self.year_combo = ttk.Combobox(self, textvariable=self.year_var, width=6, state="readonly")
        
        # پر کردن سال‌ها (از 1380 تا سال جاری + 5)
        current_year = jdatetime.datetime.now().year
        years = [str(year) for year in range(1380, current_year + 6)]
        self.year_combo['values'] = years
        self.year_combo.set(str(current_year))
        self.year_combo.pack(side=tk.LEFT, padx=2)
        
        # Month dropdown
        tk.Label(self, text="ماه:").pack(side=tk.LEFT, padx=2)
        
        self.month_var = tk.StringVar()
        self.month_combo = ttk.Combobox(self, textvariable=self.month_var, width=8, state="readonly")
        
        months = ["فروردین", "اردیبهشت", "خرداد", "تیر", "مرداد", "شهریور",
                 "مهر", "آبان", "آذر", "دی", "بهمن", "اسفند"]
        self.month_combo['values'] = months
        self.month_combo.set("فروردین")
        self.month_combo.pack(side=tk.LEFT, padx=2)
        
        # Day dropdown
        tk.Label(self, text="روز:").pack(side=tk.LEFT, padx=2)
        
        self.day_var = tk.StringVar()
        self.day_combo = ttk.Combobox(self, textvariable=self.day_var, width=4, state="readonly")
        self._update_days()
        self.day_combo.pack(side=tk.LEFT, padx=2)
        
        # Event bindings
        self.year_combo.bind('<<ComboboxSelected>>', self._on_date_change)
        self.month_combo.bind('<<ComboboxSelected>>', self._on_date_change)
        self.day_combo.bind('<<ComboboxSelected>>', self._on_date_change)
    
    def _update_days(self):
        """به‌روزرسانی روزهای ماه"""
        try:
            year = int(self.year_var.get()) if self.year_var.get() else jdatetime.datetime.now().year
            month_name = self.month_var.get()
            month = ["فروردین", "اردیبهشت", "خرداد", "تیر", "مرداد", "شهریور",
                    "مهر", "آبان", "آذر", "دی", "بهمن", "اسفند"].index(month_name) + 1 if month_name else 1
            
            # تعداد روزهای هر ماه
            if month <= 6:
                max_days = 31
            elif month <= 11:
                max_days = 30
            else:  # اسفند
                max_days = 30 if jdatetime.j_y_is_leap(year) else 29
            
            days = [str(day) for day in range(1, max_days + 1)]
            self.day_combo['values'] = days
            
            # تنظیم روز پیش‌فرض
            if not self.day_var.get() or int(self.day_var.get()) > max_days:
                self.day_combo.set("1")
                
        except (ValueError, IndexError):
            self.day_combo['values'] = [str(day) for day in range(1, 32)]
            self.day_combo.set("1")
    
    def _on_date_change(self, event=None):
        """رویداد تغییر تاریخ"""
        self._update_days()
        self._update_selected_date()
    
    def _update_selected_date(self):
        """به‌روزرسانی تاریخ انتخاب شده"""
        try:
            year = int(self.year_var.get())
            month_name = self.month_var.get()
            month = ["فروردین", "اردیبهشت", "خرداد", "تیر", "مرداد", "شهریور",
                    "مهر", "آبان", "آذر", "دی", "بهمن", "اسفند"].index(month_name) + 1
            day = int(self.day_var.get())
            
            self.selected_date = f"{year}/{month:02d}/{day:02d}"
            
        except (ValueError, IndexError):
            self.selected_date = None
    
    def get_date(self):
        """دریافت تاریخ انتخاب شده"""
        return self.selected_date
    
    def set_date(self, date_str):
        """تنظیم تاریخ"""
        try:
            if "/" in date_str:
                parts = date_str.split("/")
                if len(parts) == 3:
                    year, month, day = parts
                    self.year_var.set(year)
                    
                    months = ["فروردین", "اردیبهشت", "خرداد", "تیر", "مرداد", "شهریور",
                             "مهر", "آبان", "آذر", "دی", "بهمن", "اسفند"]
                    self.month_var.set(months[int(month) - 1])
                    
                    self._update_days()
                    self.day_var.set(str(int(day)))
                    self._update_selected_date()
        except (ValueError, IndexError):
            pass


class SearchBox(tk.Frame):
    """ویجت جعبه جستجو"""
    
    def __init__(self, parent, on_search=None, placeholder="جستجو...", **kwargs):
        super().__init__(parent, **kwargs)
        
        self.on_search = on_search
        self.placeholder = placeholder
        self._setup_ui()
    
    def _setup_ui(self):
        """راه‌اندازی رابط کاربری"""
        # Entry field
        self.search_var = tk.StringVar()
        self.search_entry = tk.Entry(self, textvariable=self.search_var, width=30)
        self.search_entry.pack(side=tk.LEFT, padx=2)
        
        # Search button
        self.search_btn = tk.Button(self, text="جستجو", command=self._on_search_click)
        self.search_btn.pack(side=tk.LEFT, padx=2)
        
        # Clear button
        self.clear_btn = tk.Button(self, text="پاک کردن", command=self._on_clear_click)
        self.clear_btn.pack(side=tk.LEFT, padx=2)
        
        # Placeholder functionality
        self._add_placeholder()
        
        # Event bindings
        self.search_entry.bind('<Return>', lambda e: self._on_search_click())
        self.search_entry.bind('<FocusIn>', self._on_focus_in)
        self.search_entry.bind('<FocusOut>', self._on_focus_out)
    
    def _add_placeholder(self):
        """اضافه کردن placeholder"""
        self.search_entry.insert(0, self.placeholder)
        self.search_entry.config(fg='grey')
    
    def _on_focus_in(self, event):
        """رویداد focus کردن"""
        if self.search_var.get() == self.placeholder:
            self.search_entry.delete(0, tk.END)
            self.search_entry.config(fg='black')
    
    def _on_focus_out(self, event):
        """رویداد از دست دادن focus"""
        if not self.search_var.get():
            self._add_placeholder()
    
    def _on_search_click(self):
        """رویداد کلیک جستجو"""
        search_text = self.search_var.get()
        if search_text and search_text != self.placeholder and self.on_search:
            self.on_search(search_text)
    
    def _on_clear_click(self):
        """رویداد پاک کردن"""
        self.search_entry.delete(0, tk.END)
        self._add_placeholder()
        if self.on_search:
            self.on_search("")
    
    def get_text(self):
        """دریافت متن جستجو"""
        text = self.search_var.get()
        return text if text != self.placeholder else ""
    
    def set_text(self, text):
        """تنظیم متن جستجو"""
        self.search_entry.delete(0, tk.END)
        if text:
            self.search_entry.insert(0, text)
            self.search_entry.config(fg='black')
        else:
            self._add_placeholder()


class StatusBar(tk.Frame):
    """نوار وضعیت"""
    
    def __init__(self, parent, **kwargs):
        super().__init__(parent, relief=tk.SUNKEN, bd=1, **kwargs)
        
        self.status_var = tk.StringVar()
        self.status_var.set("آماده")
        
        self._setup_ui()
    
    def _setup_ui(self):
        """راه‌اندازی رابط کاربری"""
        # Status label
        self.status_label = tk.Label(self, textvariable=self.status_var, anchor=tk.W)
        self.status_label.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        
        # Progress bar (hidden by default)
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(self, variable=self.progress_var, length=200)
        
        # Time label
        self.time_var = tk.StringVar()
        self.time_label = tk.Label(self, textvariable=self.time_var, width=20)
        self.time_label.pack(side=tk.RIGHT, padx=5)
        
        # Update time every second
        self._update_time()
    
    def set_status(self, message):
        """تنظیم پیام وضعیت"""
        self.status_var.set(str(message))
        self.update_idletasks()
    
    def show_progress(self, show=True):
        """نمایش/مخفی کردن progress bar"""
        if show:
            self.progress_bar.pack(side=tk.RIGHT, padx=5)
        else:
            self.progress_bar.pack_forget()
    
    def set_progress(self, value):
        """تنظیم مقدار progress bar (0-100)"""
        self.progress_var.set(value)
        self.update_idletasks()
    
    def _update_time(self):
        """به‌روزرسانی زمان"""
        try:
            current_time = jdatetime.datetime.now().strftime("%H:%M:%S")
            self.time_var.set(current_time)
        except:
            current_time = datetime.now().strftime("%H:%M:%S")
            self.time_var.set(current_time)
        
        # تکرار هر 1000 میلی‌ثانیه
        self.after(1000, self._update_time)


class FilterPanel(tk.Frame):
    """پانل فیلترها"""
    
    def __init__(self, parent, filters_config, on_filter_change=None, **kwargs):
        super().__init__(parent, **kwargs)
        
        self.filters_config = filters_config
        self.on_filter_change = on_filter_change
        self.filter_widgets = {}
        
        self._setup_ui()
    
    def _setup_ui(self):
        """راه‌اندازی رابط کاربری"""
        # Title
        title_frame = tk.Frame(self)
        title_frame.pack(fill=tk.X, padx=5, pady=2)
        
        tk.Label(title_frame, text="فیلترها", font=("Arial", 10, "bold")).pack(side=tk.LEFT)
        
        # Clear all button
        clear_btn = tk.Button(title_frame, text="پاک کردن همه", 
                            command=self._clear_all_filters)
        clear_btn.pack(side=tk.RIGHT)
        
        # Filters frame
        filters_frame = tk.Frame(self)
        filters_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Create filter widgets
        for i, (filter_name, config) in enumerate(self.filters_config.items()):
            self._create_filter_widget(filters_frame, filter_name, config, i)
    
    def _create_filter_widget(self, parent, filter_name, config, row):
        """ایجاد ویجت فیلتر"""
        filter_type = config.get('type', 'text')
        label = config.get('label', filter_name)
        
        # Label
        tk.Label(parent, text=f"{label}:").grid(row=row, column=0, sticky=tk.W, padx=2, pady=2)
        
        if filter_type == 'text':
            var = tk.StringVar()
            widget = tk.Entry(parent, textvariable=var, width=20)
            
        elif filter_type == 'combobox':
            var = tk.StringVar()
            widget = ttk.Combobox(parent, textvariable=var, width=17, state="readonly")
            widget['values'] = config.get('values', [])
            if widget['values']:
                widget.set(widget['values'][0])
        
        elif filter_type == 'date':
            var = tk.StringVar()
            widget = PersianDatePicker(parent)
            
        elif filter_type == 'number':
            var = tk.DoubleVar()
            widget = tk.Entry(parent, textvariable=var, width=20)
        
        else:
            var = tk.StringVar()
            widget = tk.Entry(parent, textvariable=var, width=20)
        
        widget.grid(row=row, column=1, sticky=tk.W, padx=2, pady=2)
        
        # Store widget reference
        self.filter_widgets[filter_name] = {
            'widget': widget,
            'variable': var,
            'type': filter_type
        }
        
        # Bind change event
        if filter_type == 'combobox':
            widget.bind('<<ComboboxSelected>>', lambda e, name=filter_name: self._on_filter_change(name))
        elif filter_type == 'date':
            # Date picker has its own change handling
            pass
        else:
            var.trace_add('write', lambda *args, name=filter_name: self._on_filter_change(name))
    
    def _on_filter_change(self, filter_name):
        """رویداد تغییر فیلتر"""
        if self.on_filter_change:
            self.on_filter_change(filter_name, self.get_filter_values())
    
    def get_filter_values(self):
        """دریافت مقادیر فیلترها"""
        values = {}
        
        for filter_name, widget_info in self.filter_widgets.items():
            if widget_info['type'] == 'date':
                values[filter_name] = widget_info['widget'].get_date()
            else:
                var_value = widget_info['variable'].get()
                values[filter_name] = var_value if var_value else None
        
        return values
    
    def set_filter_value(self, filter_name, value):
        """تنظیم مقدار فیلتر"""
        if filter_name in self.filter_widgets:
            widget_info = self.filter_widgets[filter_name]
            
            if widget_info['type'] == 'date':
                widget_info['widget'].set_date(str(value))
            else:
                widget_info['variable'].set(value)
    
    def _clear_all_filters(self):
        """پاک کردن همه فیلترها"""
        for filter_name, widget_info in self.filter_widgets.items():
            if widget_info['type'] == 'combobox':
                values = widget_info['widget']['values']
                if values:
                    widget_info['variable'].set(values[0])
            elif widget_info['type'] == 'date':
                # Reset to current date
                current_date = jdatetime.datetime.now().strftime("%Y/%m/%d")
                widget_info['widget'].set_date(current_date)
            else:
                widget_info['variable'].set("")
        
        # Notify change
        if self.on_filter_change:
            self.on_filter_change(None, self.get_filter_values())


class LoadingDialog:
    """دیالوگ لودینگ"""
    
    def __init__(self, parent, title="در حال پردازش...", message="لطفاً صبر کنید..."):
        self.parent = parent
        self.dialog = None
        self.title = title
        self.message = message
        self.progress_var = tk.DoubleVar()
        
    def show(self, progress=False):
        """نمایش دیالوگ"""
        self.dialog = tk.Toplevel(self.parent)
        self.dialog.title(self.title)
        self.dialog.geometry("300x120")
        self.dialog.resizable(False, False)
        self.dialog.transient(self.parent)
        self.dialog.grab_set()
        
        # Center the dialog
        self.dialog.geometry("+%d+%d" % (
            self.parent.winfo_rootx() + 50,
            self.parent.winfo_rooty() + 50
        ))
        
        # Message
        tk.Label(self.dialog, text=self.message, font=("Arial", 10)).pack(pady=20)
        
        # Progress bar
        if progress:
            self.progress_bar = ttk.Progressbar(
                self.dialog, 
                variable=self.progress_var, 
                length=250, 
                mode='determinate'
            )
            self.progress_bar.pack(pady=10)
        else:
            # Indeterminate progress bar
            self.progress_bar = ttk.Progressbar(
                self.dialog, 
                length=250, 
                mode='indeterminate'
            )
            self.progress_bar.pack(pady=10)
            self.progress_bar.start()
        
        self.dialog.update()
    
    def update_progress(self, value, message=None):
        """به‌روزرسانی پیشرفت"""
        if self.dialog:
            self.progress_var.set(value)
            if message:
                # Update message if needed
                pass
            self.dialog.update()
    
    def close(self):
        """بستن دیالوگ"""
        if self.dialog:
            self.progress_bar.stop()
            self.dialog.destroy()
            self.dialog = None


def show_confirmation_dialog(parent, title, message):
    """نمایش دیالوگ تأیید"""
    return messagebox.askyesno(title, message, parent=parent)


def show_info_dialog(parent, title, message):
    """نمایش دیالوگ اطلاعات"""
    messagebox.showinfo(title, message, parent=parent)


def show_error_dialog(parent, title, message):
    """نمایش دیالوگ خطا"""
    messagebox.showerror(title, message, parent=parent)


def show_warning_dialog(parent, title, message):
    """نمایش دیالوگ هشدار"""
    messagebox.showwarning(title, message, parent=parent)


def select_file_dialog(parent, title="انتخاب فایل", filetypes=None):
    """دیالوگ انتخاب فایل"""
    if not filetypes:
        filetypes = [("همه فایل‌ها", "*.*")]
    
    return filedialog.askopenfilename(
        parent=parent,
        title=title,
        filetypes=filetypes
    )


def select_directory_dialog(parent, title="انتخاب پوشه"):
    """دیالوگ انتخاب پوشه"""
    return filedialog.askdirectory(parent=parent, title=title)


def save_file_dialog(parent, title="ذخیره فایل", defaultextension=".txt", filetypes=None):
    """دیالوگ ذخیره فایل"""
    if not filetypes:
        filetypes = [("همه فایل‌ها", "*.*")]
    
    return filedialog.asksaveasfilename(
        parent=parent,
        title=title,
        defaultextension=defaultextension,
        filetypes=filetypes
    )
