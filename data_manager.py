import mysql.connector


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

        cursor.execute(
            "INSERT INTO users (username, password, role) VALUES (%s, %s, %s)",
            (username, password, role)
        )

        db.commit()
        cursor.close()
        db.close()

        return True

    # ================= LOGIN =================
    def login_user(self, username):
        db = self.get_connection()
        cursor = db.cursor(dictionary=True)

        cursor.execute(
            "SELECT * FROM users WHERE username=%s",
            (username,)
        )

        user = cursor.fetchone()

        cursor.close()
        db.close()

        return user