import random

def ai_predict(area, perimeter, mean):
    """Симулирано AI предсказание"""
    classes = ["Benign", "Malignant"]
    pred = random.choice(classes)
    conf = random.uniform(0.7, 0.99)
    return pred, conf