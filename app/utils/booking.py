from flask import jsonify, current_app
from functools import wraps
from flask_login import current_user
from datetime import datetime, timedelta
from decimal import Decimal
import random
import string
import re
from typing import Dict, List, Optional, Tuple
import requests

class BookingManager:
    """Handle booking-related operations"""
    
    @staticmethod
    def generate_reference_code(prefix: str = "TGT") -> str:
        """Generate unique reference code"""
        letters = ''.join(random.choices(string.ascii_uppercase, k=3))
        numbers = ''.join(random.choices(string.digits, k=3))
        return f"{prefix}-{letters}{numbers}"
    
    @staticmethod
    def is_domestic_flight(origin: str, destination: str) -> bool:
        """Check if flight is domestic (simplified version)"""
        # This is simplified - in production, use airport code database
        us_airports = ['JFK', 'LAX', 'ORD', 'DFW', 'DEN', 'ATL', 'SFO', 'SEA', 'LAS', 'MCO']
        
        origin = origin.upper()[:3]
        destination = destination.upper()[:3]
        
        return origin in us_airports and destination in us_airports
    
    @staticmethod
    def calculate_trip_duration(departure: datetime, return_date: datetime = None) -> int:
        """Calculate trip duration in days"""
        if not return_date:
            return 1
        return (return_date - departure).days
    
    @staticmethod
    def validate_booking_dates(departure: datetime, return_date: datetime = None) -> Tuple[bool, str]:
        """Validate booking dates"""
        now = datetime.utcnow()
        
        # Check if departure is in the past
        if departure < now:
            return False, "Departure date cannot be in the past"
        
        # Check if return date is before departure
        if return_date and return_date < departure:
            return False, "Return date cannot be before departure date"
        
        # Check if booking too far in advance (1 year)
        max_advance = now + timedelta(days=365)
        if departure > max_advance:
            return False, "Cannot book more than 1 year in advance"
        
        return True, "Valid dates"
    
    @staticmethod
    def is_urgent_booking(departure: datetime, buffer_days: int = 7) -> bool:
        """Check if booking is urgent (within buffer days)"""
        now = datetime.utcnow()
        return (departure - now).days < buffer_days