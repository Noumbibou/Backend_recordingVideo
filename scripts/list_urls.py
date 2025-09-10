import os
import sys

ROOT = os.path.dirname(os.path.dirname(__file__))
sys.path.insert(0, ROOT)
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "backend.settings")

import django
django.setup()

from django.urls import get_resolver

def walk(urlpatterns, prefix=""):
    for p in urlpatterns:
        try:
            pattern = prefix + str(p.pattern)
            if hasattr(p, "url_patterns"):
                print(f"{pattern}  [include]")
                walk(p.url_patterns, prefix=pattern)
            else:
                view = getattr(p, "callback", None)
                try:
                    view_name = view.__qualname__ if view and hasattr(view, "__qualname__") else (view.__name__ if view else repr(p))
                except Exception:
                    view_name = repr(view)
                print(f"{pattern}  -> {view_name}")
        except Exception as e:
            print("ERR:", e, getattr(p, "pattern", p))

if __name__ == "__main__":
    resolver = get_resolver()
    print("Django URL patterns:")
    walk(resolver.url_patterns)