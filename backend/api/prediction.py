"""预测API"""
import os
import json
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from flask import Blueprint, request, jsonify, current_app
from backend import db
from backend.models.prediction_log import PredictionLog
from backend.utils.auth import login_required
from backend.utils.helpers import success_response, error_response

prediction_bp = Blueprint('prediction', __name__)

# 模型加载缓存
_model_cache = {}


def get_model():
    """加载DLinear模型"""
    if 'model' in _model_cache:
        return _model_cache['model'], _model_cache['scaler']

    import torch
    model_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'ml_model')

    model_path = os.path.join(model_dir, 'dlinear_model.pth')
    scaler_path = os.path.join(model_dir, 'scaler.json')

    if not os.path.exists(model_path):
        return None, None

    # 加载scaler参数
    with open(scaler_path, 'r') as f:
        scaler_params = json.load(f)

    # 加载模型
    from backend.ml_inference import DLinearModel
    input_size = len(scaler_params['feature_columns'])
    model = DLinearModel(input_size=input_size, seq_len=96, pred_len=24)
    model.load_state_dict(torch.load(model_path, map_location='cpu', weights_only=True))
    model.eval()

    _model_cache['model'] = model
    _model_cache['scaler'] = scaler_params

    return model, scaler_params


def get_dataset():
    """加载数据集"""
    if 'dataset' in _model_cache:
        return _model_cache['dataset']

    data_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), '..', '数据集')
    csv_path = os.path.join(data_dir, '数据集_6-18.csv')

    if not os.path.exists(csv_path):
        return None

    df = pd.read_csv(csv_path)
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    df = df.sort_values('timestamp').reset_index(drop=True)
    _model_cache['dataset'] = df
    return df


@prediction_bp.route('/predict', methods=['POST'])
@login_required
def predict():
    """执行发电功率预测"""
    data = request.get_json() or {}
    predict_hours = data.get('hours', 6)  # 默认预测6小时

    model, scaler_params = get_model()
    if model is None:
        return jsonify({'code': 500, 'msg': '模型未就绪，请先训练模型'}), 500

    df = get_dataset()
    if df is None:
        return jsonify({'code': 500, 'msg': '数据集未找到'}), 500

    import torch

    # 获取最新数据用于预测输入
    feature_cols = scaler_params['feature_columns']
    seq_len = 96  # 输入序列长度（24小时 * 4个15分钟）

    # 使用数据集末尾作为输入
    recent_data = df.tail(seq_len)[feature_cols].values

    # 标准化
    mean_vals = np.array(scaler_params['mean'])
    std_vals = np.array(scaler_params['std'])
    normalized = (recent_data - mean_vals) / (std_vals + 1e-8)

    # 构造输入tensor
    input_tensor = torch.FloatTensor(normalized).unsqueeze(0)  # (1, seq_len, features)

    # 预测
    with torch.no_grad():
        output = model(input_tensor)  # (1, pred_len, 1)

    pred_values = output.squeeze().numpy()

    # 反标准化（Active_Power是第0列）
    power_mean = scaler_params['mean'][0]
    power_std = scaler_params['std'][0]
    pred_power = pred_values * power_std + power_mean
    pred_power = np.maximum(pred_power, 0)  # 功率不能为负

    # 计算pred_len对应的实际点数
    pred_len = len(pred_power)
    actual_points = min(pred_len, predict_hours * 4)

    # 生成预测时间戳
    last_time = df['timestamp'].iloc[-1]
    time_interval = timedelta(minutes=15)
    timestamps = [last_time + time_interval * (i + 1) for i in range(actual_points)]

    # 保存预测日志
    for i in range(actual_points):
        log = PredictionLog(
            predict_time=timestamps[i],
            predicted_power=float(pred_power[i]),
            model_version='DLinear-v1'
        )
        db.session.add(log)
    db.session.commit()

    result = {
        'timestamps': [t.strftime('%Y-%m-%d %H:%M') for t in timestamps],
        'predicted_power': [round(float(p), 4) for p in pred_power[:actual_points]],
        'predict_hours': predict_hours,
        'model': 'DLinear'
    }

    return jsonify({'code': 200, 'msg': '预测完成', 'data': result})


@prediction_bp.route('/history', methods=['GET'])
@login_required
def prediction_history():
    """获取预测历史"""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)

    pagination = PredictionLog.query.order_by(
        PredictionLog.predict_time.desc()
    ).paginate(page=page, per_page=per_page, error_out=False)

    return jsonify({
        'code': 200,
        'data': {
            'items': [log.to_dict() for log in pagination.items],
            'total': pagination.total,
            'page': page,
            'per_page': per_page,
            'pages': pagination.pages
        }
    })


@prediction_bp.route('/compare', methods=['GET'])
@login_required
def compare():
    """获取实时功率与预测功率对比数据"""
    date_str = request.args.get('date', '')

    df = get_dataset()
    if df is None:
        return jsonify({'code': 500, 'msg': '数据集未找到'}), 500

    if date_str:
        target_date = pd.to_datetime(date_str)
    else:
        target_date = df['timestamp'].iloc[-1].normalize()

    # 获取该日期的实际数据
    day_data = df[df['timestamp'].dt.date == target_date.date()]

    if day_data.empty:
        # 如果指定日期没数据，取最后一天
        last_date = df['timestamp'].iloc[-1].date()
        day_data = df[df['timestamp'].dt.date == last_date]

    actual_times = day_data['timestamp'].dt.strftime('%H:%M').tolist()
    actual_power = day_data['Active_Power'].round(4).tolist()

    # 获取该日期的预测数据
    date_start = target_date.replace(hour=0, minute=0, second=0)
    date_end = date_start + timedelta(days=1)
    pred_logs = PredictionLog.query.filter(
        PredictionLog.predict_time >= date_start,
        PredictionLog.predict_time < date_end
    ).order_by(PredictionLog.predict_time).all()

    pred_times = [log.predict_time.strftime('%H:%M') for log in pred_logs]
    pred_power = [log.predicted_power for log in pred_logs]

    # 计算误差指标
    matched_actual = []
    matched_pred = []
    for i, pt in enumerate(pred_times):
        if pt in actual_times:
            idx = actual_times.index(pt)
            matched_actual.append(actual_power[idx])
            matched_pred.append(pred_power[i])

    metrics = {}
    if matched_actual and matched_pred:
        mae = np.mean(np.abs(np.array(matched_actual) - np.array(matched_pred)))
        rmse = np.sqrt(np.mean((np.array(matched_actual) - np.array(matched_pred)) ** 2))
        metrics = {'mae': round(float(mae), 4), 'rmse': round(float(rmse), 4)}

    return jsonify({
        'code': 200,
        'data': {
            'date': target_date.strftime('%Y-%m-%d'),
            'actual': {'times': actual_times, 'power': actual_power},
            'predicted': {'times': pred_times, 'power': pred_power},
            'metrics': metrics
        }
    })


@prediction_bp.route('/realtime', methods=['GET'])
@login_required
def realtime():
    """获取最新实时数据"""
    df = get_dataset()
    if df is None:
        return jsonify({'code': 500, 'msg': '数据集未找到'}), 500

    # 返回最近24小时的数据
    recent = df.tail(96)  # 24h * 4
    times = recent['timestamp'].dt.strftime('%Y-%m-%d %H:%M').tolist()
    power = recent['Active_Power'].round(4).tolist()

    # 实时统计
    latest = df.iloc[-1]
    stats = {
        'current_power': round(float(latest['Active_Power']), 4),
        'temperature': round(float(latest['Weather_Temperature_Celsius']), 1),
        'humidity': round(float(latest['Weather_Relative_Humidity']), 1),
        'radiation': round(float(latest['Global_Horizontal_Radiation']), 2),
        'wind_speed': round(float(latest['Wind_Speed']), 2),
        'timestamp': latest['timestamp'].strftime('%Y-%m-%d %H:%M')
    }

    return jsonify({
        'code': 200,
        'data': {
            'times': times,
            'power': power,
            'stats': stats
        }
    })
