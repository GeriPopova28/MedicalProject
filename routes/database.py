import mysql.connector


def get_db():
    conn = mysql.connector.connect(
        host="localhost",
        user="root",
        password="GeriP2807",
        database="medicaldb"
    )
    return conn