import os
import sys
import json
import types

# ajuster si nécessaire
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "backend.settings")
ROOT = os.path.dirname(os.path.dirname(__file__))
sys.path.insert(0, ROOT)

import django
django.setup()

from django.apps import apps

def safe(v):
    """Rendre v sérialisable en JSON: primitives inchangées, autres -> string."""
    try:
        json.dumps(v)
        return v
    except Exception:
        # fonctions, classes, field objects, datetimes, etc.
        if isinstance(v, (types.FunctionType, types.BuiltinFunctionType, types.MethodType)):
            return f"<callable {getattr(v, '__name__', repr(v))}>"
        try:
            return repr(v)
        except Exception:
            return str(type(v))

def inspect_model(app_label, model_name):
    try:
        model = apps.get_model(app_label, model_name)
    except LookupError:
        return {"error": f"Model {app_label}.{model_name} not found"}
    fields = []
    for f in model._meta.get_fields():
        # skip automatic reverse relations
        if getattr(f, "auto_created", False) and not getattr(f, "concrete", False):
            continue
        info = {
            "name": getattr(f, "name", str(f)),
            "type": getattr(f, "get_internal_type", lambda: type(f).__name__)(),
        }
        # safe-read common attrs
        for attr in ("null", "blank", "unique", "max_length"):
            if hasattr(f, attr):
                info[attr] = safe(getattr(f, attr))
        # default can be callable -> safe it
        if hasattr(f, "default"):
            try:
                info["default"] = safe(getattr(f, "default"))
            except Exception:
                info["default"] = "<unreadable>"
        # relation info
        if getattr(f, "is_relation", False):
            rel = {}
            rel_obj = getattr(f, "related_model", None)
            rel["related_model"] = f"{rel_obj._meta.app_label}.{rel_obj.__name__}" if rel_obj else None
            rel["many_to_many"] = safe(getattr(f, "many_to_many", False))
            rel["one_to_many"] = safe(getattr(f, "one_to_many", False))
            info["relation"] = rel
        fields.append(info)
    return fields

out = {"models": {}, "serializers": {}}

# candidate model names to try
candidates = [
    ("interviews", "VideoCampaign"),
    ("interviews", "Campaign"),
    ("interviews", "VideoCampaignModel"),
    ("interviews", "VideoCampaigns"),
]

for app_label, model_name in candidates:
    out["models"][f"{app_label}.{model_name}"] = inspect_model(app_label, model_name)

# inspect serializers in interviews.serializers
try:
    import inspect as _inspect
    import interviews.serializers as sermod
    from rest_framework import serializers as drf_serializers
    for name, obj in _inspect.getmembers(sermod, _inspect.isclass):
        try:
            if issubclass(obj, drf_serializers.BaseSerializer):
                meta = {}
                M = getattr(obj, "Meta", None)
                if M and hasattr(M, "fields"):
                    meta["meta_fields"] = safe(getattr(M, "fields"))
                # declared fields
                declared = getattr(obj, "_declared_fields", None)
                if declared is not None:
                    meta["declared_fields"] = list(declared.keys())
                out["serializers"][name] = meta or {"note": "serializer detected"}
        except Exception:
            continue
except Exception as e:
    out["serializers_error"] = str(e)

print(json.dumps(out, indent=2, ensure_ascii=False))