"""
WSGI config for DishGennie project.
"""
import os
from django.core.wsgi import get_wsgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "dishgennie.settings")
application = get_wsgi_application()

# Vercel's Python runtime binds to a module-level `app`; gunicorn/Render use
# `application`. Both names point at the same callable so either host works.
app = application

