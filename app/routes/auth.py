from flask import Blueprint, render_template, request, jsonify, redirect, url_for

auth_bp = Blueprint('auth', __name__)

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

