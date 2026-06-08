from flask import session

def is_logged_in():
    return 'user' in session

def is_doctor():
    return session.get("role") == "Doctor"

def is_patient():
    return session.get("role") == "Patient"