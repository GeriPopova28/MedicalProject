def clamp(value, min_v, max_v):
    return max(min_v, min(value, max_v))

def safe_float(value):
    try:
        return float(value)
    except:
        return 0.0