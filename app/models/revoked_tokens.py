from app.extensions import db
from datetime import datetime, timezone

class RevokedToken(db.Model):
    __tablename__ = 'revoked_tokens'
    id = db.Column(db.Integer, primary_key=True)
    jti = db.Column(db.String(120), unique=True, nullable=False)
    type = db.Column(db.String(10), nullable=False)  # 'access' or 'refresh'
    created_at = db.Column(db.DateTime, default=datetime.now(timezone.utc))

    @classmethod
    def is_revoked(cls, jti: str):
        return cls.query.filter_by(jti=jti).first() is not None