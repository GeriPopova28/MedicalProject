from flask import Blueprint, app, render_template, jsonify, redirect, url_for

from app.services.auth_service import is_logged_in, is_doctor
from app.services.db_service import get_db

doctor_bp = Blueprint('doctor', __name__)

@app.route('/doctor-dashboard')
def doctor_dashboard():

    if not is_logged_in():
        return redirect(url_for('login_page'))

    if not is_doctor():
        return redirect(url_for('patient_dashboard'))

    return render_template("doctor/doctor_dashboard.html")

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
    doctor_id = session.get("doctor_id")

    if not doctor_id:
        return jsonify({
            "success": False,
            "error": "Doctor ID missing"
        })
    try:
        conn = get_db()
        cursor = conn.cursor(dictionary=True)
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
    if not is_doctor():
        return jsonify({
            "success": False,
            "error": "Unauthorized"
        })
    try:
        data = request.get_json()

        action = data.get("action")
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

