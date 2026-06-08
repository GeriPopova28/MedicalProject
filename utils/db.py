import mysql.connector

db_config = {
    "host": "localhost",
    "user": "root",
    "password": "GeriP2807",
    "database": "medical_ai"
}

def get_db():
    return mysql.connector.connect(**db_config)