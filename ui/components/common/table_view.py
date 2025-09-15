"""
Table View Module
کامپوننت نمایش داده‌ها در قالب جدول
"""
import tkinter as tk
from tkinter import ttk
import logging
from functools import partial


class TableView(tk.Frame):
    """کلاس نمایش داده‌ها در قالب جدول"""
    
    def __init__(self, parent, columns=None, data=None, height=20, select_mode="browse", 
                 on_row_select=None, on_header_click=None, **kwargs):
        """
        ایجاد جدول برای نمایش داده‌ها
        
        Args:
            parent: ویجت والد
            columns: تنظیمات ستون‌ها (لیستی از دیکشنری‌ها با کلیدهای id، text، width)
            data: داده‌های اولیه
            height: ارتفاع جدول (به تعداد ردیف)
            select_mode: حالت انتخاب ("browse", "extended", "none")
            on_row_select: تابع callback برای رویداد انتخاب ردیف
            on_header_click: تابع callback برای رویداد کلیک روی هدر
        """
        super().__init__(parent, **kwargs)
        
        self.columns = columns or []
        self.data = data or []
        self.height = height
        self.select_mode = select_mode
        self.on_row_select = on_row_select
        self.on_header_click = on_header_click
        self.logger = logging.getLogger(__name__)
        
        self.tree = None
        self.scrollbar_y = None
        self.scrollbar_x = None
        self.sort_column = None
        self.sort_ascending = True
        
        self._setup_ui()
    
    def _setup_ui(self):
        """راه‌اندازی رابط کاربری"""
        # Frame for treeview and scrollbars
        table_frame = tk.Frame(self)
        table_frame.pack(fill=tk.BOTH, expand=True)
        
        # Scrollbars
        self.scrollbar_y = tk.Scrollbar(table_frame, orient=tk.VERTICAL)
        self.scrollbar_y.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.scrollbar_x = tk.Scrollbar(table_frame, orient=tk.HORIZONTAL)
        self.scrollbar_x.pack(side=tk.BOTTOM, fill=tk.X)
        
        # Treeview
        self.tree = ttk.Treeview(
            table_frame,
            columns=[col['id'] for col in self.columns],
            show='headings',
            height=self.height,
            selectmode=self.select_mode,
            yscrollcommand=self.scrollbar_y.set,
            xscrollcommand=self.scrollbar_x.set
        )
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # Configure scrollbars
        self.scrollbar_y.config(command=self.tree.yview)
        self.scrollbar_x.config(command=self.tree.xview)
        
        # Setup columns
        for col in self.columns:
            self.tree.heading(
                col['id'], 
                text=col['text'],
                command=lambda c=col['id']: self._on_header_click(c)
            )
            width = col.get('width', 100)
            self.tree.column(col['id'], width=width, minwidth=50)
        
        # Setup striped rows
        self.tree.tag_configure('oddrow', background='#F9F9F9')
        self.tree.tag_configure('evenrow', background='white')
        
        # Highlight selected row
        style = ttk.Style()
        style.map('Treeview', 
                 foreground=[('selected', 'black')],
                 background=[('selected', '#c1e0ff')])
        
        # Load initial data
        self.load_data(self.data)
        
        # Event bindings
        self.tree.bind('<<TreeviewSelect>>', self._on_row_select)
    
    def load_data(self, data):
        """
        بارگذاری داده‌ها در جدول
        
        Args:
            data: لیست داده‌ها
        """
        # Clear existing data
        self.clear()
        self.data = data
        
        # No data to display
        if not data:
            return
        
        # Insert data into treeview
        for i, item in enumerate(data):
            row_values = []
            for col in self.columns:
                col_id = col['id']
                # استفاده از get برای دریافت مقدار با امکان مقدار پیش‌فرض
                val = item.get(col_id, '')
                row_values.append(val)
            
            # اضافه کردن ردیف با رنگ متناوب
            tag = 'oddrow' if i % 2 == 1 else 'evenrow'
            self.tree.insert('', tk.END, values=row_values, tags=(tag,))
    
    def clear(self):
        """پاک کردن تمام داده‌های جدول"""
        for item in self.tree.get_children():
            self.tree.delete(item)
    
    def get_selected_row(self):
        """دریافت داده‌های ردیف انتخاب شده"""
        selected_items = self.tree.selection()
        if not selected_items:
            return None
        
        selected_idx = self.tree.index(selected_items[0])
        if 0 <= selected_idx < len(self.data):
            return self.data[selected_idx]
        
        return None
    
    def get_selected_rows(self):
        """دریافت تمام داده‌های ردیف‌های انتخاب شده"""
        selected_items = self.tree.selection()
        if not selected_items:
            return []
        
        selected_rows = []
        for item in selected_items:
            idx = self.tree.index(item)
            if 0 <= idx < len(self.data):
                selected_rows.append(self.data[idx])
        
        return selected_rows
    
    def select_row(self, index):
        """انتخاب ردیف با ایندکس مشخص"""
        if not self.tree.get_children():
            return
        
        try:
            idx = int(index)
            if idx < 0:
                idx = 0
            
            items = self.tree.get_children()
            if idx >= len(items):
                idx = len(items) - 1
            
            item_id = items[idx]
            
            # انتخاب آیتم
            self.tree.selection_set(item_id)
            # اسکرول به آیتم
            self.tree.see(item_id)
            
        except (ValueError, IndexError) as e:
            self.logger.debug(f"خطا در انتخاب ردیف: {str(e)}")
    
    def _on_row_select(self, event):
        """رویداد انتخاب ردیف"""
        if self.on_row_select:
            selected_row = self.get_selected_row()
            self.on_row_select(selected_row)
    
    def _on_header_click(self, column):
        """رویداد کلیک روی هدر"""
        # Toggle sort direction if clicking on the same column
        if self.sort_column == column:
            self.sort_ascending = not self.sort_ascending
        else:
            self.sort_column = column
            self.sort_ascending = True
        
        # Call callback if provided
        if self.on_header_click:
            self.on_header_click(column, self.sort_ascending)
    
    def get_sort_info(self):
        """دریافت اطلاعات مرتب‌سازی فعلی"""
        return {
            'column': self.sort_column,
            'ascending': self.sort_ascending
        }
    
    def update_row(self, row_index, data):
        """به‌روزرسانی یک ردیف در جدول"""
        if row_index < 0 or row_index >= len(self.data):
            return False
        
        try:
            # Update data
            self.data[row_index] = data
            
            # Update treeview
            items = self.tree.get_children()
            if row_index < len(items):
                item_id = items[row_index]
                
                # Prepare values
                row_values = []
                for col in self.columns:
                    col_id = col['id']
                    val = data.get(col_id, '')
                    row_values.append(val)
                
                # Update item
                self.tree.item(item_id, values=row_values)
                return True
                
        except Exception as e:
            self.logger.error(f"خطا در به‌روزرسانی ردیف: {str(e)}")
            return False
    
    def insert_row(self, data, index=None):
        """اضافه کردن یک ردیف به جدول"""
        try:
            # Prepare values
            row_values = []
            for col in self.columns:
                col_id = col['id']
                val = data.get(col_id, '')
                row_values.append(val)
            
            # Determine index
            if index is None or index >= len(self.data):
                # Add to end
                self.data.append(data)
                idx = len(self.data) - 1
                tag = 'oddrow' if idx % 2 == 1 else 'evenrow'
                self.tree.insert('', tk.END, values=row_values, tags=(tag,))
            else:
                # Insert at specific position
                if index < 0:
                    index = 0
                
                self.data.insert(index, data)
                
                # Clear and reload data to maintain striped pattern
                self.load_data(self.data)
            
            return True
            
        except Exception as e:
            self.logger.error(f"خطا در اضافه کردن ردیف: {str(e)}")
            return False
    
    def delete_row(self, index):
        """حذف یک ردیف از جدول"""
        if index < 0 or index >= len(self.data):
            return False
        
        try:
            # Remove from data
            self.data.pop(index)
            
            # Remove from treeview
            items = self.tree.get_children()
            if index < len(items):
                item_id = items[index]
                self.tree.delete(item_id)
                
                # Update striped pattern
                self.load_data(self.data)
                
            return True
            
        except Exception as e:
            self.logger.error(f"خطا در حذف ردیف: {str(e)}")
            return False
    
    def resize_column(self, column_id, width):
        """تغییر عرض ستون"""
        try:
            self.tree.column(column_id, width=width)
            return True
        except Exception as e:
            self.logger.error(f"خطا در تغییر عرض ستون: {str(e)}")
            return False
    
    def get_visible_rows(self):
        """دریافت داده‌های ردیف‌های قابل مشاهده"""
        try:
            # Get first and last visible items
            first_visible = self.tree.identify_row(0)
            last_visible = self.tree.identify_row(self.winfo_height())
            
            if not first_visible or not last_visible:
                return []
            
            first_idx = self.tree.index(first_visible)
            last_idx = self.tree.index(last_visible)
            
            # Return slice of data
            return self.data[first_idx:last_idx+1]
            
        except Exception as e:
            self.logger.error(f"خطا در دریافت ردیف‌های قابل مشاهده: {str(e)}")
            return []
    
    def highlight_row(self, index, highlight=True):
        """برجسته کردن یک ردیف"""
        if index < 0 or index >= len(self.data):
            return False
        
        try:
            items = self.tree.get_children()
            if index < len(items):
                item_id = items[index]
                
                if highlight:
                    self.tree.item(item_id, tags=('highlight',))
                    self.tree.tag_configure('highlight', background='#ffffcc')
                else:
                    tag = 'oddrow' if index % 2 == 1 else 'evenrow'
                    self.tree.item(item_id, tags=(tag,))
                
                return True
                
        except Exception as e:
            self.logger.error(f"خطا در برجسته کردن ردیف: {str(e)}")
            return False
    
    def search_in_data(self, search_text, columns=None):
        """جستجو در داده‌های جدول"""
        if not search_text:
            return []
        
        search_text = search_text.lower()
        search_columns = columns or [col['id'] for col in self.columns]
        results = []
        
        for i, item in enumerate(self.data):
            for col_id in search_columns:
                if col_id in item:
                    cell_value = str(item[col_id]).lower()
                    if search_text in cell_value:
                        results.append((i, item))
                        break
        
        return results
    
    def get_all_data(self):
        """دریافت تمام داده‌های جدول"""
        return self.data
    
    def set_column_width(self, column_id, width):
        """تنظیم عرض ستون"""
        try:
            self.tree.column(column_id, width=width)
        except Exception as e:
            self.logger.error(f"خطا در تنظیم عرض ستون: {str(e)}")
    
    def auto_resize_columns(self):
        """تنظیم خودکار عرض ستون‌ها بر اساس محتوا"""
        try:
            if not self.tree.get_children():
                return
            
            for col in self.columns:
                col_id = col['id']
                # حداقل عرض برای نمایش عنوان ستون
                header_width = len(col['text']) * 10
                
                # محاسبه عرض مورد نیاز برای داده‌ها
                max_width = header_width
                for item in self.data:
                    if col_id in item:
                        cell_width = len(str(item[col_id])) * 8
                        max_width = max(max_width, cell_width)
                
                # محدود کردن حداکثر عرض
                max_width = min(max_width, 300)
                
                # تنظیم عرض ستون
                self.tree.column(col_id, width=max_width)
                
        except Exception as e:
            self.logger.error(f"خطا در تنظیم خودکار عرض ستون‌ها: {str(e)}")
