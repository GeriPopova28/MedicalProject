def safe_float(value):
    try:
        if value is None or value == "":
            return None
        return float(value)
    except:
        return None

def clamp(value, min_val=0.0, max_val=1.0):
    return max(min_val, min(value, max_val))