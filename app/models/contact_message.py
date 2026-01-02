from datetime import datetime, timezone
import uuid
from app.extensions import db
from app.models.enums import UserRole

class ContactMessageStatus:
    """Contact message status constants"""
    NEW = "new"
    IN_PROGRESS = "in_progress"
    RESOLVED = "resolved"

class ContactMessage(db.Model):
    __tablename__ = 'contact_messages'
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    
    # Contact details
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), nullable=False)
    phone = db.Column(db.String(20))
    subject = db.Column(db.String(200), nullable=False)
    message = db.Column(db.Text, nullable=False)
    
    # Optional user link (if authenticated user submitted)
    user_id = db.Column(db.String(36), db.ForeignKey('users.id'), index=True)
    
    # Status tracking
    status = db.Column(db.String(20), default=ContactMessageStatus.NEW, nullable=False)
    priority = db.Column(db.String(20), default='normal')  # low, normal, high, urgent
    
    # Admin management
    assigned_to = db.Column(db.String(36), db.ForeignKey('users.id'))  # Admin user assigned
    admin_notes = db.Column(db.Text)
    replied_at = db.Column(db.DateTime)
    resolved_at = db.Column(db.DateTime)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.now(timezone.utc), nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.now(timezone.utc), onupdate=datetime.now(timezone.utc))
    
    # Relationships
    user = db.relationship('User', foreign_keys=[user_id], backref='contact_messages')
    assigned_admin = db.relationship('User', foreign_keys=[assigned_to])
    
    def mark_as_resolved(self):
        """Mark message as resolved"""
        self.status = ContactMessageStatus.RESOLVED
        self.resolved_at = datetime.now(timezone.utc)
    
    def assign_to_admin(self, admin_id):
        """Assign message to admin"""
        self.assigned_to = admin_id
        if self.status == ContactMessageStatus.NEW:
            self.status = ContactMessageStatus.IN_PROGRESS
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'email': self.email,
            'phone': self.phone,
            'subject': self.subject,
            'message': self.message,
            'status': self.status,
            'priority': self.priority,
            'admin_notes': self.admin_notes,
            'replied_at': self.replied_at.isoformat() if self.replied_at else None,
            'resolved_at': self.resolved_at.isoformat() if self.resolved_at else None,
            'created_at': self.created_at.isoformat(),
            'user_id': self.user_id,
            'assigned_to': self.assigned_to
        }
