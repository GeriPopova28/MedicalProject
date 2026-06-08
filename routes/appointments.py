from flask import Blueprint, request, jsonify, session
from datetime import datetime, timedelta
from utils.db import get_db

appointments_bp = Blueprint('appointments', __name__)

@appointments_bp.route('/book-appointment', methods=['POST'])
def book_appointment():
    conn = None
    cursor = None
    try:
        if "user_id" not in session:
            return jsonify({"success": False, "error": "Not logged in"}), 401

        data = request.get_json() or {}
        doctor_id = data.get("doctor_id")
        date = data.get("date")
        time = data.get("time")

        if not doctor_id or not date or not time:
            return jsonify({"success": False, "error": "Missing data"}), 400

        try:
            selected_dt = datetime.strptime(f"{date} {time}", "%Y-%m-%d %H:%M")
        except ValueError:
            return jsonify({"success": False, "error": "Invalid date/time format"}), 400

        if selected_dt <= datetime.now():
            return jsonify({"success": False, "error": "Няма как да запазите час в миналото"}), 400

        weekday = selected_dt.weekday()
        if weekday == 5 or weekday == 6:
            return jsonify({"success": False, "error": "Събота и неделя не са позволени за записване"}), 400

        conn = get_db()
        cursor = conn.cursor(dictionary=True)

        cursor.execute("SELECT id FROM patients WHERE user_id = %s", (session["user_id"],))
        patient = cursor.fetchone()

        if not patient:
            return jsonify({"success": False, "error": "Patient profile not found"}), 400

        patient_id = patient["id"]

        cursor.execute("""
            SELECT id FROM appointments
            WHERE doctor_id=%s AND date=%s AND time=%s
        """, (doctor_id, date, time))

        if cursor.fetchone():
            return jsonify({"success": False, "error": "Slot already booked"}), 409

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
        if cursor: cursor.close()
        if conn: conn.close()

@appointments_bp.route("/doctor-availability/<int:doctor_id>/<date>")
def doctor_availability(doctor_id, date):
    try:
        conn = get_db()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT time FROM appointments WHERE doctor_id = %s AND date = %s", (doctor_id, date))
        rows = cursor.fetchall()
        cursor.close()
        conn.close()

        booked = []
        for r in rows:
            t = r["time"]
            if hasattr(t, "strftime"):
                booked.append(t.strftime("%H:%M"))
            else:
                booked.append(str(t)[:5])

        return jsonify({"success": True, "booked": booked})
    except Exception as e:
        return jsonify({"success": False, "error": str(e), "booked": []}), 500

@appointments_bp.route("/doctor/set-availability", methods=["POST"])
def set_availability():
    from utils.auth_helpers import is_doctor # Локален импорт за избягване на цикличност
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
        conn.close()

@appointments_bp.route("/doctor/generated-slots/<int:doctor_id>/<date>")
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
        if 'cursor' in locals(): cursor.close()
        if 'conn' in locals(): conn.close()