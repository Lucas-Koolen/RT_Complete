import json
from config.config import STACKASSIST_JSON_PATH, MATCH_TOLERANCE

with open(STACKASSIST_JSON_PATH, "r") as f:
    STACK_DATA = json.load(f)

def match_dimensions(length, width, height):
    measured = sorted([length, width, height])

    for item in STACK_DATA:
        try:
            dims = sorted([
                item.get("length_mm"),
                item.get("width_mm"),
                item.get("height_mm")
            ])
            product_id = item.get("product_id")

            if None in dims or product_id is None:
                continue

            diffs = [abs(a - b) / b for a, b in zip(measured, dims)]
            if all(d <= MATCH_TOLERANCE for d in diffs):
                return product_id, True
        except Exception:
            continue

    return None, False
