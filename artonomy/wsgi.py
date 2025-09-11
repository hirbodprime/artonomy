# # <project>/wsgi.py
# import os
# from django.core.wsgi import get_wsgi_application

# os.environ.setdefault("DJANGO_SETTINGS_MODULE", "artonomy.settings")
# application = get_wsgi_application()
# wsgi.py
import os, sys, traceback
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
FALLBACK_LOG = BASE_DIR / "logs" / "startup_error.log"
FALLBACK_LOG.parent.mkdir(exist_ok=True)

try:
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "artonomy.settings")  # adjust module
    from django.core.wsgi import get_wsgi_application
    application = get_wsgi_application()
except Exception:
    with open(FALLBACK_LOG, "a", encoding="utf-8") as f:
        f.write("=== WSGI startup exception ===\n")
        traceback.print_exc(file=f)
    raise
