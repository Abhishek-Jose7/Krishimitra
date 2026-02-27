from database.db import db
from database.models import Farmer

class FarmerService:
    @staticmethod
    def create_farmer(data):
        from flask_jwt_extended import create_access_token
        
        try:
            # Check if phone already exists
            existing_farmer = Farmer.query.filter_by(phone=data['phone']).first()
            if existing_farmer:
                # If exists, return token for existing user
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
                phone=data['phone'],
                name=data.get('name'),
                language=data.get('language', 'en'),
                state=data.get('state'),
                district=data.get('district'),
                latitude=data.get('latitude'),
                longitude=data.get('longitude'),
                primary_crop=data.get('primary_crop') or data.get('preferred_crop'),
                preferred_mandi=data.get('preferred_mandi'),
                land_size=data.get('land_size'),
                storage_available=data.get('storage_available', False),
                soil_type=data.get('soil_type'),
                irrigation_type=data.get('irrigation_type'),
            )
            db.session.add(new_farmer)
            db.session.commit()
            
            # Generate Token
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
            'primary_crop', 'preferred_mandi', 'land_size', 'storage_available',
            'soil_type', 'irrigation_type', 'onboarding_complete'
        ]

        for field in updatable_fields:
            if field in data:
                setattr(farmer, field, data[field])

        # Accept preferred_crop as alias
        if 'preferred_crop' in data:
            farmer.primary_crop = data['preferred_crop']

        db.session.commit()
        return farmer.to_dict()
