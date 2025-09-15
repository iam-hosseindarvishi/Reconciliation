"""
Dashboard Components Package
ماژول اجزای داشبورد - جدا شده از dashboard_tab.py
"""

from .statistics_provider import StatisticsProvider
from .chart_manager import ChartManager  
from .dashboard_operations import DashboardOperations

__all__ = [
    'StatisticsProvider',
    'ChartManager', 
    'DashboardOperations'
]
