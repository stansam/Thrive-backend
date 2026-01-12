
from flask import request, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity
from sqlalchemy import or_

from app.models import User, Package, Booking
from app.models.enums import BookingType
from app.utils.api_response import APIResponse

from . import client_bp

@client_bp.route('/packages/explore', methods=['GET'])
@jwt_required()
def explore_packages():
    """
    Get explore packages data
    """
    try:
        # Search filters
        search_query = request.args.get('search', '').strip()
        
        query = Package.query.filter_by(is_active=True)
        
        if search_query:
            query = query.filter(
                or_(
                    Package.name.ilike(f'%{search_query}%'),
                    Package.destination_city.ilike(f'%{search_query}%'),
                    Package.destination_country.ilike(f'%{search_query}%')
                )
            )
            
        packages = query.limit(20).all()
        
        # Find a featured package (e.g. curated one or just random/latest)
        featured = [packages[0].to_dict()] if packages else []

        return APIResponse.success(
            data={
                'featured': featured,
                'all_packages': [p.to_dict() for p in packages]
            },
            message="Explore packages retrieved"
        )
    except Exception as e:
        current_app.logger.error(f"Explore packages error: {str(e)}")
        return APIResponse.error('An error occurred while fetching packages')


@client_bp.route('/packages/my-packages', methods=['GET'])
@jwt_required()
def my_packages():
    """
    Get user's booked and saved packages
    """
    try:
        current_user_id = get_jwt_identity()
        
        # Booked packages
        booked_query = Booking.query.filter(
            Booking.user_id == current_user_id,
            Booking.booking_type == BookingType.PACKAGE
        ).order_by(Booking.created_at.desc()).all()
        
        booked_list = []
        for b in booked_query:
            b_data = b.to_dict()
            # Enrich with package specific details if needed (images etc)
            if b.package:
                b_data['image'] = b.package.featured_image
                b_data['package_title'] = b.package.name
                b_data['destination'] = f"{b.package.destination_city}, {b.package.destination_country}"
            booked_list.append(b_data)
            
        # Saved packages - Placeholder for now as "Saved" model might not exist yet
        # If Wishlist model exists, query it here.
        saved_list = []

        return APIResponse.success(
            data={
                'booked': booked_list,
                'saved': saved_list
            },
            message="My packages retrieved"
        )
    except Exception as e:
        current_app.logger.error(f"My packages error: {str(e)}")
        return APIResponse.error('An error occurred while fetching user packages')
