from flask_jwt_extended import jwt_required, get_jwt_identity, verify_jwt_in_request
from flask import request, current_app
from sqlalchemy import or_, and_, func, desc, asc
from datetime import datetime, date
from decimal import Decimal

from app.api.packages import packages_bp
from app.models import Package
from app.extensions import db
from app.utils.api_response import APIResponse
from app.utils.search_n_filters import SearchHelper
from app.utils.audit_logging import AuditLogger



# ============================================================================
# PACKAGE SEARCH & BROWSE ENDPOINTS
# ============================================================================

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
        
    Returns:
        JSON response with paginated package list
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


@packages_bp.route('/featured', methods=['GET'])
def get_featured_packages():
    """
    Get featured packages
    
    Query Parameters:
        limit: Maximum number of packages to return (default: 10)
        
    Returns:
        JSON response with featured packages
    """
    try:
        limit = min(request.args.get('limit', 10, type=int), 50)
        
        packages = Package.query.filter_by(
            is_active=True,
            is_featured=True
        ).order_by(
            desc(Package.booking_count),
            desc(Package.view_count),
            Package.created_at
        ).limit(limit).all()
        
        return APIResponse.success(
            data=[pkg.to_dict() for pkg in packages],
            message=f"Found {len(packages)} featured package(s)"
        )
        
    except Exception as e:
        current_app.logger.error(f"Featured packages error: {str(e)}")
        return APIResponse.error(
            message="An error occurred while fetching featured packages",
            status_code=500
        )


@packages_bp.route('/popular', methods=['GET'])
def get_popular_packages():
    """
    Get most popular packages based on bookings and views
    
    Query Parameters:
        limit: Maximum number of packages (default: 10)
        metric: Sort by 'bookings' or 'views' (default: bookings)
        
    Returns:
        JSON response with popular packages
    """
    try:
        limit = min(request.args.get('limit', 10, type=int), 50)
        metric = request.args.get('metric', 'bookings').lower()
        
        query = Package.query.filter_by(is_active=True)
        
        if metric == 'views':
            query = query.order_by(desc(Package.view_count))
        else:
            query = query.order_by(desc(Package.booking_count))
        
        packages = query.limit(limit).all()
        
        return APIResponse.success(
            data=[pkg.to_dict() for pkg in packages],
            message=f"Found {len(packages)} popular package(s)"
        )
        
    except Exception as e:
        current_app.logger.error(f"Popular packages error: {str(e)}")
        return APIResponse.error(
            message="An error occurred while fetching popular packages",
            status_code=500
        )


@packages_bp.route('/destinations', methods=['GET'])
def get_destinations():
    """
    Get list of unique destinations with package counts
    
    Returns:
        JSON response with destination list
    """
    try:
        # Group by country and city
        destinations = db.session.query(
            Package.destination_country,
            Package.destination_city,
            func.count(Package.id).label('package_count'),
            func.min(Package.starting_price).label('min_price'),
            func.max(Package.starting_price).label('max_price')
        ).filter(
            Package.is_active == True
        ).group_by(
            Package.destination_country,
            Package.destination_city
        ).order_by(
            Package.destination_country,
            Package.destination_city
        ).all()
        
        # Format response
        destination_list = []
        for dest in destinations:
            destination_list.append({
                'country': dest.destination_country,
                'city': dest.destination_city,
                'package_count': dest.package_count,
                'price_range': {
                    'min': float(dest.min_price),
                    'max': float(dest.max_price)
                }
            })
        
        return APIResponse.success(
            data=destination_list,
            message=f"Found {len(destination_list)} destination(s)"
        )
        
    except Exception as e:
        current_app.logger.error(f"Destinations error: {str(e)}")
        return APIResponse.error(
            message="An error occurred while fetching destinations",
            status_code=500
        )


@packages_bp.route('/<package_id>', methods=['GET'])
def get_package_detail(package_id):
    """
    Get detailed information about a specific package
    
    Path Parameters:
        package_id: Package UUID
        
    Returns:
        JSON response with package details
    """
    try:
        package = Package.query.get(package_id)
        
        if not package:
            return APIResponse.not_found("Package not found")
        
        if not package.is_active:
            return APIResponse.error(
                "This package is currently unavailable",
                status_code=410
            )
        
        # Increment view count
        package.view_count += 1
        db.session.commit()

        current_user = None
        try:
            verify_jwt_in_request(optional=True)
            current_user_id = get_jwt_identity() 
            current_user = User.query.get(current_user_id)
        except Exception:
            current_user = None
        
        if current_user:
            try:
                AuditLogger.log_action(
                    user_id=current_user.id,
                    action='VIEW_PACKAGE',
                    entity_type='Package',
                    entity_id=package_id,
                    description=f"Viewed package: {package.name}",
                    ip_address=request.remote_addr,
                    user_agent=request.headers.get('User-Agent')
                )
            except Exception as log_error:
                current_app.logger.warning(f"Audit log error: {str(log_error)}")
        
        return APIResponse.success(
            data=package.to_dict(),
            message="Package details retrieved successfully"
        )
        
    except Exception as e:
        current_app.logger.error(f"Package detail error: {str(e)}")
        return APIResponse.error(
            message="An error occurred while fetching package details",
            status_code=500
        )


@packages_bp.route('/slug/<slug>', methods=['GET'])
def get_package_by_slug(slug):
    """
    Get package by URL-friendly slug
    
    Path Parameters:
        slug: Package slug
        
    Returns:
        JSON response with package details
    """
    try:
        package = Package.query.filter_by(slug=slug).first()
        
        if not package:
            return APIResponse.not_found("Package not found")
        
        if not package.is_active:
            return APIResponse.error(
                "This package is currently unavailable",
                status_code=410
            )
        
        # Increment view count
        package.view_count += 1
        db.session.commit()
        
        current_user = None
        try:
            verify_jwt_in_request(optional=True)
            current_user_id = get_jwt_identity() 
            current_user = User.query.get(current_user_id)
        except Exception:
            current_user = None
        
        # Log view action if user is authenticated
        if current_user:
            try:
                AuditLogger.log_action(
                    user_id=current_user.id,
                    action='VIEW_PACKAGE',
                    entity_type='Package',
                    entity_id=package.id,
                    description=f"Viewed package: {package.name}",
                    ip_address=request.remote_addr,
                    user_agent=request.headers.get('User-Agent')
                )
            except Exception as log_error:
                current_app.logger.warning(f"Audit log error: {str(log_error)}")
        
        return APIResponse.success(
            data=package.to_dict(),
            message="Package details retrieved successfully"
        )
        
    except Exception as e:
        current_app.logger.error(f"Package slug error: {str(e)}")
        return APIResponse.error(
            message="An error occurred while fetching package details",
            status_code=500
        )


@packages_bp.route('/similar/<package_id>', methods=['GET'])
def get_similar_packages(package_id):
    """
    Get similar packages based on destination and price range
    
    Path Parameters:
        package_id: Package UUID
        
    Query Parameters:
        limit: Maximum number of similar packages (default: 5)
        
    Returns:
        JSON response with similar packages
    """
    try:
        package = Package.query.get(package_id)
        
        if not package:
            return APIResponse.not_found("Package not found")
        
        limit = min(request.args.get('limit', 5, type=int), 20)
        
        # Calculate price range (±30%)
        price_margin = float(package.starting_price) * 0.3
        min_price = float(package.starting_price) - price_margin
        max_price = float(package.starting_price) + price_margin
        
        # Find similar packages
        similar_packages = Package.query.filter(
            Package.id != package_id,
            Package.is_active == True,
            or_(
                # Same destination
                and_(
                    Package.destination_city == package.destination_city,
                    Package.destination_country == package.destination_country
                ),
                # Similar price range
                and_(
                    Package.starting_price >= min_price,
                    Package.starting_price <= max_price
                )
            )
        ).order_by(
            # Prioritize same destination
            desc(
                and_(
                    Package.destination_city == package.destination_city,
                    Package.destination_country == package.destination_country
                )
            ),
            desc(Package.is_featured),
            desc(Package.booking_count)
        ).limit(limit).all()
        
        return APIResponse.success(
            data=[pkg.to_dict() for pkg in similar_packages],
            message=f"Found {len(similar_packages)} similar package(s)"
        )
        
    except Exception as e:
        current_app.logger.error(f"Similar packages error: {str(e)}")
        return APIResponse.error(
            message="An error occurred while fetching similar packages",
            status_code=500
        )


@packages_bp.route('/price-range', methods=['GET'])
def get_price_range():
    """
    Get minimum and maximum package prices for filtering
    
    Query Parameters:
        destination_city: Filter by city (optional)
        destination_country: Filter by country (optional)
        
    Returns:
        JSON response with price range
    """
    try:
        query = Package.query.filter_by(is_active=True)
        
        # Apply destination filters if provided
        destination_city = request.args.get('destination_city', '').strip()
        destination_country = request.args.get('destination_country', '').strip()
        
        if destination_city:
            query = query.filter(Package.destination_city.ilike(f'%{destination_city}%'))
        
        if destination_country:
            query = query.filter(Package.destination_country.ilike(f'%{destination_country}%'))
        
        # Get price range
        price_stats = db.session.query(
            func.min(Package.starting_price).label('min_price'),
            func.max(Package.starting_price).label('max_price'),
            func.avg(Package.starting_price).label('avg_price'),
            func.count(Package.id).label('count')
        ).filter(query.whereclause).first()
        
        if price_stats.count == 0:
            return APIResponse.success(
                data={
                    'min_price': 0,
                    'max_price': 0,
                    'avg_price': 0,
                    'package_count': 0
                },
                message="No packages found"
            )
        
        return APIResponse.success(
            data={
                'min_price': float(price_stats.min_price) if price_stats.min_price else 0,
                'max_price': float(price_stats.max_price) if price_stats.max_price else 0,
                'avg_price': float(price_stats.avg_price) if price_stats.avg_price else 0,
                'package_count': price_stats.count
            },
            message="Price range retrieved successfully"
        )
        
    except Exception as e:
        current_app.logger.error(f"Price range error: {str(e)}")
        return APIResponse.error(
            message="An error occurred while fetching price range",
            status_code=500
        )


@packages_bp.route('/stats', methods=['GET'])
def get_package_statistics():
    """
    Get overall package statistics
    
    Returns:
        JSON response with package statistics
    """
    try:
        stats = db.session.query(
            func.count(Package.id).label('total_packages'),
            func.count(Package.id).filter(Package.is_active == True).label('active_packages'),
            func.count(Package.id).filter(Package.is_featured == True).label('featured_packages'),
            func.sum(Package.view_count).label('total_views'),
            func.sum(Package.booking_count).label('total_bookings'),
            func.avg(Package.starting_price).label('avg_price'),
            func.min(Package.starting_price).label('min_price'),
            func.max(Package.starting_price).label('max_price')
        ).first()
        
        # Get top destinations
        top_destinations = db.session.query(
            Package.destination_country,
            func.count(Package.id).label('count')
        ).filter(
            Package.is_active == True
        ).group_by(
            Package.destination_country
        ).order_by(
            desc(func.count(Package.id))
        ).limit(5).all()
        
        return APIResponse.success(
            data={
                'total_packages': stats.total_packages or 0,
                'active_packages': stats.active_packages or 0,
                'featured_packages': stats.featured_packages or 0,
                'total_views': stats.total_views or 0,
                'total_bookings': stats.total_bookings or 0,
                'price_stats': {
                    'average': float(stats.avg_price) if stats.avg_price else 0,
                    'minimum': float(stats.min_price) if stats.min_price else 0,
                    'maximum': float(stats.max_price) if stats.max_price else 0
                },
                'top_destinations': [
                    {
                        'country': dest.destination_country,
                        'package_count': dest.count
                    }
                    for dest in top_destinations
                ]
            },
            message="Statistics retrieved successfully"
        )
        
    except Exception as e:
        current_app.logger.error(f"Package statistics error: {str(e)}")
        return APIResponse.error(
            message="An error occurred while fetching statistics",
            status_code=500
        )


# ============================================================================
# OPTIONAL: USER FAVORITES/WISHLIST (if user system exists)
# ============================================================================

@packages_bp.route('/favorites', methods=['GET'])
@jwt_required()
def get_user_favorites():
    """
    Get user's favorite packages (requires favorites relationship in User model)
    
    Returns:
        JSON response with favorite packages
    """
    try:
        # This assumes a many-to-many relationship between User and Package
        # You'll need to implement this in your models
        current_user_id = get_jwt_identity()
        user = User.query.get(current_user_id)

        if hasattr(user, 'favorite_packages'):
            favorites = user.favorite_packages.filter_by(is_active=True).all()
            return APIResponse.success(
                data=[pkg.to_dict() for pkg in favorites],
                message=f"Found {len(favorites)} favorite package(s)"
            )
        else:
            return APIResponse.error(
                "Favorites feature not implemented",
                status_code=501
            )
            
    except Exception as e:
        current_app.logger.error(f"User favorites error: {str(e)}")
        return APIResponse.error(
            message="An error occurred while fetching favorites",
            status_code=500
        )