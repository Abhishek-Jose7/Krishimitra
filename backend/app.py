from flask import Flask
from flask_cors import CORS
from config import Config
from database.db import db
from routes.yield_routes import yield_bp
from routes.price_routes import price_bp
from routes.mandi_routes import mandi_bp
from routes.recommendation_routes import recommendation_bp
from routes.farmer_routes import farmer_bp
from routes.weather_routes import weather_bp
from routes.auth_routes import auth_bp
from routes.dashboard_routes import dashboard_bp
from routes.notification_routes import notification_bp
from routes.evaluation_routes import evaluation_bp
import atexit
import logging

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)
    app.config['JWT_SECRET_KEY'] = 'super-secret-key-change-this-in-env'  # Change this!

    from flask_jwt_extended import JWTManager
    jwt = JWTManager(app)

    db.init_app(app)
    CORS(app)  # Allow Flutter web frontend to call API

    # ── Rate Limiting ──
    try:
        from flask_limiter import Limiter
        from flask_limiter.util import get_remote_address
        limiter = Limiter(
            get_remote_address,
            app=app,
            default_limits=["60 per minute"],
            storage_uri="memory://",
        )
        # Stricter limit for auth endpoints
        limiter.limit("10 per minute")(auth_bp)
        app.logger.info("Rate limiting enabled: 60/min general, 10/min auth")
    except ImportError:
        app.logger.warning("Flask-Limiter not installed. Rate limiting disabled.")

    # ── Observability ──
    try:
        from services.observability import setup_observability
        setup_observability(app)
    except Exception as e:
        logging.warning(f"Observability setup failed: {e}")

    # Register blueprints (original)
    app.register_blueprint(yield_bp)
    app.register_blueprint(price_bp)
    app.register_blueprint(mandi_bp)
    app.register_blueprint(recommendation_bp)
    app.register_blueprint(farmer_bp)
    app.register_blueprint(weather_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)

    # Register new blueprints
    app.register_blueprint(notification_bp)
    app.register_blueprint(evaluation_bp)

    with app.app_context():
        db.create_all()

    # ── Background Scheduler ──
    try:
        from services.scheduler import init_scheduler, shutdown_scheduler
        init_scheduler(app)
        atexit.register(shutdown_scheduler)
    except ImportError:
        app.logger.warning("APScheduler not installed. Background jobs disabled.")
    except Exception as e:
        app.logger.warning(f"Scheduler init failed: {e}")

    @app.route('/')
    def index():
        return {"message": "KrishiMitra AI API is running", "version": "2.0"}

    return app

if __name__ == '__main__':
    app = create_app()
    app.run(host='0.0.0.0', port=5000)
