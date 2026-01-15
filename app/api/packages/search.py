from flask import request, current_app
from sqlalchemy import or_, and_, desc, asc
from datetime import datetime

from app.api.packages import packages_bp
from app.models import Package
from app.utils.api_response import APIResponse
from app.utils.search_n_filters import SearchHelper

# ==================== SEARCH ENDPOINTS ====================

@packages_bp.route('/search', methods=['GET'])
def search_packages():
    """
    Advanced package search with multiple filters
    
    Query Parameters:
        q: Search query (searches name, description, destination)
        destination_city: Filter by city
        destination_country: Filter by country
        min_price: Minimum price
        max_price: Maximum price
        min_days: Minimum duration in days
        max_days: Maximum duration in days
        hotel_rating: Minimum hotel star rating
        is_featured: Filter featured packages (true/false)
        is_active: Filter active packages (default: true)
        available_date: Check availability for specific date (YYYY-MM-DD)
        sort_by: Sort field (price, duration, popularity, name, created_at)
        sort_order: Sort order (asc/desc, default: asc)
        page: Page number (default: 1)
        per_page: Items per page (default: 20, max: 100)
    """
    try:
        # Get query parameters
        search_query = request.args.get('q', '').strip()
        destination_city = request.args.get('destination_city', '').strip()
        destination_country = request.args.get('destination_country', '').strip()
        
        # Price filters
        min_price = request.args.get('min_price', type=float)
        max_price = request.args.get('max_price', type=float)
        
        # Duration filters
        min_days = request.args.get('min_days', type=int)
        max_days = request.args.get('max_days', type=int)
        
        # Rating filter
        hotel_rating = request.args.get('hotel_rating', type=int)
        
        # Boolean filters
        is_featured = request.args.get('is_featured', '').lower()
        is_active = request.args.get('is_active', 'true').lower()
        
        # Date availability
        available_date_str = request.args.get('available_date')
        
        # Sorting
        sort_by = request.args.get('sort_by', 'created_at')
        sort_order = request.args.get('sort_order', 'desc').lower()
        
        # Pagination
        page = request.args.get('page', 1, type=int)
        per_page = min(request.args.get('per_page', 20, type=int), 100)
        
        # Build base query
        query = Package.query
        
        # Filter by active status (default: only active)
        if is_active == 'true':
            query = query.filter(Package.is_active == True)
        elif is_active == 'false':
            query = query.filter(Package.is_active == False)
        
        # Text search across multiple fields
        if search_query:
            search_filter = or_(
                Package.name.ilike(f'%{search_query}%'),
                Package.short_description.ilike(f'%{search_query}%'),
                Package.full_description.ilike(f'%{search_query}%'),
                Package.destination_city.ilike(f'%{search_query}%'),
                Package.destination_country.ilike(f'%{search_query}%'),
                Package.marketing_tagline.ilike(f'%{search_query}%')
            )
            query = query.filter(search_filter)
        
        # Destination filters
        if destination_city:
            query = query.filter(Package.destination_city.ilike(f'%{destination_city}%'))
        
        if destination_country:
            query = query.filter(Package.destination_country.ilike(f'%{destination_country}%'))
        
        # Price filters
        if min_price is not None:
            query = query.filter(Package.starting_price >= min_price)
        
        if max_price is not None:
            query = query.filter(Package.starting_price <= max_price)
        
        # Duration filters
        if min_days is not None:
            query = query.filter(Package.duration_days >= min_days)
        
        if max_days is not None:
            query = query.filter(Package.duration_days <= max_days)
        
        # Hotel rating filter
        if hotel_rating is not None:
            query = query.filter(Package.hotel_rating >= hotel_rating)
        
        # Featured filter
        if is_featured == 'true':
            query = query.filter(Package.is_featured == True)
        elif is_featured == 'false':
            query = query.filter(Package.is_featured == False)
        
        # Availability date filter
        if available_date_str:
            try:
                check_date = datetime.strptime(available_date_str, '%Y-%m-%d').date()
                query = query.filter(
                    and_(
                        or_(
                            Package.available_from.is_(None),
                            Package.available_from <= check_date
                        ),
                        or_(
                            Package.available_until.is_(None),
                            Package.available_until >= check_date
                        )
                    )
                )
            except ValueError:
                return APIResponse.validation_error(
                    {'available_date': 'Invalid date format. Use YYYY-MM-DD'}
                )
        
        # Sorting
        sort_field_map = {
            'price': Package.starting_price,
            'duration': Package.duration_days,
            'popularity': Package.booking_count,
            'views': Package.view_count,
            'name': Package.name,
            'created_at': Package.created_at,
            'rating': Package.hotel_rating
        }
        
        sort_field = sort_field_map.get(sort_by, Package.created_at)
        
        if sort_order == 'desc':
            query = query.order_by(desc(sort_field))
        else:
            query = query.order_by(asc(sort_field))
        
        # Secondary sort by featured status and name
        query = query.order_by(desc(Package.is_featured), Package.name)
        
        # Paginate results
        paginated_data = SearchHelper.paginate_query(query, page, per_page)
        
        # Add search metadata
        paginated_data['filters_applied'] = {
            'search_query': search_query if search_query else None,
            'destination_city': destination_city if destination_city else None,
            'destination_country': destination_country if destination_country else None,
            'min_price': min_price,
            'max_price': max_price,
            'min_days': min_days,
            'max_days': max_days,
            'hotel_rating': hotel_rating,
            'is_featured': is_featured if is_featured else None,
            'available_date': available_date_str if available_date_str else None,
            'sort_by': sort_by,
            'sort_order': sort_order
        }
        
        return APIResponse.success(
            data=paginated_data,
            message=f"Found {paginated_data['total']} package(s)"
        )
        
    except Exception as e:
        current_app.logger.error(f"Package search error: {str(e)}")
        return APIResponse.error(
            message="An error occurred while searching packages",
            status_code=500
        )
