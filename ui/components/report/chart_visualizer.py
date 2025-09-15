"""
Chart Visualization Module
جدا شده از report_tab.py برای ماژولار کردن کد
"""
import logging
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import tkinter as tk
from tkinter import messagebox
import jdatetime
from datetime import datetime
import pandas as pd
import seaborn as sns
from collections import Counter


class ChartVisualizer:
    """کلاس تجسم داده‌ها و ایجاد نمودار"""
    
    def __init__(self, parent_frame, logger=None):
        self.parent_frame = parent_frame
        self.logger = logger or logging.getLogger(__name__)
        self.canvas = None
        self.figure = None
        
        # تنظیم فونت فارسی برای matplotlib
        self._setup_persian_font()
    
    def _setup_persian_font(self):
        """تنظیم فونت فارسی برای matplotlib"""
        try:
            import matplotlib.font_manager as fm
            
            # تلاش برای یافتن فونت فارسی
            persian_fonts = ['Vazir', 'Tahoma', 'B Nazanin', 'IRANSans']
            
            for font_name in persian_fonts:
                try:
                    plt.rcParams['font.family'] = font_name
                    # تست کردن فونت
                    fig, ax = plt.subplots(figsize=(1, 1))
                    ax.text(0.5, 0.5, 'تست', fontsize=12)
                    plt.close(fig)
                    self.logger.info(f"فونت {font_name} با موفقیت تنظیم شد")
                    break
                except:
                    continue
            else:
                # در صورت عدم دسترسی به فونت فارسی
                plt.rcParams['font.family'] = 'DejaVu Sans'
                self.logger.warning("فونت فارسی یافت نشد، از فونت پیش‌فرض استفاده می‌شود")
                
        except Exception as e:
            self.logger.error(f"خطا در تنظیم فونت: {str(e)}")
    
    def create_transaction_chart(self, data, chart_type="bar", title="نمودار تراکنش‌ها"):
        """ایجاد نمودار تراکنش‌ها"""
        try:
            if not data:
                messagebox.showwarning("هشدار", "هیچ داده‌ای برای نمایش نمودار وجود ندارد")
                return False
            
            # پاک کردن نمودار قبلی
            self._clear_previous_chart()
            
            # ایجاد figure جدید
            self.figure, ax = plt.subplots(figsize=(12, 6))
            
            if chart_type == "bar":
                self._create_bar_chart(data, ax, title)
            elif chart_type == "pie":
                self._create_pie_chart(data, ax, title)
            elif chart_type == "line":
                self._create_line_chart(data, ax, title)
            elif chart_type == "timeline":
                self._create_timeline_chart(data, ax, title)
            
            # تنظیم خصوصیات کلی
            plt.tight_layout()
            
            # نمایش نمودار در tkinter
            self._display_chart()
            
            return True
            
        except Exception as e:
            error_msg = f"خطا در ایجاد نمودار: {str(e)}"
            self.logger.error(error_msg)
            messagebox.showerror("خطا", error_msg)
            return False
    
    def _create_bar_chart(self, data, ax, title):
        """ایجاد نمودار میله‌ای"""
        # تحلیل داده‌ها برای نمودار میله‌ای
        if isinstance(data, list) and len(data) > 0:
            # اگر داده شامل تراکنش‌ها باشد
            if isinstance(data[0], dict):
                # نمودار تعداد تراکنش‌ها بر اساس بانک
                bank_counts = Counter()
                for transaction in data:
                    bank = transaction.get('bank_name', 'نامشخص')
                    bank_counts[bank] += 1
                
                banks = list(bank_counts.keys())
                counts = list(bank_counts.values())
                
                bars = ax.bar(banks, counts, color=['#FF9999', '#66B2FF', '#99FF99', '#FFCC99', '#FFB366'])
                
                # اضافه کردن عدد روی میله‌ها
                for bar, count in zip(bars, counts):
                    height = bar.get_height()
                    ax.text(bar.get_x() + bar.get_width()/2., height + 0.1,
                           f'{count}', ha='center', va='bottom')
                
                ax.set_ylabel('تعداد تراکنش')
                ax.set_xlabel('بانک')
            
        ax.set_title(title, fontsize=14, fontweight='bold')
        ax.grid(True, alpha=0.3)
    
    def _create_pie_chart(self, data, ax, title):
        """ایجاد نمودار دایره‌ای"""
        if isinstance(data, list) and len(data) > 0:
            if isinstance(data[0], dict):
                # نمودار درصد تراکنش‌ها بر اساس بانک
                bank_counts = Counter()
                for transaction in data:
                    bank = transaction.get('bank_name', 'نامشخص')
                    bank_counts[bank] += 1
                
                labels = list(bank_counts.keys())
                sizes = list(bank_counts.values())
                colors = ['#FF9999', '#66B2FF', '#99FF99', '#FFCC99', '#FFB366']
                
                # ایجاد نمودار دایره‌ای
                wedges, texts, autotexts = ax.pie(sizes, labels=labels, autopct='%1.1f%%', 
                                                 colors=colors[:len(labels)], startangle=90)
                
                # تنظیم خصوصیات متن
                for autotext in autotexts:
                    autotext.set_color('white')
                    autotext.set_fontweight('bold')
        
        ax.set_title(title, fontsize=14, fontweight='bold')
    
    def _create_line_chart(self, data, ax, title):
        """ایجاد نمودار خطی"""
        if isinstance(data, list) and len(data) > 0:
            if isinstance(data[0], dict):
                # تحلیل داده‌ها بر اساس زمان
                dates = []
                amounts = []
                
                for transaction in data:
                    try:
                        # تبدیل تاریخ
                        date_str = transaction.get('transaction_date', '')
                        if date_str:
                            # فرض می‌کنیم تاریخ در فرمت جلالی است
                            date_obj = self._parse_persian_date(date_str)
                            if date_obj:
                                dates.append(date_obj)
                                amount = float(transaction.get('amount', 0))
                                amounts.append(amount)
                    except:
                        continue
                
                if dates and amounts:
                    # مرتب‌سازی بر اساس تاریخ
                    sorted_data = sorted(zip(dates, amounts))
                    dates, amounts = zip(*sorted_data)
                    
                    ax.plot(dates, amounts, marker='o', linewidth=2, markersize=4)
                    ax.set_ylabel('مبلغ تراکنش')
                    ax.set_xlabel('تاریخ')
                    
                    # تنظیم فرمت تاریخ
                    ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y/%m/%d'))
                    ax.xaxis.set_major_locator(mdates.DayLocator(interval=7))
                    plt.setp(ax.xaxis.get_majorticklabels(), rotation=45)
        
        ax.set_title(title, fontsize=14, fontweight='bold')
        ax.grid(True, alpha=0.3)
    
    def _create_timeline_chart(self, data, ax, title):
        """ایجاد نمودار زمان‌بندی تراکنش‌ها"""
        if isinstance(data, list) and len(data) > 0:
            if isinstance(data[0], dict):
                # تحلیل تراکنش‌ها بر اساس ساعت
                hour_counts = Counter()
                
                for transaction in data:
                    try:
                        date_str = transaction.get('transaction_date', '')
                        if date_str:
                            # استخراج ساعت از تاریخ
                            hour = self._extract_hour_from_date(date_str)
                            if hour is not None:
                                hour_counts[hour] += 1
                    except:
                        continue
                
                if hour_counts:
                    hours = sorted(hour_counts.keys())
                    counts = [hour_counts[hour] for hour in hours]
                    
                    ax.bar(hours, counts, width=0.8, color='skyblue', alpha=0.7)
                    ax.set_xlabel('ساعت روز')
                    ax.set_ylabel('تعداد تراکنش')
                    ax.set_xticks(range(0, 24, 2))
        
        ax.set_title(title, fontsize=14, fontweight='bold')
        ax.grid(True, alpha=0.3)
    
    def _parse_persian_date(self, date_str):
        """تبدیل تاریخ فارسی به datetime"""
        try:
            # تلاش برای تبدیل تاریخ فارسی
            jalali_date = jdatetime.datetime.strptime(date_str, '%Y/%m/%d')
            gregorian_date = jalali_date.togregorian()
            return gregorian_date
        except:
            try:
                # تلاش برای تبدیل تاریخ میلادی
                return datetime.strptime(date_str, '%Y-%m-%d')
            except:
                return None
    
    def _extract_hour_from_date(self, date_str):
        """استخراج ساعت از رشته تاریخ"""
        try:
            # بررسی فرمت‌های مختلف
            formats = ['%Y/%m/%d %H:%M:%S', '%Y-%m-%d %H:%M:%S', '%H:%M:%S']
            
            for fmt in formats:
                try:
                    dt = datetime.strptime(date_str, fmt)
                    return dt.hour
                except:
                    continue
            
            # اگر فقط ساعت باشد
            if ':' in date_str:
                hour_part = date_str.split(':')[0]
                return int(hour_part)
                
        except:
            pass
        
        return None
    
    def _display_chart(self):
        """نمایش نمودار در tkinter"""
        # حذف canvas قبلی در صورت وجود
        if self.canvas:
            self.canvas.get_tk_widget().destroy()
        
        # ایجاد canvas جدید
        self.canvas = FigureCanvasTkinter(self.figure, master=self.parent_frame)
        self.canvas.draw()
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
    
    def _clear_previous_chart(self):
        """پاک کردن نمودار قبلی"""
        if self.figure:
            plt.close(self.figure)
            self.figure = None
        
        if self.canvas:
            self.canvas.get_tk_widget().destroy()
            self.canvas = None
    
    def export_chart(self, filename, format='png', dpi=300):
        """ذخیره نمودار به فایل"""
        try:
            if not self.figure:
                messagebox.showwarning("هشدار", "هیچ نموداری برای ذخیره وجود ندارد")
                return False
            
            self.figure.savefig(filename, format=format, dpi=dpi, bbox_inches='tight',
                              facecolor='white', edgecolor='none')
            
            self.logger.info(f"نمودار با موفقیت در {filename} ذخیره شد")
            return True
            
        except Exception as e:
            error_msg = f"خطا در ذخیره نمودار: {str(e)}"
            self.logger.error(error_msg)
            messagebox.showerror("خطا", error_msg)
            return False
    
    def create_summary_statistics_chart(self, data):
        """ایجاد نمودار آمار خلاصه"""
        try:
            if not data:
                return False
            
            self._clear_previous_chart()
            
            # ایجاد subplot های متعدد
            self.figure, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(15, 10))
            
            # نمودار 1: توزیع مبالغ
            amounts = [float(t.get('amount', 0)) for t in data if t.get('amount')]
            if amounts:
                ax1.hist(amounts, bins=20, color='lightblue', alpha=0.7, edgecolor='black')
                ax1.set_title('توزیع مبالغ تراکنش')
                ax1.set_xlabel('مبلغ')
                ax1.set_ylabel('تعداد')
                ax1.grid(True, alpha=0.3)
            
            # نمودار 2: تراکنش‌ها بر اساس بانک
            bank_counts = Counter(t.get('bank_name', 'نامشخص') for t in data)
            if bank_counts:
                banks = list(bank_counts.keys())
                counts = list(bank_counts.values())
                ax2.pie(counts, labels=banks, autopct='%1.1f%%', startangle=90)
                ax2.set_title('توزیع تراکنش‌ها بر اساس بانک')
            
            # نمودار 3: آمار روزانه
            daily_counts = self._get_daily_transaction_counts(data)
            if daily_counts:
                dates, counts = zip(*daily_counts.items())
                ax3.plot(dates, counts, marker='o', linewidth=2)
                ax3.set_title('تعداد تراکنش‌ها در روزهای مختلف')
                ax3.set_xlabel('تاریخ')
                ax3.set_ylabel('تعداد')
                ax3.grid(True, alpha=0.3)
            
            # نمودار 4: آمار نوع تراکنش
            type_counts = Counter(t.get('transaction_type', 'نامشخص') for t in data)
            if type_counts:
                types = list(type_counts.keys())
                counts = list(type_counts.values())
                ax4.bar(types, counts, color=['#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4'])
                ax4.set_title('تراکنش‌ها بر اساس نوع')
                ax4.set_xlabel('نوع تراکنش')
                ax4.set_ylabel('تعداد')
                ax4.tick_params(axis='x', rotation=45)
                ax4.grid(True, alpha=0.3)
            
            plt.tight_layout()
            self._display_chart()
            return True
            
        except Exception as e:
            error_msg = f"خطا در ایجاد نمودار آماری: {str(e)}"
            self.logger.error(error_msg)
            messagebox.showerror("خطا", error_msg)
            return False
    
    def _get_daily_transaction_counts(self, data):
        """محاسبه تعداد تراکنش‌های روزانه"""
        daily_counts = Counter()
        
        for transaction in data:
            try:
                date_str = transaction.get('transaction_date', '')
                if date_str:
                    # استخراج تاریخ بدون ساعت
                    date_only = date_str.split(' ')[0]
                    daily_counts[date_only] += 1
            except:
                continue
        
        return daily_counts
    
    def destroy(self):
        """پاک کردن منابع"""
        self._clear_previous_chart()
