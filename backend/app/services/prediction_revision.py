from collections.abc import Mapping
from datetime import datetime
from decimal import Decimal
import hashlib
import json


def _normalize(value):
    if value is None or isinstance(value, (str, bool)):
        return value
    if isinstance(value, (int, float, Decimal)):
        number = Decimal(str(value))
        if not number.is_finite():
            raise ValueError("Prediction revision inputs must be finite")
        if not number:
            rendered = "0"
        else:
            rendered = format(number, "f")
            if "." in rendered:
                rendered = rendered.rstrip("0").rstrip(".")
        return {"number": rendered}
    if isinstance(value, datetime):
        return {"datetime": value.isoformat()}
    if isinstance(value, Mapping):
        if not all(isinstance(key, str) for key in value):
            raise TypeError("Prediction revision mapping keys must be strings")
        return {"mapping": {key: _normalize(item) for key, item in value.items()}}
    if isinstance(value, (list, tuple)):
        return {"sequence": [_normalize(item) for item in value]}
    raise TypeError(f"Unsupported prediction input type: {type(value).__name__}")


def input_fingerprint(payload: Mapping) -> str:
    encoded = json.dumps(
        _normalize(payload), sort_keys=True, separators=(",", ":"), allow_nan=False,
    )
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()
