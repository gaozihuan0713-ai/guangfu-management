"""预测日志模型"""
from backend import db
from datetime import datetime


class PredictionLog(db.Model):
    __tablename__ = 'prediction_logs'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    predict_time = db.Column(db.DateTime, nullable=False)  # 预测的目标时间
    predicted_power = db.Column(db.Float, nullable=False)  # 预测功率
    actual_power = db.Column(db.Float)  # 实际功率（事后填充）
    model_version = db.Column(db.String(50), default='DLinear-v1')
    created_at = db.Column(db.DateTime, default=datetime.now)

    def to_dict(self):
        return {
            'id': self.id,
            'predict_time': self.predict_time.strftime('%Y-%m-%d %H:%M:%S') if self.predict_time else None,
            'predicted_power': round(self.predicted_power, 4) if self.predicted_power else None,
            'actual_power': round(self.actual_power, 4) if self.actual_power else None,
            'model_version': self.model_version,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S') if self.created_at else None
        }
