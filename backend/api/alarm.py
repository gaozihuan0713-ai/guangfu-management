"""
报警API - 故障报警查询、确认、统计
"""
from flask import Blueprint, request, jsonify
from datetime import datetime
from backend.models import db, AlarmRecord, OperationLog
from backend.utils.auth import login_required, admin_required
from backend.utils.data_service import check_alarms

alarm_bp = Blueprint('alarm', __name__, url_prefix='/api/alarm')


@alarm_bp.route('/list', methods=['GET'])
@login_required
def get_alarms():
    """获取报警列表"""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    status = request.args.get('status', '')
    level = request.args.get('level', '')
    alarm_type = request.args.get('alarm_type', '')
    start_date = request.args.get('start_date', '')
    end_date = request.args.get('end_date', '')

    query = AlarmRecord.query

    if status:
        query = query.filter(AlarmRecord.status == status)
    if level:
        query = query.filter(AlarmRecord.level == level)
    if alarm_type:
        query = query.filter(AlarmRecord.alarm_type == alarm_type)
    if start_date:
        query = query.filter(AlarmRecord.timestamp >= start_date)
    if end_date:
        query = query.filter(AlarmRecord.timestamp <= end_date + ' 23:59:59')

    query = query.order_by(AlarmRecord.timestamp.desc())
    total = query.count()
    alarms = query.offset((page - 1) * per_page).limit(per_page).all()

    return jsonify({
        'code': 200,
        'data': {
            'records': [a.to_dict() for a in alarms],
            'total': total,
            'page': page,
            'per_page': per_page,
            'pages': (total + per_page - 1) // per_page
        }
    })


@alarm_bp.route('/stats', methods=['GET'])
@login_required
def alarm_stats():
    """报警统计"""
    # 各状态数量
    unacked = AlarmRecord.query.filter_by(status='unacked').count()
    acked = AlarmRecord.query.filter_by(status='acked').count()
    resolved = AlarmRecord.query.filter_by(status='resolved').count()

    # 各级别数量
    critical = AlarmRecord.query.filter_by(level='critical').count()
    warning = AlarmRecord.query.filter_by(level='warning').count()
    info = AlarmRecord.query.filter_by(level='info').count()

    # 各类型数量
    zero_output = AlarmRecord.query.filter_by(alarm_type='zero_output').count()
    high_deviation = AlarmRecord.query.filter_by(alarm_type='high_deviation').count()

    # 今日新增
    today = datetime.now().strftime('%Y-%m-%d')
    today_count = AlarmRecord.query.filter(AlarmRecord.timestamp >= today).count()

    return jsonify({
        'code': 200,
        'data': {
            'by_status': {'unacked': unacked, 'acked': acked, 'resolved': resolved},
            'by_level': {'critical': critical, 'warning': warning, 'info': info},
            'by_type': {'zero_output': zero_output, 'high_deviation': high_deviation},
            'today_count': today_count,
            'total': unacked + acked + resolved
        }
    })


@alarm_bp.route('/check', methods=['POST'])
@login_required
def run_alarm_check():
    """手动触发报警检测"""
    try:
        new_alarms = check_alarms()
        return jsonify({
            'code': 200,
            'message': f'检测完成，发现{len(new_alarms)}条新报警',
            'data': new_alarms
        })
    except Exception as e:
        return jsonify({'code': 500, 'message': f'报警检测失败: {str(e)}'})


@alarm_bp.route('/<int:alarm_id>/ack', methods=['POST'])
@login_required
def ack_alarm(alarm_id):
    """确认报警"""
    alarm = AlarmRecord.query.get(alarm_id)
    if alarm is None:
        return jsonify({'code': 404, 'message': '报警记录不存在'})

    alarm.status = 'acked'
    alarm.acked_by = request.current_user.get('username')
    alarm.acked_at = datetime.now()

    log = OperationLog(
        username=request.current_user.get('username'),
        action='确认报警',
        detail=f'确认报警ID={alarm_id}: {alarm.message}',
        ip_address=request.remote_addr
    )
    db.session.add(log)
    db.session.commit()

    return jsonify({'code': 200, 'message': '报警已确认', 'data': alarm.to_dict()})


@alarm_bp.route('/batch-ack', methods=['POST'])
@login_required
def batch_ack_alarms():
    """批量确认报警"""
    data = request.get_json()
    ids = data.get('ids', [])

    if not ids:
        return jsonify({'code': 400, 'message': '请选择要确认的报警'})

    count = 0
    username = request.current_user.get('username')
    for alarm_id in ids:
        alarm = AlarmRecord.query.get(alarm_id)
        if alarm and alarm.status == 'unacked':
            alarm.status = 'acked'
            alarm.acked_by = username
            alarm.acked_at = datetime.now()
            count += 1

    db.session.commit()

    return jsonify({'code': 200, 'message': f'已确认{count}条报警'})


@alarm_bp.route('/<int:alarm_id>/resolve', methods=['POST'])
@login_required
def resolve_alarm(alarm_id):
    """解除报警"""
    alarm = AlarmRecord.query.get(alarm_id)
    if alarm is None:
        return jsonify({'code': 404, 'message': '报警记录不存在'})

    alarm.status = 'resolved'
    alarm.acked_by = request.current_user.get('username')
    alarm.acked_at = datetime.now()

    db.session.commit()

    return jsonify({'code': 200, 'message': '报警已解除', 'data': alarm.to_dict()})
