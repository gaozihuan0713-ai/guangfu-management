"""告警模型"""
from backend import db
from datetime import datetime


class Alarm(db.Model):
    __tablename__ = 'alarms'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    alarm_type = db.Column(db.String(50), nullable=False)  # 设备故障/功率异常/通信中断/效率偏低
    level = db.Column(db.String(20), nullable=False)  # 严重/警告/提示
    message = db.Column(db.String(500), nullable=False)
    device = db.Column(db.String(100), default='光伏阵列-1')
    status = db.Column(db.String(20), default='未处理')  # 未处理/已处理/已忽略
    created_at = db.Column(db.DateTime, default=datetime.now)
    resolved_at = db.Column(db.DateTime)
    resolved_by = db.Column(db.String(80))

    def to_dict(self):
        return {
            'id': self.id,
            'alarm_type': self.alarm_type,
            'level': self.level,
            'message': self.message,
            'device': self.device,
            'status': self.status,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S') if self.created_at else None,
            'resolved_at': self.resolved_at.strftime('%Y-%m-%d %H:%M:%S') if self.resolved_at else None,
            'resolved_by': self.resolved_by
        }
