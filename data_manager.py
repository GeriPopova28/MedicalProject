import mysql.connector
from werkzeug.security import generate_password_hash, check_password_hash

class DataManager:

    def __init__(self, db_config):
        self.db_config = db_config

    def get_connection(self):
        return mysql.connector.connect(**self.db_config)

    # ================= REGISTER =================
    def register_user(self, username, password, role):
        db = self.get_connection()
        cursor = db.cursor()

        cursor.execute(
            "SELECT id FROM users WHERE username=%s",
            (username,)
        )
        existing = cursor.fetchone()

        if existing:
            cursor.close()
            db.close()
            return False

        hashed_password = generate_password_hash(password)

        cursor.execute(
            "INSERT INTO users (username, password, role) VALUES (%s, %s, %s)",
            (username, hashed_password, role)
        )

        db.commit()
        cursor.close()
        db.close()

        return True

    # ================= LOGIN =================
    def login_user(self, username, password_input):
        db = self.get_connection()
        cursor = db.cursor(dictionary=True)

        cursor.execute(
            "SELECT * FROM users WHERE username=%s",
            (username,)
        )

        user = cursor.fetchone()

        cursor.close()
        db.close()

        if user and check_password_hash(user['password'], password_input):
            return user
        
        return None