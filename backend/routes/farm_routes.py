"""
Farm & Crop CRUD Routes

POST   /farms                              — Create a new farm
POST   /farms/<farm_id>/crops              — Add a crop to a farm
PUT    /farms/<farm_id>/crops/<crop_id>    — Update a crop record
DELETE /farms/<farm_id>/crops/<crop_id>    — Delete a crop record
GET    /user/<user_id>/farms               — List all farms + crops for a user
GET    /user/<user_id>/active-crop         — Return the default crop context
"""

from flask import Blueprint, request, jsonify
from services.farmer_service import FarmerService

farm_bp = Blueprint('farm_bp', __name__)


# ──────────────────────────────────────────
# FARM
# ──────────────────────────────────────────

@farm_bp.route('/farms', methods=['POST'])
def create_farm():
    data = request.json or {}
    user_id = data.get('user_id')
    if not user_id:
        return jsonify({"error": "user_id is required"}), 400

    farm = FarmerService.create_farm(user_id, data)
    farm_dict = farm.to_dict()
    farm_dict['crops'] = []
    return jsonify({"success": True, "farm": farm_dict}), 201


# ──────────────────────────────────────────
# FARM CROPS
# ──────────────────────────────────────────

@farm_bp.route('/farms/<farm_id>/crops', methods=['POST'])
def add_crop(farm_id):
    data = request.json or {}
    crop = FarmerService.add_crop_to_farm(farm_id, data)
    return jsonify({"success": True, "crop": crop.to_dict()}), 201


@farm_bp.route('/farms/<farm_id>/crops/<crop_id>', methods=['PUT'])
def update_crop(farm_id, crop_id):
    data = request.json or {}
    crop = FarmerService.update_crop(crop_id, data)
    if crop:
        return jsonify({"success": True, "crop": crop.to_dict()})
    return jsonify({"error": "Crop not found"}), 404


@farm_bp.route('/farms/<farm_id>/crops/<crop_id>', methods=['DELETE'])
def delete_crop(farm_id, crop_id):
    deleted = FarmerService.delete_crop(crop_id)
    if deleted:
        return jsonify({"success": True, "message": "Crop deleted"})
    return jsonify({"error": "Crop not found"}), 404


# ──────────────────────────────────────────
# USER → FARMS LISTING
# ──────────────────────────────────────────

@farm_bp.route('/user/<user_id>/farms', methods=['GET'])
def get_user_farms(user_id):
    farms = FarmerService.get_user_farms(user_id)
    return jsonify({"farms": farms})


@farm_bp.route('/user/<user_id>/active-crop', methods=['GET'])
def get_active_crop(user_id):
    """Return the default crop context for a user (first farm-crop)."""
    crop = FarmerService.get_default_crop(user_id)
    if crop:
        context = FarmerService.get_crop_context(crop.id)
        return jsonify({"active_crop": context})
    return jsonify({"active_crop": None, "message": "No crops registered"})
