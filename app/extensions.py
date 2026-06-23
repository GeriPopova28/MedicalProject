import mysql.connector
from flask import g
from tensorflow.keras.models import load_model
import os

ai_model = None


def get_db():
    if 'db' not in g:
        g.db = mysql.connector.connect(
            host="localhost",
            user="root",
            password="",
            database="medical_ai"
        )
    return g.db


def load_ai_model(app):
    global ai_model

    model_path = os.path.join(os.getcwd(), "ai_model.h5")

    if os.path.exists(model_path):
        ai_model = load_model(model_path, compile=False)
        print("AI model loaded!")