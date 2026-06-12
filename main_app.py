import os
import io
import re
import random
import uuid
from datetime import datetime, timedelta
from functools import wraps

import cv2
import numpy as np
import mysql.connector
import qrcode
import tensorflow as tf
from tensorflow.keras.models import load_model
from dotenv import load_dotenv

from flask import (
    Flask, render_template, request, jsonify, session, 
    redirect, url_for, send_file, g
)
from werkzeug.security import generate_password_hash, check_password_hash

from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont
from reportlab.pdfbase.ttfonts import TTFont

from flask import Flask, render_template, request, jsonify, session, redirect, url_for, send_file, g

def doctor_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get("logged_in") or session.get("role") != "Doctor":
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.content_type == 'application/json':
                return jsonify({"success": False, "error": "Нямате права за достъп"}), 403
            return redirect(url_for('login_page'))
        return f(*args, **kwargs)
    return decorated_function

def validate_future_datetime(date, time):
    try:
        dt = datetime.strptime(f"{date} {time}", "%Y-%m-%d %H:%M")
        return dt > datetime.now()
    except:
        return False

app = Flask(__name__, static_folder='static', template_folder='templates')

app.secret_key = os.environ.get(
    "FLASK_SECRET_KEY",
    "super_secret_diploma_key_2026"
)

def is_logged_in():
    return 'user' in session

def is_doctor():
    return session.get("role") == "Doctor"

def is_patient():
    return session.get("role") == "Patient"

def is_strong_password(password: str) -> bool:
    if len(password) < 8:
        return False
    if not re.search(r"[A-Za-z]", password):
        return False
    if not re.search(r"[0-9]", password):
        return False
    return True

db_config = {
    "host": os.getenv("DB_HOST", "localhost"),
    "user": os.getenv("DB_USER", "root"),
    "password": os.getenv("DB_PASSWORD"),
    "database": os.getenv("DB_NAME", "medical_ai")
}

def get_db():
    if 'db' not in g:
        g.db = mysql.connector.connect(**db_config)
    return g.db

@app.teardown_appcontext
def close_db(error):
    db = g.pop('db', None)
    if db is not None:
        try:
            db.close()
        except Exception as e:
            print("Грешка при затваряне на DB връзката:", e)


def safe_float(value):
    try:
        return float(value)
    except:
        return 0.0


def clamp(value, min_v, max_v):
    return max(min_v, min(value, max_v))


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_PATH = os.path.join(BASE_DIR, "ai_model.h5")

print("MODEL PATH:", MODEL_PATH)
print("EXISTS:", os.path.exists(MODEL_PATH))

with open(MODEL_PATH, "rb") as f:
    print(f.read(20))

ai_model = None

try:
    ai_model = load_model(MODEL_PATH, compile=False)
    print("AI model loaded!")
except Exception as e:
    print("Model error:", e)
ai_model = None

if os.path.exists(MODEL_PATH):
    try:
        ai_model = load_model(MODEL_PATH, compile=False)
        print("AI model loaded!")
    except Exception as e:
        print("Model error:", e)


@app.route('/')
def home():
    if 'user' not in session:
        return redirect(url_for('login_page'))

    if session.get("role") == "Doctor":
        return redirect(url_for('doctor_dashboard'))

    return redirect(url_for('patient_dashboard'))

@app.route('/login')
def login_page():
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login_page'))

@app.route('/handle_auth', methods=['POST'])
def handle_auth():

    data = request.get_json() or {}

    username = (data.get("username") or "").strip()
    password = data.get("password") or ""
    action = data.get("action", "login")

    if not username or not password:
        return jsonify({
            "success": False,
            "error": "Missing credentials"
        }), 400

    try:
        conn = get_db()
        cursor = conn.cursor(dictionary=True)

        if action == "register":

            role = data.get("role", "Patient")

            if role not in ["Doctor", "Patient"]:
                role = "Patient"

            if not is_strong_password(password):
                return jsonify({
                    "success": False,
                    "error": "Password must be 8+ chars, include letters + numbers"
                }), 400

            cursor.execute(
                "SELECT id FROM users WHERE username = %s",
                (username,)
            )

            if cursor.fetchone():
                return jsonify({
                    "success": False,
                    "error": "User already exists"
                }), 409

            hashed = generate_password_hash(password)

            cursor.execute("""
                INSERT INTO users (username, password, role, failed_attempts, lock_until)
                VALUES (%s, %s, %s, 0, NULL)
            """, (username, hashed, role))

            conn.commit()
            user_id = cursor.lastrowid

            if role == "Patient":
                cursor.execute("""
                    INSERT INTO patients (user_id, full_name)
                    VALUES (%s, %s)
                """, (user_id, username))
                conn.commit()

            session.clear()
            session["user_id"] = int(user_id)
            session["user"] = username
            session["role"] = role
            session.permanent = True

            return jsonify({
                "success": True,
                "role": role,
                "id": user_id
            })


        cursor.execute("""
            SELECT id, username, password, role, failed_attempts, lock_until
            FROM users
            WHERE username = %s
        """, (username,))

        user = cursor.fetchone()

        if not user:
            return jsonify({
                "success": False,
                "error": "User not found"
            }), 404


        if user["lock_until"]:
            if user["lock_until"] > datetime.now():
                return jsonify({
                    "success": False,
                    "error": "Account locked. Try again later."
                }), 403

            # unlock if expired
            cursor.execute("""
                UPDATE users
                SET failed_attempts = 0,
                    lock_until = NULL
                WHERE id = %s
            """, (user["id"],))
            conn.commit()

        if not check_password_hash(user["password"], password):

            attempts = user["failed_attempts"] + 1
            lock_until = None

            if attempts >= 5:
                lock_until = datetime.now() + timedelta(minutes=10)
                attempts = 0

            cursor.execute("""
                UPDATE users
                SET failed_attempts = %s,
                    lock_until = %s
                WHERE id = %s
            """, (attempts, lock_until, user["id"]))

            conn.commit()

            return jsonify({
                "success": False,
                "error": "Wrong password"
            }), 401

        cursor.execute("""
            UPDATE users
            SET failed_attempts = 0,
                lock_until = NULL
            WHERE id = %s
        """, (user["id"],))

        conn.commit()

        session.clear()
        session["user_id"] = int(user["id"])
        session["user"] = user["username"]
        session["role"] = user["role"]
        session.permanent = True

        return jsonify({
            "success": True,
            "role": user["role"],
            "id": user["id"]
        })

    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

    finally:
        try:
            cursor.close()
        except:
            pass


@app.route("/debug-session")
def debug_session():
    return jsonify({
        "session": dict(session)
    }) 

@app.route('/patient-dashboard')
def patient_dashboard():

    if not is_logged_in():
        return redirect(url_for('login_page'))

    if not is_patient():
        return redirect(url_for('doctor_dashboard'))

    return render_template("patient/patient_dashboard.html")


@app.route('/doctor-dashboard')
def doctor_dashboard():

    if not is_logged_in():
        return redirect(url_for('login_page'))

    if not is_doctor():
        return redirect(url_for('patient_dashboard'))

    return render_template("doctor/doctor_dashboard.html")


@app.route('/upload')
def upload_page():

    if not is_logged_in():
        return redirect(url_for('login_page'))

    if is_doctor():
        return redirect(url_for('doctor_dashboard'))

    return render_template("upload.html")


@app.route('/endocrine')
def endocrine():
    return render_template("endocrine.html")

@app.route('/endocrine_quiz')
def endocrine_quiz():
    return render_template("endocrine_quiz.html")

@app.route('/endocrine-clinics')
def endocrine_clinics():
    return render_template("endocrine_clinics.html")

@app.route('/patient-history')
def patient_history():

    if not is_logged_in():
        return redirect(url_for('login_page'))

    if not is_patient():
        return redirect(url_for('doctor_dashboard'))

    return render_template("patient_history.html")

# =====================================================
# PATIENT DATA API
# =====================================================
@app.route('/patient-data', methods=['GET'])
def patient_data():
    if not is_logged_in():
        return jsonify([]), 401
        
    user_id = session.get("user_id")
    
    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    
    try:
        # 1. Намираме patient_id за текущия потребител
        cursor.execute("SELECT id FROM patients WHERE user_id = %s", (user_id,))
        patient = cursor.fetchone()
        
        if not patient:
            return jsonify([])  # Все още няма анализи
            
        patient_id = patient["id"]
        
        # 2. Взимаме всички анализи, подредени от най-новия към най-стария
        cursor.execute("""
            SELECT
                id,
                confidence,
                risk_level,
                advice,
                explanation,
                created_at,
                ai_class
            FROM analysis_results
            WHERE patient_id = %s
            ORDER BY created_at DESC
            """, (patient_id,))
        
        results = cursor.fetchall()
        
        # Важно: Сървърът трябва да върне created_at като ISO стринг за JavaScript
        for row in results:
            if row.get('created_at'):
                row['created_at'] = row['created_at'].isoformat()
                
        return jsonify(results)
        
    except Exception as e:
        print(f"Грешка в /patient-data: {str(e)}")
        return jsonify([]), 500
    finally:
        cursor.close()

# =====================================================
# AI PREDICT
# =====================================================
@app.route('/doctor/patients-data')
def doctor_patients_data():

    if not is_doctor():
        return jsonify([])

    try:
        conn = get_db()
        cursor = conn.cursor(dictionary=True)

        cursor.execute("""
            SELECT *
            FROM analysis_results
            ORDER BY created_at DESC
        """)

        data = cursor.fetchall()

        cursor.close()
        return jsonify(data)

    except Exception as e:
        print("PATIENTS DATA ERROR:", e)
        return jsonify([])

# ================= DOCTOR PAGES =================

@app.route('/doctor/patients')
def doctor_patients():
    if not is_logged_in():
        return redirect(url_for('login_page'))
    if not is_doctor():
        return redirect(url_for('patient_dashboard'))
    return render_template("doctor_patients.html")


@app.route('/doctor/alerts')
def doctor_alerts():
    if not is_logged_in():
        return redirect(url_for('login_page'))
    if not is_doctor():
        return redirect(url_for('patient_dashboard'))
    return render_template("doctor_alerts.html")


@app.route('/doctor/statistics')
def doctor_statistics():
    if not is_logged_in():
        return redirect(url_for('login_page'))
    if not is_doctor():
        return redirect(url_for('patient_dashboard'))
    return render_template("doctor_statistics.html")


@app.route('/doctor/appointments')
def doctor_appointments():
    if not is_logged_in():
        return redirect(url_for('login_page'))
    if not is_doctor():
        return redirect(url_for('patient_dashboard'))
    return render_template("doctor_appointments.html")

@app.route('/doctor/alerts-data')
def doctor_alerts_data():

    if not is_doctor():
        return jsonify([])

    try:
        conn = get_db()
        cursor = conn.cursor(dictionary=True)

        cursor.execute("""
            SELECT *
            FROM analysis_results
            WHERE risk_level = 'HIGH'
            ORDER BY created_at DESC
        """)

        data = cursor.fetchall()

        cursor.close()
        return jsonify(data)

    except Exception as e:
        print("ALERTS ERROR:", e)
        return jsonify([])

@app.route('/api/doctors')
def api_doctors():

    try:

        conn = get_db()
        cursor = conn.cursor(dictionary=True)

        cursor.execute("""
            SELECT *
            FROM doctors
        """)

        data = cursor.fetchall()

        cursor.close()
        return jsonify(data)

    except Exception as e:

        print(e)

        return jsonify([])

@app.route("/doctor/pending-analyses")
def pending_analyses():

    # =====================================================
    # DOCTOR AUTH CHECK
    # =====================================================

    if not is_logged_in():

        return jsonify({
            "success": False,
            "error": "Not logged in"
        })

    if not is_doctor():

        return jsonify({
            "success": False,
            "error": "Unauthorized"
        })

    # =====================================================
    # GET DOCTOR ID
    # =====================================================

    doctor_id = session.get("doctor_id")

    if not doctor_id:

        return jsonify({
            "success": False,
            "error": "Doctor ID missing"
        })

    try:

        conn = get_db()
        cursor = conn.cursor(dictionary=True)

        # =====================================================
        # LOAD ANALYSES
        # =====================================================

        cursor.execute("""
            SELECT
                id,
                patient_name,
                prediction,
                confidence,
                risk_level,
                status,
                created_at
            FROM analysis_results
            WHERE doctor_id = %s
            ORDER BY created_at DESC
        """, (doctor_id,))

        data = cursor.fetchall()

        # =====================================================
        # FORMAT DATES
        # =====================================================

        for row in data:

            if row.get("created_at"):
                row["created_at"] = str(row["created_at"])

        cursor.close()
        return jsonify({
            "success": True,
            "count": len(data),
            "data": data
        })

    except Exception as e:

        print("PENDING ANALYSES ERROR:", e)

        return jsonify({
            "success": False,
            "error": str(e)
        })
    
@app.route("/doctor/update-analysis/<int:id>", methods=["POST"])
def update_analysis(id):

    # =====================================================
    # DOCTOR CHECK
    # =====================================================

    if not is_doctor():

        return jsonify({
            "success": False,
            "error": "Unauthorized"
        })

    try:

        data = request.get_json()

        action = data.get("action")

        # =====================================================
        # VALID STATUS CHECK
        # =====================================================

        allowed_actions = [
            "APPROVED",
            "REJECTED",
            "PENDING",
            "REVIEWED"
        ]

        if action not in allowed_actions:

            return jsonify({
                "success": False,
                "error": "Invalid status"
            })

        conn = get_db()
        cursor = conn.cursor()

        # =====================================================
        # CHECK IF ANALYSIS EXISTS
        # =====================================================

        cursor.execute("""
            SELECT id
            FROM analysis_results
            WHERE id = %s
        """, (id,))

        existing = cursor.fetchone()

        if not existing:

            cursor.close()
            return jsonify({
                "success": False,
                "error": "Analysis not found"
            })

        # =====================================================
        # UPDATE STATUS
        # =====================================================

        cursor.execute("""
            UPDATE analysis_results
            SET status = %s
            WHERE id = %s
        """, (
            action,
            id
        ))

        conn.commit()

        cursor.close()
        return jsonify({
            "success": True,
            "message": "Analysis updated successfully"
        })

    except Exception as e:

        print("UPDATE ANALYSIS ERROR:", e)

        return jsonify({
            "success": False,
            "error": str(e)
        })

@app.route("/appointments-data")
def appointments_data():

    if not is_logged_in():
        return jsonify([])

    try:

        conn = get_db()
        cursor = conn.cursor(dictionary=True)

        cursor.execute("""

            SELECT

                a.id,
                a.patient_id,
                a.date,
                a.time,
                a.status,
                a.doctor_comment,
                a.notes,

                p.full_name AS patient_name,

                ar.prediction,
                ar.confidence,
                ar.risk_level,
                ar.advice,
                ar.explanation

            FROM appointments a

            LEFT JOIN patients p
                ON a.patient_id = p.id

            LEFT JOIN analysis_results ar
                ON ar.appointment_id = a.id

            ORDER BY a.date DESC, a.time DESC

        """)

        data = cursor.fetchall()

        # SAFE JSON SERIALIZATION
        for row in data:

            if row.get("date"):
                row["date"] = str(row["date"])

            if row.get("time"):
                row["time"] = str(row["time"])

            if row.get("confidence") is not None:
                row["confidence"] = float(row["confidence"])

        cursor.close()

        return jsonify(data)

    except Exception as e:

        print("APPOINTMENTS ERROR:", e)

        return jsonify({
            "error": str(e)
        }), 500

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

    # ================= IMAGE READ =================
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

    # ================= LAB =================
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

    # ================= SYMPTOMS =================
    hypo_keywords = ["умор","отпаднал","слабост","напълня","тегло","студ","зиморнич","косопад","суха кожа","запек","депрес","сънлив"]
    hyper_keywords = ["нерв","тревож","сърцебиене","пулс","отслабна","слабеене","изпотя","топло","горещо","трепере","безсън"]

    symptom_score = 0
    symptom_score += min(sum(k in complain_text for k in hypo_keywords) * 15, 50)
    symptom_score += min(sum(k in complain_text for k in hyper_keywords) * 15, 50)
    symptom_score = min(symptom_score, 100)

    # ================= DEFAULTS =================
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
        if ai_model:

            img_input = tf.keras.applications.efficientnet.preprocess_input(img)
            img_input = np.expand_dims(img_input, axis=0)

            pred = ai_model.predict(img_input, verbose=0)[0]

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

            # ================= FIXED EXPLANATION =================
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

        # ================= DB UPDATE =================
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

@app.route("/save-comment", methods=["POST"])
def save_comment():

    if not is_doctor():
        return jsonify({"success": False})

    data = request.get_json()

    appointment_id = data["id"]
    comment = data["comment"]

    try:
        conn = get_db()
        cursor = conn.cursor()

        cursor.execute("""
            UPDATE appointments
            SET doctor_comment = %s
            WHERE id = %s
        """, (comment, appointment_id))

        conn.commit()

        return jsonify({"success": True})

    except Exception as e:
        return jsonify({"success": False, "error": str(e)})
    
import random
from flask import request, jsonify

used_questions = set()

@app.route("/generate_ai_quiz", methods=["POST"])
def generate_ai_quiz():

    try:

        data = request.get_json()

        lab_data = data.get("lab_data", {})
        symptoms = data.get("symptoms", "").lower()

        tsh = float(lab_data.get("tsh", 0))
        ft4 = float(lab_data.get("ft4", 0))
        mat = float(lab_data.get("mat", 0))
        tat = float(lab_data.get("tat", 0))

        # ==========================================
        # AI CLINICAL LOGIC
        # ==========================================

        if tsh > 4.5 and ft4 < 12:
            diagnosis = "Hypothyroidism"

        elif tsh < 0.4 and ft4 > 22:
            diagnosis = "Hyperthyroidism"

        else:
            diagnosis = "Normal"

        # ==========================================
        # QUESTION DATABASE
        # ==========================================

        quiz_bank = [

            {
                "question": "Кой симптом е типичен за хипотиреоидизъм?",
                "options": ["Умора", "Тахикардия", "Безсъние", "Хиперактивност"],
                "correct": "Умора"
            },

            {
                "question": "Кой симптом е типичен за хипертиреоидизъм?",
                "options": ["Брадикардия", "Сънливост", "Сърцебиене", "Качване на тегло"],
                "correct": "Сърцебиене"
            },

            {
                "question": "Какво се повишава при първичен хипотиреоидизъм?",
                "options": ["TSH", "FT4", "Калций", "Инсулин"],
                "correct": "TSH"
            },

            {
                "question": "Какво обикновено се понижава при хипертиреоидизъм?",
                "options": ["TSH", "Глюкоза", "Инсулин", "Калций"],
                "correct": "TSH"
            },

            {
                "question": "Кой орган произвежда T3 и T4?",
                "options": ["Хипофиза", "Щитовидна жлеза", "Панкреас", "Надбъбречна жлеза"],
                "correct": "Щитовидна жлеза"
            },

            {
                "question": "Какво е нормалното състояние на TSH?",
                "options": ["Много високо", "Много ниско", "В норма", "Липсва"],
                "correct": "В норма"
            },

            {
                "question": "Кой симптом НЕ е типичен за хипотиреоидизъм?",
                "options": ["Умора", "Студени крайници", "Тахикардия", "Качване на тегло"],
                "correct": "Тахикардия"
            },

            {
                "question": "Кое заболяване е автоимунна причина за хипотиреоидизъм?",
                "options": ["Hashimoto", "Asthma", "Pneumonia", "Migraine"],
                "correct": "Hashimoto"
            },

            {
                "question": "Какво често се наблюдава при хипертиреоидизъм?",
                "options": ["Качване на тегло", "Бавен пулс", "Тремор", "Сънливост"],
                "correct": "Тремор"
            },

            {
                "question": "Какво представлява FT4?",
                "options": ["Свободен тироксин", "Кръвна захар", "Антитяло", "Ензим"],
                "correct": "Свободен тироксин"
            },

            {
                "question": "Кой симптом е типичен при нисък FT4?",
                "options": ["Умора", "Хиперактивност", "Еуфория", "Безсъние"],
                "correct": "Умора"
            },

            {
                "question": "Кой симптом е типичен при висок FT4?",
                "options": ["Тахикардия", "Сънливост", "Студени крайници", "Брадикардия"],
                "correct": "Тахикардия"
            },

            {
                "question": "Какво може да показва висок MAT?",
                "options": ["Автоимунен процес", "Инфекция", "Диабет", "Хипертония"],
                "correct": "Автоимунен процес"
            },

            {
                "question": "Какво може да показва висок TAT?",
                "options": ["Автоимунно заболяване", "Анемия", "Пневмония", "Инсулт"],
                "correct": "Автоимунно заболяване"
            },

            {
                "question": "Кое е най-често срещаното оплакване?",
                "options": ["Умора", "Загуба на слух", "Кашлица", "Болка в коляното"],
                "correct": "Умора"
            },

            {
                "question": "Какво е типично за Graves disease?",
                "options": ["Хипертиреоидизъм", "Хипотиреоидизъм", "Диабет", "Инфаркт"],
                "correct": "Хипертиреоидизъм"
            },

            {
                "question": "Кое изследване оценява функцията на щитовидната жлеза?",
                "options": ["TSH", "CRP", "HbA1c", "Creatinine"],
                "correct": "TSH"
            },

            {
                "question": "Какво е типично при бавен метаболизъм?",
                "options": ["Качване на тегло", "Отслабване", "Тахикардия", "Тремор"],
                "correct": "Качване на тегло"
            },

            {
                "question": "Кой симптом е свързан с ускорен метаболизъм?",
                "options": ["Отслабване", "Умора", "Сънливост", "Брадикардия"],
                "correct": "Отслабване"
            },

            {
                "question": "Какво често има при хипертиреоидизъм?",
                "options": ["Топлинна непоносимост", "Студени крайници", "Бавен пулс", "Умора"],
                "correct": "Топлинна непоносимост"
            },

            {
                "question": "Какво често има при хипотиреоидизъм?",
                "options": ["Студова непоносимост", "Тремор", "Тахикардия", "Отслабване"],
                "correct": "Студова непоносимост"
            },

            {
                "question": "Какво означава нисък TSH?",
                "options": ["Възможен хипертиреоидизъм", "Нормална функция", "Диабет", "Инфекция"],
                "correct": "Възможен хипертиреоидизъм"
            },

            {
                "question": "Какво означава висок TSH?",
                "options": ["Възможен хипотиреоидизъм", "Хипергликемия", "Инфаркт", "Инсулт"],
                "correct": "Възможен хипотиреоидизъм"
            },

            {
                "question": "Каква е ролята на TSH?",
                "options": [
                    "Стимулира щитовидната жлеза",
                    "Контролира кръвната захар",
                    "Регулира калция",
                    "Контролира бъбреците"
                ],
                "correct": "Стимулира щитовидната жлеза"
            },

            {
                "question": "Къде се произвежда TSH?",
                "options": ["Хипофиза", "Щитовидна жлеза", "Сърце", "Черен дроб"],
                "correct": "Хипофиза"
            },

            {
                "question": "Какво е често при Hashimoto?",
                "options": ["Повишени антитела", "Нисък калций", "Пневмония", "Хипогликемия"],
                "correct": "Повишени антитела"
            },

            {
                "question": "Кой симптом е неврологичен?",
                "options": ["Тремор", "Кашлица", "Обрив", "Коремна болка"],
                "correct": "Тремор"
            },

            {
                "question": "Какво може да покаже ехографията?",
                "options": [
                    "Структура на жлезата",
                    "Кръвна група",
                    "Глюкоза",
                    "Кислород"
                ],
                "correct": "Структура на жлезата"
            },

            {
                "question": "Кой хормон ускорява метаболизма?",
                "options": ["T3/T4", "Инсулин", "Кортизол", "Пролактин"],
                "correct": "T3/T4"
            },

            {
                "question": "Какво често има при тежък хипотиреоидизъм?",
                "options": ["Сънливост", "Еуфория", "Хиперактивност", "Тремор"],
                "correct": "Сънливост"
            }

        ]

        # ==========================================
        # FILTER QUESTIONS
        # ==========================================

        available_questions = [

            q for q in quiz_bank

            if q["question"] not in used_questions
        ]

        if not available_questions:

            used_questions.clear()

            available_questions = quiz_bank

        quiz = random.choice(available_questions)

        used_questions.add(quiz["question"])

        # ==========================================
        # RANDOMIZE ANSWERS
        # ==========================================

        options = quiz["options"].copy()

        random.shuffle(options)

        answer_index = options.index(quiz["correct"])

        # ==========================================
        # RESPONSE
        # ==========================================

        return jsonify({

            "success": True,

            "diagnosis": diagnosis,

            "quiz": {

                "question": quiz["question"],

                "options": options,

                "answer": answer_index

            }

        })

    except Exception as e:

        return jsonify({
            "success": False,
            "error": str(e)
        })
    
@app.route('/me')
def me():
    if "user_id" not in session:
        return jsonify({"logged_in": False})

    return jsonify({
        "logged_in": True,
        "user": session.get("user"),
        "role": session.get("role")
    })

@app.route('/book-appointment', methods=['POST'])
def book_appointment():

    conn = None
    cursor = None

    try:
        # =========================
        # AUTH CHECK
        # =========================
        if "user_id" not in session:
            return jsonify({"success": False, "error": "Not logged in"}), 401

        data = request.get_json() or {}

        doctor_id = data.get("doctor_id")
        date = data.get("date")
        time = data.get("time")

        if not doctor_id or not date or not time:
            return jsonify({"success": False, "error": "Missing data"}), 400

        # =========================
        # PARSE DATETIME
        # =========================
        try:
            selected_dt = datetime.strptime(f"{date} {time}", "%Y-%m-%d %H:%M")
        except ValueError:
            return jsonify({
                "success": False,
                "error": "Invalid date/time format"
            }), 400

        # =========================
        # BLOCK PAST
        # =========================
        if selected_dt <= datetime.now():
            return jsonify({
                "success": False,
                "error": "Няма как да запазите час в миналотом"
            }), 400

        # =========================
        # BLOCK WEEKENDS
        # =========================
        weekday = selected_dt.weekday()
        if weekday == 5 or weekday == 6:
            return jsonify({
                "success": False,
                "error": "Събота и неделя не са позволени за записване"
            }), 400

        # =========================
        # DB CONNECTION
        # =========================
        conn = get_db()
        cursor = conn.cursor(dictionary=True)

        # =========================
        # GET PATIENT ID
        # =========================
        cursor.execute("""
            SELECT id FROM patients WHERE user_id = %s
        """, (session["user_id"],))

        patient = cursor.fetchone()

        if not patient:
            return jsonify({
                "success": False,
                "error": "Patient profile not found"
            }), 400

        patient_id = patient["id"]

        # =========================
        # CHECK DUPLICATE SLOT
        # =========================
        cursor.execute("""
            SELECT id FROM appointments
            WHERE doctor_id=%s AND date=%s AND time=%s
        """, (doctor_id, date, time))

        if cursor.fetchone():
            return jsonify({
                "success": False,
                "error": "Slot already booked"
            }), 409

        # =========================
        # INSERT APPOINTMENT
        # =========================
        cursor.execute("""
            INSERT INTO appointments (doctor_id, patient_id, date, time)
            VALUES (%s, %s, %s, %s)
        """, (doctor_id, patient_id, date, time))

        conn.commit()

        return jsonify({"success": True})

    except Exception as e:
        print("BOOK ERROR:", e)
        return jsonify({"success": False, "error": str(e)}), 500

    finally:
        try:
            if cursor:
                cursor.close()
        except:
            pass

@app.route("/doctor-availability/<int:doctor_id>/<date>")
def doctor_availability(doctor_id, date):

    try:
        conn = get_db()
        cursor = conn.cursor(dictionary=True)

        cursor.execute("""
            SELECT time
            FROM appointments
            WHERE doctor_id = %s AND date = %s
        """, (doctor_id, date))

        rows = cursor.fetchall()

        cursor.close()

        booked = []

        for r in rows:
            t = r["time"]

            # SAFE conversion (fix crash)
            if hasattr(t, "strftime"):
                booked.append(t.strftime("%H:%M"))
            else:
                booked.append(str(t)[:5])

        return jsonify({
            "success": True,
            "booked": booked
        })

    except Exception as e:
        print("AVAILABILITY ERROR:", e)
        return jsonify({
            "success": False,
            "error": str(e),
            "booked": []
        }), 500
    
        
@app.route("/doctor/set-availability", methods=["POST"])
def set_availability():

    if not is_doctor():
        return jsonify({"success": False, "error": "Unauthorized"}), 403

    data = request.get_json() or {}

    doctor_id = session.get("user_id")
    date = data.get("date")
    start = data.get("start_time")
    end = data.get("end_time")

    if not date or not start or not end:
        return jsonify({"success": False, "error": "Missing data"}), 400

    try:
        conn = get_db()
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO doctor_schedule (doctor_id, date, start_time, end_time)
            VALUES (%s, %s, %s, %s)
        """, (doctor_id, date, start, end))

        conn.commit()

        return jsonify({"success": True})

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

    finally:
        cursor.close()

@app.route("/doctor/generated-slots/<int:doctor_id>/<date>")
def generated_slots(doctor_id, date):

    try:
        conn = get_db()
        cursor = conn.cursor(dictionary=True)

        cursor.execute("""
            SELECT start_time, end_time, slot_minutes
            FROM doctor_schedule
            WHERE doctor_id=%s AND date=%s
        """, (doctor_id, date))

        schedule = cursor.fetchone()

        if not schedule:
            return jsonify({"success": True, "slots": []})

        step = schedule["slot_minutes"] or 60

        start = datetime.strptime(str(schedule["start_time"])[:5], "%H:%M")
        end = datetime.strptime(str(schedule["end_time"])[:5], "%H:%M")

        slots = []

        while start < end:
            slots.append(start.strftime("%H:%M"))
            start += timedelta(minutes=step)

        return jsonify({"success": True, "slots": slots})

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

    finally:
        try:
            cursor.close()
        except:
            pass

from flask import request, jsonify

# -------------------------
# HELPERS
# -------------------------
def safe_float(value):
    try:
        if value is None or value == "":
            return 0.0
        return float(value)
    except:
        return 0.0


def clamp(value, min_val=0.0, max_val=1.0):
    return max(min_val, min(value, max_val))


@app.route("/run-analysis", methods=["POST"])
def run_analysis():

    try:
        if not is_logged_in():
            return jsonify({"error": "Unauthorized"}), 401

        # =========================
        # SAFE HELPERS (local, no dependencies)
        # =========================
        def safe_float(value):
            try:
                if value is None or value == "":
                    return None
                return float(value)
            except:
                return None

        def clamp(x, min_v=0, max_v=1):
            return max(min_v, min(x, max_v))

        # =========================
        # INPUTS
        # =========================
        file = request.files.get("file")

        complain = (request.form.get("complain") or "").lower()

        tsh = safe_float(request.form.get("tsh"))
        ft4 = safe_float(request.form.get("ft4"))
        mat = safe_float(request.form.get("mat"))
        tat = safe_float(request.form.get("tat"))

        # =========================
        # SCORES
        # =========================
        lab_score = 0.0
        symptom_score = 0.0
        image_score = 0.0

        # =========================
        # LAB SCORE (robust)
        # =========================
        if tsh is not None:
            if tsh > 4.5:
                lab_score += 0.4
            elif tsh < 0.4:
                lab_score += 0.35
            else:
                lab_score += 0.1

        if ft4 is not None:
            if ft4 < 10 or ft4 > 22:
                lab_score += 0.35
            else:
                lab_score += 0.1

        if mat is not None and mat > 34:
            lab_score += 0.2

        if tat is not None and tat > 115:
            lab_score += 0.2

        lab_score = clamp(lab_score, 0, 1)

        # =========================
        # SYMPTOMS ENGINE
        # =========================
        symptoms_map = {
            "fatigue": 0.15,
            "tired": 0.15,
            "weight": 0.18,
            "hair": 0.12,
            "palpitation": 0.2,
            "anxiety": 0.18,
            "cold": 0.12,
            "heat": 0.12
        }

        for k, v in symptoms_map.items():
            if k in complain:
                symptom_score += v

        symptom_score = clamp(symptom_score, 0, 1)

        # =========================
        # IMAGE SCORE
        # =========================
        if file and file.filename != "":
            image_score = 0.25

        # =========================
        # FINAL FUSION MODEL
        # =========================
        score = (
            lab_score * 0.5 +
            symptom_score * 0.3 +
            image_score * 0.2
        )

        score = clamp(score, 0, 1)

        confidence = round(score * 100, 2)

        # =========================
        # EXPLAINABLE AI BLOCK (WHY)
        # =========================
        explain = {
            "why_high_risk": {
                "lab_contribution": round(lab_score * 0.5, 2),
                "symptom_contribution": round(symptom_score * 0.3, 2),
                "image_contribution": round(image_score * 0.2, 2),
                "dominant_factor": max(
                    [
                        ("lab", lab_score),
                        ("symptoms", symptom_score),
                        ("image", image_score)
                    ],
                    key=lambda x: x[1]
                )[0]
            }
        }

        # =========================
        # CLINICAL DECISION
        # =========================
        if score < 0.30:
            risk = "LOW"
            advice = "Normal findings. Routine follow-up recommended."

        elif score < 0.55:
            risk = "MODERATE"
            advice = "Mild abnormalities detected. Endocrinology consultation recommended."

        elif score < 0.80:
            risk = "HIGH"
            advice = "Significant abnormalities detected. Further diagnostic evaluation required."

        else:
            risk = "CRITICAL"
            advice = "Severe risk detected. Immediate medical attention required."

        return jsonify({
            "status": "OK",
            "prediction": "Thyroid Risk Analysis",
            "confidence": confidence,
            "risk": risk,
            "follow_up": advice,
            "lab_score": round(lab_score, 2),
            "symptom_score": round(symptom_score, 2),
            "image_score": round(image_score, 2),
            "explain": explain
        })

    except Exception as e:
        return jsonify({
            "status": "ERROR",
            "message": str(e),
            "risk": "LOW"
        }), 500

@app.route('/doctor/stats-data')
def doctor_stats_data():

    user_id = session.get("user_id")
    role = session.get("role")

    if not user_id:
        return jsonify([]), 200   # важно: array, не object

    try:
        conn = get_db()
        cursor = conn.cursor(dictionary=True)

        cursor.execute("""
            SELECT 
                r.id AS id,
                p.full_name AS patient_name,
                r.prediction,
                r.confidence,
                r.risk_level,
                r.advice,
                r.explanation,
                r.created_at
            FROM analysis_results r
            JOIN patients p ON r.patient_id = p.id
            ORDER BY r.created_at DESC
        """)

        rows = cursor.fetchall()

        result = [{
            "id": r["id"],
            "patient_name": r["patient_name"],
            "prediction": r["prediction"],
            "confidence": float(r["confidence"] or 0),
            "risk_level": r["risk_level"],
            "advice": r["advice"],
            "explanation": r["explanation"],
            "created_at": r["created_at"].isoformat() if r["created_at"] else None
        } for r in rows]

        return jsonify(result)   # ALWAYS ARRAY

    except Exception as e:
        print("stats-data error:", e)
        return jsonify([])

    finally:
        if 'cursor' in locals(): cursor.close()

@app.route('/doctor/generate-pdf/<int:analysis_id>', methods=["POST"])
@doctor_required
def generate_medical_pdf(analysis_id):

    import os
    import io
    from datetime import datetime
    from reportlab.pdfgen import canvas
    from reportlab.lib.pagesizes import A4
    from reportlab.platypus import Paragraph, Spacer, Table, TableStyle, Image
    from reportlab.lib import colors
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.enums import TA_CENTER
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    from flask import send_file, request

    conn = None
    cursor = None

    def safe(val):
        if val is None or val == "":
            return "-"
        return val

    try:
        conn = get_db()
        cursor = conn.cursor(dictionary=True)

        # ======================
        # GET DATA
        # ======================
        cursor.execute("""
            SELECT 
                r.*, 
                p.full_name AS patient_name,
                p.age,
                p.gender,
                p.family_history,
                p.previous_thyroid_disease,
                p.autoimmune_history
            FROM analysis_results r
            JOIN patients p ON r.patient_id = p.id
            WHERE r.id = %s
            """, (analysis_id,))

        result = cursor.fetchone()
        print("IMAGE PATH:", result.get("image_path"))

        if not result:
            return "No record found", 404

        # ======================
        # GET EDITED EXPLANATION
        # ======================
        data = request.get_json(silent=True) or {}
        edited_explanation = data.get("explanation")

        if edited_explanation:
            cursor.execute("""
                UPDATE analysis_results
                SET doctor_explanation = %s
                WHERE id = %s
            """, (edited_explanation, analysis_id))
            conn.commit()

        final_explanation = edited_explanation or result.get("explanation") or "-"
        final_explanation = str(final_explanation)

        # ======================
        # PDF SETUP
        # ======================
        buffer = io.BytesIO()

        font_path = r"C:\Windows\Fonts\arial.ttf"

        if os.path.exists(font_path):
            pdfmetrics.registerFont(TTFont('Arial', font_path))
            font_name = "Arial"
        else:
            font_name = "Helvetica"

        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            rightMargin=40,
            leftMargin=40,
            topMargin=40,
            bottomMargin=30
        )

        styles = getSampleStyleSheet()

        title_style = ParagraphStyle(
            "title",
            parent=styles["Heading1"],
            fontName=font_name,
            fontSize=20,
            alignment=TA_CENTER,
            textColor=colors.HexColor("#1e3a8a"),
            spaceAfter=10
        )

        normal = ParagraphStyle(
            "normal",
            parent=styles["BodyText"],
            fontName=font_name,
            fontSize=10,
            leading=14
        )

        section = ParagraphStyle(
            "section",
            parent=styles["Heading2"],
            fontName=font_name,
            fontSize=12,
            textColor=colors.HexColor("#1e40af"),
            spaceBefore=10,
            spaceAfter=5
        )

        small = ParagraphStyle(
            "small",
            parent=styles["BodyText"],
            fontSize=8,
            textColor=colors.grey
        )

        story = []

        # ======================
        # HEADER
        # ======================

        logo_path = "static/logo.png"

        header_text = [
            Paragraph("УНИВЕРСИТЕТСКА БОЛНИЦА МЕДИЦИНСКИ ЦЕНТЪР", title_style),
            Paragraph("Отдел Ендoкриnология • AI Клиничен отчет", normal),
        ]

        # LOGO
        if os.path.exists(logo_path):
            logo = Image(logo_path, width=70, height=70)
        else:
            logo = ""

        # TABLE HEADER (logo + text)
        header_table = Table(
        [[logo, header_text]],
        colWidths=[80, 420]
        )

        header_table.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("LEFTPADDING", (0, 0), (-1, -1), 0),
            ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ]))

        story.append(header_table)
        story.append(Spacer(1, 10))

        # ======================
        # ПАЦИЕНТСКА ИНФОРМАЦИЯ
        # ======================
        patient_info = [
        ["Пациент", safe(result.get('patient_name'))],
        ["Номер на отчет", safe(result.get('id'))],
        ["Дата", safe(result.get('created_at'))],
        ["Риск", safe(result.get('risk_level'))],
        ]

        table = Table(patient_info, colWidths=[140, 330])
        table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#1e3a8a")),
            ("TEXTCOLOR", (0, 0), (0, -1), colors.white),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
            ("FONTNAME", (0, 0), (-1, -1), font_name),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
        ]))

        story.append(table)
        story.append(Spacer(1, 15))

        # ======================
        # ЕХОГРАФИЯ
        # ======================
        image_path = result.get("image_path")

        if image_path and os.path.exists(image_path):
            story.append(Spacer(1, 10))
            story.append(Paragraph("УЛТРАЗВУКОВО ИЗОБРАЖЕНИЕ", section))
            story.append(Image(image_path, width=250, height=250))

        # ======================
        # ДИАГНОЗА
        # ======================
        story.append(Paragraph("КЛИНИЧНА ДИАГНОЗA", section))
        story.append(Paragraph(f"AI: {safe(result.get('prediction'))}", normal))
        story.append(Paragraph(f"Точност: {safe(result.get('confidence', 0))}%", normal))
        story.append(Paragraph(f"Риск: {safe(result.get('risk_level'))}", normal))

        # ======================
        # ОЦЕНКА НА РИСКА
        # ======================
        story.append(Spacer(1, 10))
        story.append(Paragraph("ОЦЕНКА НА РИСКА", section))

        risk_table = Table([
            ["AI Клас", safe(result.get("ai_class"))],
            ["AI Точност", f"{safe(result.get('confidence', 0))}%"],
            ["Лабораторен резултат", safe(result.get("lab_score"))],
            ["Симптомен резултат", safe(result.get("symptom_score"))],
            ["Допълнителен риск", safe(result.get("extra_score"))],
            ["Общ риск", safe(result.get("risk_level"))]
        ], colWidths=[180, 280])

        risk_table.setStyle(TableStyle([
            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
            ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#1e3a8a")),
            ("TEXTCOLOR", (0, 0), (0, -1), colors.white),
            ("FONTNAME", (0, 0), (-1, -1), font_name),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
        ]))

        story.append(risk_table)

        # ======================
        # ПАЦИЕНТСКИ ФАКТОРИ
        # ======================
        story.append(Spacer(1, 10))
        story.append(Paragraph("РИСКОВИ ФАКТОРИ НА ПАЦИЕНТА", section))

        patient_table = Table([
            ["Възраст", safe(result.get("age"))],
            ["Пол", safe(result.get("gender"))],
            ["Фамилна обремененост", "Да" if result.get("family_history") else "Не"],
            ["Предишни заболявания на щитовидната жлеза", "Да" if result.get("previous_thyroid_disease") else "Не"],
            ["Автоимунни заболявания", "Да" if result.get("autoimmune_history") else "Не"]
        ], colWidths=[180, 280])

        patient_table.setStyle(TableStyle([
            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
            ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#1e3a8a")),
            ("TEXTCOLOR", (0, 0), (0, -1), colors.white),
            ("FONTNAME", (0, 0), (-1, -1), font_name),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
        ]))

        story.append(patient_table)

        # ======================
        # ПРЕПОРЪКА
        # ======================
        story.append(Spacer(1, 10))
        story.append(Paragraph("МЕДИЦИНСКА ПРЕПОРЪКА", section))
        story.append(Paragraph(safe(result.get('advice')), normal))

        # ======================
        # КЛИНИЧЕН АНАЛИЗ
        # ======================
        story.append(Spacer(1, 10))
        story.append(Paragraph("КЛИНИЧЕН АНАЛИЗ", section))

        for line in str(final_explanation).splitlines():
            line = line.strip()
            if line:
                if ":" in line:
                    parts = line.split(":", 1)
                    story.append(Paragraph(f"<b>{parts[0].strip()}</b>: {parts[1].strip()}", normal))
                else:
                    story.append(Paragraph(line, normal))

        # ======================
        # ДИСКЛЕЙМЪР
        # ======================
        story.append(Spacer(1, 10))
        story.append(Paragraph(
            "⚠ Този отчет е генериран с помощта на изкуствен интелект и е проверен от лекар.",
            small
        ))

        # ======================
        # ПОДПИС
        # ======================
        story.append(Spacer(1, 15))

        signature = Table([
            ["Лекар", "MED-AI Система"],
            ["Отдел", "Ендокринология"],
            ["Подпис", "__________________"],
        ], colWidths=[180, 280])

        signature.setStyle(TableStyle([
            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
            ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#1e3a8a")),
            ("TEXTCOLOR", (0, 0), (0, -1), colors.white),
            ("FONTNAME", (0, 0), (-1, -1), font_name),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
        ]))

        story.append(signature)
        
        # ======================
        # BUILD
        # ======================
        def add_watermark(canvas_obj, doc_obj):
            canvas_obj.saveState()
            canvas_obj.setFont("Helvetica-Bold", 40)
            canvas_obj.setFillColorRGB(0.85, 0.85, 0.85)
            canvas_obj.translate(300, 400)
            canvas_obj.rotate(45)
            canvas_obj.drawCentredString(0, 0, "MED-AI SYSTEM")
            canvas_obj.restoreState()

        doc.build(story, onFirstPage=add_watermark, onLaterPages=add_watermark)
        buffer.seek(0)

        return send_file(
            buffer,
            as_attachment=True,
            download_name=f"report_{analysis_id}.pdf",
            mimetype="application/pdf"
        )

    except Exception as e:
        print("PDF ERROR:", e)
        return str(e), 500

    finally:
        if cursor:
            cursor.close()

@app.route('/doctor/save-edit/<int:analysis_id>', methods=["POST"])
def save_edit(analysis_id):

    conn = get_db()
    cursor = conn.cursor()

    data = request.get_json()
    explanation = data.get("explanation")

    cursor.execute("""
        UPDATE analysis_results
        SET doctor_explanation = %s
        WHERE id = %s
    """, (explanation, analysis_id))

    conn.commit()

    cursor.close()

    return {"success": True}

@app.route('/doctor/diagnosis-decision', methods=['POST'])
@doctor_required
def diagnosis_decision():
    conn = None
    cursor = None

    try:
        data = request.get_json(silent=True)

        if not data:
            return jsonify({"success": False, "error": "No JSON received"}), 400

        analysis_id = data.get("analysis_id")
        decision = data.get("decision")

        if analysis_id is None or decision is None:
            return jsonify({"success": False, "error": "Missing data"}), 400

        conn = get_db()
        cursor = conn.cursor()

        cursor.execute("""
            UPDATE analysis_results
            SET doctor_decision = %s
            WHERE id = %s
        """, (decision, analysis_id))

        conn.commit()

        return jsonify({"success": True})

    except Exception as e:
        if conn:
            conn.rollback()
        print("ERROR diagnosis_decision:", e)

        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

    finally:
        if cursor:
            cursor.close()
# =====================================================
# RUN
# =====================================================

if __name__ == '__main__':
    app.run(debug=True, port=5000)