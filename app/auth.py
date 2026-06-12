from flask import Blueprint, request, jsonify, session, redirect, url_for
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
import re
import mysql.connector
import os

auth = Blueprint("auth", __name__)

db_config = {
    "host": "localhost",
    "user": "root",
    "password": "GeriP2807",
    "database": "medical_ai"
}

def get_db():
    return mysql.connector.connect(**db_config)


def is_strong_password(password: str) -> bool:
    if len(password) < 8:
        return False
    if not re.search(r"[A-Za-z]", password):
        return False
    if not re.search(r"[0-9]", password):
        return False
    return True


@auth.route("/handle_auth", methods=["POST"])
def handle_auth():

    data = request.get_json() or {}

    username = (data.get("username") or "").strip()
    password = data.get("password") or ""
    action = data.get("action", "login")

    if not username or not password:
        return jsonify({"success": False, "error": "Missing credentials"}), 400

    conn = get_db()
    cursor = conn.cursor(dictionary=True)

    try:

        if action == "register":

            role = data.get("role", "Patient")

            if role not in ["Doctor", "Patient"]:
                role = "Patient"

            if not is_strong_password(password):
                return jsonify({
                    "success": False,
                    "error": "Password must be 8+ chars with letters + numbers"
                }), 400

            cursor.execute(
                "SELECT id FROM users WHERE username=%s",
                (username,)
            )

            if cursor.fetchone():
                return jsonify({"success": False, "error": "User already exists"}), 409

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
            session["user_id"] = user_id
            session["user"] = username
            session["role"] = role

            return jsonify({"success": True, "role": role})

        cursor.execute("""
            SELECT id, username, password, role, failed_attempts, lock_until
            FROM users
            WHERE username=%s
        """, (username,))

        user = cursor.fetchone()

        if not user:
            return jsonify({"success": False, "error": "User not found"}), 404

        if user["lock_until"]:
            if user["lock_until"] > datetime.now():
                return jsonify({"success": False, "error": "Account locked"}), 403

            cursor.execute("""
                UPDATE users
                SET failed_attempts=0, lock_until=NULL
                WHERE id=%s
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
                SET failed_attempts=%s, lock_until=%s
                WHERE id=%s
            """, (attempts, lock_until, user["id"]))

            conn.commit()

            return jsonify({"success": False, "error": "Wrong password"}), 401

        cursor.execute("""
            UPDATE users
            SET failed_attempts=0, lock_until=NULL
            WHERE id=%s
        """, (user["id"],))

        conn.commit()

        session.clear()
        session["user_id"] = user["id"]
        session["user"] = user["username"]
        session["role"] = user["role"]

        return jsonify({
            "success": True,
            "role": user["role"]
        })

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

    finally:
        cursor.close()
        conn.close()

@auth.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login_page"))