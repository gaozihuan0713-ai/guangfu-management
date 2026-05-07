"""
数据服务工具 - 数据加载、预测、报警检测
"""
import os
import json
import math
import numpy as np
import pandas as pd
import torch
from datetime import datetime, timedelta

_model = None
_scaler_params = None
_device = None

FEATURE_COLUMNS = [
    'Active_Power', 'Wind_Speed', 'Weather_Temperature_Celsius',
    'Weather_Relative_Humidity', 'Global_Horizontal_Radiation',
    'Diffuse_Horizontal_Radiation', 'Wind_Direction', 'Weather_Daily_Rainfall'
]


def get_model():
    global _model, _scaler_params, _device
    if _model is not None:
        return _model, _scaler_params, _device

    from backend.config import Config
    from ml_model.train import DLinear

    model_dir = Config.MODEL_DIR

    scaler_path = os.path.join(model_dir, 'scaler.json')
    with open(scaler_path, 'r') as f:
        _scaler_params = json.load(f)

    feature_columns = _scaler_params['feature_columns']
    seq_len = _scaler_params.get('seq_len', 96)
    pred_len = _scaler_params.get('pred_len', 24)

    _device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    _model = DLinear(
        input_size=len(feature_columns),
        seq_len=seq_len,
        pred_len=pred_len,
        kernel_size=25
    )

    model_path = os.path.join(model_dir, 'dlinear_model.pth')
    state_dict = torch.load(model_path, map_location=_device, weights_only=True)
    _model.load_state_dict(state_dict)
    _model.to(_device)
    _model.eval()

    return _model, _scaler_params, _device


def load_dataset():
    from backend.config import Config
    df = pd.read_csv(Config.DATA_PATH)
    df['timestamp'] = pd.to_datetime(df['timestamp'])

    for col in FEATURE_COLUMNS:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')

    df = df.dropna(subset=FEATURE_COLUMNS)
    df = df.drop_duplicates(subset=['timestamp'], keep='first')
    df = df.sort_values('timestamp').reset_index(drop=True)
    return df


def _safe_round(val, digits=2):
    if val is None or (isinstance(val, float) and math.isnan(val)):
        return 0
    return round(float(val), digits)


def predict_future(hours=6):
    try:
        model, scaler_params, device = get_model()
    except Exception as e:
        return _fallback_predict(hours)

    df = load_dataset()
    if len(df) < 96:
        return _fallback_predict(hours)

    feature_columns = scaler_params['feature_columns']
    mean_vals = np.array(scaler_params['mean'])
    std_vals = np.array(scaler_params['std'])
    seq_len = scaler_params.get('seq_len', 96)
    model_pred_len = scaler_params.get('pred_len', 24)

    latest_data = df[feature_columns].values[-seq_len:].astype(np.float32)
    normalized = (latest_data - mean_vals) / (std_vals + 1e-8)
    normalized = np.nan_to_num(normalized, nan=0.0)

    x = torch.FloatTensor(normalized).unsqueeze(0).to(device)

    with torch.no_grad():
        output = model(x)

    pred = output.cpu().numpy()[0, :, 0]
    pred = np.nan_to_num(pred, nan=0.0)

    power_mean = mean_vals[0]
    power_std = std_vals[0]
    pred_real = pred * power_std + power_mean
    pred_real = np.maximum(pred_real, 0)

    last_ts = df['timestamp'].iloc[-1]
    interval = timedelta(minutes=15)
    requested_count = hours * 4

    results = []
    model_count = min(len(pred_real), requested_count)

    for i in range(model_count):
        ts = last_ts + interval * (i + 1)
        results.append({
            'timestamp': ts.strftime('%Y-%m-%d %H:%M:%S'),
            'predicted_power': _safe_round(pred_real[i])
        })

    if requested_count > model_count:
        last_pred = pred_real[-1] if len(pred_real) > 0 else float(df['Active_Power'].iloc[-1])
        for i in range(model_count, requested_count):
            ts = last_ts + interval * (i + 1)
            decay = 0.95 ** (i - model_count + 1)
            extended_power = last_pred * decay
            extended_power = max(0, extended_power + np.random.normal(0, 0.1))
            results.append({
                'timestamp': ts.strftime('%Y-%m-%d %H:%M:%S'),
                'predicted_power': _safe_round(extended_power)
            })

    return results


def _fallback_predict(hours=6):
    df = load_dataset()
    if len(df) == 0:
        return []

    last_ts = df['timestamp'].iloc[-1]
    interval = timedelta(minutes=15)
    count = hours * 4
    last_power = float(df['Active_Power'].iloc[-1])

    results = []
    for i in range(count):
        ts = last_ts + interval * (i + 1)
        results.append({
            'timestamp': ts.strftime('%Y-%m-%d %H:%M:%S'),
            'predicted_power': _safe_round(last_power)
        })
    return results


def get_realtime_data(hours=None, start_date=None, end_date=None):
    df = load_dataset()
    if len(df) == 0:
        return []

    if start_date:
        start_ts = pd.to_datetime(start_date)
        df = df[df['timestamp'] >= start_ts]
    if end_date:
        end_ts = pd.to_datetime(end_date + ' 23:59:59')
        df = df[df['timestamp'] <= end_ts]
    if not start_date and not end_date and hours:
        latest_ts = df['timestamp'].iloc[-1]
        start_ts = latest_ts - timedelta(hours=hours)
        df = df[df['timestamp'] >= start_ts]

    results = []
    for _, row in df.iterrows():
        results.append({
            'timestamp': row['timestamp'].strftime('%Y-%m-%d %H:%M:%S'),
            'active_power': _safe_round(row['Active_Power']),
            'radiation': _safe_round(row['Global_Horizontal_Radiation']),
            'temperature': _safe_round(row['Weather_Temperature_Celsius']),
            'humidity': _safe_round(row['Weather_Relative_Humidity']),
            'wind_speed': _safe_round(row['Wind_Speed']),
            'wind_direction': _safe_round(row['Wind_Direction']),
            'rainfall': _safe_round(row['Weather_Daily_Rainfall'], 4)
        })

    return results


def get_comparison_data(hours=None, start_date=None, end_date=None):
    df = load_dataset()
    if len(df) == 0:
        return [], []

    try:
        model, scaler_params, device = get_model()
    except Exception:
        model = None

    if start_date:
        start_ts = pd.to_datetime(start_date)
        df = df[df['timestamp'] >= start_ts]
    if end_date:
        end_ts = pd.to_datetime(end_date + ' 23:59:59')
        df = df[df['timestamp'] <= end_ts]
    elif not start_date and hours:
        latest_ts = df['timestamp'].iloc[-1]
        start_ts = latest_ts - timedelta(hours=hours)
        df = df[df['timestamp'] >= start_ts]

    filtered = df.copy().reset_index(drop=True)

    actual_data = []
    for _, row in filtered.iterrows():
        actual_data.append({
            'timestamp': row['timestamp'].strftime('%Y-%m-%d %H:%M:%S'),
            'active_power': _safe_round(row['Active_Power'])
        })

    predicted_data = []

    if model is not None and len(filtered) >= 96:
        feature_columns = scaler_params['feature_columns']
        mean_vals = np.array(scaler_params['mean'])
        std_vals = np.array(scaler_params['std'])
        seq_len = scaler_params.get('seq_len', 96)

        data_values = filtered[feature_columns].values.astype(np.float32)
        data_values = np.nan_to_num(data_values, nan=0.0)
        normalized_all = (data_values - mean_vals) / (std_vals + 1e-8)
        normalized_all = np.nan_to_num(normalized_all, nan=0.0)

        with torch.no_grad():
            for i, (_, row) in enumerate(filtered.iterrows()):
                if i >= seq_len:
                    x = torch.FloatTensor(normalized_all[i - seq_len:i]).unsqueeze(0).to(device)
                    output = model(x)
                    pred = output.cpu().numpy()[0, 0, 0]
                    pred_real = max(float(pred * std_vals[0] + mean_vals[0]), 0)
                else:
                    pred_real = _safe_round(row['Active_Power'])

                predicted_data.append({
                    'timestamp': row['timestamp'].strftime('%Y-%m-%d %H:%M:%S'),
                    'predicted_power': _safe_round(pred_real)
                })
    else:
        for item in actual_data:
            predicted_data.append({
                'timestamp': item['timestamp'],
                'predicted_power': item['active_power']
            })

    return actual_data, predicted_data


def check_alarms():
    from backend.models import db, AlarmRecord
    from backend.config import Config

    df = load_dataset()
    if len(df) < 96:
        return []

    try:
        model, scaler_params, device = get_model()
    except Exception:
        return []

    feature_columns = scaler_params['feature_columns']
    mean_vals = np.array(scaler_params['mean'])
    std_vals = np.array(scaler_params['std'])
    seq_len = scaler_params.get('seq_len', 96)

    data_values = df[feature_columns].values.astype(np.float32)
    data_values = np.nan_to_num(data_values, nan=0.0)
    normalized_all = (data_values - mean_vals) / (std_vals + 1e-8)
    normalized_all = np.nan_to_num(normalized_all, nan=0.0)

    new_alarms = []
    check_count = 4

    with torch.no_grad():
        for i in range(check_count):
            idx = len(df) - check_count + i
            if idx < seq_len:
                continue

            row = df.iloc[idx]
            ts = row['timestamp']
            active_power = float(row['Active_Power'])
            radiation = float(row['Global_Horizontal_Radiation'])
            temperature = float(row['Weather_Temperature_Celsius'])

            x = torch.FloatTensor(normalized_all[idx - seq_len:idx]).unsqueeze(0).to(device)
            output = model(x)
            pred_power = float(output.cpu().numpy()[0, 0, 0] * std_vals[0] + mean_vals[0])
            pred_power = max(pred_power, 0)

            if radiation > Config.ALARM_RADIATION_THRESHOLD and active_power < Config.ALARM_THRESHOLD_ZERO_WHEN_SUNNY:
                existing = AlarmRecord.query.filter_by(timestamp=ts, alarm_type='zero_output').first()
                if not existing:
                    alarm = AlarmRecord(
                        alarm_type='zero_output',
                        level='critical',
                        message=f'高辐射零输出: 辐射{radiation:.0f}W/m2, 实际功率仅{active_power:.2f}kW',
                        timestamp=ts,
                        active_power=active_power,
                        predicted_power=pred_power,
                        radiation=radiation,
                        temperature=temperature
                    )
                    db.session.add(alarm)
                    new_alarms.append(alarm)

            if pred_power > 5 and active_power > 0:
                deviation = abs(active_power - pred_power) / pred_power
                if deviation > Config.ALARM_THRESHOLD_HIGH_DEVIATION:
                    existing = AlarmRecord.query.filter_by(timestamp=ts, alarm_type='high_deviation').first()
                    if not existing:
                        level = 'warning' if deviation < 0.8 else 'critical'
                        alarm = AlarmRecord(
                            alarm_type='high_deviation',
                            level=level,
                            message=f'功率偏差过大: 预测{pred_power:.2f}kW, 实际{active_power:.2f}kW, 偏差{deviation*100:.1f}%',
                            timestamp=ts,
                            active_power=active_power,
                            predicted_power=pred_power,
                            radiation=radiation,
                            temperature=temperature
                        )
                        db.session.add(alarm)
                        new_alarms.append(alarm)

    if new_alarms:
        db.session.commit()

    return [a.to_dict() for a in new_alarms]
