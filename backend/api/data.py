"""
数据API - 实时数据、预测数据、对比数据
"""
import io
import csv
from flask import Blueprint, request, jsonify, send_file
from backend.utils.auth import login_required
from backend.utils.data_service import (
    predict_future, get_realtime_data, get_comparison_data,
    load_dataset, check_alarms
)
from backend.models import db, OperationLog

data_bp = Blueprint('data', __name__, url_prefix='/api/data')


@data_bp.route('/realtime', methods=['GET'])
@login_required
def realtime():
    """获取实时发电数据"""
    hours = request.args.get('hours', type=int)
    start_date = request.args.get('start_date', '')
    end_date = request.args.get('end_date', '')

    if hours:
        hours = min(max(hours, 1), 168)
        data = get_realtime_data(hours=hours)
    elif start_date or end_date:
        data = get_realtime_data(start_date=start_date, end_date=end_date)
    else:
        data = get_realtime_data(hours=24)

    try:
        return jsonify({'code': 200, 'data': data})
    except Exception as e:
        return jsonify({'code': 500, 'message': f'获取实时数据失败: {str(e)}'})


@data_bp.route('/predict', methods=['GET'])
@login_required
def predict():
    """获取预测发电数据"""
    hours = request.args.get('hours', 6, type=int)
    hours = min(max(hours, 1), 24)  # 限制1-24小时

    try:
        data = predict_future(hours=hours)
        return jsonify({'code': 200, 'data': data})
    except Exception as e:
        return jsonify({'code': 500, 'message': f'获取预测数据失败: {str(e)}'})


@data_bp.route('/comparison', methods=['GET'])
@login_required
def comparison():
    """获取实际与预测对比数据"""
    hours = request.args.get('hours', type=int)
    start_date = request.args.get('start_date', '')
    end_date = request.args.get('end_date', '')

    try:
        if hours:
            hours = min(max(hours, 1), 48)
            actual, predicted = get_comparison_data(hours=hours)
        elif start_date or end_date:
            if not start_date or not end_date:
                return jsonify({'code': 400, 'message': '日期范围需要同时提供开始和结束日期'})
            actual, predicted = get_comparison_data(start_date=start_date, end_date=end_date)
        else:
            actual, predicted = get_comparison_data(hours=6)

        if len(actual) == 0:
            return jsonify({'code': 404, 'message': '指定日期范围内没有数据，请选择2014年的日期'})

        return jsonify({
            'code': 200,
            'data': {
                'actual': actual,
                'predicted': predicted
            }
        })
    except Exception as e:
        return jsonify({'code': 500, 'message': f'获取对比数据失败: {str(e)}'})


@data_bp.route('/dashboard', methods=['GET'])
@login_required
def dashboard():
    """获取仪表盘汇总数据"""
    try:
        df = load_dataset()
        latest_row = df.iloc[-1]

        # 当前发电功率
        current_power = round(float(latest_row['Active_Power']), 2)

        # 今日发电量估算（简化：取今天所有15分钟间隔的功率*0.25h累加）
        today = latest_row['timestamp'].normalize()
        today_data = df[df['timestamp'] >= today]
        today_energy = round(float(today_data['Active_Power'].sum() * 0.25 / 1000), 2)  # kWh -> MWh

        # 总装机容量参考
        max_power = round(float(df['Active_Power'].max()), 2)

        # 当前辐照度
        current_radiation = round(float(latest_row['Global_Horizontal_Radiation']), 2)

        # 当前温度
        current_temp = round(float(latest_row['Weather_Temperature_Celsius']), 2)

        # 今日最高功率
        today_max_power = round(float(today_data['Active_Power'].max()), 2) if len(today_data) > 0 else 0

        # 预测数据
        predictions = predict_future(hours=6)

        return jsonify({
            'code': 200,
            'data': {
                'current_power': current_power,
                'today_energy': today_energy,
                'max_power': max_power,
                'current_radiation': current_radiation,
                'current_temp': current_temp,
                'today_max_power': today_max_power,
                'latest_timestamp': latest_row['timestamp'].strftime('%Y-%m-%d %H:%M:%S'),
                'predictions': predictions
            }
        })
    except Exception as e:
        return jsonify({'code': 500, 'message': f'获取仪表盘数据失败: {str(e)}'})


@data_bp.route('/history', methods=['GET'])
@login_required
def history():
    """获取历史数据（分页）"""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 50, type=int)
    start_date = request.args.get('start_date', '')
    end_date = request.args.get('end_date', '')

    try:
        df = load_dataset()

        if start_date:
            df = df[df['timestamp'] >= start_date]
        if end_date:
            df = df[df['timestamp'] <= end_date + ' 23:59:59']

        total = len(df)
        start = (page - 1) * per_page
        end = start + per_page
        page_data = df.iloc[start:end]

        records = []
        for _, row in page_data.iterrows():
            records.append({
                'timestamp': row['timestamp'].strftime('%Y-%m-%d %H:%M:%S'),
                'active_power': round(float(row['Active_Power']), 2),
                'radiation': round(float(row['Global_Horizontal_Radiation']), 2),
                'temperature': round(float(row['Weather_Temperature_Celsius']), 2),
                'humidity': round(float(row['Weather_Relative_Humidity']), 2),
                'wind_speed': round(float(row['Wind_Speed']), 2),
                'wind_direction': round(float(row['Wind_Direction']), 2),
                'rainfall': round(float(row['Weather_Daily_Rainfall']), 4)
            })

        return jsonify({
            'code': 200,
            'data': {
                'records': records,
                'total': total,
                'page': page,
                'per_page': per_page,
                'pages': (total + per_page - 1) // per_page
            }
        })
    except Exception as e:
        return jsonify({'code': 500, 'message': f'获取历史数据失败: {str(e)}'})


@data_bp.route('/export', methods=['GET'])
@login_required
def export_csv():
    """导出数据为CSV"""
    start_date = request.args.get('start_date', '')
    end_date = request.args.get('end_date', '')
    export_type = request.args.get('type', 'history')  # history / comparison

    try:
        df = load_dataset()

        if start_date:
            df = df[df['timestamp'] >= start_date]
        if end_date:
            df = df[df['timestamp'] <= end_date + ' 23:59:59']

        if export_type == 'comparison':
            actual, predicted = get_comparison_data(hours=24)
            # 合并对比数据
            output = io.StringIO()
            writer = csv.writer(output)
            writer.writerow(['时间', '实际功率(kW)', '预测功率(kW)', '偏差(kW)', '偏差率(%)'])
            for a, p in zip(actual, predicted):
                diff = a['active_power'] - p['predicted_power']
                rate = (diff / p['predicted_power'] * 100) if p['predicted_power'] > 0 else 0
                writer.writerow([a['timestamp'], a['active_power'], p['predicted_power'],
                               round(diff, 2), round(rate, 2)])
        else:
            output = io.StringIO()
            writer = csv.writer(output)
            writer.writerow(['时间', '有功功率(kW)', '水平总辐射(W/m2)', '温度(°C)',
                           '相对湿度(%)', '风速(m/s)', '风向(°)', '日降雨量(mm)'])
            for _, row in df.iterrows():
                writer.writerow([
                    row['timestamp'].strftime('%Y-%m-%d %H:%M:%S'),
                    round(float(row['Active_Power']), 2),
                    round(float(row['Global_Horizontal_Radiation']), 2),
                    round(float(row['Weather_Temperature_Celsius']), 2),
                    round(float(row['Weather_Relative_Humidity']), 2),
                    round(float(row['Wind_Speed']), 2),
                    round(float(row['Wind_Direction']), 2),
                    round(float(row['Weather_Daily_Rainfall']), 4)
                ])

        output.seek(0)
        byte_output = io.BytesIO()
        byte_output.write(output.getvalue().encode('utf-8-sig'))
        byte_output.seek(0)

        filename = f'solar_{export_type}_{start_date or "all"}_{end_date or "all"}.csv'

        # 记录日志
        log = OperationLog(
            username=request.current_user.get('username'),
            action='导出数据',
            detail=f'导出{export_type}数据: {filename}',
            ip_address=request.remote_addr
        )
        db.session.add(log)
        db.session.commit()

        return send_file(byte_output, mimetype='text/csv',
                        as_attachment=True, download_name=filename)
    except Exception as e:
        return jsonify({'code': 500, 'message': f'导出失败: {str(e)}'})
