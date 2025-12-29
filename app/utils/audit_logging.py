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

class AuditLogger:
    """Log important actions for audit trail"""
    
    @staticmethod
    def log_action(
        user_id: str,
        action: str,
        entity_type: str = None,
        entity_id: str = None,
        description: str = None,
        changes: dict = None,
        ip_address: str = None,
        user_agent: str = None
    ):
        """Log an action to audit trail"""
        from app.models import AuditLog
        from app.extensions import db
        
        log = AuditLog(
            user_id=user_id,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            description=description,
            changes=changes,
            ip_address=ip_address,
            user_agent=user_agent
        )
        
        db.session.add(log)
        db.session.commit()
        return log