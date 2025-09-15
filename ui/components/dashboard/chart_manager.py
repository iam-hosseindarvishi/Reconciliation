"""
Chart Manager Module
ماژول مدیریت نمودارها - جدا شده از dashboard_tab.py
"""
import os
import logging
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import arabic_reshaper
from bidi.algorithm import get_display


class ChartManager:
    """کلاس مدیریت نمودارهای داشبورد"""
    
    def __init__(self, logger=None):
        self.logger = logger or logging.getLogger(__name__)
        self._setup_persian_fonts()
    
    def _setup_persian_fonts(self):
        """تنظیم فونت فارسی برای matplotlib"""
        try:
            import matplotlib.font_manager as fm
            
            # مسیر فونت فارسی
            font_path = os.path.join(
                os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 
                'assets', 'fonts', 'Vazir.ttf'
            )
            
            if os.path.exists(font_path):
                fm.fontManager.addfont(font_path)
                plt.rcParams['font.family'] = 'Vazir, Tahoma'
                self.logger.info(f"فونت فارسی از مسیر {font_path} تنظیم شد")
            else:
                plt.rcParams['font.family'] = 'Tahoma'
                self.logger.warning("فونت Vazir یافت نشد، از Tahoma استفاده می‌شود")
            
            # تنظیمات اضافی برای نمایش صحیح فارسی
            plt.rcParams['axes.unicode_minus'] = False
            plt.rcParams['axes.formatter.use_locale'] = True
            plt.rcParams['text.color'] = 'black'
            
        except Exception as e:
            self.logger.error(f"خطا در تنظیم فونت فارسی: {str(e)}")
            plt.rcParams['font.family'] = 'Tahoma'
    
    def create_reconciliation_chart(self, stats_data, chart_frame, chart_type="bank"):
        """
        ایجاد نمودار وضعیت مغایرت‌گیری
        
        Args:
            stats_data: داده‌های آماری
            chart_frame: فریم برای نمایش نمودار
            chart_type: نوع نمودار ("bank", "accounting", "pos")
        """
        try:
            if not stats_data:
                self.logger.warning(f"داده‌ای برای نمودار {chart_type} وجود ندارد")
                return None
            
            # پاک کردن نمودار قبلی
            for widget in chart_frame.winfo_children():
                widget.destroy()
            
            # ایجاد figure جدید
            fig, ax = plt.subplots(figsize=(6, 4))
            
            # تبدیل نام‌های بانک به فرمت صحیح فارسی
            bank_names_original = [stat['bank_name'] for stat in stats_data]
            bank_names = [get_display(arabic_reshaper.reshape(name)) for name in bank_names_original]
            reconciled = [stat['reconciled_records'] for stat in stats_data]
            unreconciled = [stat['unreconciled_records'] for stat in stats_data]
            
            # ایجاد نمودار میله‌ای
            x = range(len(bank_names))
            width = 0.35
            
            # تبدیل برچسب‌ها به فرمت صحیح فارسی
            reshaped_label1 = get_display(arabic_reshaper.reshape('مغایرت‌گیری شده'))
            reshaped_label2 = get_display(arabic_reshaper.reshape('مغایرت‌گیری نشده'))
            
            ax.bar([i - width/2 for i in x], reconciled, width, 
                   label=reshaped_label1, color='#4CAF50', alpha=0.8)
            ax.bar([i + width/2 for i in x], unreconciled, width, 
                   label=reshaped_label2, color='#F44336', alpha=0.8)
            
            # تنظیم عناوین و برچسب‌ها
            reshaped_ylabel = get_display(arabic_reshaper.reshape('تعداد رکوردها'))
            
            chart_titles = {
                'bank': 'وضعیت مغایرت‌گیری بانک‌ها',
                'accounting': 'وضعیت مغایرت‌گیری حسابداری',
                'pos': 'وضعیت مغایرت‌گیری پوز'
            }
            
            reshaped_title = get_display(arabic_reshaper.reshape(chart_titles.get(chart_type, 'نمودار')))
            
            ax.set_ylabel(reshaped_ylabel)
            ax.set_title(reshaped_title, fontsize=12, fontweight='bold')
            ax.set_xticks(x)
            ax.set_xticklabels(bank_names, rotation=45, ha='right')
            ax.legend()
            ax.grid(True, alpha=0.3)
            
            # اضافه کردن مقادیر روی میله‌ها
            for i, (rec, unrec) in enumerate(zip(reconciled, unreconciled)):
                if rec > 0:
                    ax.text(i - width/2, rec + 0.5, str(rec), ha='center', va='bottom', fontsize=9)
                if unrec > 0:
                    ax.text(i + width/2, unrec + 0.5, str(unrec), ha='center', va='bottom', fontsize=9)
            
            plt.tight_layout()
            
            # اضافه کردن نمودار به UI
            canvas = FigureCanvasTkAgg(fig, master=chart_frame)
            canvas.draw()
            canvas.get_tk_widget().pack(fill="both", expand=True)
            
            self.logger.info(f"نمودار {chart_type} با موفقیت ایجاد شد")
            return canvas
            
        except Exception as e:
            self.logger.error(f"خطا در ایجاد نمودار {chart_type}: {str(e)}")
            return None
    
    def create_summary_pie_chart(self, overall_stats, chart_frame):
        """
        ایجاد نمودار دایره‌ای خلاصه آمار کلی
        
        Args:
            overall_stats: آمار کلی
            chart_frame: فریم برای نمایش نمودار
        """
        try:
            if not overall_stats or 'grand_total' not in overall_stats:
                self.logger.warning("داده‌ای برای نمودار خلاصه وجود ندارد")
                return None
            
            # پاک کردن نمودار قبلی
            for widget in chart_frame.winfo_children():
                widget.destroy()
            
            fig, ax = plt.subplots(figsize=(8, 6))
            
            # داده‌های نمودار دایره‌ای
            grand_total = overall_stats['grand_total']
            
            if grand_total['total_records'] == 0:
                # نمایش پیام عدم وجود داده
                ax.text(0.5, 0.5, 'هیچ رکوردی یافت نشد', 
                       ha='center', va='center', transform=ax.transAxes, fontsize=14)
                ax.axis('off')
            else:
                # آماده‌سازی داده‌ها برای نمودار دایره‌ای
                sections = ['بانک', 'حسابداری', 'پوز']
                reconciled_counts = [
                    overall_stats['bank']['reconciled_records'],
                    overall_stats['accounting']['reconciled_records'],
                    overall_stats['pos']['reconciled_records']
                ]
                unreconciled_counts = [
                    overall_stats['bank']['unreconciled_records'],
                    overall_stats['accounting']['unreconciled_records'],
                    overall_stats['pos']['unreconciled_records']
                ]
                
                # فیلتر کردن بخش‌هایی که داده دارند
                valid_sections = []
                valid_reconciled = []
                valid_unreconciled = []
                
                for i, section in enumerate(sections):
                    total = reconciled_counts[i] + unreconciled_counts[i]
                    if total > 0:
                        valid_sections.append(section)
                        valid_reconciled.append(reconciled_counts[i])
                        valid_unreconciled.append(unreconciled_counts[i])
                
                if valid_sections:
                    # ایجاد نمودار دایره‌ای دوگانه
                    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 6))
                    
                    # نمودار اول: توزیع کلی بر اساس بخش‌ها
                    total_by_section = [r + u for r, u in zip(valid_reconciled, valid_unreconciled)]
                    
                    # تبدیل برچسب‌ها به فارسی
                    persian_sections = [get_display(arabic_reshaper.reshape(s)) for s in valid_sections]
                    
                    wedges1, texts1, autotexts1 = ax1.pie(
                        total_by_section, labels=persian_sections, autopct='%1.1f%%',
                        colors=['#2196F3', '#FF9800', '#4CAF50'], startangle=90
                    )
                    
                    ax1.set_title(get_display(arabic_reshaper.reshape('توزیع کلی رکوردها')), 
                                 fontsize=12, fontweight='bold')
                    
                    # نمودار دوم: مقایسه مغایرت‌گیری شده و نشده
                    reconciled_total = sum(valid_reconciled)
                    unreconciled_total = sum(valid_unreconciled)
                    
                    if reconciled_total > 0 or unreconciled_total > 0:
                        status_labels = ['مغایرت‌گیری شده', 'مغایرت‌گیری نشده']
                        persian_status_labels = [get_display(arabic_reshaper.reshape(l)) for l in status_labels]
                        status_values = [reconciled_total, unreconciled_total]
                        
                        # فیلتر کردن مقادیر صفر
                        filtered_labels = []
                        filtered_values = []
                        colors = ['#4CAF50', '#F44336']
                        filtered_colors = []
                        
                        for i, value in enumerate(status_values):
                            if value > 0:
                                filtered_labels.append(persian_status_labels[i])
                                filtered_values.append(value)
                                filtered_colors.append(colors[i])
                        
                        if filtered_values:
                            wedges2, texts2, autotexts2 = ax2.pie(
                                filtered_values, labels=filtered_labels, autopct='%1.1f%%',
                                colors=filtered_colors, startangle=90
                            )
                            
                            ax2.set_title(get_display(arabic_reshaper.reshape('وضعیت مغایرت‌گیری')), 
                                         fontsize=12, fontweight='bold')
                
            plt.tight_layout()
            
            # اضافه کردن نمودار به UI
            canvas = FigureCanvasTkAgg(fig, master=chart_frame)
            canvas.draw()
            canvas.get_tk_widget().pack(fill="both", expand=True)
            
            self.logger.info("نمودار خلاصه آمار با موفقیت ایجاد شد")
            return canvas
            
        except Exception as e:
            self.logger.error(f"خطا در ایجاد نمودار خلاصه: {str(e)}")
            return None
    
    def create_progress_chart(self, stats_data, chart_frame, chart_title="پیشرفت مغایرت‌گیری"):
        """
        ایجاد نمودار نوار پیشرفت
        
        Args:
            stats_data: داده‌های آماری
            chart_frame: فریم برای نمایش نمودار  
            chart_title: عنوان نمودار
        """
        try:
            if not stats_data:
                return None
            
            # پاک کردن نمودار قبلی
            for widget in chart_frame.winfo_children():
                widget.destroy()
            
            fig, ax = plt.subplots(figsize=(8, 6))
            
            # آماده‌سازی داده‌ها
            bank_names = [stat['bank_name'] for stat in stats_data]
            percentages = [stat['reconciled_percentage'] for stat in stats_data]
            
            # تبدیل نام‌ها به فارسی
            persian_names = [get_display(arabic_reshaper.reshape(name)) for name in bank_names]
            
            # ایجاد نمودار نوار افقی
            bars = ax.barh(persian_names, percentages, color='#2196F3', alpha=0.7)
            
            # اضافه کردن درصدها روی نوارها
            for i, (bar, percentage) in enumerate(zip(bars, percentages)):
                width = bar.get_width()
                ax.text(width + 1, bar.get_y() + bar.get_height()/2, 
                       f'{percentage:.1f}%', ha='left', va='center', fontweight='bold')
            
            # تنظیمات نمودار
            ax.set_xlabel(get_display(arabic_reshaper.reshape('درصد مغایرت‌گیری شده')))
            ax.set_title(get_display(arabic_reshaper.reshape(chart_title)), fontsize=12, fontweight='bold')
            ax.set_xlim(0, 105)  # کمی فضای اضافی برای نمایش درصدها
            ax.grid(True, alpha=0.3, axis='x')
            
            plt.tight_layout()
            
            # اضافه کردن نمودار به UI
            canvas = FigureCanvasTkAgg(fig, master=chart_frame)
            canvas.draw()
            canvas.get_tk_widget().pack(fill="both", expand=True)
            
            self.logger.info(f"نمودار پیشرفت '{chart_title}' با موفقیت ایجاد شد")
            return canvas
            
        except Exception as e:
            self.logger.error(f"خطا در ایجاد نمودار پیشرفت: {str(e)}")
            return None
    
    def clear_chart(self, chart_frame):
        """پاک کردن نمودار از فریم"""
        try:
            for widget in chart_frame.winfo_children():
                widget.destroy()
        except Exception as e:
            self.logger.error(f"خطا در پاک کردن نمودار: {str(e)}")
    
    def save_chart_to_file(self, canvas, filename, file_format='png', dpi=300):
        """
        ذخیره نمودار در فایل
        
        Args:
            canvas: canvas نمودار
            filename: نام فایل
            file_format: فرمت فایل (png, jpg, pdf, svg)
            dpi: کیفیت تصویر
        """
        try:
            if canvas and hasattr(canvas, 'figure'):
                canvas.figure.savefig(filename, format=file_format, dpi=dpi, 
                                    bbox_inches='tight', facecolor='white', edgecolor='none')
                self.logger.info(f"نمودار با موفقیت در {filename} ذخیره شد")
                return True
            else:
                self.logger.warning("canvas معتبری برای ذخیره یافت نشد")
                return False
                
        except Exception as e:
            self.logger.error(f"خطا در ذخیره نمودار: {str(e)}")
            return False
