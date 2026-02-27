from flask import Blueprint, request, jsonify
from flask_jwt_extended import create_access_token
from database.db import db
from database.models import Farmer
from werkzeug.security import generate_password_hash, check_password_hash
import random

auth_bp = Blueprint('auth_bp', __name__)

# In-memory OTP store (in production, use Redis or SMS service)
_otp_store = {}


@auth_bp.route('/auth/send-otp', methods=['POST'])
def send_otp():
    """Send OTP to phone number (simulated for dev)."""
    data = request.json
    phone = data.get('phone', '').strip()

    if not phone or len(phone) < 10:
        return jsonify({"error": "Invalid phone number"}), 400

    # Generate 6-digit OTP (in production, send via SMS gateway)
    otp = str(random.randint(100000, 999999))
    _otp_store[phone] = otp

    # For development, return OTP in response body
    return jsonify({
        "success": True,
        "message": "OTP sent successfully",
        "dev_otp": otp  # Remove in production!
    }), 200


@auth_bp.route('/auth/verify-otp', methods=['POST'])
def verify_otp():
    """Verify OTP and return JWT + farmer profile (or signal new user)."""
    data = request.json
    phone = data.get('phone', '').strip()
    otp = data.get('otp', '').strip()

    if not phone or not otp:
        return jsonify({"error": "Phone and OTP required"}), 400

    # Check OTP (accept '123456' as dev bypass)
    stored_otp = _otp_store.get(phone)
    if otp != stored_otp and otp != '123456':
        return jsonify({"error": "Invalid OTP"}), 401

    # Clear used OTP
    _otp_store.pop(phone, None)

    # Find or create farmer
    farmer = Farmer.query.filter_by(phone=phone).first()
    is_new_user = farmer is None

    if is_new_user:
        farmer = Farmer(phone=phone)
        db.session.add(farmer)
        db.session.commit()

    # Generate JWT
    access_token = create_access_token(identity=farmer.id)

    return jsonify({
        "success": True,
        "token": access_token,
        "farmer_id": farmer.id,
        "is_new_user": is_new_user,
        "onboarding_complete": farmer.onboarding_complete,
        "farmer": farmer.to_dict()
    }), 200


@auth_bp.route('/auth/update-profile', methods=['POST'])
def update_profile():
    """Update farmer profile during or after onboarding."""
    data = request.json
    farmer_id = data.get('farmer_id')

    if not farmer_id:
        return jsonify({"error": "farmer_id required"}), 400

    farmer = Farmer.query.get(farmer_id)
    if not farmer:
        return jsonify({"error": "Farmer not found"}), 404

    # Update only provided fields
    updatable_fields = [
        'name', 'language', 'state', 'district', 'latitude', 'longitude',
        'primary_crop', 'preferred_mandi', 'land_size', 'storage_available',
        'soil_type', 'irrigation_type', 'onboarding_complete'
    ]

    for field in updatable_fields:
        if field in data:
            setattr(farmer, field, data[field])

    # Also accept 'preferred_crop' as alias
    if 'preferred_crop' in data:
        farmer.primary_crop = data['preferred_crop']

    db.session.commit()

    return jsonify({
        "success": True,
        "farmer": farmer.to_dict()
    }), 200


# ============================================================
#  PASSWORD-BASED AUTH
# ============================================================

@auth_bp.route('/auth/register', methods=['POST'])
def register_with_password():
    """
    Register a new user with phone + password.
    Body: { phone, password, name? }
    """
    data = request.json or {}
    phone = data.get('phone', '').strip()
    password = data.get('password', '').strip()
    name = data.get('name', '').strip()

    if not phone or len(phone) < 10:
        return jsonify({"error": "Invalid phone number"}), 400
    if not password or len(password) < 6:
        return jsonify({"error": "Password must be at least 6 characters"}), 400

    # Check if user already exists
    existing = Farmer.query.filter_by(phone=phone).first()
    if existing:
        # If they registered via OTP before (no password), let them set one
        if existing.password_hash:
            return jsonify({"error": "Phone number already registered. Please login."}), 409
        else:
            existing.password_hash = generate_password_hash(password)
            if name:
                existing.name = name
            db.session.commit()
            access_token = create_access_token(identity=existing.id)
            return jsonify({
                "success": True,
                "token": access_token,
                "farmer_id": existing.id,
                "is_new_user": False,
                "onboarding_complete": existing.onboarding_complete,
                "farmer": existing.to_dict(),
                "message": "Password set for existing account"
            }), 200

    # Create new user with password
    farmer = Farmer(
        phone=phone,
        password_hash=generate_password_hash(password),
        name=name or None,
    )
    db.session.add(farmer)
    db.session.commit()

    access_token = create_access_token(identity=farmer.id)

    return jsonify({
        "success": True,
        "token": access_token,
        "farmer_id": farmer.id,
        "is_new_user": True,
        "onboarding_complete": False,
        "farmer": farmer.to_dict()
    }), 201


@auth_bp.route('/auth/login', methods=['POST'])
def login_with_password():
    """
    Login with phone + password.
    Body: { phone, password }
    """
    data = request.json or {}
    phone = data.get('phone', '').strip()
    password = data.get('password', '').strip()

    if not phone or not password:
        return jsonify({"error": "Phone and password required"}), 400

    farmer = Farmer.query.filter_by(phone=phone).first()
    if not farmer:
        return jsonify({"error": "Account not found. Please register first."}), 404

    if not farmer.password_hash:
        return jsonify({
            "error": "This account uses OTP login. Please use OTP or set a password via Register."
        }), 400

    if not check_password_hash(farmer.password_hash, password):
        return jsonify({"error": "Incorrect password"}), 401

    access_token = create_access_token(identity=farmer.id)

    return jsonify({
        "success": True,
        "token": access_token,
        "farmer_id": farmer.id,
        "is_new_user": False,
        "onboarding_complete": farmer.onboarding_complete,
        "farmer": farmer.to_dict()
    }), 200

