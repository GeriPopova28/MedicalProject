from flask import Flask # type: ignore
from utils import db # type: ignore
from .extensions import load_ai_model, get_db

def create_app():
    app = Flask(__name__)

    app.config.from_object("config.Config")

    load_ai_model(app)

    # BLUEPRINTS
    from .routes.auth import auth_bp
    from .routes.patient import patient_bp  # type: ignore
    from .routes.doctor import doctor_bp  # type: ignore
    from .routes.analysis import analysis_bp # type: ignore
    from .routes.appointments import appointment_bp  # type: ignore

    app.register_blueprint(auth_bp)
    app.register_blueprint(patient_bp)
    app.register_blueprint(doctor_bp)
    app.register_blueprint(analysis_bp)
    app.register_blueprint(appointment_bp)

    return app