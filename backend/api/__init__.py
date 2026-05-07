"""
API蓝图包
"""
from backend.api.auth import auth_bp
from backend.api.data import data_bp
from backend.api.alarm import alarm_bp

__all__ = ['auth_bp', 'data_bp', 'alarm_bp']
