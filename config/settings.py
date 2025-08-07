# تنظیمات کلی برنامه

WINDOW_WIDTH = 1400
WINDOW_HEIGHT = 800
WINDOW_RESIZABLE = False

import os
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, 'Data')
DB_PATH = os.path.join(DATA_DIR, 'app.db')
