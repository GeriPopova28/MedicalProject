import cv2
from flask import Blueprint, jsonify, render_template, redirect, request, session, url_for
import numpy as np
import tensorflow as tf

import ai_module
import app
from app.extensions import get_db
from utils.auth_helpers import is_doctor, is_logged_in, is_patient

patient_bp = Blueprint('patient', __name__)

@app.route('/patient-dashboard')
def patient_dashboard():

    if not is_logged_in():
        return redirect(url_for('login_page'))

    if not is_patient():
        return redirect(url_for('doctor_dashboard'))

    return render_template("patient/patient_dashboard.html")

@app.route('/upload')
def upload_page():

    if not is_logged_in():
        return redirect(url_for('login_page'))

    if is_doctor():
        return redirect(url_for('doctor_dashboard'))

    return render_template("upload.html")

@app.route('/predict', methods=['POST'])
def predict():

    if not is_logged_in():
        return jsonify({"success": False, "error": "Not logged in"}), 401

    user_id = session.get("user_id")
    if not user_id:
        return jsonify({"success": False, "error": "Missing session user_id"}), 401

    try:
        user_id = int(user_id)
    except:
        return jsonify({"success": False, "error": "Invalid user_id"}), 400

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("SELECT id FROM patients WHERE user_id = %s", (user_id,))
    patient_row = cursor.fetchone()

    if not patient_row:
        return jsonify({"success": False, "error": "Patient not found"}), 400

    patient_id = patient_row[0]

    # ================= FILE =================
    file = request.files.get('file')
    if not file:
        return jsonify({"success": False, "error": "No file uploaded"}), 400

    import os, uuid
    UPLOAD_FOLDER = "static/uploads"
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)

    filename = f"{uuid.uuid4()}.jpg"
    image_path = os.path.join(UPLOAD_FOLDER, filename)

    file.save(image_path)

    try:
        img = cv2.imdecode(
            np.frombuffer(open(image_path, "rb").read(), np.uint8),
            cv2.IMREAD_COLOR
        )

        if img is None:
            return jsonify({"success": False, "error": "Invalid image"}), 400

        img = cv2.resize(img, (224, 224))

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

    def clean_float(val):
        if val is None or val == "":
            return 0.0
        return float(str(val).replace(",", ".").strip())

    tsh = clean_float(request.form.get("tsh"))
    ft4 = clean_float(request.form.get("ft4"))
    mat = clean_float(request.form.get("mat"))
    tat = clean_float(request.form.get("tat"))

    age = int(request.form.get("age") or 0)
    gender = (request.form.get("gender") or "").lower()

    family_history = request.form.get("family_history") == "on"
    previous_thyroid_disease = request.form.get("previous_thyroid_disease") == "on"
    autoimmune_history = request.form.get("autoimmune_history") == "on"

    complain_text = (request.form.get("complain", "") or "").lower()

    hypo_keywords = ["умор","отпаднал","слабост","напълня","тегло","студ","зиморнич","косопад","суха кожа","запек","депрес","сънлив"]
    hyper_keywords = ["нерв","тревож","сърцебиене","пулс","отслабна","слабеене","изпотя","топло","горещо","трепере","безсън"]

    symptom_score = 0
    symptom_score += min(sum(k in complain_text for k in hypo_keywords) * 15, 50)
    symptom_score += min(sum(k in complain_text for k in hyper_keywords) * 15, 50)
    symptom_score = min(symptom_score, 100)

    ai_class = "Unknown"
    ai_verdict = "Нормално"
    risk_level = "LOW"
    advice = ""

    lab_score = 0
    benign_prob = 0.0
    malignant_prob = 0.0
    ai_conf = 0.0
    ai_score = 0.0
    extra_score = 0
    confidence = 0.0

    explanation = "" 

    try:
        if ai_module:

            img_input = tf.keras.applications.efficientnet.preprocess_input(img)
            img_input = np.expand_dims(img_input, axis=0)

            pred = ai_module.model.predict(img_input, verbose=0)[0]

            benign_prob = float(pred[0])
            malignant_prob = float(pred[1])

            diff = abs(benign_prob - malignant_prob)

            if diff < 0.15:
                ai_class = "Uncertain"
            elif malignant_prob > benign_prob:
                ai_class = "Malignant"
            else:
                ai_class = "Benign"

            ai_conf = max(benign_prob, malignant_prob) * 100
            ai_score = malignant_prob * 100

            # LAB
            if tsh > 4.5: lab_score += 25
            if ft4 < 9 or ft4 > 20: lab_score += 20
            if mat > 34 or tat > 115: lab_score += 30
            lab_score = min(lab_score, 100)

            # EXTRA
            if age >= 60: extra_score += 5
            elif age >= 45: extra_score += 2
            if gender == "female": extra_score += 2
            if family_history: extra_score += 8
            if previous_thyroid_disease: extra_score += 7
            if autoimmune_history: extra_score += 5

            final_score = (
                ai_score * 0.65 +
                lab_score * 0.20 +
                symptom_score * 0.10 +
                extra_score
            )

            final_score = max(0, min(final_score, 99))
            confidence = round(final_score, 1)

            if ai_class == "Malignant" and final_score >= 80:
                ai_verdict = "Критично"
                risk_level = "CRITICAL"
                advice = "Спешен преглед"
            elif ai_class == "Malignant":
                ai_verdict = "Подозрително"
                risk_level = "MODERATE"
                advice = "Контролен преглед"
            elif final_score >= 60:
                ai_verdict = "Подозрително"
                risk_level = "MODERATE"
                advice = "Контролни изследвания"
            else:
                ai_verdict = "Нормално"
                risk_level = "LOW"
                advice = "Нормален резултат"

            explanation = f"""
            AI CLASS: {ai_class}
            Confidence: {ai_conf:.1f}%
            Risk: {risk_level}
            Lab score: {lab_score}
            Symptom score: {symptom_score}
            Extra score: {extra_score}

            Final verdict: {ai_verdict}
            Advice: {advice}
            """

        cursor.execute("""
            UPDATE patients
            SET age=%s,
                gender=%s,
                family_history=%s,
                previous_thyroid_disease=%s,
                autoimmune_history=%s
            WHERE id=%s
        """, (age, gender, family_history, previous_thyroid_disease, autoimmune_history, patient_id))

        cursor.execute("""
            INSERT INTO analysis_results (
                patient_id,
                prediction,
                confidence,
                risk_level,
                advice,
                explanation,
                ai_class,
                lab_score,
                symptom_score,
                extra_score,
                ai_confidence,
                created_at,
                image_path
            )
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,NOW(),%s)
        """, (
            patient_id,
            ai_verdict,
            confidence,
            risk_level,
            advice,
            explanation,  
            ai_class,
            lab_score,
            symptom_score,
            extra_score,
            ai_conf,
            image_path
        ))

        conn.commit()

    except Exception as e:
        conn.rollback()
        return jsonify({"success": False, "error": str(e)}), 500

    finally:
        cursor.close()

    return jsonify({
        "success": True,
        "status": ai_verdict,
        "confidence": confidence,
        "risk": risk_level.lower(),
        "follow_up": advice,
        "lab_score": lab_score,
        "symptom_score": symptom_score,
        "image_score": round(ai_score, 1),

        "ai_class": ai_class,
        "ai_confidence": round(ai_conf, 1),
        "benign_prob": round(benign_prob, 3),
        "malignant_prob": round(malignant_prob, 3),

        "extra_score": extra_score,
        "age": age,
        "gender": gender,
        "family_history": family_history,
        "previous_thyroid_disease": previous_thyroid_disease,
        "autoimmune_history": autoimmune_history,
        "image_path": image_path
    })