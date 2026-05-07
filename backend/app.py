"""
Flask应用工厂 - 纯API模式
"""
import os
from flask import Flask
from flask_cors import CORS
from backend.config import Config
from backend.models import db, User
from backend.api import auth_bp, data_bp, alarm_bp


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    CORS(app, resources={
        r"/api/*": {
            "origins": ["http://localhost:5173", "http://localhost:5174", "http://localhost:5175", "http://localhost:5176",
                       "http://127.0.0.1:5173", "http://127.0.0.1:5174", "http://127.0.0.1:5175", "http://127.0.0.1:5176",
                       "http://localhost:51731", "http://127.0.0.1:51731",
                       "http://localhost:8080", "http://127.0.0.1:8080",
                       "http://localhost:8081", "http://127.0.0.1:8081",
                       "http://10.0.2.2:5000"],
            "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
            "allow_headers": ["Content-Type", "Authorization"],
            "supports_credentials": True
        }
    })

    db.init_app(app)

    app.register_blueprint(auth_bp)
    app.register_blueprint(data_bp)
    app.register_blueprint(alarm_bp)

    with app.app_context():
        init_db(app)

    return app


def init_db(app):
    instance_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'instance')
    os.makedirs(instance_dir, exist_ok=True)
    db.create_all()

    admin = User.query.filter_by(username='admin').first()
    if admin is None:
        admin = User(username='admin', real_name='系统管理员', role='admin', status=1)
        admin.set_password('admin123')
        db.session.add(admin)

        operator = User(username='operator', real_name='操作员', role='operator', status=1)
        operator.set_password('operator123')
        db.session.add(operator)

        viewer = User(username='viewer', real_name='观察者', role='viewer', status=1)
        viewer.set_password('viewer123')
        db.session.add(viewer)

        db.session.commit()
        print('[INIT] 默认用户创建成功:')
        print('  admin / admin123 (管理员)')
        print('  operator / operator123 (操作员)')
        print('  viewer / viewer123 (观察者)')
