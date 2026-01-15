from flask import request, current_app
from sqlalchemy import desc, func

from app.api.packages import packages_bp
from app.models import Package
from app.extensions import db
from app.utils.api_response import APIResponse

# ==================== LISTING & STATS ENDPOINTS ====================

@packages_bp.route('/featured', methods=['GET'])
def get_featured_packages():
    """
    Get featured packages
    
    Query Parameters:
        limit: Maximum number of packages to return (default: 10)
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
    """Get list of unique destinations with package counts"""
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


@packages_bp.route('/price-range', methods=['GET'])
def get_price_range():
    """
    Get minimum and maximum package prices for filtering
    
    Query Parameters:
        destination_city: Filter by city (optional)
        destination_country: Filter by country (optional)
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
    """Get overall package statistics"""
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
