"""
JWT认证工具
"""
import jwt
import functools
from datetime import datetime, timedelta
from flask import request, jsonify, current_app


def generate_token(user_id, username, role):
    """生成JWT Token"""
    payload = {
        'user_id': user_id,
        'username': username,
        'role': role,
        'exp': datetime.utcnow() + timedelta(hours=current_app.config.get('JWT_EXPIRATION_HOURS', 24)),
        'iat': datetime.utcnow()
    }
    token = jwt.encode(payload, current_app.config['JWT_SECRET'], algorithm='HS256')
    return token


def decode_token(token):
    """解码JWT Token"""
    try:
        payload = jwt.decode(token, current_app.config['JWT_SECRET'], algorithms=['HS256'])
        return payload
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None


def login_required(f):
    """登录验证装饰器"""
    @functools.wraps(f)
    def decorated_function(*args, **kwargs):
        auth_header = request.headers.get('Authorization', '')
        if not auth_header.startswith('Bearer '):
            return jsonify({'code': 401, 'message': '未登录或Token已过期'}), 401

        token = auth_header[7:]
        payload = decode_token(token)
        if payload is None:
            return jsonify({'code': 401, 'message': 'Token无效或已过期'}), 401

        request.current_user = payload
        return f(*args, **kwargs)
    return decorated_function


def admin_required(f):
    """管理员权限验证装饰器"""
    @functools.wraps(f)
    @login_required
    def decorated_function(*args, **kwargs):
        if request.current_user.get('role') != 'admin':
            return jsonify({'code': 403, 'message': '权限不足'}), 403
        return f(*args, **kwargs)
    return decorated_function
