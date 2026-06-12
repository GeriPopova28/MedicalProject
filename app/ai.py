from flask import Blueprint, request, jsonify, session
import cv2
import numpy as np
import tensorflow as tf
from tensorflow.keras.models import load_model
import os

ai = Blueprint("ai", __name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_PATH = os.path.join(BASE_DIR, "ai_model.h5")

ai_model = None

if os.path.exists(MODEL_PATH):
    try:
        ai_model = load_model(MODEL_PATH, compile=False)
        print("AI model loaded successfully")
    except Exception as e:
        print("Model load error:", e)

def safe_float(val):
    try:
        return float(val)
    except:
        return 0.0

@ai.route("/predict", methods=["POST"])
def predict():

    if "user_id" not in session:
        return jsonify({"success": False, "error": "Not logged in"}), 401

    file = request.files.get("file")

    if not file:
        return jsonify({"success": False, "error": "No file"}), 400
    img = cv2.imdecode(
        np.frombuffer(file.read(), np.uint8),
        cv2.IMREAD_COLOR
    )

    if img is None:
        return jsonify({"success": False, "error": "Invalid image"}), 400

    img = cv2.resize(img, (224, 224))

    tsh = safe_float(request.form.get("tsh"))
    ft4 = safe_float(request.form.get("ft4"))
    mat = safe_float(request.form.get("mat"))
    tat = safe_float(request.form.get("tat"))

    complain = (request.form.get("complain") or "").lower()

    symptom_score = 0

    keywords = {
        "fatigue": 15,
        "tired": 15,
        "weight": 20,
        "hair": 10,
        "cold": 10,
        "palpitation": 20,
        "anxiety": 15
    }

    for k, v in keywords.items():
        if k in complain:
            symptom_score += v

    symptom_score = min(symptom_score, 100)

    lab_score = 0

    if tsh > 4.5:
        lab_score += 25
    elif tsh < 0.4 and tsh != 0:
        lab_score += 20

    if ft4 < 9 or ft4 > 20:
        lab_score += 20

    if mat > 34:
        lab_score += 20

    if tat > 115:
        lab_score += 20

    lab_score = min(lab_score, 100)

    image_score = 0
    ai_verdict = "Нормално"

    if ai_model:

        try:
            img_input = tf.keras.applications.efficientnet.preprocess_input(img)
            img_input = np.expand_dims(img_input, axis=0)

            pred = ai_model.predict(img_input, verbose=0)

            probs = pred[0]
            idx = int(np.argmax(probs))

            classes = ["Benign", "Malignant"]
            ai_verdict = classes[idx]

            image_score = float(probs[idx]) * 100

        except Exception as e:
            return jsonify({"success": False, "error": str(e)}), 500

    final_score = (
        image_score * 0.5 +
        lab_score * 0.35 +
        symptom_score * 0.15
    )

    final_score = max(0, min(final_score, 99))

    if final_score >= 80:
        risk = "HIGH"
        advice = "Спешна консултация"

    elif final_score >= 60:
        risk = "MODERATE"
        advice = "Контролен преглед"

    else:
        risk = "LOW"
        advice = "Нормално състояние"
        
    return jsonify({
        "success": True,
        "prediction": ai_verdict,
        "confidence": round(final_score, 1),
        "risk": risk.lower(),
        "follow_up": advice,
        "lab_score": lab_score,
        "symptom_score": symptom_score,
        "image_score": image_score
    })