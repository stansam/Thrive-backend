from datetime import datetime, timezone
import uuid
from app.extensions import db

class AuditLog(db.Model):
    __tablename__ = 'audit_logs'
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = db.Column(db.String(36), db.ForeignKey('users.id'), index=True)
    
    # Action details
    action = db.Column(db.String(100), nullable=False)
    entity_type = db.Column(db.String(50))  # booking, payment, user, etc.
    entity_id = db.Column(db.String(36))
    
    # Details
    description = db.Column(db.Text)
    changes = db.Column(db.JSON)  # Before/after values
    
    # Request info
    ip_address = db.Column(db.String(45))
    user_agent = db.Column(db.String(500))
    
    created_at = db.Column(db.DateTime, default=datetime.now(timezone.utc), nullable=False)

