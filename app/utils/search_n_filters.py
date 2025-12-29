from flask import jsonify, current_app
from functools import wraps
from flask_login import current_user
from datetime import datetime, timedelta


class SearchHelper:
    """Search and filtering helpers"""
    
    @staticmethod
    def paginate_query(query, page: int = 1, per_page: int = 20):
        """Paginate SQLAlchemy query"""
        pagination = query.paginate(
            page=page,
            per_page=per_page,
            error_out=False
        )
        
        return {
            'items': [item.to_dict() for item in pagination.items],
            'total': pagination.total,
            'pages': pagination.pages,
            'current_page': page,
            'per_page': per_page,
            'has_next': pagination.has_next,
            'has_prev': pagination.has_prev
        }
    
    @staticmethod
    def filter_by_date_range(query, date_field, start_date, end_date):
        """Filter query by date range"""
        if start_date:
            query = query.filter(date_field >= start_date)
        if end_date:
            query = query.filter(date_field <= end_date)
        return query