"""报表导出API"""
import io
import os
import pandas as pd
from datetime import datetime
from flask import Blueprint, request, jsonify, send_file
from backend import db
from backend.models.prediction_log import PredictionLog
from backend.models.alarm import Alarm
from backend.utils.auth import login_required

report_bp = Blueprint('report', __name__)


def get_dataset():
    """加载数据集"""
    data_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), '..', '数据集')
    csv_path = os.path.join(data_dir, '数据集_6-18.csv')
    if not os.path.exists(csv_path):
        return None
    df = pd.read_csv(csv_path)
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    return df


@report_bp.route('/daily', methods=['GET'])
@login_required
def daily_report():
    """生成日报表"""
    date_str = request.args.get('date', datetime.now().strftime('%Y-%m-%d'))

    df = get_dataset()
    if df is None:
        return jsonify({'code': 500, 'msg': '数据集未找到'}), 500

    target_date = pd.to_datetime(date_str)
    day_data = df[df['timestamp'].dt.date == target_date.date()]

    if day_data.empty:
        return jsonify({'code': 404, 'msg': f'{date_str} 无数据'}), 404

    # 统计信息
    total_energy = day_data['Active_Power'].sum() * 0.25  # 15分钟间隔，换算kWh
    avg_power = day_data['Active_Power'].mean()
    max_power = day_data['Active_Power'].max()
    min_power = day_data['Active_Power'].min()
    avg_radiation = day_data['Global_Horizontal_Radiation'].mean()
    avg_temp = day_data['Weather_Temperature_Celsius'].mean()

    # 按小时汇总
    hourly = day_data.set_index('timestamp').resample('1h').agg({
        'Active_Power': 'mean',
        'Global_Horizontal_Radiation': 'mean',
        'Weather_Temperature_Celsius': 'mean'
    }).round(4)

    hourly_data = []
    for idx, row in hourly.iterrows():
        hourly_data.append({
            'time': idx.strftime('%H:%M'),
            'avg_power': round(float(row['Active_Power']), 4),
            'avg_radiation': round(float(row['Global_Horizontal_Radiation']), 2),
            'avg_temp': round(float(row['Weather_Temperature_Celsius']), 1)
        })

    return jsonify({
        'code': 200,
        'data': {
            'date': date_str,
            'total_energy_kwh': round(total_energy, 2),
            'avg_power_kw': round(avg_power, 4),
            'max_power_kw': round(max_power, 4),
            'min_power_kw': round(min_power, 4),
            'avg_radiation': round(avg_radiation, 2),
            'avg_temperature': round(avg_temp, 1),
            'hourly_data': hourly_data
        }
    })


@report_bp.route('/monthly', methods=['GET'])
@login_required
def monthly_report():
    """生成月报表"""
    month_str = request.args.get('month', datetime.now().strftime('%Y-%m'))

    df = get_dataset()
    if df is None:
        return jsonify({'code': 500, 'msg': '数据集未找到'}), 500

    target_month = pd.to_datetime(month_str + '-01')
    month_data = df[(df['timestamp'].dt.year == target_month.year) &
                    (df['timestamp'].dt.month == target_month.month)]

    if month_data.empty:
        return jsonify({'code': 404, 'msg': f'{month_str} 无数据'}), 404

    # 按日汇总
    daily = month_data.set_index('timestamp').resample('1D').agg({
        'Active_Power': ['mean', 'max', 'sum'],
        'Global_Horizontal_Radiation': 'mean',
        'Weather_Temperature_Celsius': 'mean'
    }).round(4)

    daily_data = []
    for idx, row in daily.iterrows():
        daily_data.append({
            'date': idx.strftime('%Y-%m-%d'),
            'avg_power': round(float(row[('Active_Power', 'mean')]), 4),
            'max_power': round(float(row[('Active_Power', 'max')]), 4),
            'total_energy': round(float(row[('Active_Power', 'sum')]) * 0.25, 2),
            'avg_radiation': round(float(row[('Global_Horizontal_Radiation', 'mean')]), 2),
            'avg_temp': round(float(row[('Weather_Temperature_Celsius', 'mean')]), 1)
        })

    total_energy = month_data['Active_Power'].sum() * 0.25

    return jsonify({
        'code': 200,
        'data': {
            'month': month_str,
            'total_energy_kwh': round(total_energy, 2),
            'avg_power_kw': round(month_data['Active_Power'].mean(), 4),
            'days': daily_data
        }
    })


@report_bp.route('/export/excel', methods=['GET'])
@login_required
def export_excel():
    """导出Excel报表"""
    report_type = request.args.get('type', 'daily')  # daily/monthly/alarm/prediction
    date_str = request.args.get('date', datetime.now().strftime('%Y-%m-%d'))

    output = io.BytesIO()

    if report_type == 'daily':
        df_data = get_dataset()
        if df_data is None:
            return jsonify({'code': 500, 'msg': '数据集未找到'}), 500
        target_date = pd.to_datetime(date_str)
        day_data = df_data[df_data['timestamp'].dt.date == target_date.date()]
        if day_data.empty:
            return jsonify({'code': 404, 'msg': '无数据'}), 404
        export_df = day_data[['timestamp', 'Active_Power', 'Global_Horizontal_Radiation',
                               'Weather_Temperature_Celsius', 'Weather_Relative_Humidity',
                               'Wind_Speed']].copy()
        export_df.columns = ['时间', '有功功率(kW)', '水平面辐射(W/m²)',
                              '温度(℃)', '湿度(%)', '风速(m/s)']
        export_df['时间'] = export_df['时间'].dt.strftime('%Y-%m-%d %H:%M')

    elif report_type == 'monthly':
        df_data = get_dataset()
        if df_data is None:
            return jsonify({'code': 500, 'msg': '数据集未找到'}), 500
        month_str = date_str[:7]
        target_month = pd.to_datetime(month_str + '-01')
        month_data = df_data[(df_data['timestamp'].dt.year == target_month.year) &
                             (df_data['timestamp'].dt.month == target_month.month)]
        if month_data.empty:
            return jsonify({'code': 404, 'msg': '无数据'}), 404
        daily = month_data.set_index('timestamp').resample('1D').agg({
            'Active_Power': ['mean', 'max', 'sum'],
            'Global_Horizontal_Radiation': 'mean',
            'Weather_Temperature_Celsius': 'mean'
        })
        export_df = pd.DataFrame({
            '日期': daily.index.strftime('%Y-%m-%d'),
            '平均功率(kW)': daily[('Active_Power', 'mean')].round(4).values,
            '最大功率(kW)': daily[('Active_Power', 'max')].round(4).values,
            '发电量(kWh)': (daily[('Active_Power', 'sum')].values * 0.25).round(2),
            '平均辐射(W/m²)': daily[('Global_Horizontal_Radiation', 'mean')].round(2).values,
            '平均温度(℃)': daily[('Weather_Temperature_Celsius', 'mean')].round(1).values
        })

    elif report_type == 'alarm':
        alarms = Alarm.query.order_by(Alarm.created_at.desc()).all()
        export_df = pd.DataFrame([a.to_dict() for a in alarms])
        if export_df.empty:
            export_df = pd.DataFrame(columns=['id', 'alarm_type', 'level', 'message',
                                               'device', 'status', 'created_at', 'resolved_at', 'resolved_by'])
        export_df.columns = ['ID', '告警类型', '告警级别', '告警信息',
                              '设备', '状态', '创建时间', '解决时间', '处理人']

    elif report_type == 'prediction':
        logs = PredictionLog.query.order_by(PredictionLog.predict_time.desc()).limit(500).all()
        export_df = pd.DataFrame([l.to_dict() for l in logs])
        if export_df.empty:
            export_df = pd.DataFrame(columns=['id', 'predict_time', 'predicted_power',
                                               'actual_power', 'model_version', 'created_at'])
        export_df.columns = ['ID', '预测时间', '预测功率(kW)', '实际功率(kW)',
                              '模型版本', '创建时间']
    else:
        return jsonify({'code': 400, 'msg': '不支持的报表类型'}), 400

    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        export_df.to_excel(writer, index=False, sheet_name='报表数据')

    output.seek(0)
    filename = f'solar_report_{report_type}_{date_str.replace("-", "")}.xlsx'

    return send_file(
        output,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        as_attachment=True,
        download_name=filename
    )
