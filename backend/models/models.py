"""
数据库模型
"""
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()


class User(db.Model):
    """用户模型"""
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(256), nullable=False)
    real_name = db.Column(db.String(80), default='')
    role = db.Column(db.String(20), default='operator')  # admin / operator / viewer
    status = db.Column(db.Integer, default=1)  # 1=启用 0=禁用
    created_at = db.Column(db.DateTime, default=datetime.now)
    last_login = db.Column(db.DateTime)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def to_dict(self):
        return {
            'id': self.id,
            'username': self.username,
            'real_name': self.real_name,
            'role': self.role,
            'status': self.status,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S') if self.created_at else None,
            'last_login': self.last_login.strftime('%Y-%m-%d %H:%M:%S') if self.last_login else None
        }


class AlarmRecord(db.Model):
    """故障报警记录"""
    __tablename__ = 'alarm_records'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    alarm_type = db.Column(db.String(50), nullable=False)  # zero_output / high_deviation / low_efficiency
    level = db.Column(db.String(20), default='warning')  # critical / warning / info
    message = db.Column(db.String(500), nullable=False)
    timestamp = db.Column(db.DateTime, nullable=False, index=True)
    active_power = db.Column(db.Float, default=0)
    predicted_power = db.Column(db.Float, default=0)
    radiation = db.Column(db.Float, default=0)
    temperature = db.Column(db.Float, default=0)
    status = db.Column(db.String(20), default='unacked')  # unacked / acked / resolved
    acked_by = db.Column(db.String(80), default='')
    acked_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.now)

    def to_dict(self):
        return {
            'id': self.id,
            'alarm_type': self.alarm_type,
            'level': self.level,
            'message': self.message,
            'timestamp': self.timestamp.strftime('%Y-%m-%d %H:%M:%S') if self.timestamp else None,
            'active_power': round(self.active_power, 2) if self.active_power else 0,
            'predicted_power': round(self.predicted_power, 2) if self.predicted_power else 0,
            'radiation': round(self.radiation, 2) if self.radiation else 0,
            'temperature': round(self.temperature, 2) if self.temperature else 0,
            'status': self.status,
            'acked_by': self.acked_by,
            'acked_at': self.acked_at.strftime('%Y-%m-%d %H:%M:%S') if self.acked_at else None,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S') if self.created_at else None
        }


class OperationLog(db.Model):
    """操作日志"""
    __tablename__ = 'operation_logs'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    username = db.Column(db.String(80), nullable=False)
    action = db.Column(db.String(100), nullable=False)
    detail = db.Column(db.String(500), default='')
    ip_address = db.Column(db.String(50), default='')
    created_at = db.Column(db.DateTime, default=datetime.now)

    def to_dict(self):
        return {
            'id': self.id,
            'username': self.username,
            'action': self.action,
            'detail': self.detail,
            'ip_address': self.ip_address,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S') if self.created_at else None
        }
