import sys
sys.path.insert(0, r"E:\project\workspace\myrepo\quant-atlas")

from app.config import get_settings
s = get_settings()
print("OK:", s.database.backend, s.debug, s.celery.broker_url, s.celery.result_backend)
print("tdx_root_path:", s.tdx_root_path)
print("enable_qlib:", s.enable_qlib)
print("enable_celery:", s.enable_celery)
print("ui_color_scheme:", s.ui_color_scheme)
print("use_mysql:", s.database.use_mysql)
print("ALL OK")
