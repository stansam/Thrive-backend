from datetime import datetime, timezone
import uuid
from app.extensions import db

class Settings(db.Model):
    __tablename__ = 'settings'
    
    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(100), unique=True, nullable=False, index=True)
    value = db.Column(db.Text)
    data_type = db.Column(db.String(20), default='string')  # string, int, float, bool, json
    description = db.Column(db.String(500))
    
    updated_at = db.Column(db.DateTime, default=datetime.now(timezone.utc), onupdate=datetime.now(timezone.utc))
    
    @staticmethod
    def get_value(key, default=None):
        setting = Settings.query.filter_by(key=key).first()
        if not setting:
            return default
        
        if setting.data_type == 'int':
            return int(setting.value)
        elif setting.data_type == 'float':
            return float(setting.value)
        elif setting.data_type == 'bool':
            return setting.value.lower() in ('true', '1', 'yes')
        elif setting.data_type == 'json':
            import json
            return json.loads(setting.value)
        return setting.value
    
    @staticmethod
    def set_value(key, value, data_type='string', description=None):
        import json
        setting = Settings.query.filter_by(key=key).first()
        
        if data_type == 'json':
            value = json.dumps(value)
        else:
            value = str(value)
        
        if setting:
            setting.value = value
            setting.data_type = data_type
            if description:
                setting.description = description
        else:
            setting = Settings(
                key=key,
                value=value,
                data_type=data_type,
                description=description
            )
            db.session.add(setting)
        
        db.session.commit()
        return setting