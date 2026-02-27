import uuid
from database.db import db
from database.models import User, Farm, FarmCrop

# Backward compat alias
Farmer = User


class FarmerService:
    # ──────────────────────────────────────────
    # USER CRUD (unchanged)
    # ──────────────────────────────────────────

    @staticmethod
    def create_farmer(data):
        from flask_jwt_extended import create_access_token

        try:
            existing_farmer = Farmer.query.filter_by(phone=data['phone']).first()
            if existing_farmer:
                access_token = create_access_token(identity=existing_farmer.id)
                return {
                    "success": True,
                    "token": access_token,
                    "farmer_id": existing_farmer.id,
                    "onboarding_complete": existing_farmer.onboarding_complete,
                    "farmer": existing_farmer.to_dict(),
                    "message": "User already exists, logged in."
                }

            new_farmer = Farmer(
                id=str(uuid.uuid4()),
                phone=data['phone'],
                name=data.get('name'),
                language=data.get('language', 'en'),
                state=data.get('state'),
                district=data.get('district'),
                latitude=data.get('latitude'),
                longitude=data.get('longitude'),
            )
            db.session.add(new_farmer)
            db.session.commit()

            access_token = create_access_token(identity=new_farmer.id)

            return {
                "success": True,
                "token": access_token,
                "farmer_id": new_farmer.id,
                "farmer": new_farmer.to_dict()
            }
        except Exception as e:
            db.session.rollback()
            return {"error": str(e)}

    @staticmethod
    def get_farmer(farmer_id):
        farmer = Farmer.query.get(farmer_id)
        if farmer:
            return farmer.to_dict()
        return None

    @staticmethod
    def update_farmer(farmer_id, data):
        farmer = Farmer.query.get(farmer_id)
        if not farmer:
            return None

        updatable_fields = [
            'name', 'language', 'state', 'district', 'latitude', 'longitude',
            'taluk', 'onboarding_complete'
        ]

        for field in updatable_fields:
            if field in data:
                setattr(farmer, field, data[field])

        db.session.commit()
        return farmer.to_dict()

    # ──────────────────────────────────────────
    # FARM CRUD
    # ──────────────────────────────────────────

    @staticmethod
    def create_farm(user_id, data):
        """Create a new farm for the given user."""
        farm = Farm(
            id=str(uuid.uuid4()),
            user_id=user_id,
            farm_name=data.get('farm_name', 'My Farm'),
            total_land_hectares=data.get('total_land_hectares', 0),
            soil_type=data.get('soil_type'),
            irrigation_type=data.get('irrigation_type'),
            has_storage=data.get('has_storage', False),
            storage_capacity_quintals=data.get('storage_capacity_quintals', 0),
        )
        db.session.add(farm)
        db.session.commit()
        return farm

    @staticmethod
    def update_farm(farm_id, data):
        """Update an existing farm."""
        farm = Farm.query.get(farm_id)
        if not farm:
            return None

        updatable = [
            'farm_name', 'total_land_hectares', 'soil_type',
            'irrigation_type', 'has_storage', 'storage_capacity_quintals',
        ]
        for field in updatable:
            if field in data:
                setattr(farm, field, data[field])

        db.session.commit()
        return farm

    # ──────────────────────────────────────────
    # FARM-CROP CRUD
    # ──────────────────────────────────────────

    @staticmethod
    def add_crop_to_farm(farm_id, data):
        """Add a crop record to a farm."""
        from datetime import date as date_type

        sowing_date = data.get('sowing_date')
        if isinstance(sowing_date, str):
            try:
                sowing_date = date_type.fromisoformat(sowing_date)
            except ValueError:
                sowing_date = None

        harvest_date = data.get('expected_harvest_date')
        if isinstance(harvest_date, str):
            try:
                harvest_date = date_type.fromisoformat(harvest_date)
            except ValueError:
                harvest_date = None

        crop = FarmCrop(
            id=str(uuid.uuid4()),
            farm_id=farm_id,
            crop_name=data.get('crop_name', 'Rice'),
            variety=data.get('variety'),
            area_hectares=data.get('area_hectares', 0),
            sowing_date=sowing_date,
            expected_harvest_date=harvest_date,
            planting_year=data.get('planting_year'),
            tree_count=data.get('tree_count'),
            is_perennial=data.get('is_perennial', False),
            preferred_mandi=data.get('preferred_mandi'),
        )
        db.session.add(crop)
        db.session.commit()
        return crop

    @staticmethod
    def update_crop(crop_id, data):
        """Update an existing crop record."""
        crop = FarmCrop.query.get(crop_id)
        if not crop:
            return None

        updatable = [
            'crop_name', 'variety', 'area_hectares', 'sowing_date',
            'expected_harvest_date', 'planting_year', 'tree_count',
            'is_perennial', 'preferred_mandi',
        ]
        for field in updatable:
            if field in data:
                setattr(crop, field, data[field])

        db.session.commit()
        return crop

    @staticmethod
    def delete_crop(crop_id):
        """Delete a crop record."""
        crop = FarmCrop.query.get(crop_id)
        if not crop:
            return False
        db.session.delete(crop)
        db.session.commit()
        return True

    # ──────────────────────────────────────────
    # QUERY HELPERS
    # ──────────────────────────────────────────

    @staticmethod
    def get_user_farms(user_id):
        """Return all farms + nested crops for a user."""
        farms = Farm.query.filter_by(user_id=user_id).all()
        result = []
        for farm in farms:
            farm_dict = farm.to_dict()
            farm_dict['crops'] = [c.to_dict() for c in farm.crops]
            result.append(farm_dict)
        return result

    @staticmethod
    def get_crop_context(farm_crop_id):
        """
        Load full crop context for the intelligence pipeline.
        Returns a dict with everything the dashboard/recommendation
        engine needs, pulled from FarmCrop + Farm + User.
        """
        crop = FarmCrop.query.get(farm_crop_id)
        if not crop:
            return None

        farm = Farm.query.get(crop.farm_id)
        if not farm:
            return None

        user = User.query.get(farm.user_id)
        if not user:
            return None

        return {
            # Crop context
            'farm_crop_id': crop.id,
            'crop': crop.crop_name,
            'crop_name': crop.crop_name,
            'variety': crop.variety,
            'area_hectares': crop.area_hectares or 0,
            'land_size': crop.area_hectares or 0,
            'sowing_date': crop.sowing_date.isoformat() if crop.sowing_date else None,
            'expected_harvest_date': crop.expected_harvest_date.isoformat() if crop.expected_harvest_date else None,
            'is_perennial': crop.is_perennial,
            'preferred_mandi': crop.preferred_mandi,

            # Farm context
            'farm_id': farm.id,
            'farm_name': farm.farm_name,
            'soil_type': farm.soil_type,
            'irrigation_type': farm.irrigation_type,
            'has_storage': farm.has_storage,
            'storage_available': farm.has_storage,
            'storage_capacity_quintals': farm.storage_capacity_quintals or 0,

            # User/location context
            'user_id': user.id,
            'state': user.state,
            'district': user.district,
            'taluk': user.taluk,
            'latitude': user.latitude,
            'longitude': user.longitude,
        }

    @staticmethod
    def get_default_crop(user_id):
        """Return the first FarmCrop for a user (default active context)."""
        farms = Farm.query.filter_by(user_id=user_id).all()
        for farm in farms:
            crops = FarmCrop.query.filter_by(farm_id=farm.id).first()
            if crops:
                return crops
        return None

    @staticmethod
    def setup_farm_from_onboarding(user_id, data):
        """
        Create Farm + FarmCrop records from onboarding data.

        Accepts either:
          - New format: { farm: {...}, crops: [{crop_name, area_hectares, ...}] }
          - Old format: { primary_crop, land_size, soil_type, ... }

        Returns the created farm dict with nested crops.
        """
        farm_data = data.get('farm', {})
        crops_list = data.get('crops', [])

        # ── New structured format ──
        if crops_list:
            total_ha = sum(c.get('area_hectares', 0) for c in crops_list)

            farm = FarmerService.create_farm(user_id, {
                'farm_name': farm_data.get('farm_name', 'My Farm'),
                'total_land_hectares': total_ha,
                'soil_type': farm_data.get('soil_type') or data.get('soil_type'),
                'irrigation_type': farm_data.get('irrigation_type') or data.get('irrigation_type'),
                'has_storage': farm_data.get('has_storage', data.get('storage_available', False)),
                'storage_capacity_quintals': farm_data.get('storage_capacity_quintals', 0),
            })

            created_crops = []
            mandi = data.get('preferred_mandi') or data.get('mandi')
            for crop_data in crops_list:
                crop = FarmerService.add_crop_to_farm(farm.id, {
                    'crop_name': crop_data.get('crop_name'),
                    'area_hectares': crop_data.get('area_hectares', 0),
                    'preferred_mandi': crop_data.get('preferred_mandi') or mandi,
                    'variety': crop_data.get('variety'),
                    'sowing_date': crop_data.get('sowing_date'),
                    'is_perennial': crop_data.get('is_perennial', False),
                })
                created_crops.append(crop.to_dict())

            farm_dict = farm.to_dict()
            farm_dict['crops'] = created_crops
            return farm_dict

        # ── Old flat format fallback ──
        primary_crop = data.get('primary_crop') or data.get('preferred_crop')
        land_size = data.get('land_size', 0)

        if not primary_crop:
            return None

        farm = FarmerService.create_farm(user_id, {
            'farm_name': 'My Farm',
            'total_land_hectares': land_size,
            'soil_type': data.get('soil_type'),
            'irrigation_type': data.get('irrigation_type'),
            'has_storage': data.get('storage_available', False),
        })

        # Create crop records for each crop in the list (or just primary)
        crop_names = data.get('crops', [primary_crop])
        if isinstance(crop_names, list) and crop_names:
            per_crop_area = land_size / len(crop_names)
        else:
            crop_names = [primary_crop]
            per_crop_area = land_size

        # Use per-crop areas if provided
        crop_areas = data.get('crop_areas', {})
        mandi = data.get('preferred_mandi') or data.get('mandi')

        created_crops = []
        for name in crop_names:
            area = crop_areas.get(name, per_crop_area)
            # Convert acres to hectares if crop_areas values are in acres
            if crop_areas:
                area = area * 0.4047  # acres to hectares
            crop = FarmerService.add_crop_to_farm(farm.id, {
                'crop_name': name,
                'area_hectares': area,
                'preferred_mandi': mandi,
            })
            created_crops.append(crop.to_dict())

        farm_dict = farm.to_dict()
        farm_dict['crops'] = created_crops
        return farm_dict
