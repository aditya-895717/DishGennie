"""
Vercel serverless entrypoint.

Vercel's @vercel/python runtime imports this module and looks for a module
level variable named `app` holding a WSGI/ASGI callable. Without one it has
nothing to invoke, and every request — not just one route — comes back as
Vercel's own NOT_FOUND page, which is what took the whole domain down.
"""
import os
import sys
from pathlib import Path

# The function's working directory is not guaranteed to be the repo root.
BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'dishgennie.settings')

from dishgennie.wsgi import application  # noqa: E402

app = application
# Some Vercel runtime versions look for `handler` instead.
handler = application
