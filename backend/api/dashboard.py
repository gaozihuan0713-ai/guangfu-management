"""仪表盘API"""
import os
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from flask import Blueprint, request, jsonify
from backend import db
from backend.models.alarm import Alarm
from backend.models.prediction_log import PredictionLog
from backend.utils.auth import login_required

dashboard_bp = Blueprint('dashboard', __name__)


def get_dataset():
    """加载数据集"""
    data_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), '..', '数据集')
    csv_path = os.path.join(data_dir, '数据集_6-18.csv')
    if not os.path.exists(csv_path):
        return None
    df = pd.read_csv(csv_path)
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    return df


@dashboard_bp.route('/overview', methods=['GET'])
@login_required
def overview():
    """仪表盘概览数据"""
    df = get_dataset()
    if df is None:
        return jsonify({'code': 500, 'msg': '数据集未找到'}), 500

    # 今日数据（取最后一天模拟）
    last_date = df['timestamp'].iloc[-1].date()
    today_data = df[df['timestamp'].dt.date == last_date]

    # 当前功率
    current_power = round(float(df.iloc[-1]['Active_Power']), 4)

    # 今日发电量
    today_energy = round(float(today_data['Active_Power'].sum()) * 0.25, 2)

    # 总发电量
    total_energy = round(float(df['Active_Power'].sum()) * 0.25, 2)

    # 峰值功率
    peak_power = round(float(today_data['Active_Power'].max()), 4)

    # 平均效率（简化计算）
    avg_radiation = float(today_data['Global_Horizontal_Radiation'].mean())
    efficiency = round(float(today_data['Active_Power'].mean() / (avg_radiation + 1e-6)) * 100, 2) if avg_radiation > 0 else 0

    # 告警数
    alarm_count = Alarm.query.filter(Alarm.status == '未处理').count()

    # 最近24小时趋势
    recent = df.tail(96)
    trend_times = recent['timestamp'].dt.strftime('%H:%M').tolist()
    trend_power = recent['Active_Power'].round(4).tolist()

    # 7日发电量趋势
    last_7_days = df[df['timestamp'] >= df['timestamp'].iloc[-1] - timedelta(days=7)]
    daily_energy = last_7_days.set_index('timestamp').resample('1D')['Active_Power'].sum() * 0.25
    week_dates = daily_energy.index.strftime('%m-%d').tolist()
    week_energy = daily_energy.round(2).tolist()

    return jsonify({
        'code': 200,
        'data': {
            'current_power': current_power,
            'today_energy': today_energy,
            'total_energy': total_energy,
            'peak_power': peak_power,
            'efficiency': efficiency,
            'alarm_count': alarm_count,
            'trend': {'times': trend_times, 'power': trend_power},
            'weekly': {'dates': week_dates, 'energy': week_energy}
        }
    })


@dashboard_bp.route('/weather', methods=['GET'])
@login_required
def weather():
    """获取气象数据"""
    df = get_dataset()
    if df is None:
        return jsonify({'code': 500, 'msg': '数据集未找到'}), 500

    recent = df.tail(96)
    return jsonify({
        'code': 200,
        'data': {
            'times': recent['timestamp'].dt.strftime('%H:%M').tolist(),
            'temperature': recent['Weather_Temperature_Celsius'].round(1).tolist(),
            'humidity': recent['Weather_Relative_Humidity'].round(1).tolist(),
            'radiation': recent['Global_Horizontal_Radiation'].round(2).tolist(),
            'wind_speed': recent['Wind_Speed'].round(2).tolist()
        }
    })
