"""
Flask应用配置
"""
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INSTANCE_DIR = os.path.join(BASE_DIR, 'instance')


class Config:
    """基础配置"""
    SECRET_KEY = os.environ.get('SECRET_KEY', 'solar-platform-secret-key-2026')
    SQLALCHEMY_DATABASE_URI = 'sqlite:///' + os.path.join(INSTANCE_DIR, 'solar.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # 数据集路径
    DATA_PATH = os.path.join(BASE_DIR, '数据集', '数据集_6-18.csv')

    # 模型路径
    MODEL_DIR = os.path.join(BASE_DIR, 'ml_model')

    # JWT配置
    JWT_SECRET = 'solar-jwt-secret-2026'
    JWT_EXPIRATION_HOURS = 24

    # 故障报警阈值
    ALARM_THRESHOLD_ZERO_WHEN_SUNNY = 5.0  # 辐射>500时功率接近0视为异常(kW)
    ALARM_THRESHOLD_HIGH_DEVIATION = 0.5    # 预测偏差超过50%报警
    ALARM_RADIATION_THRESHOLD = 500         # 判定为晴天的辐射阈值(W/m²)

    # 分页
    PER_PAGE = 20
